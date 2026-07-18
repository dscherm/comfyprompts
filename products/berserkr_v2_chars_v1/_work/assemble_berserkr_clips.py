"""Assemble the Meshy-rigged berserkr into ONE Godot-ready GLB with idle/walk/run.

Meshy returns each clip in its own full-mesh GLB and gives no idle. This:
  - imports the walking GLB as the base (textured rigged mesh + walk action),
  - appends the running action from the running GLB,
  - synthesizes a subtle breathing IDLE on the humanoid rig (Hips bob + Spine
    breathing + micro arm sway; amplitude tiny so it reads as 'alive' without
    depending on exact bone-local axis signs),
  - renames actions to idle/walk/run and exports every action as its own glTF
    clip (export_animation_mode='ACTIONS').

Usage:
  blender --background --factory-startup --python assemble_berserkr_clips.py \
    -- <walking.glb> <running.glb> <rig.rigvec.json> <out.glb> [idle_frames=72]
"""

from __future__ import annotations

import json
import math
import sys

import bpy
from mathutils import Quaternion, Vector

argv = sys.argv[sys.argv.index("--") + 1:]
WALK, RUN, MANIFEST, OUT = argv[0], argv[1], argv[2], argv[3]
IDLE_FRAMES = int(argv[4]) if len(argv) > 4 else 72

bpy.ops.wm.read_factory_settings(use_empty=True)

# --- base: walking GLB (mesh + armature + walk action) ---------------------
bpy.ops.import_scene.gltf(filepath=WALK)
arm = next(o for o in bpy.data.objects if o.type == "ARMATURE")
walk_action = arm.animation_data.action if arm.animation_data else None
if walk_action:
    walk_action.name = "walk"
    walk_action.use_fake_user = True

# --- append the running action from the running GLB ------------------------
before = set(bpy.data.actions.keys())
bpy.ops.import_scene.gltf(filepath=RUN)
run_action = None
for name in bpy.data.actions.keys():
    if name not in before:
        run_action = bpy.data.actions[name]
        break
if run_action:
    run_action.name = "run"
    run_action.use_fake_user = True

# the running import brought in a second mesh+armature; delete everything that
# is not our base arm / its mesh children.
keep = {arm}
for c in arm.children_recursive:
    keep.add(c)
# also keep meshes parented to arm
for o in list(bpy.data.objects):
    if o.type == "MESH" and o.find_armature() == arm:
        keep.add(o)
for o in list(bpy.data.objects):
    if o not in keep:
        bpy.data.objects.remove(o, do_unlink=True)

# --- synthesize a neutral-stand breathing idle -----------------------------
# The rig REST pose is a T-pose (arms out, ~7deg leg splay). Meshy gives no idle
# clip, so we build one from the MEASURED neutral-standing corrections in the rig
# manifest (rig_scan.py): each arm/leg bone has a world axis+angle that lowers it
# from the T-pose to a natural stand (Meshy's are asymmetric: 73.3 / 71.6 deg).
# We compose in world space and conjugate the single result to bone-local — the
# exact transform humanoid_walk.py uses (wiki: human-walk-cycle-from-a-rig-manifest).
# Then a gentle breath is layered on the spine + a small hips bob.
M = json.load(open(MANIFEST))
FR = M["frame"]
SIDE = Vector(FR["side"])          # spine breathing tilts about the side axis
UP = Vector(FR["up"])
FORWARD = Vector(FR["forward"]).normalized()
SHOULDER_ABDUCT = math.radians(13.0)  # hold each arm away from the body (clears hip)

bpy.context.view_layer.objects.active = arm
bpy.ops.object.mode_set(mode="POSE")
for pb in arm.pose.bones:
    pb.rotation_mode = "QUATERNION"
    pb.rotation_quaternion = Quaternion()
    pb.location = (0.0, 0.0, 0.0)
bpy.context.view_layer.update()


