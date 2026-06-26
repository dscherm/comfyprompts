"""retarget_mocap — transfer a Mixamo/Rokoko (Character1_*) mocap clip onto a
renamed UniRig rig (role names from rename_unirig_bones.py).

STATUS: SCAFFOLD / NOT WORKING YET. Bone matching is solid (20/20 via the map),
the clip loads, and it runs end-to-end — but the blind rest-pose-relative world
transfer below COLLAPSES the rig (verified: barbarian + zombiewalk → flat sprawl,
while the same renamed rig renders upright statically). Proper retargeting needs
rest-pose calibration the addons do (Rokoko/Auto-Rig Pro) or the blender-mcp
visual-iteration loop — a headless one-shot transfer is not enough. Kept as the
tool skeleton + the empirical finding; do NOT treat its output as usable.

Rest-pose-relative WORLD-rotation transfer: for each mapped bone, the source's
rotation *relative to its own rest* (in world space) is applied to the target's
rest — so differing bone orientations between the two skeletons are handled.
Rotation only / in-place (no root motion) for a clean first pass. A --src-z
facing offset (degrees) aligns the source's facing to the target's.

Usage (headless):
    blender --background --python retarget_mocap.py -- \
        <renamed_rig.glb> <mocap.fbx> <map.json> <out.glb> <f0> <f1> [src_z_deg]
"""
import bpy, sys, json, math
from mathutils import Matrix

a = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
RIG, MOCAP, MAP, OUT = a[0], a[1], a[2], a[3]
F0, F1 = int(a[4]), int(a[5])
SRC_Z = math.radians(float(a[6])) if len(a) > 6 else 0.0


def imp(path):
    (bpy.ops.import_scene.gltf if path.lower().endswith((".glb", ".gltf"))
     else bpy.ops.import_scene.fbx)(filepath=path)


def main():
    bpy.ops.object.select_all(action='SELECT'); bpy.ops.object.delete()
    imp(RIG)
    tgt = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
    tgt_mesh = next((o for o in bpy.data.objects if o.type == 'MESH'), None)
    pre = set(bpy.data.objects)
    imp(MOCAP)
    src = next(o for o in bpy.data.objects if o.type == 'ARMATURE' and o not in pre)
    src.rotation_euler.z += SRC_Z
    bpy.context.view_layer.update()

    bone_map = json.load(open(MAP, encoding="utf-8"))["bone_map"]
    pairs = []
    for sname, role in bone_map.items():
        sb = src.pose.bones.get(sname); tb = tgt.pose.bones.get(role)
        if sb and tb:
            tb.rotation_mode = 'QUATERNION'
            pairs.append((sb, tb))
    def depth(pb):
        d = 0; p = pb.bone.parent
        while p: d += 1; p = p.parent
        return d
    pairs.sort(key=lambda pr: depth(pr[1]))  # parents first
    print(f"MATCHED {len(pairs)}/{len(bone_map)} bones")

    # rest world matrices (src includes facing rotation via matrix_world)
    rest = {}
    for sb, tb in pairs:
        rest[sb.name] = (src.matrix_world @ sb.bone.matrix_local).to_3x3()
        rest[tb.name] = (tgt.matrix_world @ tb.bone.matrix_local)

    sc = bpy.context.scene
    for f in range(F0, F1 + 1):
        sc.frame_set(f)
        for sb, tb in pairs:
            src_w3 = (src.matrix_world @ sb.matrix).to_3x3()
            delta = src_w3 @ rest[sb.name].inverted()
            tgt_w3 = delta @ rest[tb.name].to_3x3()
            tgt_w = Matrix.Translation(rest[tb.name].translation) @ tgt_w3.to_4x4()
            tb.matrix = tgt.matrix_world.inverted() @ tgt_w
            bpy.context.view_layer.update()  # parent posed before child reads it
            tb.keyframe_insert("rotation_quaternion", frame=f - F0)

    # drop the source armature; export only the retargeted rig+mesh
    for o in (src,):
        bpy.data.objects.remove(o, do_unlink=True)
    sc.frame_start = 0; sc.frame_end = F1 - F0
    for o in bpy.data.objects:
        o.select_set(o.type in ("ARMATURE", "MESH"))
    bpy.context.view_layer.objects.active = tgt
    bpy.ops.export_scene.gltf(filepath=OUT, use_selection=True, export_format="GLB",
                              export_animations=True, export_frame_range=True)
    print(f"RETARGET_DONE frames {F1-F0+1} -> {OUT}")


main()
