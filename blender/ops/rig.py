"""Rig ops: wrap the quad-rig procedural cycle script
(products/grimforge_bestiary_v1/_quadrig/quad_anim_v2.py)."""

from pathlib import Path

import bpy

from . import REPO_ROOT, default_out, register, require_file, run_script

QUAD_ANIM = REPO_ROOT / "products" / "grimforge_bestiary_v1" / "_quadrig" / "quad_anim_v2.py"
CLIPS = ("idle", "walk", "run", "attack")


@register("apply_cycle")
def apply_cycle(path=None, clip=None, out=None):
    """Author the procedural quadruped cycles on a UniRig-rigged GLB and export a
    GLB carrying `clip` (one of idle/walk/run/attack), or all four with
    clip='all'. quad_anim_v2.py authors all four as NLA tracks; for a single clip
    the other tracks are dropped and the GLB is re-exported."""
    src = require_file(path)
    if clip not in (*CLIPS, "all"):
        raise ValueError(f"apply_cycle clip must be one of {', '.join(CLIPS)} or 'all', got {clip!r}")
    dst = out or default_out(src, f"apply_cycle_{clip}")
    log = run_script(QUAD_ANIM, [src, dst])
    if clip != "all":
        arm = next(o for o in bpy.context.scene.objects if o.type == "ARMATURE")
        for tr in list(arm.animation_data.nla_tracks):
            if tr.name != clip:
                arm.animation_data.nla_tracks.remove(tr)
        for name in [a.name for a in bpy.data.actions if a.name != clip]:
            bpy.data.actions.remove(bpy.data.actions[name])
        bpy.ops.object.select_all(action="SELECT")
        bpy.ops.export_scene.gltf(filepath=dst, export_format="GLB", use_selection=True,
                                  export_animations=True, export_nla_strips=True)
        log += f"\napply_cycle: kept clip '{clip}' only"
    if not Path(dst).is_file():
        raise RuntimeError(f"quad_anim_v2.py wrote no file at {dst}\n{log}")
    return dst, log
