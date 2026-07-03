"""retarget_mocap — transfer a Mixamo/Rokoko (Character1_*) mocap clip onto a
renamed UniRig rig (role names from rename_unirig_bones.py).

STATUS (2026-07-02 rewrite): the GS1-era output was scrambled on EVERY rig; three
stacked root causes were found and fixed (validated on The Rookie, idle + walk):

1. UN-KEYED POSE LOCATIONS. The old transfer pinned every bone's world head at its
   rest position via `tb.matrix = ...` — which writes large per-bone pose LOCATIONS
   that were never keyframed. The in-scene pose looked right (hence the old "proven
   live" note), but the FBX export baked each frame's rotations against the LAST
   frame's stale locations — scrambled body. Fix: rotation-only transfer (children
   inherit position through the hierarchy) and key location on every bone.
2. MIRRORED SIDE LABELS. rename_unirig_bones.py assigns .l/.r by raw +/-X, which is
   anatomically mirrored on rigs that bind facing -Y (all TRELLIS/UniRig rigs here).
   Pairing source Left <-> target .l then CROSSES the limbs, and ALIGN aims each
   limb 180 deg into the body. Fix: bind-pose side-consistency check; swap the
   map's .l/.r roles when conventions differ.
3. FBX STUB BONE AXES. Rokoko/Mixamo FBX joints carry arbitrary joint-orient axes
   AND importer-synthesized stub tails, so neither quaternion@Y nor head->tail is
   the limb direction on the SOURCE. ALIGN now uses joint-to-CHILD-JOINT bind
   positions resolved via the role chain (spine + arm/leg chains) —
   orientation-proof on every skeleton.

FACING: src_z accepts "auto" (default): yaw = target facing (from foot-bone
geometry, real on glTF rigs) minus source facing (from its anatomically-
trustworthy Left/Right leg labels). Manual degrees still accepted.

ROOT MOTION: "transfer" (default) replays the source hips' world travel onto the
target hips, scaled by the leg-length ratio so the stride matches the character's
size; "off" = in place; a float synthesizes a constant forward speed
(target units/frame) for genuinely in-place source clips.

EXPORT: use FBX, not glTF. Blender's glTF exporter DROPS this baked armature
animation (exports a static rest pose), while FBX retains it. Output imports at
~0.01 scale (UniRig bind pose) — set the engine's FBX import Scale Factor (~100),
same as stock Mixamo FBX.

KNOWN LIMITS: end-of-chain bones (hands, feet) have no chain child to align by and
keep their bind orientation (slight foot tilt); minimal-arc alignment leaves elbow/
knee twist unconstrained (slight elbow kink); source hip bob is not transferred
when root_motion=off.

Usage (headless):
    blender --background --python retarget_mocap.py --         <renamed_rig.glb> <mocap.fbx> <map.json> <out.glb> <f0> <f1> [src_z_deg|auto] [root_motion]

    root_motion: transfer (default) | off | <float speed/frame>
"""
import bpy, sys, json, math
from mathutils import Matrix, Vector

a = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
RIG, MOCAP, MAP, OUT = a[0], a[1], a[2], a[3]
F0, F1 = int(a[4]), int(a[5])
# "auto" (default) = yaw from bind-pose facings; "auto_travel" = yaw so the CLIP'S
# TRAVEL aligns to the target's forward (use for locomotion — ROM takes have an
# arbitrary heading; the actor faces his travel, so this gives a straight,
# game-forward walk); a number = manual degrees.
SRC_Z = "auto"
if len(a) > 6:
    _v = a[6].strip().lower()
    SRC_Z = _v if _v in ("auto", "auto_travel") else math.radians(float(_v))
# root motion: "transfer" (default) replays the source hips' world travel onto the
# target hips (scaled to the target's leg length); "straight" = transfer with the
# XY offsets projected onto the mean travel axis (kills the lateral wander of ROM
# takes; Z bob kept); "off" = in-place (legacy); a float = synthesize a constant
# forward speed (target units/frame) for in-place sources.
ROOT_MOTION = a[7] if len(a) > 7 else "transfer"
STRAIGHT = ROOT_MOTION == "straight"   # straight is transfer + axis projection
# bind alignment: aim each target bone's rest to the source bone's rest DIRECTION before
# transfer, so limb directions track the source (fixes the arms-up/frozen artifact from the
# wide-T UniRig bind). "on" (default) | "off" (legacy full-quaternion transfer).
ALIGN = (a[8] if len(a) > 8 else "on").lower() != "off"


