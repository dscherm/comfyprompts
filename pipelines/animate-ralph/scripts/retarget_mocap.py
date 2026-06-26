"""retarget_mocap — transfer a Mixamo/Rokoko (Character1_*) mocap clip onto a
renamed UniRig rig (role names from rename_unirig_bones.py).

STATUS: rotation transfer WORKING (proven live via blender-mcp — an upright,
walking barbarian; see validation/retarget/walk_f*.png). The earlier collapse was
a SCALE bug: the source is scaled 0.01 (Mixamo cm->m) and .to_3x3() baked that
into the rotation matrices. Pure quaternions (below) fix it.

ROOT MOTION: the body now translates forward (see the optional <root_motion> arg).
"transfer" (default) replays the source hips' world travel onto the target hips,
scaled by the leg-length ratio so the stride matches the character's size; "off"
restores the legacy in-place behavior; a float synthesizes a constant forward
speed (target units/frame) for genuinely in-place source clips.

EXPORT: use FBX, not glTF. Blender's glTF exporter DROPS this baked armature
animation (exports a static rest pose); FBX retains it (verified: distinct walk
poses across frames). Output imports at ~0.01 scale (UniRig bind pose) — set the
engine's FBX import Scale Factor (~100), same as stock Mixamo FBX.

Rest-pose-relative WORLD-rotation transfer: for each mapped bone, the source's
rotation *relative to its own rest* (in world space) is applied to the target's
rest — so differing bone orientations between the two skeletons are handled. A
src_z facing offset (degrees) aligns the source's facing to the target's; that
same alignment carries the root-motion translation, so forward is forward.

Usage (headless):
    blender --background --python retarget_mocap.py -- \
        <renamed_rig.glb> <mocap.fbx> <map.json> <out.glb> <f0> <f1> [src_z_deg] [root_motion]

    root_motion: transfer (default) | off | <float speed/frame>
"""
import bpy, sys, json, math
from mathutils import Matrix, Vector

a = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
RIG, MOCAP, MAP, OUT = a[0], a[1], a[2], a[3]
F0, F1 = int(a[4]), int(a[5])
SRC_Z = math.radians(float(a[6])) if len(a) > 6 else 0.0
# root motion: "transfer" (default) replays the source hips' world travel onto the
# target hips (scaled to the target's leg length); "off" = in-place (legacy); a float
# = synthesize a constant forward speed (target units/frame) for in-place sources.
ROOT_MOTION = a[7] if len(a) > 7 else "transfer"


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

    # --- root motion --------------------------------------------------------------
    # Each bone below is posed by its ABSOLUTE world matrix, so to translate the body
    # forward we offset EVERY bone's world target by the same per-frame root vector
    # (a rigid shift) and key `location` only on the hips — children keep their rest
    # *local* transform and ride along with the moved parent, so the gait is intact.
    # Without this, pinning every bone to its rest world position is what made the
    # walk play in place.
    hips_pair = next(((sb, tb) for sb, tb in pairs if tb.name == "hips"), None)
    root_hips = hips_pair[1] if hips_pair else None
    root_off_fn = (lambda f: Vector((0.0, 0.0, 0.0)))            # "off"
    if ROOT_MOTION != "off" and hips_pair is not None:
        hsb, htb = hips_pair
        try:
            speed = float(ROOT_MOTION)                           # synthesize constant speed
            fwd = (tgt.matrix_world.to_3x3() @ Vector((0.0, 1.0, 0.0))).normalized()
            root_off_fn = lambda f: fwd * (speed * (f - F0))
            print(f"ROOT_MOTION synthesize speed={speed}/frame fwd={tuple(round(c,2) for c in fwd)}")
        except ValueError:                                       # "transfer": scaled source travel
            sc.frame_set(F0)
            src_hip_f0 = (src.matrix_world @ hsb.matrix).translation.copy()  # start = no jump
            # Size proxy = leg length (hips->foot world distance). A Euclidean length is
            # orientation- and sign-safe, unlike hip Z (UniRig rigs import with the hips
            # below origin / a non-Z up axis, which gives a bogus negative scale).
            def _leg(arm, hips_b, foot_name):
                fb = arm.pose.bones.get(foot_name)
                if not fb:
                    return None
                hp = (arm.matrix_world @ hips_b.bone.matrix_local).translation
                fp = (arm.matrix_world @ fb.bone.matrix_local).translation
                return (hp - fp).length
            src_foot = next((s for s, r in bone_map.items() if r == "foot.r"), None)
            src_leg = _leg(src, hsb, src_foot) if src_foot else None
            tgt_leg = _leg(tgt, htb, "foot.r")
            root_scale = (tgt_leg / src_leg) if (src_leg and tgt_leg and src_leg > 1e-6) else 1.0
            def root_off_fn(f):
                now = (src.matrix_world @ hsb.matrix).translation
                return (now - src_hip_f0) * root_scale
            print(f"ROOT_MOTION transfer src_leg={src_leg} tgt_leg={tgt_leg} scale={root_scale:.4f}")
    else:
        print("ROOT_MOTION off (in-place)")

    for f in range(F0, F1 + 1):
        sc.frame_set(f)
        root_off = root_off_fn(f)
        for sb, tb in pairs:
            sq = (src.matrix_world @ sb.matrix).to_quaternion()
            delta = sq @ rest[("s", sb.name)].inverted()          # world rotation from rest
            tq = delta @ rest[("t", tb.name)].to_quaternion()     # apply to target rest
            loc = rest[("t", tb.name)].translation + root_off     # rigid forward shift
            tw = Matrix.Translation(loc) @ tq.to_matrix().to_4x4()
            tb.matrix = tgt.matrix_world.inverted() @ tw
            bpy.context.view_layer.update()  # parent posed before child reads it
            tb.keyframe_insert("rotation_quaternion", frame=f - F0)
            if tb is root_hips and ROOT_MOTION != "off":
                tb.keyframe_insert("location", frame=f - F0)      # only the hips carries translation

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
