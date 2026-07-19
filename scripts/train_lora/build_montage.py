"""Build a labeled contact-sheet montage for a LoRA training dataset.

A pre-training human-approval gate: render every image in a dataset dir as a
labeled thumbnail grid so the whole set can be eyeballed in one PNG before any
GPU time is spent. CPU/PIL only — no torch, no CUDA.

Usage:
    python build_montage.py --dir E:/ai-training/datasets/tile_iso \
        --out E:/ai-training/datasets/tile_iso/_montage.png
    python build_montage.py --dir E:/ai-training/datasets/tile_iso   # -> <dir>/_montage.png
"""

from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

THUMB = 224          # thumbnail square (px)
LABEL_H = 20         # label strip under each thumb
PAD = 8              # gap between cells
COLS = 6             # thumbnails per row
BG = (24, 24, 28)
FG = (230, 230, 230)
CELL_BG = (40, 40, 46)
HEADER_H = 56


def _font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for name in ("arial.ttf", "DejaVuSans.ttf", "segoeui.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def _label_for(png: Path) -> str:
    """Human label from filename: the subject token before the first '__'."""
    stem = png.stem
    return stem.split("__")[0] if "__" in stem else stem


def _fit(img: Image.Image, box: int) -> Image.Image:
    """Contain-fit an image into a box×box square on CELL_BG, centered."""
    img = img.convert("RGB")
    img.thumbnail((box, box), Image.LANCZOS)
    canvas = Image.new("RGB", (box, box), CELL_BG)
    canvas.paste(img, ((box - img.width) // 2, (box - img.height) // 2))
    return canvas


def build(directory: Path, out: Path) -> Path:
    pngs = sorted(p for p in directory.glob("*.png") if not p.name.startswith("_"))
    if not pngs:
        raise SystemExit(f"no images in {directory}")

    rows = (len(pngs) + COLS - 1) // COLS
    cell_w = THUMB + PAD
    cell_h = THUMB + LABEL_H + PAD
    W = COLS * cell_w + PAD
    H = HEADER_H + rows * cell_h + PAD

    sheet = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(sheet)

    title = f"{directory.name}   —   {len(pngs)} images"
    draw.text((PAD + 4, 16), title, fill=FG, font=_font(26))

    small = _font(13)
    for i, png in enumerate(pngs):
        r, c = divmod(i, COLS)
        x = PAD + c * cell_w
        y = HEADER_H + r * cell_h
        try:
            thumb = _fit(Image.open(png), THUMB)
        except Exception as e:  # noqa: BLE001 — a corrupt file shouldn't kill the sheet
            thumb = Image.new("RGB", (THUMB, THUMB), (80, 20, 20))
            ImageDraw.Draw(thumb).text((6, 6), f"ERR\n{e}", fill=FG, font=small)
        sheet.paste(thumb, (x, y))
        label = _label_for(png)
        if draw.textlength(label, font=small) > THUMB - 6:
            while label and draw.textlength(label + "…", font=small) > THUMB - 6:
                label = label[:-1]
            label += "…"
        draw.text((x + 3, y + THUMB + 3), label, fill=FG, font=small)

    out.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out)
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dir", required=True, type=Path, help="dataset directory of *.png")
    ap.add_argument("--out", type=Path, default=None, help="output PNG (default <dir>/_montage)")
    args = ap.parse_args()
    out = args.out or (args.dir / "_montage.png")
    saved = build(args.dir, out)
    print(f"wrote {saved}  ({saved.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
