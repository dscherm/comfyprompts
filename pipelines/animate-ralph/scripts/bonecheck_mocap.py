"""bonecheck_mocap.py — vet candidate mocap clips for retargeting onto a rig.

For each source clip, replicates retarget_mocap.py's pairing (source Character1_* bone
present AND target role present AND role not in the head/neck skip set) to report the
true MATCHED/20 count, and measures the source hips' travel + vertical range so the
root-motion policy (transfer vs off) can be set from evidence rather than guessed.

Usage (headless):
    blender --background --python bonecheck_mocap.py -- <rig.glb> <map.json> <clip1.fbx> [clip2.fbx ...]
"""
import bpy, sys, json, os
from mathutils import Vector

a = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
RIG, MAP = a[0], a[1]
CLIPS = a[2:]
SKIP = {"head", "neck"}
bone_map = json.load(open(MAP, encoding="utf-8"))["bone_map"]


def imp(path):
    (bpy.ops.import_scene.gltf if path.lower().endswith((".glb", ".gltf"))
     else bpy.ops.import_scene.fbx)(filepath=path)


def hips_metrics(arm):
    """(xy_travel, z_range, frames) for the source hips over the clip."""
    hb = arm.pose.bones.get("Character1_Hips")
    sc = bpy.context.scene
    f0, f1 = sc.frame_start, sc.frame_end
    if not hb:
        return None, None, (f0, f1)
    p0 = None
    zs = []
    xymax = 0.0
    for f in range(f0, f1 + 1):
        sc.frame_set(f)
        p = (arm.matrix_world @ hb.matrix).translation.copy()
        if p0 is None:
            p0 = p
        zs.append(p.z)
        d = (Vector((p.x, p.y, 0)) - Vector((p0.x, p0.y, 0))).length
        xymax = max(xymax, d)
    return xymax, (max(zs) - min(zs)), (f0, f1)


# target roles present
imp(RIG)
tgt = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
tgt_roles = {pb.name for pb in tgt.pose.bones}

for clip in CLIPS:
    pre = set(bpy.data.objects)
    imp(clip)
    src = next((o for o in bpy.data.objects if o.type == 'ARMATURE' and o not in pre), None)
    name = os.path.basename(clip)
    if src is None:
        print(f"BONECHECK {name} matched=0/20 ERROR=no_armature")
        continue
    src_bones = {pb.name for pb in src.pose.bones}
    matched = sum(1 for s, r in bone_map.items()
                  if r not in SKIP and s in src_bones and r in tgt_roles)
    xy, zr, (f0, f1) = hips_metrics(src)
    xy_s = f"{xy:.3f}" if xy is not None else "n/a"
    zr_s = f"{zr:.3f}" if zr is not None else "n/a"
    print(f"BONECHECK {name} matched={matched}/20 frames={f1 - f0 + 1} "
          f"hips_xy_travel={xy_s} hips_z_range={zr_s}")
    # drop the source so the next clip imports clean
    for o in list(bpy.data.objects):
        if o not in pre:
            bpy.data.objects.remove(o, do_unlink=True)