def axis_in_bone(pb, world_vec: Vector) -> Vector:
    R = (arm.matrix_world @ pb.bone.matrix_local).to_3x3()
    return (R.inverted() @ world_vec).normalized()


def local_from_world(pb, q_world: Quaternion) -> Quaternion:
    # conjugation preserves the angle and rotates only the axis, so a world-space
    # composition converts exactly to the bone's local frame.
    axis, angle = q_world.to_axis_angle()
    return Quaternion(axis_in_bone(pb, axis), angle)


NEUTRAL = {}
for name, c in M.get("neutral_pose", {}).get("corrections", {}).items():
    NEUTRAL[name] = Quaternion(Vector(c["world_axis"]), math.radians(c["angle_deg"]))

# Shoulder abduction per upperarm: hold the arm out from the body so it doesn't
# clip the torso. Sign measured (not guessed) — pick the rotation about FORWARD
# whose arm tip moves toward its OWN side (away from centreline). Applied on top
# of neutral for the upperarm bones only; forearms follow as children.
ABDUCT = {}
for key, ch in M.get("chains", {}).items():
    if not key.startswith("arm."):
        continue
    side = key.split(".")[1]
    up_name = ch["upperarm"]
    q_n = NEUTRAL.get(up_name, Quaternion())
    down = (q_n @ Vector(M["bones"][up_name]["rest_dir"])).normalized()
    lateral_out = (SIDE if side == "L" else -SIDE)
    plus = (Quaternion(FORWARD, SHOULDER_ABDUCT) @ down).dot(lateral_out)
    minus = (Quaternion(FORWARD, -SHOULDER_ABDUCT) @ down).dot(lateral_out)
    ABDUCT[up_name] = Quaternion(FORWARD, SHOULDER_ABDUCT * (1.0 if plus >= minus else -1.0))

hips_up_local = axis_in_bone(arm.pose.bones["Hips"], UP) if "Hips" in arm.pose.bones else None

idle = bpy.data.actions.new("idle")
idle.use_fake_user = True
arm.animation_data.action = idle

BREATHE = math.radians(2.0)   # spine pitch amplitude (breathing)
BOB = 0.010                   # hips vertical bob (metres)


def key_rot(pb, q_world, frame):
    pb.rotation_quaternion = local_from_world(pb, q_world)
    pb.keyframe_insert("rotation_quaternion", frame=frame)


for f in range(IDLE_FRAMES + 1):
    t = f / IDLE_FRAMES
    breath = math.sin(t * 2 * math.pi)          # one full breath per loop
    # arms + legs held at the measured neutral stand (upperarms also abducted out)
    for name, q_n in NEUTRAL.items():
        pb = arm.pose.bones.get(name)
        if pb is not None:
            key_rot(pb, ABDUCT.get(name, Quaternion()) @ q_n, f)
    # spine breathing, composed on the (upright) rest in world space
    for sname, scale in (("Spine", 1.0), ("Spine01", 0.5)):
        pb = arm.pose.bones.get(sname)
        if pb is not None:
            key_rot(pb, Quaternion(SIDE, BREATHE * scale * breath), f)
    # hips vertical bob (translate along world-up expressed in the hips frame)
    ph = arm.pose.bones.get("Hips")
    if ph is not None and hips_up_local is not None:
        ph.location = hips_up_local * (BOB * breath)
        ph.keyframe_insert("location", frame=f)

bpy.ops.object.mode_set(mode="OBJECT")

# --- export: every action as its own clip ----------------------------------
for o in bpy.data.objects:
    o.select_set(True)
bpy.ops.export_scene.gltf(
    filepath=OUT, export_format="GLB", use_selection=True,
    export_animation_mode="ACTIONS", export_animations=True,
    export_skins=True, export_morph=False,
)
print("ASSEMBLED %s  actions=%s" % (OUT, sorted(bpy.data.actions.keys())))
