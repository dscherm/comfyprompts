"""retarget_mocap — transfer a Mixamo/Rokoko (Character1_*) mocap clip onto a
renamed UniRig rig (role names from rename_unirig_bones.py).

STATUS: rotation transfer WORKING (proven live via blender-mcp — an upright,
walking barbarian; see validation/retarget/walk_f*.png). The earlier collapse was
a SCALE bug: the source is scaled 0.01 (Mixamo cm->m) and .to_3x3() baked that
into the rotation matrices. Pure quaternions (below) fix it. In-place (no root
motion); a minor head-bone artifact may still want tuning.

EXPORT: use FBX, not glTF. Blender's glTF exporter DROPS this baked armature
animation (exports a static rest pose); FBX retains it (verified: distinct walk
poses across frames). Output imports at ~0.01 scale (UniRig bind pose) — set the
engine's FBX import Scale Factor (~100), same as stock Mixamo FBX.

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
    # UniRig's auto-rename mis-detects the upper spine on some rigs ("neck" ends up
    # being the arm-branch bone, "head" hangs off an unnamed bone), so retargeting
    # head/neck swings the head into a stretched artifact. Leave them at rest — a
    # neutral head reads fine on a walk. (Arms are separate bones, still retargeted.)
    SKIP_ROLES = {"head", "neck"}
    pairs = []
    for sname, role in bone_map.items():
        if role in SKIP_ROLES:
            continue
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

    # rest as pure-rotation QUATERNIONS (scale-free — the source is often scaled
    # 0.01 (Mixamo cm->m); .to_3x3() would bake that scale in and collapse the rig).
    rest = {}
    for sb, tb in pairs:
        rest[("s", sb.name)] = (src.matrix_world @ sb.bone.matrix_local).to_quaternion()
        rest[("t", tb.name)] = (tgt.matrix_world @ tb.bone.matrix_local)

    sc = bpy.context.scene
    for f in range(F0, F1 + 1):
        sc.frame_set(f)
        for sb, tb in pairs:
            sq = (src.matrix_world @ sb.matrix).to_quaternion()
            delta = sq @ rest[("s", sb.name)].inverted()          # world rotation from rest
            tq = delta @ rest[("t", tb.name)].to_quaternion()     # apply to target rest
            loc = rest[("t", tb.name)].translation                # keep rest position (in-place)
            tw = Matrix.Translation(loc) @ tq.to_matrix().to_4x4()
            tb.matrix = tgt.matrix_world.inverted() @ tw
            bpy.context.view_layer.update()  # parent posed before child reads it
            tb.keyframe_insert("rotation_quaternion", frame=f - F0)

    # drop the source armature; export only the retargeted rig+mesh
    for o in (src,):
        bpy.data.objects.remove(o, do_unlink=True)
    sc.frame_start = 0; sc.frame_end = F1 - F0
    for o in bpy.data.objects:
        o.select_set(o.type in ("ARMATURE", "MESH"))
    bpy.context.view_layer.objects.active = tgt
    # Export FBX, NOT glTF: Blender's glTF exporter drops this baked armature
    # animation (exports a static rest pose), while FBX retains it — and FBX is
    # the game-engine format anyway. Output imports at ~0.01 scale (UniRig bind
    # pose); set the engine's FBX import Scale Factor (~100), like stock Mixamo.
    out_fbx = OUT.rsplit(".", 1)[0] + ".fbx"
    bpy.ops.export_scene.fbx(filepath=out_fbx, use_selection=True, bake_anim=True,
                             add_leaf_bones=False, object_types={'ARMATURE', 'MESH'})
    print(f"RETARGET_DONE frames {F1-F0+1} -> {out_fbx}")


main()
