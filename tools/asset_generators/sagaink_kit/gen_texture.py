#!/usr/bin/env python3
"""sagaink kit — detailed inked seamless material textures.

Drives the ComfyUI generate_texture_tile workflow (SDXL + SeamlessTile, truly
tileable) with sagaink-style ink prompts to produce DETAILED grayscale
cross-hatched material textures (wood grain, carved stone, thatch, plaster) for
the kit atlas. This is the "real detail" layer, not a post-process filter.

The sagaink LoRA is Flux (won't tile), so tiling surfaces get the ink look via
prompting SDXL; Flux+sagaink is reserved for non-tiling hero details elsewhere.

Usage:
  python gen_texture.py wood            # one material
  python gen_texture.py all             # every material
Env: COMFYUI_URL (default http://127.0.0.1:8188)
"""
from __future__ import annotations

import json
import os
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

COMFY = os.environ.get("COMFYUI_URL", "http://127.0.0.1:8188").rstrip("/")
ROOT = Path(__file__).resolve().parents[3]  # comfyui-toolchain/
WORKFLOW = ROOT / "workflows" / "mcp" / "generate_texture_tile.json"
OUT = Path(__file__).resolve().parent / "out"

# The shared ink style every material inherits (from vibrant_rpg STYLE.md) — the
# locked "blend": inked linework + carved tonal mass, grayscale, tiling. Tuned so
# each material reads as a surface (mid-grey body), not a bimodal barcode or a
# delicate line drawing.
INK = ("hand-inked graphic-novel illustration, seamless tileable, top-down flat "
       "orthographic, bold confident dark ink outlines defining every edge and form, "
       "cross-hatched ink shading carving deep shadows into the recesses, mid-grey "
       "tonal body with strong dark-to-light contrast, detailed inked artwork, "
       "grayscale, no colour, not photorealistic, not a delicate line drawing")
NEG = ("colour, colored, brown, sepia, blue, painterly, photorealistic, photo, "
       "pure black and white, bimodal, barcode, high frequency stripes, "
       "light airy, thin delicate line drawing, blank white background, flat even "
       "lighting, smooth gradient, soft, blurry, cel shaded, coloring book, flat "
       "graphic, text, watermark, visible seam, perspective, object, border, vignette, "
       # keep material textures as flat surfaces, never a depicted scene
       "building, house, cottage, roof edge, tree, pine tree, sky, horizon, "
       "landscape, scenery, window, chimney, snowman")

# material -> subject description (INK is appended). Seeds fixed for repeatable
# regeneration; each gets its own so they don't look identical.
MATERIALS = {
    "wood":    ("a wall of horizontal weathered wooden planks, clear plank seams, "
                "wood grain and a few knots", 42),
    "stone":   ("a wall of rough-hewn stone masonry blocks with deep mortar courses "
                "and chipped edges", 43),
    "thatch":  ("a thatched straw roof of bundled dry reeds in overlapping rows with "
                "frayed ends", 44),
    "plaster": ("a rough cracked plaster daub wall with hairline cracks and pitting", 45),
    "shingle": ("a roof of overlapping split-timber wood shingles in courses with "
                "split grain", 46),
    # ground material (roofs reuse `shingle` tinted per type — SDXL wouldn't make
    # clean tile rows, only cracked stone; and smooth snow is procedural, see
    # bake_sagaink_atlas / the snow.png generator, not SDXL)
    "cobble":     ("a ground of rounded cobblestone setts with deep mortar gaps, "
                   "worn paving stones", 49),
    "snow_stone": ("a stone masonry wall dusted with snow, snow settled on every "
                   "ledge and packed into the mortar courses", 52),
}


def _sub(obj, params):
    """Recursively replace PARAM_* placeholder strings with values."""
    if isinstance(obj, dict):
        return {k: _sub(v, params) for k, v in obj.items() if k not in ("_defaults", "_meta")}
    if isinstance(obj, list):
        return [_sub(v, params) for v in obj]
    if isinstance(obj, str) and obj.startswith("PARAM_"):
        return params[obj]
    return obj


def _defaults(workflow):
    d = {}
    for node in workflow.values():
        d.update(node.get("_defaults", {}))
    return d


def _post(path, payload=None):
    url = f"{COMFY}{path}"
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())


def generate(material: str) -> Path:
    subject, seed = MATERIALS[material]
    workflow = json.loads(WORKFLOW.read_text())
    params = _defaults(workflow)
    params["PARAM_PROMPT"] = f"{subject}, {INK}"
    params["PARAM_NEGATIVE_PROMPT"] = NEG
    params["PARAM_INT_SEED"] = seed
    params["PARAM_INT_STEPS"] = 30
    params["PARAM_FLOAT_CFG"] = 6.5
    prompt = _sub(workflow, params)

    print(f"[{material}] queuing on {COMFY} ...", flush=True)
    resp = _post("/prompt", {"prompt": prompt})
    pid = resp["prompt_id"]
    # poll history
    for _ in range(240):
        time.sleep(1.5)
        with urllib.request.urlopen(f"{COMFY}/history/{pid}", timeout=30) as r:
            hist = json.loads(r.read())
        if pid in hist and hist[pid].get("outputs"):
            imgs = hist[pid]["outputs"]["8"]["images"]
            img = imgs[0]
            q = urllib.parse.urlencode({"filename": img["filename"], "subfolder": img.get("subfolder", ""), "type": img.get("type", "output")})
            OUT.mkdir(parents=True, exist_ok=True)
            dst = OUT / f"{material}.png"
            with urllib.request.urlopen(f"{COMFY}/view?{q}", timeout=60) as r:
                dst.write_bytes(r.read())
            print(f"[{material}] saved -> {dst}", flush=True)
            return dst
    raise TimeoutError(f"{material}: generation timed out")


if __name__ == "__main__":
    which = sys.argv[1] if len(sys.argv) > 1 else "wood"
    names = list(MATERIALS) if which == "all" else [which]
    for m in names:
        generate(m)
