"""Wrap-edge MAD — the seamlessness metric for tile LoRA evals (TX3/TX7).

Trainer-agnostic (Pillow + NumPy only). Per tile_loras_spec.md §6b:

    horizontal seam = mean(|I[:, 0] - I[:, W-1]|)   (left col vs right col)
    vertical seam   = mean(|I[0, :] - I[H-1, :]|)   (top row vs bottom row)
    edge_MAD%       = 100 * (horiz + vert) / 2 / 255

Seamless tiles score < 5%; a non-tiling image typically 10-40%. Also renders
the visual evidence: 2x2 and 4x4 mosaics plus an OffsetImage-style 50% roll
(any seam lands centre-frame).

Usage:
    python eval/tile_edge_mad.py IMAGE [IMAGE ...] [--mosaics-dir DIR] [--json OUT]
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
from PIL import Image


def edge_mad(img: Image.Image) -> dict:
    arr = np.asarray(img.convert("RGB"), dtype=np.float32)
    horiz = float(np.mean(np.abs(arr[:, 0, :] - arr[:, -1, :])))
    vert = float(np.mean(np.abs(arr[0, :, :] - arr[-1, :, :])))
    return {
        "horiz_mad": horiz,
        "vert_mad": vert,
        "edge_mad_pct": 100.0 * (horiz + vert) / 2.0 / 255.0,
    }


def render_evidence(img: Image.Image, stem: str, out_dir: Path) -> list[str]:
    out_dir.mkdir(parents=True, exist_ok=True)
    arr = np.asarray(img.convert("RGB"))
    written = []
    for n in (2, 4):
        mosaic = np.tile(arr, (n, n, 1))
        m = Image.fromarray(mosaic)
        if m.width > 2048:
            m = m.resize((2048, 2048), Image.LANCZOS)
        p = out_dir / f"{stem}_mosaic{n}x{n}.png"
        m.save(p)
        written.append(str(p))
    rolled = np.roll(np.roll(arr, arr.shape[0] // 2, axis=0), arr.shape[1] // 2, axis=1)
    p = out_dir / f"{stem}_roll50.png"
    Image.fromarray(rolled).save(p)
    written.append(str(p))
    return written


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("images", nargs="+", type=Path)
    parser.add_argument("--mosaics-dir", type=Path, default=None,
                        help="also render 2x2/4x4 mosaics + 50%% roll here")
    parser.add_argument("--json", type=Path, default=None, help="write results as JSON")
    args = parser.parse_args()

    results = []
    for path in args.images:
        img = Image.open(path)
        r = {"image": str(path)} | edge_mad(img)
        if args.mosaics_dir:
            r["evidence"] = render_evidence(img, path.stem, args.mosaics_dir)
        results.append(r)
        verdict = "seamless" if r["edge_mad_pct"] < 5.0 else "SEAM"
        print(f"{path.name:<50} edge_MAD {r['edge_mad_pct']:6.2f}%  {verdict}")

    if args.json:
        args.json.write_text(json.dumps(results, indent=1))
        print(f"wrote {args.json}")


if __name__ == "__main__":
    main()
