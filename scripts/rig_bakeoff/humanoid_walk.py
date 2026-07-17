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

STRIDE = math.radians(28)
KNEE = math.radians(50)
ARM_SWING = math.radians(18)
ARM_LOWER = math.radians(75)
BOB_FRACTION = 0.010          # of rig height, 2x cadence

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
        phase = 0.0 if leg["side"] == "L" else math.pi
        th = th_base + phase
        hinge = M["hinges"][leg["hinge"]]
        # +swing = forward, a consequence of the frame definition (see docstring)
        swing = STRIDE * math.sin(th)
        # knee bends through the SWING phase (foot lifts) and straightens in stance
        bend = KNEE * max(0.0, math.cos(th)) * hinge["fold_sign"]
        thigh_pb = bones[leg["thigh"]]
        calf_pb = bones[leg["calf"]]
        thigh_pb.rotation_quaternion = Quaternion(axis_in_bone(thigh_pb, SIDE), swing)
        calf_pb.rotation_quaternion = Quaternion(
            axis_in_bone(calf_pb, Vector(hinge["axis_vector"])), bend)

    for a in arms:
        phase = math.pi if a["side"] == "L" else 0.0    # counter to same-side leg
        swing = ARM_SWING * math.sin(th_base + phase)
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
