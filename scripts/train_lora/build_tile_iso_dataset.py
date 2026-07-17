"""build_tile_iso_dataset — slice the CC0 isometric tile dataset (Task TI1).

Extracts individual isometric diamond tiles from the CC0 OpenGameArt "updated
grassland tileset (stylized)" by rubberduck (license-verified 2026-07-17,
tile_loras_spec.md §8). The pack's rendered sheets place each tile as a
gap-separated alpha blob, so connected-component labeling isolates single tiles.
Each tile is flattened onto a neutral grey background, padded to a square (to
preserve the 2:1 diamond shape without distortion at train time), and upscaled
to 512px. Then prep_dataset.py normalizes into E:/ai-training/datasets/tile_iso,
short captions + manifest are written.

Caption template (spec §8):
    tile_iso, <terrain> tile, isometric RPG tileset, diamond tile, even lighting

Run with the project venv (needs Pillow + scipy + numpy):
    "D:/Projects/ComfyUI/venv/Scripts/python.exe" scripts/train_lora/build_tile_iso_dataset.py
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage

HERE = Path(__file__).resolve().parent
STAGING = Path("E:/ai-training/datasets/tile_topdown_staging")
RAW = Path("E:/ai-training/_raw/tile_iso")
OUT = Path("E:/ai-training/datasets/tile_iso")
PREP = HERE / "prep_dataset.py"
BG = (128, 128, 128)  # neutral grey the model learns to place the diamond on
SRC_PAGE = "https://opengameart.org/content/updated-grassland-tileset-stylized"

# sheet stem -> (terrain family, caption phrase, blob filter, max tiles)
# filter: (min_w, max_w, min_h, max_h, min_area) — bbox of the diamond/object blob.
GROUND = (60, 200, 30, 110, 1800)   # a single flat diamond ground tile
OBJECT = (60, 640, 60, 320, 3200)   # a raised iso object (rock / cliff / structure)
SHEETS: list[tuple[str, str, str, tuple, int]] = [
    ("grass_tiles", "grass", "grass", GROUND, 6),
    ("dirt_tiles", "dirt", "dirt", GROUND, 6),
    ("sand_tiles", "sand", "sand", GROUND, 6),
    ("water_v01", "water", "water", (200, 900, 100, 500, 20000), 1),
    ("water_v02", "water", "water", (200, 900, 100, 500, 20000), 1),
    ("rock_cliffs", "rock", "rock", OBJECT, 8),
    ("grassland_2x2", "cliff", "grassy cliff", OBJECT, 6),
    ("grassland_1x1", "cliff", "grassy cliff", OBJECT, 4),
]


def phash(img: Image.Image) -> int:
    g = np.asarray(img.convert("L").resize((16, 16), Image.LANCZOS), dtype=float)
    return int(np.packbits(g > g.mean()).tobytes().hex(), 16)


def hamming(a: int, b: int) -> int:
    return bin(a ^ b).count("1")


def square_upscale(tile: Image.Image, size: int = 512) -> Image.Image:
    w, h = tile.size
    side = max(w, h)
    canvas = Image.new("RGB", (side, side), BG)
    canvas.paste(tile, ((side - w) // 2, (side - h) // 2))
    return canvas.resize((size, size), Image.LANCZOS)


def extract(stem: str, flt: tuple, cap: int) -> list[Image.Image]:
    im = Image.open(STAGING / f"grassland_tiles__{stem}.png").convert("RGBA")
    arr = np.array(im)
    mask = arr[:, :, 3] > 32
    lbl, n = ndimage.label(mask)
    objs = ndimage.find_objects(lbl)
    min_w, max_w, min_h, max_h, min_area = flt
    cands: list[tuple[float, Image.Image]] = []
    for i, sl in enumerate(objs, start=1):
        if sl is None:
            continue
        h = sl[0].stop - sl[0].start
        w = sl[1].stop - sl[1].start
        if not (min_w <= w <= max_w and min_h <= h <= max_h):
            continue
        area = int((lbl[sl] == i).sum())
        if area < min_area:
            continue
        # crop just this blob; zero out other blobs bleeding into the bbox
        sub = arr[sl].copy()
        keep = (lbl[sl] == i)
        sub[~keep, 3] = 0
        # Reject blobs dominated by pure-black faces (a cliff's unlit underside):
        # they read as "not even lighting" and, at the extreme, as an empty tile.
        opaque_rgb = sub[keep, :3].astype(float)
        if opaque_rgb.size:
            lum = opaque_rgb.mean(axis=1)
            if (lum < 24).mean() > 0.42:
                continue
        rgba = Image.fromarray(sub, "RGBA")
        flat = Image.new("RGB", rgba.size, BG)
        flat.paste(rgba, mask=rgba.split()[-1])
        cands.append((area, square_upscale(flat)))
    cands.sort(key=lambda x: -x[0])  # biggest/cleanest first
    picked: list[Image.Image] = []
    hashes: list[int] = []
    for _, tile in cands:
        ph = phash(tile)
        if any(hamming(ph, h) < 13 for h in hashes):  # skip near-duplicates
            continue
        hashes.append(ph)
        picked.append(tile)
        if len(picked) >= cap:
            break
    return picked


def main() -> int:
    if RAW.exists():
        shutil.rmtree(RAW)
    picked: list[dict] = []
    for stem, family, phrase, flt, cap in SHEETS:
        tiles = extract(stem, flt, cap)
        d = RAW / family
        d.mkdir(parents=True, exist_ok=True)
        for j, t in enumerate(tiles):
            name = f"{family}__{phrase.replace(' ', '_')}__{stem}_{j:02d}.png"
            t.save(d / name)
            picked.append({"curated": name, "family": family, "phrase": phrase, "sheet": stem})
        print(f"{stem:14s} -> {len(tiles):2d} {family} tiles")
    print(f"\nTotal sliced: {len(picked)}")

    # Normalize with the trainer-agnostic prep_dataset.py (acceptance criterion).
    if OUT.exists():
        shutil.rmtree(OUT)
    cmd = [sys.executable, str(PREP), "--src", str(RAW), "--out", str(OUT),
           "--max-edge", "1024", "--bg", "128,128,128"]
    print("Running:", " ".join(cmd))
    subprocess.run(cmd, check=True)

    # Captions, matched back by stem.
    by_stem = {p["curated"][:-4]: p for p in picked}
    fam: dict[str, int] = {}
    for png in sorted(OUT.glob("*.png")):
        rec = by_stem.get(png.stem)
        if not rec:
            continue
        cap_txt = (f"tile_iso, {rec['phrase']} tile, isometric RPG tileset, "
                   f"diamond tile, even lighting")
        png.with_suffix(".txt").write_text(cap_txt + "\n", encoding="utf-8")
        fam[rec["family"]] = fam.get(rec["family"], 0) + 1
    (OUT / "_curation.json").write_text(json.dumps(
        {"picked": picked, "family_counts": fam, "count": sum(fam.values()),
         "source_page": SRC_PAGE, "author": "rubberduck", "license": "CC0"},
        indent=2), encoding="utf-8")
    print(f"Captioned. Family counts: {fam}")
    print(f"-> {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
