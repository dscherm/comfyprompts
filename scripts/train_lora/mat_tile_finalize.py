"""Captions + manifest for the mat_tile dataset (TX1, runs after prep_dataset.py).

Reads the fetcher's _selection.json, writes one short tag-style caption per
prepped image — 'mat_tile, <material>, seamless texture, even top-down lighting'
(deliberately NOT verbose VLM captions: flat material surfaces, short natural
tags suit SDXL) — and the CC0 provenance manifest the acceptance criteria name.

Usage:
    python scripts/train_lora/mat_tile_finalize.py \\
        --selection E:/ai-training/datasets/mat_tile_raw/_selection.json \\
        --dataset E:/ai-training/datasets/mat_tile \\
        --manifest pipelines/tileset-ralph/loras/mat_tile/mat_tile_manifest.md
"""

from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path

CAPTION = "mat_tile, {family}, seamless texture, even top-down lighting"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--selection", type=Path, required=True)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    args = parser.parse_args()

    records = json.loads(args.selection.read_text())
    by_stem = {Path(r["file"]).stem: r for r in records}

    images = sorted(
        p for p in args.dataset.iterdir()
        if p.suffix.lower() in (".jpg", ".jpeg", ".png", ".webp")
    )
    captioned = []
    orphans = []
    for img in images:
        rec = by_stem.get(img.stem)
        if rec is None:
            orphans.append(img.name)
            continue
        img.with_suffix(".txt").write_text(CAPTION.format(family=rec["family"]) + "\n")
        captioned.append(rec | {"dataset_file": img.name})

    if orphans:
        raise SystemExit(f"ERROR: {len(orphans)} dataset images missing from selection "
                         f"metadata (first: {orphans[:3]}) — captions would be wrong")

    families = sorted({r["family"] for r in captioned})
    lines = [
        "# mat_tile dataset manifest",
        "",
        f"Built {date.today().isoformat()} (TX1). {len(captioned)} images, "
        f"{len(families)} material families: {', '.join(families)}.",
        "",
        "All sources are Poly Haven **CC0** albedo/diffuse maps (unlit by nature —",
        "the 'even top-down lighting' caption describes the rendered look SDXL",
        "should associate with the trigger). Prep: scripts/train_lora/prep_dataset.py",
        "--max-edge 1024, RGB. Captions: short tag style,",
        f"`{CAPTION.format(family='<material>')}`.",
        "",
        "| dataset file | material | Poly Haven slug | license | source |",
        "|---|---|---|---|---|",
    ]
    for r in sorted(captioned, key=lambda r: (r["family"], r["slug"])):
        lines.append(
            f"| {r['dataset_file']} | {r['family']} | {r['slug']} | {r['license']} "
            f"| {r['source']} |"
        )
    args.manifest.parent.mkdir(parents=True, exist_ok=True)
    args.manifest.write_text("\n".join(lines) + "\n")
    print(f"{len(captioned)} captions written; manifest at {args.manifest}")


if __name__ == "__main__":
    main()
