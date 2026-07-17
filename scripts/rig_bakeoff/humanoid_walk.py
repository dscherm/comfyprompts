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
from mathutils import Quaternion, Vector

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

ARM_SWING = math.radians(12)   # shoulder flexion/extension; counter-phase to the
                               # ipsilateral leg (left leg forward = right arm forward)
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


def lower_sign(rest_dir: Vector) -> float:
    """Which rotation sign about FORWARD points this limb most downward.
    Measured from the rig's own rest direction — mirrored arms get opposite
    signs automatically, with no left/right special-casing."""
    return min((+1.0, -1.0),
               key=lambda s: (Quaternion(FORWARD, ARM_LOWER * s) @ rest_dir).dot(UP))


chains = M["chains"]
legs, arms = [], []
for key, ch in chains.items():
    if key.startswith("leg."):
        legs.append({"side": key.split(".")[1], "thigh": ch["thigh"],
                     "calf": ch["calf"], "hinge": f"knee.{key.split('.')[1]}"})
    elif key.startswith("arm."):
        arms.append({"side": key.split(".")[1], "upperarm": ch["upperarm"]})

if len(legs) != 2:
    print(f"ERROR: manifest has {len(legs)} legs, need 2", file=sys.stderr)
    sys.exit(1)

# The thigh swings about `side`; assert the rig allows it (a thigh resting along
# the side axis would be a splits pose, not a humanoid, but never assume).
for leg in legs:
    require_free(leg["thigh"], "side")

# Arms: if the rest pose parks them along `side` (a T-pose), swinging about
# `side` would twist them. Lower them out of it first, about `forward`.
for a in arms:
    rec = M["bones"][a["upperarm"]]
    a["needs_lower"] = "side" in rec.get("degenerate_axes", [])
    if a["needs_lower"]:
        require_free(a["upperarm"], "forward")   # must be free to lower about it
        a["lower"] = ARM_LOWER * lower_sign(Vector(rec["rest_dir"]))
    else:
        a["lower"] = 0.0

for pb in bones:
    pb.rotation_mode = "QUATERNION"
    pb.rotation_quaternion = Quaternion()
    pb.location = (0.0, 0.0, 0.0)

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
    print(f"  arm.{a['side']}: needs_lower={a['needs_lower']} "
          f"lower={math.degrees(a['lower']):+.0f}deg")

for f in range(FRAMES + 1):
    t = f / FRAMES
    th_base = 2 * math.pi * t

    for leg in legs:
        # contralateral legs are half a cycle apart
        pct = t * 100.0 + (0.0 if leg["side"] == "L" else 50.0)
        hip_deg, knee_deg = gait_at(pct)
        hinge = M["hinges"][leg["hinge"]]
        # +rotation about `side` = forward tilt, a consequence of the frame
        # definition (proof in the module docstring), so hip flexion maps directly
        swing = math.radians(hip_deg)
        bend = math.radians(knee_deg) * hinge["fold_sign"]
        thigh_pb = bones[leg["thigh"]]
        calf_pb = bones[leg["calf"]]
        thigh_pb.rotation_quaternion = Quaternion(axis_in_bone(thigh_pb, SIDE), swing)
        calf_pb.rotation_quaternion = Quaternion(
            axis_in_bone(calf_pb, Vector(hinge["axis_vector"])), bend)

    for a in arms:
        # arms swing out of phase with the ipsilateral leg: the left leg and the
        # RIGHT arm travel forward together. Drive the shoulder off the hip curve
        # of the OPPOSITE leg so the arm inherits gait timing rather than a
        # detached sine.
        opp_pct = t * 100.0 + (50.0 if a["side"] == "L" else 0.0)
        opp_hip, _ = gait_at(opp_pct)
        swing = ARM_SWING * (opp_hip / 30.0)   # normalise by peak hip flexion
        pb = bones[a["upperarm"]]
        q = Quaternion(axis_in_bone(pb, SIDE), swing)
        if a["needs_lower"]:
            # world-space R_side(swing) . R_forward(lower), conjugated per factor;
            # `@` applies the RIGHT operand first, so it lowers THEN swings
            q = q @ Quaternion(axis_in_bone(pb, FORWARD), a["lower"])
        pb.rotation_quaternion = q

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