def imp(path):
    p = path.lower()
    if p.endswith(".bvh"):                       # CMU/clean mocap BVH (Y-up -> Z-up)
        bpy.ops.import_anim.bvh(filepath=path, update_scene_fps=False,
                                update_scene_duration=True)
    elif p.endswith((".glb", ".gltf")):
        bpy.ops.import_scene.gltf(filepath=path)
    else:
        bpy.ops.import_scene.fbx(filepath=path)


def main():
    bpy.ops.object.select_all(action='SELECT'); bpy.ops.object.delete()
    imp(RIG)
    tgt = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
    tgt_mesh = next((o for o in bpy.data.objects if o.type == 'MESH'), None)
    pre = set(bpy.data.objects)
    imp(MOCAP)
    src = next(o for o in bpy.data.objects if o.type == 'ARMATURE' and o not in pre)

    bone_map = json.load(open(MAP, encoding="utf-8"))["bone_map"]

    # --- facing + side-convention calibration (bind poses, label-independent) ----
    # Facing comes from the FEET (bone head->tail = heel->toe = forward), which is
    # front/back-unambiguous and independent of .l/.r naming. UniRig rigs renamed by
    # rename_unirig_bones.py have their .l/.r labels assigned by raw +/-X (viewer
    # side), which is anatomically MIRRORED on rigs that bind facing -Y — so labels
    # cannot be trusted for facing, and the map pairing may cross limbs (see below).
    def _bind_pos(arm, pb):
        return (arm.matrix_world @ pb.bone.matrix_local).translation

    def _feet_facing(arm, foot_names):
        # geometric foot direction (head->tail). Valid for glTF/UniRig targets whose
        # bones have real tails; NOT valid for FBX stub-tail sources.
        fwd = Vector((0.0, 0.0, 0.0))
        for n in foot_names:
            pb = arm.pose.bones.get(n)
            if pb:
                h = arm.matrix_world @ pb.bone.head_local
                t = arm.matrix_world @ pb.bone.tail_local
                v = t - h
                v.z = 0.0
                if v.length > 1e-9:
                    fwd += v.normalized()
        return math.atan2(fwd.y, fwd.x) if fwd.length > 1e-9 else None

    def _label_facing(arm, name_l, name_r):
        # facing from anatomically-trustworthy .l/.r labels (Mixamo/Rokoko sources):
        # fwd = (left - right) x up.
        bl, br = arm.pose.bones.get(name_l), arm.pose.bones.get(name_r)
        if not (bl and br):
            return None
        pl = (arm.matrix_world @ bl.bone.matrix_local).translation
        pr = (arm.matrix_world @ br.bone.matrix_local).translation
        fwd = (pl - pr).cross(Vector((0.0, 0.0, 1.0)))
        return math.atan2(fwd.y, fwd.x) if fwd.length > 1e-9 else None

    s_lleg = next((s for s, r in bone_map.items() if r == "upperleg.l"), None)
    s_rleg = next((s for s, r in bone_map.items() if r == "upperleg.r"), None)

    def _src_facing():
        return _label_facing(src, s_lleg or "", s_rleg or "")

    def _tgt_facing():
        return _feet_facing(tgt, ["foot.l", "foot.r"])

    def _src_travel(f0, f1):
        """Source hip XY travel (direction, length) over [f0,f1], pre-yaw world."""
        s_hips_n = next((s for s, r in bone_map.items() if r == "hips"), None)
        hb = src.pose.bones.get(s_hips_n) if s_hips_n else None
        if hb is None:
            return None, 0.0
        sc0 = bpy.context.scene
        sc0.frame_set(f0)
        bpy.context.view_layer.update()
        p0 = (src.matrix_world @ hb.matrix).translation.copy()
        sc0.frame_set(f1)
        bpy.context.view_layer.update()
        p1 = (src.matrix_world @ hb.matrix).translation.copy()
        tr = p1 - p0
        tr.z = 0.0
        return (math.atan2(tr.y, tr.x) if tr.length > 1e-6 else None), tr.length

    if SRC_Z in ("auto", "auto_travel"):
        t_f = _tgt_facing()
        yaw = 0.0
        how = "facing"
        if SRC_Z == "auto_travel":
            s_dir, s_len = _src_travel(F0, F1)
            if s_dir is not None and t_f is not None and s_len > 0.05:
                yaw = t_f - s_dir      # clip travel -> target forward
                how = f"travel(len={s_len:.3f})"
        if how == "facing":
            s_f = _src_facing()
            yaw = (t_f - s_f) if (t_f is not None and s_f is not None) else 0.0
        # DELTA rotation, not rotation_euler: the source armature OBJECT carries
        # keyed transforms from the FBX import, so frame_set() would overwrite a
        # base-rotation yaw during the bake (rest would see the yaw, frames not —
        # a constant spurious delta). delta_rotation composes on top of the keys.
        src.delta_rotation_euler.z += yaw
        print(f"SRC_Z {SRC_Z}: yaw={math.degrees(yaw):.1f} deg via {how}")
    else:
        src.delta_rotation_euler.z += SRC_Z
    bpy.context.view_layer.update()

    # side-consistency: if (after yaw) the source's Left leg sits on the OPPOSITE
    # side of the body from the target's ".l" leg, the label conventions differ —
    # pairing left<->.l would cross the limbs (ALIGN then aims each limb 180 deg
    # into the body: the classic scrambled result). Swap .l/.r roles in the map.
    def _lat_offset(arm, hips_pb, limb_pb, fwd_ang):
        off = _bind_pos(arm, limb_pb) - _bind_pos(arm, hips_pb)
        # lateral = component along (up x fwd) = character's left axis
        fwd_v = Vector((math.cos(fwd_ang), math.sin(fwd_ang), 0.0))
        left_v = Vector((0.0, 0.0, 1.0)).cross(fwd_v)
        return off.dot(left_v)

    s_hips = next((s for s, r in bone_map.items() if r == "hips"), None)
    swap_sides = False
    if s_hips and s_lleg:
        t_f2 = _tgt_facing()
        s_f2 = _src_facing()
        t_hips = tgt.pose.bones.get("hips")
        t_lleg = tgt.pose.bones.get("upperleg.l")
        sb_h = src.pose.bones.get(s_hips)
        sb_l = src.pose.bones.get(s_lleg)
        if all((t_hips, t_lleg, sb_h, sb_l)) and t_f2 is not None and s_f2 is not None:
            s_side = _lat_offset(src, sb_h, sb_l, s_f2)
            t_side = _lat_offset(tgt, t_hips, t_lleg, t_f2)
            swap_sides = (s_side * t_side) < 0
    if swap_sides:
        def _flip(role):
            if role.endswith(".l"):
                return role[:-2] + ".r"
            if role.endswith(".r"):
                return role[:-2] + ".l"
            return role
        bone_map = {s: _flip(r) for s, r in bone_map.items()}
        print("SIDE_SWAP on: target .l/.r labels are mirrored vs source — map crossed to match anatomy")
    else:
        print("SIDE_SWAP off: label conventions agree")
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
    # Bind-direction ALIGNMENT: the transfer applies the source's world-rotation delta to
    # the TARGET bind, so target_dir(f) = delta . target_bind_dir. When a bone's target bind
    # axis differs from the source's (notably the arms on the wide-T UniRig bind), that
    # diverges from the source pose — the "arms forced up / frozen" artifact. Aiming each
    # target bind to point the SAME world direction as the source bind makes target_dir(f)
    # track source_dir(f). A no-op where binds already align (legs).
    # ALIGN uses JOINT-TO-CHILD-JOINT bind directions — the only orientation-proof
    # limb axis. FBX sources (Rokoko/Mixamo) have BOTH arbitrary joint-orient axes
    # (quaternion@Y is garbage) AND synthesized stub tails (head->tail is garbage);
    # child-joint POSITIONS are real on every skeleton. Resolved via the role chain.
    CHAIN_CHILD = {"hips": "spine", "spine": "chest", "chest": "neck",
                   "shoulder.l": "upperarm.l", "upperarm.l": "lowerarm.l",
                   "lowerarm.l": "hand.l",
                   "shoulder.r": "upperarm.r", "upperarm.r": "lowerarm.r",
                   "lowerarm.r": "hand.r",
                   "upperleg.l": "lowerleg.l", "lowerleg.l": "foot.l",
                   "upperleg.r": "lowerleg.r", "lowerleg.r": "foot.r"}
    inv_map = {}
    for s, r in bone_map.items():
        inv_map.setdefault(r, s)

    def _head_w(arm, bone):
        return arm.matrix_world @ bone.head_local

    Y = Vector((0.0, 1.0, 0.0))
    rest = {}
    aligned_n = 0
    for sb, tb in pairs:
        sbind = src.matrix_world @ sb.bone.matrix_local
        tbind = tgt.matrix_world @ tb.bone.matrix_local
        rest[("s", sb.name)] = sbind.to_quaternion()
        rest[("t", tb.name)] = tbind                        # matrix: rest position (+ root motion)
        tq_rest = tbind.to_quaternion()
        if ALIGN:
            child_role = CHAIN_CHILD.get(tb.name)
            s_child = src.pose.bones.get(inv_map.get(child_role, "")) if child_role else None
            t_child = tgt.pose.bones.get(child_role) if child_role else None
            if s_child and t_child:
                sdir = _head_w(src, s_child.bone) - _head_w(src, sb.bone)
                tdir = _head_w(tgt, t_child.bone) - _head_w(tgt, tb.bone)
                if sdir.length > 1e-9 and tdir.length > 1e-9:
                    # aim the target's VISUAL bone axis (pose-matrix Y = head->tail,
                    # real on Blender-built/glTF bones) along the source's bind limb:
                    # then dir(f) = delta @ sdir_bind tracks the source limb exactly.
                    tvis = (tq_rest @ Y).normalized()
                    tq_rest = tvis.rotation_difference(sdir.normalized()) @ tq_rest
                    aligned_n += 1
        rest[("tq", tb.name)] = tq_rest                     # aligned rest ORIENTATION
    print(f"ALIGN chain-child: {aligned_n}/{len(pairs)} bones aligned")

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
            # "straight": project XY travel onto the clip's mean travel axis so ROM
            # takes don't wander laterally (Z bob is kept as-is).
            axis_v = None
            if STRAIGHT:
                sc.frame_set(F1)
                tr = (src.matrix_world @ hsb.matrix).translation - src_hip_f0
                tr.z = 0.0
                axis_v = tr.normalized() if tr.length > 1e-6 else None
                sc.frame_set(F0)
            def root_off_fn(f):
                now = (src.matrix_world @ hsb.matrix).translation
                off = (now - src_hip_f0) * root_scale
                if axis_v is not None:
                    off = axis_v * Vector((off.x, off.y, 0.0)).dot(axis_v) \
                          + Vector((0.0, 0.0, off.z))
                return off
            print(f"ROOT_MOTION {'straight' if STRAIGHT else 'transfer'} "
                  f"src_leg={src_leg} tgt_leg={tgt_leg} scale={root_scale:.4f}")
    else:
        print("ROOT_MOTION off (in-place)")

    for f in range(F0, F1 + 1):
        sc.frame_set(f)
        root_off = root_off_fn(f)
        for sb, tb in pairs:
            sq = (src.matrix_world @ sb.matrix).to_quaternion()
            delta = sq @ rest[("s", sb.name)].inverted()          # world rotation from rest
            tq = delta @ rest[("tq", tb.name)]                    # apply to aligned target rest
            # ROTATION-ONLY transfer: children inherit position through the posed
            # hierarchy (standard retarget). Pinning every bone's world head at its
            # rest position (the old behavior) required large per-bone pose LOCATIONS
            # that were never keyed — the FBX export then baked each frame's rotations
            # against the LAST frame's stale locations, scrambling the body.
            if tb is root_hips:
                loc = rest[("t", tb.name)].translation + root_off  # root carries travel
            else:
                loc = (tgt.matrix_world @ tb.matrix).translation   # inherit from posed parent
            tw = Matrix.Translation(loc) @ tq.to_matrix().to_4x4()
            tb.matrix = tgt.matrix_world.inverted() @ tw
            bpy.context.view_layer.update()  # parent posed before child reads it
            tb.keyframe_insert("rotation_quaternion", frame=f - F0)
            tb.keyframe_insert("location", frame=f - F0)  # key ALL channels the pose uses


    # transfer-fidelity handshake: the exported clip's hip travel should match this
    # (frame F1 root offset). batch_retarget parses it and measures the actual
    # travel on the exported FBX — direction error ~0 and magnitude ratio ~1 is the
    # honest gate (unlike the old bind-facing "misalign", which was noise).
    sc.frame_set(F1)
    _exp = root_off_fn(F1)
    print(f"EXPECTED_TRAVEL {_exp.x:.4f} {_exp.y:.4f} {_exp.z:.4f}")

    # drop EVERYTHING imported with the mocap — the source armature AND any skinned
    # source mesh it brought in — keeping only the target rig+mesh (the objects present
    # in `pre`, captured after the rig import). Rokoko/Mixamo source FBX usually include
    # their own character mesh; leaving it in the export adds a second, differently-scaled
    # mesh (~100x) that swamps the target and renders as a flat sprawl.
    for o in [obj for obj in bpy.data.objects if obj not in pre]:
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
