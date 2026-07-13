#!/usr/bin/env python3
"""sagaink kit — re-bake the shared GrimForge atlas in the inked sagaink style.

The kit's ~100 GLB pieces all sample ONE 512x512 atlas: each palette colour owns
a swatch cell (8-col grid, order = list(PALETTE)), and faces UV-unwrap into their
colour's cell. So re-skinning the atlas re-skins the whole kit at once, with the
existing UVs untouched — no Blender, no re-export (honours the "patch exported
files, don't regenerate" rule).

Per cell, in the sagaink logic (stark grayscale + one accent pop):
  * accent cells  (the EMISSION set: window/fire/ember/gem/rune/...) -> keep colour
  * material cells (planks/brick/shingle/straw) -> stamp the real inked texture
                    (out/<mat>.png), tone-shifted to that swatch's own luminance so
                    the kit's tonal hierarchy survives (slate stays darker than plaster)
  * everything else (plain colour, foliage, metal, cobble, gravel) -> desaturate

Also emits a matching NORMAL and AO atlas (derived maps stamped into the material
cells, flat elsewhere) so the pieces carry real surface depth on the mesh.

Outputs (out/): atlas_sagaink_color.png, atlas_sagaink_n.png, atlas_sagaink_ao.png
Run derive_maps.py first (needs out/<mat>_n.png, _ao.png).
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import numpy as np
from PIL import Image

HERE = Path(__file__).resolve().parent
OUT = HERE / "out"
KITLIB = HERE.parents[1] / "asset_generators" / "village_kit"
BASE_ATLAS = HERE.parents[2] / "products" / "grimforge_playable_demo_v1" / "kit" / "atlas_color_fixed.png"

sys.path.insert(0, str(KITLIB))
from kitlib import EMISSION, PALETTE  # noqa: E402  (pure data, no bpy)

# UVs are normalised into cell rects, so the atlas can be baked at any resolution
# and the same GLBs still map. 512 crushed each material to a 64px cell (12:1
# downsample of the 1024 ink source, losing the detail); 2048 keeps it (4:1).
SIZE = int(os.environ.get("SAGAINK_ATLAS_SIZE", "2048"))
COLS = 8

# pattern group -> which sagaink texture skins it (mirrors kitlib _ensure_atlas)
PLANKS = ("wood", "wood_dk", "charwood", "beam")
BRICK = ("stone", "stone_dk", "plaster", "plaster2")
SHINGLE = ("slate", "roof_red", "shake")
STRAW = ("thatch", "thatch_dk")
# name -> sagaink texture basename in out/. All roofs use the shingle texture —
# its clean horizontal COURSES read as a roof; the material is set by the tint
# (blood-red clay tile, blue-grey slate, brown shake), which reads far better than
# SDXL's cracked-"tile" attempts that just looked like stone. cobble is its own.
TEX_OF: dict[str, str] = {}
for n in PLANKS:
    TEX_OF[n] = "wood"
TEX_OF["stone"] = TEX_OF["stone_dk"] = "stone"
TEX_OF["plaster"] = TEX_OF["plaster2"] = "plaster"
for n in SHINGLE:            # slate, roof_red, shake — differentiated by tint below
    TEX_OF[n] = "shingle"
for n in STRAW:
    TEX_OF[n] = "thatch"
TEX_OF["cobble"] = "cobble"

# Cells kept verbatim (the emissive glows) as vivid accents.
ACCENT = set(EMISSION)

# Cells RECOLOURED to a solid accent (keeping the swatch's luminance detail): the
# banners/capes/cloth become vivid blood-red torn fabric.
_BLOOD_BANNER = np.array([170.0, 30.0, 24.0])
RECOLOR = {
    "crimson": _BLOOD_BANNER,
    "flag": _BLOOD_BANNER,
    "cloth_r": _BLOOD_BANNER,
}

# The kit stays COLOURED (not strict-grayscale sagaink): each material's inked
# linework + carved relief is TINTED by a colour so surfaces differentiate and the
# world isn't grey-on-grey. Most materials tint by their own palette swatch (stone
# stays neutral grey, wood brown); these override to the vivid sagaink accents the
# art calls for — amber/gold straw, blood-red clay roof tiles.
_AMBER = np.array([224.0, 168.0, 66.0])   # golden straw
_BLOOD = np.array([152.0, 44.0, 34.0])    # blood-red clay tile
TINT = {
    "thatch": _AMBER,
    "thatch_dk": _AMBER * 0.78,
    "roof_red": _BLOOD,
}

# --- snow theme ------------------------------------------------------------- #
# A themed variant: roofs/ground/masonry wear the snow textures, tinted near-white
# (the snow_* textures encode where the material shows through the snow). Built as
# atlas_sagaink_snow_* and selectable in-demo via --snow.
SNOW_TEX = {
    "slate": "snow", "roof_red": "snow", "shake": "snow",
    "thatch": "snow", "thatch_dk": "snow",
    "stone": "snow_stone", "stone_dk": "snow_stone",
    "plaster": "snow_stone", "plaster2": "snow_stone",
    "wood": "snow_stone", "wood_dk": "snow_stone", "beam": "snow_stone", "charwood": "snow_stone",
    "cobble": "snow", "gravel": "snow",
}
_SNOW = {  # snow texture -> tint (pale, cool)
    "snow_stone": np.array([206.0, 214.0, 226.0]),  # snowy masonry (stone shows through)
    "snow": np.array([234.0, 240.0, 249.0]),        # clean snow blanket (roofs + ground)
}

_LUMA = np.array([0.299, 0.587, 0.114], dtype=np.float32)


def _luma(rgb: np.ndarray) -> np.ndarray:
    return rgb.astype(np.float32) @ _LUMA


def _tex(mat: str, suffix: str, w: int, h: int) -> np.ndarray:
    im = Image.open(OUT / f"{mat}{suffix}.png").resize((w, h), Image.LANCZOS)
    return np.asarray(im, dtype=np.float32)


def bake(base_atlas: Path = BASE_ATLAS, out_prefix: str = "atlas_sagaink",
         out_dir: Path = OUT, roll: tuple[float, float] = (0.0, 0.0),
         theme: str | None = None) -> None:
    # upscale the shipped atlas to the target size (NEAREST keeps the flat
    # colour/accent swatches crisp); material cells get replaced by fresh hi-res ink
    base_img = Image.open(base_atlas).convert("RGB").resize((SIZE, SIZE), Image.NEAREST)
    base = np.asarray(base_img, dtype=np.float32)
    names = list(PALETTE)
    rows = -(-len(names) // COLS)
    cw, ch = SIZE // COLS, SIZE // rows

    color = base.copy()
    normal = np.tile(np.array([128, 128, 255], np.float32), (SIZE, SIZE, 1))
    ao = np.full((SIZE, SIZE), 255.0, np.float32)

    for i, name in enumerate(names):
        # Blender writes image.pixels bottom-row-first, so the saved atlas PNG is
        # vertically flipped vs list(PALETTE) order — cell i=0 (stone) is the
        # BOTTOM row. Flip the row index to hit the right cell in the shipped PNG.
        cx = (i % COLS) * cw
        cy = (rows - 1 - i // COLS) * ch
        cell = base[cy : cy + ch, cx : cx + cw]  # source RGB for this swatch

        if name in ACCENT:
            continue  # keep the colour pop as-is (also drives the emit atlas)

        if name in RECOLOR:
            # blood-red torn fabric: solid accent modulated by the swatch's folds
            shade = (0.5 + 0.62 * (_luma(cell) / 255.0))[..., None]
            color[cy : cy + ch, cx : cx + cw] = np.clip(RECOLOR[name][None, None, :] * shade, 0.0, 255.0)
            continue

        mat = SNOW_TEX.get(name) if theme == "snow" else TEX_OF.get(name)
        if mat is not None:
            # stamp the inked texture, tone-shifted to this swatch's mean luminance.
            # roll (a seam-safe shift, textures tile) yields variant atlases so
            # repeated pieces don't clone the identical brick/plank arrangement.
            dy, dx = int(roll[1] * ch), int(roll[0] * cw)
            g = _tex(mat, "", cw, ch)[..., :3] @ _LUMA
            nrm = _tex(mat, "_n", cw, ch)[..., :3]
            aomap = _tex(mat, "_ao", cw, ch)
            aomap = aomap[..., 0] if aomap.ndim == 3 else aomap
            if dx or dy:
                g = np.roll(g, (dy, dx), axis=(0, 1))
                nrm = np.roll(nrm, (dy, dx), axis=(0, 1))
                aomap = np.roll(aomap, (dy, dx), axis=(0, 1))
            # tint the inked light/dark detail by the material colour: snow theme
            # tints near-white per snow texture; otherwise the swatch's own palette
            # colour (stone grey, wood brown) or an override (amber straw, red tile)
            if theme == "snow":
                tint = _SNOW[mat]
            else:
                tint = TINT.get(name)
                if tint is None:
                    tint = cell.reshape(-1, 3).mean(axis=0)  # the swatch's palette colour
            ink = g / max(float(g.mean()), 1.0)                 # detail as a ~1.0 multiplier
            ink = np.clip((ink - 1.0) * 1.35 + 1.0, 0.35, 1.7)  # punch the ink contrast
            tinted = np.clip(tint[None, None, :] * ink[..., None], 0.0, 255.0)
            color[cy : cy + ch, cx : cx + cw] = tinted
            normal[cy : cy + ch, cx : cx + cw] = nrm
            ao[cy : cy + ch, cx : cx + cw] = aomap
        elif theme == "snow":
            # plain ground/foliage under snow: push toward snow white, faint detail
            snowed = _SNOW["snow"][None, None, :] * (0.72 + 0.34 * (_luma(cell) / 255.0)[..., None])
            color[cy : cy + ch, cx : cx + cw] = np.clip(snowed, 0.0, 255.0)
        # else: plain / foliage / metal — keep the original colour swatch
        # (color starts as base.copy()), so foliage green / cloth stay coloured

    out_dir.mkdir(parents=True, exist_ok=True)
    Image.fromarray(color.clip(0, 255).astype(np.uint8), "RGB").save(out_dir / f"{out_prefix}_color.png")
    Image.fromarray(normal.clip(0, 255).astype(np.uint8), "RGB").save(out_dir / f"{out_prefix}_n.png")
    Image.fromarray(ao.clip(0, 255).astype(np.uint8), "L").save(out_dir / f"{out_prefix}_ao.png")
    print(f"baked {out_prefix} ({len(names)} cells, {cw}x{ch}) from {base_atlas.name} -> {out_dir}", flush=True)


def bake_into_kit(kit_dir: Path) -> None:
    """Reusable finish for ANY kit built by the toolchain: find the kit's shared
    atlas and write the sagaink_{color,n,ao} set INTO the kit folder, so the kit
    carries the inked look standalone. Run after productize.py (needs PIL, so it
    runs outside Blender). Assumes the kit uses the kitlib PALETTE atlas layout."""
    kit_dir = Path(kit_dir)
    atlas = next((kit_dir / n for n in ("atlas_color_fixed.png", "atlas_color.png")
                  if (kit_dir / n).exists()), None)
    if atlas is None:
        raise SystemExit(f"no atlas_color[_fixed].png in {kit_dir}")
    bake(atlas, "atlas_sagaink", kit_dir)


# Named atlas variants keyed to the same kitlib PALETTE layout: the courtyard/town
# fixed atlas and town's wood-building recolour. (Occult embeds per-GLB atlases in
# a different palette and is handled by a spatial shader instead.)
DEMO = HERE.parents[2] / "products" / "grimforge_playable_demo_v1"
# prefix -> (base atlas, roll, theme). The _v1 entries are half-shifted so repeated
# pieces can pick a different arrangement per instance (see env.gd _apply_variant);
# the _snow entries wear the snow textures (selectable in-demo via --snow).
_KIT = DEMO / "kit" / "atlas_color_fixed.png"
_WOOD = DEMO / "town" / "atlas_color_wood.png"
VARIANTS = {
    "atlas_sagaink": (_KIT, (0.0, 0.0), None),
    "atlas_sagaink_v1": (_KIT, (0.5, 0.37), None),
    "atlas_sagaink_wood": (_WOOD, (0.0, 0.0), None),
    "atlas_sagaink_wood_v1": (_WOOD, (0.5, 0.37), None),
    "atlas_sagaink_snow": (_KIT, (0.0, 0.0), "snow"),
    "atlas_sagaink_snow_v1": (_KIT, (0.5, 0.37), "snow"),
    "atlas_sagaink_wood_snow": (_WOOD, (0.0, 0.0), "snow"),
    "atlas_sagaink_wood_snow_v1": (_WOOD, (0.5, 0.37), "snow"),
}

if __name__ == "__main__":
    args = sys.argv[1:]
    if args and args[0] == "--kit":
        # reusable finish: sagaink-ify any kit folder in place
        bake_into_kit(Path(args[1]))
    else:
        which = args[0] if args else "all"
        todo = VARIANTS if which == "all" else {which: VARIANTS[which]}
        for prefix, (base, roll, theme) in todo.items():
            bake(base, prefix, roll=roll, theme=theme)
