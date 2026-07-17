"""Humanoid walk cycle driven ENTIRELY by a measured rig manifest.

Consumes <rig>.rigvec.json (see rig_scan.py). Contains ZERO hardcoded signs,
axes, or bone names — every rig-specific fact is read from the manifest, so the
same recipe drives any humanoid rig regardless of rigger or naming convention.

This replaces unirig_humanoid_walk.py, which hardcoded exactly the facts the
scanner now measures and got two of them wrong (knee sign copied from the
QUADRUPED animator -> backwards knees; arms swung about the side axis while the
rest pose was a T-POSE, so they twisted instead of swinging).

The one thing that is DERIVED rather than measured, and why it is safe:
  Rotating a downward-resting limb about `side` by +theta always tilts it toward
  `forward`. Proof, given side = forward x up and limb rest_dir = -up:
      (side x -up) = -[(forward x up) x up] = -[up(forward.up) - forward(up.up)]
                   = -[0 - forward] = forward
      v_rot = -up*cos(t) + forward*sin(t)   =>   v_rot . forward = sin(t) > 0
  So +swing = forward holds for ANY rig whose frame follows that definition —
  it is a consequence of the frame, not an assumption about a particular rig.

Usage:
    blender --background --factory-startup --python humanoid_walk.py \\
        -- <rigged.glb|fbx> <rig.rigvec.json> <out.glb> [frames]
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Matrix, Quaternion, Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
from hand_pose import pose_relaxed_hands  # noqa: E402

argv = sys.argv[sys.argv.index("--") + 1 :]
SRC, MANIFEST_PATH, DST = argv[0], argv[1], argv[2]
FRAMES = int(argv[3]) if len(argv) > 3 else 24

# ---------------------------------------------------------------------------
# NORMATIVE SAGITTAL GAIT KINEMATICS  (see wiki: anatomy-of-the-human-walk-cycle)
#
# Replaces a hand-invented sin/cos model that was copied from the QUADRUPED
# animator and had no biomechanical basis. Source: Perry's gait phases +
# normative sagittal joint angles (musculoskeletalkey.com/normal-gait/).
#
# Convention: percent of gait cycle, 0% = initial contact (heel strike) of THIS
# leg, toe-off ~60%, next heel strike = 100%. Flexion POSITIVE for hip and knee.
#
# The critical relationship — and the whole reason the old model looked wrong:
#   peak KNEE flexion (~62 deg) lands at ~70-73% (initial swing)
#   peak HIP  flexion (~30 deg) lands at ~85-90% (terminal swing)
# The knee LEADS the hip by roughly 15-20% of the cycle. The limb swings as a
# kinetic chain: thigh drives forward, the shank lags and the knee folds, then
# the shank whips out and the knee extends just before heel strike. A symmetric
# sin/cos pair cannot express that lag, which is why thigh and shin appeared to
# move together.
GAIT = [
    # (pct, hip, knee)
    (0,    30,   5),   # initial contact — hip flexed, knee nearly straight
    (10,   25,  18),   # loading response — knee flexes to absorb shock
    (20,   15,  12),
    (30,    5,   5),   # midstance — knee re-extends
    (40,   -5,   5),   # terminal stance — hip extending behind
    (50,  -15,   8),
    (60,  -10,  40),   # toe-off — knee ALREADY folding fast, hip still behind
    (70,    5,  62),   # initial swing — KNEE PEAK, hip only just past neutral
    (80,   20,  45),   # mid-swing — knee extending while hip keeps flexing
    (90,   30,  15),   # terminal swing — HIP PEAK, shank whipping out
    (100,  30,   5),   # next initial contact
]

# Arm swing (see wiki: anatomy-of-the-human-walk-cycle). One shoulder oscillation
# per gait cycle, OUT of phase with the ipsilateral leg (left leg forward = right
# arm forward). Normative: shoulder flexion/extension ~+/-22 deg; elbow ~30 deg ROM
# and — the detail that stops the hand clipping the body — the elbow FLEXES MORE as
# the arm swings FORWARD (carrying a ~18 deg baseline that rises to ~42 deg), then
# extends toward baseline as the arm goes back. A dead-straight elbow (the earlier
# model) sweeps the hand through the hip on the forward swing.
SHOULDER_AMP = 14.0            # deg, peak shoulder flex/ext (was 22 — swung too far)
SHOULDER_ABDUCT = 13.0       # deg, constant hold-away-from-body
ELBOW_BASE = 5.0            # deg, resting elbow flexion — kept SMALL so the resting
                            # forearm hangs down beside the thigh instead of folding
                            # forward to meet the other hand at the centreline
ELBOW_FWD_GAIN = 0.9         # elbow flexion added per deg of FORWARD shoulder
ARM_LOWER = math.radians(75)
BOB_FRACTION = 0.010           # of rig height, 2x cadence


def gait_at(pct: float) -> tuple[float, float]:
    """Linearly interpolate (hip, knee) degrees at a percent of the gait cycle."""
    pct %= 100.0
    for i in range(len(GAIT) - 1):
        p0, h0, k0 = GAIT[i]
        p1, h1, k1 = GAIT[i + 1]
        if p0 <= pct <= p1:
            f = (pct - p0) / (p1 - p0) if p1 > p0 else 0.0
            return h0 + (h1 - h0) * f, k0 + (k1 - k0) * f
    return GAIT[-1][1], GAIT[-1][2]


def arm_at(opp_hip_deg: float) -> tuple[float, float]:
    """(shoulder_flex, elbow_flex) in degrees, driven by the OPPOSITE leg's hip
    (arms counter-swing the ipsilateral leg). Forward shoulder flexion is positive;
    elbow flexion rises with forward shoulder so the hand lifts clear of the body."""
    shoulder = SHOULDER_AMP * (opp_hip_deg / 30.0)          # +forward, -back
    elbow = ELBOW_BASE + ELBOW_FWD_GAIN * max(0.0, shoulder)
    return shoulder, elbow

M = json.loads(Path(MANIFEST_PATH).read_text())
FORWARD = Vector(M["frame"]["forward"]).normalized()
UP = Vector(M["frame"]["up"]).normalized()
SIDE = Vector(M["frame"]["side"]).normalized()
AXES = {"forward": FORWARD, "up": UP, "side": SIDE}

bpy.ops.wm.read_factory_settings(use_empty=True)
if Path(SRC).suffix.lower() == ".fbx":
    bpy.ops.import_scene.fbx(filepath=SRC)
else:
    bpy.ops.import_scene.gltf(filepath=SRC)
arm_obj = next(o for o in bpy.data.objects if o.type == "ARMATURE")
arm_obj.animation_data_clear()
skinned_meshes = [o for o in bpy.data.objects if o.type == "MESH"
                  and any(m.type == "ARMATURE" and m.object == arm_obj for m in o.modifiers)]
for mesh in [o for o in bpy.data.objects if o.type == "MESH"]:
    if mesh.animation_data:
        mesh.animation_data_clear()
    if mesh.data.shape_keys and mesh.data.shape_keys.animation_data:
        mesh.data.shape_keys.animation_data_clear()
bones = arm_obj.pose.bones


def axis_in_bone(pb, world_vec: Vector) -> Vector:
    R = (arm_obj.matrix_world @ pb.bone.matrix_local).to_3x3()
    return (R.inverted() @ world_vec).normalized()


def require_free(bone_name: str, axis_name: str) -> None:
    """Refuse to rotate a bone about an axis the scanner flagged as parallel to it.
    Silently twisting instead of swinging is the bug this whole design exists to
    prevent, so it is an ERROR, never a warning."""
    rec = M["bones"].get(bone_name, {})
    if axis_name in rec.get("degenerate_axes", []):
        print(f"ERROR: {bone_name} ({rec.get('role')}) is DEGENERATE about "
              f"'{axis_name}': {rec.get('degenerate_note', '')}", file=sys.stderr)
        sys.exit(1)


def local_from_world(pb, q_world: Quaternion) -> Quaternion:
    """Bone-local quaternion achieving a world-space rotation. Conjugation
    preserves the angle and rotates only the axis, so composing motions in world
    space and converting the SINGLE result is exact — the reliable way to stack
    the neutral correction, an arm roll, and the gait swing without frame drift."""
    axis, angle = q_world.to_axis_angle()
    return Quaternion(axis_in_bone(pb, axis), angle)


# Per-bone neutral-standing correction, MEASURED by the scanner (world axis+angle).
# Every motion is composed on top of this: R_total_world = R_motion . R_neutral.
NEUTRAL = {}
for name, c in M.get("neutral_pose", {}).get("corrections", {}).items():
    NEUTRAL[name] = Quaternion(Vector(c["world_axis"]), math.radians(c["angle_deg"]))


def neutral_of(bone_name: str) -> Quaternion:
    return NEUTRAL.get(bone_name, Quaternion())


chains = M["chains"]
legs, arms = [], []
for key, ch in chains.items():
    if key.startswith("leg."):
        legs.append({"side": key.split(".")[1], "thigh": ch["thigh"],
                     "calf": ch["calf"], "hinge": f"knee.{key.split('.')[1]}"})
    elif key.startswith("arm."):
        arms.append({"side": key.split(".")[1], "upperarm": ch["upperarm"],
                     "forearm": ch.get("forearm"), "hand": ch.get("hand")})

if len(legs) != 2:
    print(f"ERROR: manifest has {len(legs)} legs, need 2", file=sys.stderr)
    sys.exit(1)

for a in arms:
    a["palm_roll"] = None   # filled after fingers are posed (below)

for pb in bones:
    pb.rotation_mode = "QUATERNION"
    pb.rotation_quaternion = Quaternion()
    pb.location = (0.0, 0.0, 0.0)
bpy.context.view_layer.update()

# Relaxed hands: curl fingers where they exist, and measure the palm-plane normal
# from the HAND MESH (works even on a fingerless rig — this is what gives Meshy
# palm control via a wrist roll). Then roll each arm about its neutralised
# (vertical) axis so the palm faces the body. The mesh normal's sign is arbitrary
# (a plane has two faces), so palm-in vs back-of-hand-in is a single global 180deg
# choice — one mesh, one handedness. `--palm-out` flips it if a render shows the
# back of the hand.
PALM_OUT = "--palm-out" in sys.argv
palm = pose_relaxed_hands(arm_obj, arms, skinned_meshes)
for a in arms:
    pn = palm.get(a["upperarm"])
    if pn is None:
        continue
    q_n = neutral_of(a["upperarm"])
    palm_after = (q_n @ Vector(pn)).normalized()         # palm normal once at side
    arm_axis = (q_n @ Vector(M["bones"][a["upperarm"]]["rest_dir"])).normalized()
    # target: palm faces the body centreline (medial). +SIDE = left, so medial is
    # -SIDE from the left arm and +SIDE from the right.
    medial = (-SIDE if a["side"] == "L" else SIDE)
    if PALM_OUT:
        medial = -medial
    pa = (palm_after - arm_axis * palm_after.dot(arm_axis))
    md = (medial - arm_axis * medial.dot(arm_axis))
    if pa.length > 1e-6 and md.length > 1e-6:
        pa, md = pa.normalized(), md.normalized()
        ang = pa.angle(md)
        if arm_axis.dot(pa.cross(md)) < 0:
            ang = -ang
        a["palm_roll"] = (arm_axis, ang)

# Constant shoulder ABDUCTION: hold each arm slightly AWAY from the body about
# the forward axis so the forearm/hand clears the hip instead of drifting inward.
# Sign is measured, not guessed: pick the rotation about FORWARD whose upperarm
# tip moves toward the arm's OWN side (away from the centreline).
for a in arms:
    q_n = neutral_of(a["upperarm"])
    down = (q_n @ Vector(M["bones"][a["upperarm"]]["rest_dir"])).normalized()
    lateral_out = (SIDE if a["side"] == "L" else -SIDE)     # away from the centre
    plus = (Quaternion(FORWARD, math.radians(SHOULDER_ABDUCT)) @ down).dot(lateral_out)
    minus = (Quaternion(FORWARD, math.radians(-SHOULDER_ABDUCT)) @ down).dot(lateral_out)
    a["abduct"] = math.radians(SHOULDER_ABDUCT) * (1.0 if plus >= minus else -1.0)

root_name = M["root"]
height = max(abs(v) for v in (
    max(b["head"][2] for b in M["bones"].values()),
    min(b["head"][2] for b in M["bones"].values()))) or 1.0
BOB = height * BOB_FRACTION

action = bpy.data.actions.new("walk")
arm_obj.animation_data_create()
arm_obj.animation_data.action = action

print(f"frame: forward={[round(c,2) for c in FORWARD]} side={[round(c,2) for c in SIDE]}")
for leg in legs:
    h = M["hinges"][leg["hinge"]]
    print(f"  {leg['hinge']}: axis={h['axis']} sign={h['fold_sign']:+.0f} "
          f"src={h['axis_source']}")
for a in arms:
    roll = a["palm_roll"]
    print(f"  arm.{a['side']}: neutral={math.degrees(neutral_of(a['upperarm']).angle):+.0f}deg "
          f"palm_roll={('%.0fdeg' % math.degrees(roll[1])) if roll else 'none (no fingers)'}")

for f in range(FRAMES + 1):
    t = f / FRAMES
    th_base = 2 * math.pi * t

    for leg in legs:
        # contralateral legs are half a cycle apart
        pct = t * 100.0 + (0.0 if leg["side"] == "L" else 50.0)
        hip_deg, knee_deg = gait_at(pct)
        hinge = M["hinges"][leg["hinge"]]
        thigh_pb = bones[leg["thigh"]]
        calf_pb = bones[leg["calf"]]
        # gait applied on top of the neutral (splay-removed) pose, composed in
        # world space: R_total = R_gait . R_neutral, then conjugated to bone-local.
        thigh_swing = Quaternion(SIDE, math.radians(hip_deg))
        thigh_pb.rotation_quaternion = local_from_world(
            thigh_pb, thigh_swing @ neutral_of(leg["thigh"]))
        calf_bend = Quaternion(Vector(hinge["axis_vector"]),
                               math.radians(knee_deg) * hinge["fold_sign"])
        calf_pb.rotation_quaternion = local_from_world(
            calf_pb, calf_bend @ neutral_of(leg["calf"]))

    for a in arms:
        # arms swing out of phase with the ipsilateral leg: the left leg and the
        # RIGHT arm travel forward together. Drive off the OPPOSITE leg's hip so
        # the arm inherits gait timing rather than a detached sine.
        opp_pct = t * 100.0 + (50.0 if a["side"] == "L" else 0.0)
        opp_hip, _ = gait_at(opp_pct)
        shoulder_deg, elbow_deg = arm_at(opp_hip)

        # shoulder: neutral -> abduct (hold out) -> palm roll -> fore/aft swing
        # (world order, right operand applied first)
        pb = bones[a["upperarm"]]
        q_world = neutral_of(a["upperarm"])
        q_world = Quaternion(FORWARD, a["abduct"]) @ q_world
        if a["palm_roll"]:
            axis, ang = a["palm_roll"]
            q_world = Quaternion(axis, ang) @ q_world
        q_world = Quaternion(SIDE, math.radians(shoulder_deg)) @ q_world
        pb.rotation_quaternion = local_from_world(pb, q_world)

        # elbow / forearm: orient it by POSED WORLD matrix, not a rest-frame local
        # rotation. The rest-frame conjugation (local_from_world) is wrong once the
        # parent is posed, and it compounded badly on rigs whose arms rest angled
        # forward (Meshy), pulling the forearms inward to meet at the centreline.
        # World-space is parent-agnostic: aim the forearm straight down from the
        # posed upper arm, then flex forward by the elbow angle.
        fore_name = a.get("forearm")
        eh = M["hinges"].get(f"elbow.{a['side']}")
        if fore_name and fore_name in bones and eh:
            bpy.context.view_layer.update()          # so the upper arm's pose is live
            fore_pb = bones[fore_name]
            elbow_axis = Vector(eh["axis_vector"])
            # target forearm direction: straight down (-UP), flexed forward at the elbow
            target = (Quaternion(elbow_axis, math.radians(elbow_deg) * eh["fold_sign"])
                      @ (-UP)).normalized()
            cur_world = arm_obj.matrix_world @ fore_pb.matrix
            cur_y = (cur_world.to_3x3() @ Vector((0.0, 1.0, 0.0))).normalized()
            align = cur_y.rotation_difference(target)   # world rotation to the target
            new3 = align.to_matrix() @ cur_world.to_3x3()   # keeps roll (palm) intact
            new_world = Matrix.Translation(cur_world.translation) @ new3.to_4x4()
            fore_pb.matrix = arm_obj.matrix_world.inverted() @ new_world

    root_pb = bones[root_name]
    root_pb.location = UP * (BOB * math.sin(2 * th_base))
    root_pb.keyframe_insert("location", frame=f)
    for pb in bones:
        pb.keyframe_insert("rotation_quaternion", frame=f)

bpy.context.scene.frame_start = 0
bpy.context.scene.frame_end = FRAMES
track = arm_obj.animation_data.nla_tracks.new()
track.name = "walk"
track.strips.new("walk", 0, action)
arm_obj.animation_data.action = None

bpy.ops.export_scene.gltf(filepath=DST, export_format="GLB", export_yup=True,
                          export_animations=True, export_nla_strips=True)
print("EXPORTED", DST, f"({FRAMES} frames)")
