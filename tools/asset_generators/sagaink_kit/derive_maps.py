#!/usr/bin/env python3
"""sagaink kit — derive normal + AO maps from the inked albedo textures.

The ink textures already encode depth as tone: cross-hatched recesses read dark,
lit faces read light. That height signal drives a tangent-space normal map (so
the plank seams / mortar courses / reed bundles catch light on the mesh) and a
soft ambient-occlusion map (so the carved recesses stay shaded). Purely local —
no ComfyUI, no network. Tiling is preserved by wrapping the Sobel/blur at the
edges so the derived maps stay seamless like their source.

Usage:
  python derive_maps.py wood        # one material -> wood_n.png, wood_ao.png
  python derive_maps.py all         # every material in out/
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter

OUT = Path(__file__).resolve().parent / "out"
MATERIALS = ["wood", "stone", "thatch", "plaster", "shingle"]

# Per-material relief strength: how tall the height field reads. Deep mortar and
# overlapping reeds/shingles want more; flat plaster wants less.
STRENGTH = {"wood": 1.5, "stone": 2.2, "thatch": 2.4, "plaster": 1.0, "shingle": 2.3}


def _height(img: Image.Image, blur: float = 1.2) -> np.ndarray:
    """Grayscale luminance as a [0,1] height field, lightly blurred to kill
    single-pixel ink noise that would otherwise pit the normals."""
    g = img.convert("L").filter(ImageFilter.GaussianBlur(blur))
    return np.asarray(g, dtype=np.float32) / 255.0


def _normal_map(h: np.ndarray, strength: float) -> Image.Image:
    """Tangent-space normal map from a height field, seam-safe via np.roll (wrap)."""
    # central differences with wrap-around so the map tiles like the source
    dx = (np.roll(h, -1, axis=1) - np.roll(h, 1, axis=1)) * 0.5
    dy = (np.roll(h, -1, axis=0) - np.roll(h, 1, axis=0)) * 0.5
    nx = -dx * strength
    ny = -dy * strength
    nz = np.ones_like(h)
    inv = 1.0 / np.sqrt(nx * nx + ny * ny + nz * nz)
    nx, ny, nz = nx * inv, ny * inv, nz * inv
    # encode [-1,1] -> [0,255]; +Y up (OpenGL/Godot convention)
    rgb = np.stack([(nx * 0.5 + 0.5), (ny * 0.5 + 0.5), (nz * 0.5 + 0.5)], axis=-1)
    return Image.fromarray((rgb * 255.0).clip(0, 255).astype(np.uint8), "RGB")


def _ao_map(img: Image.Image, h: np.ndarray) -> Image.Image:
    """Soft AO: darken the recesses (low height) relative to a wide-blur local
    average, so broad tone doesn't wash out but crevices stay occluded. Wrapped
    blur keeps it tiling."""
    # wide seam-safe blur via tiling the image 3x, blurring, cropping centre
    H, W = h.shape
    tiled = np.tile(h, (3, 3))
    wide = np.asarray(
        Image.fromarray((tiled * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(W * 0.03)),
        dtype=np.float32,
    )[H : 2 * H, W : 2 * W] / 255.0
    # occlusion where local height sits below its neighbourhood average
    ao = 1.0 - np.clip((wide - h) * 2.2, 0.0, 0.6)
    return Image.fromarray((ao * 255.0).clip(0, 255).astype(np.uint8), "L")


def derive(material: str) -> None:
    src = OUT / f"{material}.png"
    img = Image.open(src)
    h = _height(img)
    s = STRENGTH.get(material, 1.5)
    _normal_map(h, s).save(OUT / f"{material}_n.png")
    _ao_map(img, h).save(OUT / f"{material}_ao.png")
    print(f"[{material}] -> {material}_n.png  {material}_ao.png  (strength {s})", flush=True)


if __name__ == "__main__":
    which = sys.argv[1] if len(sys.argv) > 1 else "all"
    names = MATERIALS if which == "all" else [which]
    for m in names:
        derive(m)
