"""Neon bloom post-step for DissonantCity renders (EEVEE Next has no legacy bloom).
Vectorized: mask hot/emissive pixels -> gaussian blur -> screen-blend back.
Run with a python that has numpy+PIL (e.g. ComfyUI venv):
    python bloom.py <in.png> [out.png] [threshold] [radius] [intensity]
"""
import sys
import numpy as np
from PIL import Image, ImageFilter

inp = sys.argv[1]
out = sys.argv[2] if len(sys.argv) > 2 else inp
thresh = float(sys.argv[3]) if len(sys.argv) > 3 else 470.0
radius = float(sys.argv[4]) if len(sys.argv) > 4 else 10.0
intensity = float(sys.argv[5]) if len(sys.argv) > 5 else 1.3

arr = np.asarray(Image.open(inp).convert("RGB")).astype(np.float32)
lum = arr.sum(axis=2)
bright = (arr * (lum > thresh)[..., None]).astype(np.uint8)
glow = np.asarray(Image.fromarray(bright).filter(ImageFilter.GaussianBlur(radius))).astype(np.float32) * intensity
glow = np.clip(glow, 0, 255)
res = 255.0 - (255.0 - arr) * (255.0 - glow) / 255.0   # screen blend
Image.fromarray(np.clip(res, 0, 255).astype(np.uint8)).save(out)
print("bloom ->", out)
