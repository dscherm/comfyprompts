"""prep_dataset — curate an arbitrary image set into an ai-toolkit training folder.

Stage 1 of the train_lora harness (see scripts/train_lora/README.md). Takes any
source dir(s)/glob(s) or a list file, normalizes the images (RGB, alpha flattened
onto a background colour, optional longest-edge downscale), drops exact duplicates
and unreadable files, and writes a flat folder of PNGs that ai-toolkit can train
on directly. Captions (.txt sidecars) are added later by caption.py.

Dataset-agnostic: nothing about any particular style/character is hardcoded —
point --src at any folder and it produces a clean training set.

Requires Pillow. Run with the project venv (D:\\Projects\\comfyui-toolchain\\.venv)
or any Python 3.10+ with Pillow installed.

Usage:
    python scripts/train_lora/prep_dataset.py \\
        --src "D:/Projects/ComfyUI/output/Berserkr_*.png" \\
        --out scripts/train_lora/datasets/berserkr_style \\
        --max-images 150 --max-edge 1024
"""

from __future__ import annotations

import argparse
import glob
import hashlib
import json
import sys
from pathlib import Path

from PIL import Image, UnidentifiedImageError

DEFAULT_EXTS = (".png", ".jpg", ".jpeg", ".webp", ".bmp")


def _gather(srcs: list[str], list_file: str | None, exts: tuple[str, ...]) -> list[Path]:
    """Resolve --src dirs/globs and an optional --list file into a sorted, deduped
    list of candidate image paths."""
    paths: list[Path] = []
    for s in srcs:
        p = Path(s)
        if p.is_dir():
            for ext in exts:
                paths.extend(p.rglob(f"*{ext}"))
        else:
            # treat as a glob (covers explicit files too)
            paths.extend(Path(m) for m in glob.glob(s, recursive=True))
    if list_file:
        for line in Path(list_file).read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#"):
                paths.append(Path(line))
    # keep only image-like extensions, unique, deterministic order
    seen: set[str] = set()
    out: list[Path] = []
    for p in sorted(paths, key=lambda x: str(x).lower()):
        key = str(p.resolve()).lower()
        if p.suffix.lower() in exts and key not in seen:
            seen.add(key)
            out.append(p)
    return out


def _normalize(img: Image.Image, max_edge: int | None, bg: tuple[int, int, int]) -> Image.Image:
    """Flatten alpha onto `bg`, convert to RGB, optionally downscale longest edge."""
    if img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info):
        rgba = img.convert("RGBA")
        canvas = Image.new("RGB", rgba.size, bg)
        canvas.paste(rgba, mask=rgba.split()[-1])
        img = canvas
    else:
        img = img.convert("RGB")
    if max_edge and max(img.size) > max_edge:
        scale = max_edge / max(img.size)
        new_size = (round(img.width * scale), round(img.height * scale))
        img = img.resize(new_size, Image.LANCZOS)
    return img


def prep_dataset(
    srcs: list[str],
    out: str | Path,
    *,
    list_file: str | None = None,
    max_images: int | None = None,
    max_edge: int | None = None,
    bg: tuple[int, int, int] = (255, 255, 255),
    exts: tuple[str, ...] = DEFAULT_EXTS,
) -> dict:
    """Normalize a candidate image set into `out`. Returns a stats dict and writes
    a manifest.json next to the images."""
    out_dir = Path(out)
    out_dir.mkdir(parents=True, exist_ok=True)
    candidates = _gather(srcs, list_file, exts)

    stats = {"scanned": len(candidates), "included": 0, "skipped_unreadable": 0,
             "skipped_duplicate": 0, "resized": 0}
    content_hashes: set[str] = set()
    used_names: set[str] = set()
    manifest: list[dict] = []

    for src in candidates:
        if max_images is not None and stats["included"] >= max_images:
            break
        try:
            with Image.open(src) as raw:
                raw.load()
                orig_max = max(raw.size)
                norm = _normalize(raw, max_edge, bg)
        except (UnidentifiedImageError, OSError, ValueError):
            stats["skipped_unreadable"] += 1
            continue

        digest = hashlib.sha256(norm.tobytes()).hexdigest()
        if digest in content_hashes:
            stats["skipped_duplicate"] += 1
            continue
        content_hashes.add(digest)

        stem = src.stem
        name = f"{stem}.png"
        i = 1
        while name.lower() in used_names:
            name = f"{stem}_{i}.png"
            i += 1
        used_names.add(name.lower())

        norm.save(out_dir / name, format="PNG")
        if max_edge and orig_max > max_edge:
            stats["resized"] += 1
        stats["included"] += 1
        manifest.append({"out": name, "src": str(src), "size": list(norm.size)})

    (out_dir / "manifest.json").write_text(
        json.dumps({"stats": stats, "images": manifest}, indent=2), encoding="utf-8"
    )
    return stats


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Curate images into an ai-toolkit training folder.")
    ap.add_argument("--src", action="append", default=[], metavar="DIR_OR_GLOB",
                    help="Source dir or glob. Repeatable.")
    ap.add_argument("--list", dest="list_file", default=None,
                    help="Optional file with one image path per line.")
    ap.add_argument("--out", required=True, help="Output training folder.")
    ap.add_argument("--max-images", type=int, default=None, help="Cap on included images.")
    ap.add_argument("--max-edge", type=int, default=None,
                    help="Downscale so the longest edge is at most this many px.")
    ap.add_argument("--bg", default="255,255,255",
                    help="Background colour for flattening alpha, R,G,B (default white).")
    args = ap.parse_args(argv)

    if not args.src and not args.list_file:
        ap.error("provide at least one --src or a --list file")
    parts = [int(c) for c in args.bg.split(",")]
    if len(parts) != 3:
        ap.error("--bg must be three comma-separated ints, e.g. 255,255,255")
    bg: tuple[int, int, int] = (parts[0], parts[1], parts[2])

    stats = prep_dataset(args.src, args.out, list_file=args.list_file,
                         max_images=args.max_images, max_edge=args.max_edge, bg=bg)
    print(json.dumps(stats, indent=2))
    print(f"-> {Path(args.out).resolve()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
