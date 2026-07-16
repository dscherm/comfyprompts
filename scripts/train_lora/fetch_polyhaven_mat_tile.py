"""Fetch CC0 Poly Haven albedo maps for the mat_tile SDXL LoRA dataset (TX1).

Selects textures across the material families the tile LoRA must cover, downloads
each asset's Diffuse map (2k JPG — downscaled to 1024 by prep_dataset.py, cleaner
than native 1k), and writes selection metadata (slug, family, URL) for the caption
and manifest steps. Everything on Poly Haven is CC0 and seamless/tileable by
design; albedo maps are unlit, satisfying the "evenly lit" requirement.

Usage:
    python scripts/train_lora/fetch_polyhaven_mat_tile.py \\
        --out E:/ai-training/datasets/mat_tile_raw --per-family 5
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
import urllib.request
from pathlib import Path

API_ASSETS = "https://api.polyhaven.com/assets?type=textures"
API_FILES = "https://api.polyhaven.com/files/{slug}"

# family -> keywords matched against slug + categories + tags
FAMILIES: dict[str, list[str]] = {
    "brick": ["brick"],
    "stone": ["stone wall", "stone_wall", "rock wall", "stone"],
    "cobblestone": ["cobble", "paving", "pavement"],
    "wood": ["wood", "bark"],
    "planks": ["plank", "wood floor", "wood_floor", "parquet"],
    "metal": ["metal", "steel", "rust"],
    "concrete": ["concrete", "plaster"],
    "fabric": ["fabric", "cloth", "leather", "carpet"],
    "dirt": ["dirt", "mud", "soil"],
    "sand": ["sand", "gravel"],
    "grass": ["grass", "moss", "forest floor", "forest_floor"],
}


def _get_json(url: str) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": "comfyui-toolchain-tx1"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read().decode())


def _asset_text(slug: str, meta: dict) -> str:
    return " ".join(
        [slug.replace("_", " ")]
        + [c.lower() for c in meta.get("categories", [])]
        + [t.lower() for t in meta.get("tags", [])]
    )


def _pick(assets: dict, per_family: int) -> list[tuple[str, str]]:
    chosen: list[tuple[str, str]] = []
    used: set[str] = set()
    for family, keywords in FAMILIES.items():
        ranked = []
        for slug, meta in assets.items():
            if slug in used:
                continue
            text = _asset_text(slug, meta)
            score = sum(1 for kw in keywords if kw in text)
            if score:
                ranked.append((score, slug))
        ranked.sort(key=lambda x: (-x[0], x[1]))
        for _, slug in ranked[:per_family]:
            chosen.append((family, slug))
            used.add(slug)
    return chosen


def _diffuse_url(slug: str) -> str | None:
    files = _get_json(API_FILES.format(slug=slug))
    for key in ("Diffuse", "diffuse", "diff", "albedo", "Albedo", "Color"):
        node = files.get(key)
        if not node:
            continue
        for res in ("2k", "1k", "4k"):
            entry = node.get(res, {})
            fmt = entry.get("jpg") or entry.get("png")
            if fmt and fmt.get("url"):
                return fmt["url"]
    return None


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--per-family", type=int, default=5)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)

    print("Fetching Poly Haven texture index ...")
    assets = _get_json(API_ASSETS)
    print(f"  {len(assets)} texture assets available")

    chosen = _pick(assets, args.per_family)
    print(f"  selected {len(chosen)} across {len(FAMILIES)} families")

    records = []
    for i, (family, slug) in enumerate(chosen, start=1):
        url = _diffuse_url(slug)
        if not url:
            print(f"[{i}/{len(chosen)}] SKIP {slug} (no diffuse map)")
            continue
        safe = re.sub(r"[^A-Za-z0-9_-]", "_", slug)
        dest = args.out / f"{family}__{safe}.jpg"
        if not dest.exists():
            print(f"[{i}/{len(chosen)}] {family:<12} {slug} ...", end=" ", flush=True)
            req = urllib.request.Request(url, headers={"User-Agent": "comfyui-toolchain-tx1"})
            with urllib.request.urlopen(req, timeout=120) as resp:
                dest.write_bytes(resp.read())
            print(f"{dest.stat().st_size // 1024} KB")
            time.sleep(0.3)
        else:
            print(f"[{i}/{len(chosen)}] {family:<12} {slug} (cached)")
        records.append({
            "file": dest.name, "slug": slug, "family": family,
            "license": "CC0", "source": f"https://polyhaven.com/a/{slug}", "map_url": url,
        })

    meta_path = args.out / "_selection.json"
    meta_path.write_text(json.dumps(records, indent=1))
    print(f"\n{len(records)} maps downloaded; selection metadata at {meta_path}")
    if len(records) < 30:
        print("WARNING: fewer than 30 images — acceptance wants ~30-50", file=sys.stderr)


if __name__ == "__main__":
    main()
