"""fetch_polyhaven_albedo — download CC0 Poly Haven albedo maps for a tile LoRA.

Stage 0 of the `mat_tile` dataset (Phase TX, see datasets/tile_loras_spec.md).
Poly Haven assets are ALL CC0, so the downloaded albedo (Diffuse) maps are
license-clean for shippable game textures.

It hits the public Poly Haven API (no key needed):
    GET https://api.polyhaven.com/assets?type=textures   -> asset catalogue
    GET https://api.polyhaven.com/files/<asset_id>        -> per-asset file URLs

and pulls the **Diffuse** map (the flat colour surface — NOT normal/roughness) at
a chosen resolution/format for a balanced spread of material families. Writes the
images to <out> and a provenance JSON (<out>/_polyhaven_provenance.json) recording
slug -> name -> url -> CC0 -> family, which feeds the dataset manifest.

Stdlib only (urllib). Run with any Python 3.10+.

Usage:
    python scripts/train_lora/fetch_polyhaven_albedo.py \\
        --out E:/ai-training/_raw/mat_tile --per-family 4 --res 1k
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

API = "https://api.polyhaven.com"

# Material families -> substrings matched against an asset's categories+tags+name.
# Order matters: an asset is claimed by the first family it matches (deduped after).
FAMILIES: dict[str, list[str]] = {
    "brick": ["brick"],
    "cobblestone": ["cobblestone", "cobble"],
    "stone": ["rock", "stone", "cliff"],
    "wood": ["wood", "plank", "bark"],
    "concrete": ["concrete", "plaster"],
    "metal": ["metal", "rust", "steel"],
    "fabric": ["fabric", "leather", "denim", "wool"],
    "dirt": ["dirt", "mud", "soil", "ground"],
    "sand": ["sand", "desert"],
    "gravel": ["gravel"],
    "grass": ["grass"],
    "pavement": ["pavement", "paving", "paver", "tiles", "cobblestone floor"],
}


def http_json(url: str, retries: int = 4) -> dict:
    last = ""
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "comfyui-toolchain/tx"})
            with urllib.request.urlopen(req, timeout=40) as r:
                return json.loads(r.read())
        except (urllib.error.URLError, OSError, json.JSONDecodeError) as e:
            last = str(e)
            time.sleep(2 * (attempt + 1))
    raise RuntimeError(f"GET {url} failed after {retries}: {last[:200]}")


def download(url: str, dest: Path, retries: int = 4) -> int:
    last = ""
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "comfyui-toolchain/tx"})
            with urllib.request.urlopen(req, timeout=120) as r:
                blob = r.read()
            dest.write_bytes(blob)
            return len(blob)
        except (urllib.error.URLError, OSError) as e:
            last = str(e)
            time.sleep(2 * (attempt + 1))
    raise RuntimeError(f"download {url} failed after {retries}: {last[:200]}")


def humanize_material(name: str, family: str) -> str:
    """A short caption-ready material phrase from the Poly Haven display name."""
    # drop trailing version numbers ("Red Brick 03" -> "red brick")
    cleaned = re.sub(r"\s+\d+\s*$", "", name).strip().lower()
    return cleaned or family


def select_assets(catalogue: dict, per_family: int) -> list[dict]:
    """Pick up to `per_family` assets per family, deduped, deterministic order."""
    claimed: set[str] = set()
    picked: list[dict] = []
    for family, keys in FAMILIES.items():
        hits: list[tuple[str, dict]] = []
        for slug, meta in catalogue.items():
            if slug in claimed:
                continue
            hay = " ".join(
                [slug, meta.get("name", "")]
                + list(meta.get("categories", []))
                + list(meta.get("tags", []))
            ).lower()
            if any(k in hay for k in keys):
                hits.append((slug, meta))
        hits.sort(key=lambda x: x[0])
        for slug, meta in hits[:per_family]:
            claimed.add(slug)
            picked.append({
                "slug": slug,
                "name": meta.get("name", slug),
                "family": family,
                "material": humanize_material(meta.get("name", slug), family),
            })
    return picked


def diffuse_url(files: dict, res: str, fmt: str) -> str | None:
    """Find the Diffuse map URL at the requested res/fmt, with graceful fallback."""
    for key in ("Diffuse", "diffuse", "diff", "albedo", "col", "Color"):
        node = files.get(key)
        if not isinstance(node, dict):
            continue
        res_node = node.get(res) or next(iter(node.values()), None)
        if not isinstance(res_node, dict):
            continue
        fmt_node = res_node.get(fmt) or res_node.get("jpg") or res_node.get("png")
        if isinstance(fmt_node, dict) and fmt_node.get("url"):
            return fmt_node["url"]
    return None


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Download CC0 Poly Haven albedo maps for a tile LoRA.")
    ap.add_argument("--out", required=True, help="Output dir for the raw albedo images.")
    ap.add_argument("--per-family", type=int, default=4, help="Max assets per material family.")
    ap.add_argument("--res", default="1k", help="Texture resolution (1k/2k/4k).")
    ap.add_argument("--fmt", default="jpg", choices=("jpg", "png"), help="Image format.")
    ap.add_argument("--limit", type=int, default=None, help="Optional hard cap on total downloads.")
    args = ap.parse_args(argv)

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    print("Fetching Poly Haven texture catalogue ...")
    catalogue = http_json(f"{API}/assets?type=textures")
    picks = select_assets(catalogue, args.per_family)
    if args.limit:
        picks = picks[: args.limit]
    print(f"Selected {len(picks)} assets across {len(FAMILIES)} families.")

    provenance: list[dict] = []
    ok = 0
    for i, p in enumerate(picks, 1):
        try:
            files = http_json(f"{API}/files/{p['slug']}")
            url = diffuse_url(files, args.res, args.fmt)
            if not url:
                print(f"  ! {p['slug']}: no diffuse map", file=sys.stderr)
                continue
            dest = out / f"{p['slug']}_diff_{args.res}.{args.fmt}"
            n = download(url, dest)
            ok += 1
            rec = {**p, "url": url, "file": dest.name, "bytes": n, "license": "CC0"}
            provenance.append(rec)
            print(f"  + [{i}/{len(picks)}] {p['family']:11s} {p['slug']:28s} {n//1024:5d} KB")
        except RuntimeError as e:
            print(f"  ! {p['slug']}: {e}", file=sys.stderr)

    (out / "_polyhaven_provenance.json").write_text(
        json.dumps({"source": "polyhaven.com", "license": "CC0",
                    "count": ok, "assets": provenance}, indent=2),
        encoding="utf-8",
    )
    print(f"\nDownloaded {ok}/{len(picks)} albedo maps -> {out.resolve()}")
    print(f"Provenance -> {(out / '_polyhaven_provenance.json').resolve()}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
