"""productize spec for the GrimForge Bestiary kit — finished (decimated +
texture-baked) low-poly creature GLBs from the low-poly pipeline.

    blender -b --python tools/asset_generators/village_kit/productize.py -- \
        products/grimforge_bestiary_v1/_work/spec_bestiary.py \
        products/grimforge_bestiary_v1 --gallery      # NO --atlas (imported/textured meshes)
"""
import sys

sys.path.insert(0, r"D:/Projects/comfyui-toolchain/tools/asset_generators/lowpoly")
from imported_kit import pieces_from_dir  # noqa: E402

# every finished .glb in models_glb/ (skeleton_warrior + the 14 batch creatures)
PIECES = pieces_from_dir(r"D:/Projects/comfyui-toolchain/products/grimforge_bestiary_v1/models_glb")

AESTHETIC = "medieval"
TITLE = "GrimForge Bestiary — undead & demon creature kit"
HERO_VIEW = "3q"  # character-like verticals: 3/4 beauty shot, not top-down
