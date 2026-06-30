"""Blender smoke test for kitlib.Kit — builds a tiny piece with every primitive,
joins it, exports a GLB, and prints a result line for the harness to grep.

Run headless::

    blender -b --python kitlib_smoke.py -- <out_dir>

Exits non-zero on failure. The pure DSL surface is covered by
tests/test_kitlib.py; this exercises the bpy-dependent builders.
"""

import os
import sys

# Make kitlib importable regardless of Blender's cwd.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from kitlib import Kit, validate_palette  # noqa: E402


def main() -> int:
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    out_dir = argv[0] if argv else os.path.join(os.path.dirname(__file__), "_smoke")
    os.makedirs(out_dir, exist_ok=True)
    glb = os.path.join(out_dir, "kitlib_smoke.glb")

    validate_palette()
    k = Kit(reset_scene=True)
    parts: list = []
    k.box(parts, 1.0, 1.0, 0.6, (0, 0, 0.3), "stone")            # base
    k.cyl(parts, 8, 0.15, 0.7, (0, 0, 0.95), "wood")             # post
    k.cone(parts, 7, 0.5, 0, 0.7, (0, 0, 1.6), "leaf")           # canopy
    k.ico(parts, 0.12, (0.3, 0.3, 0.7), "fire", sub=1)           # emissive bead
    k.gable(parts, 1.0, 1.0, 0.5, (0, 0, 0.6), "slate")          # roof
    obj = k.join(parts, "smoke_piece")
    nverts = len(obj.data.vertices)
    nmats = len(obj.data.materials)
    k.export_glb(obj, glb)

    glb_bytes = os.path.getsize(glb) if os.path.isfile(glb) else 0
    ok = glb_bytes > 0 and nverts > 0
    print(
        f"KITLIB_SMOKE result={'OK' if ok else 'FAIL'} "
        f"verts={nverts} mats={nmats} glb_bytes={glb_bytes} path={glb}"
    )
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
