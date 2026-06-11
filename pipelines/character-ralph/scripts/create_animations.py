"""Create procedural idle, walk, and run animations for the rigged character in Blender 5.0."""
import bpy
import math
from mathutils import Euler

FPS = 30
bpy.context.scene.render.fps = FPS

armature = [o for o in bpy.data.objects if o.type == "ARMATURE"][0]
bpy.context.view_layer.objects.active = armature

if not armature.animation_data:
    armature.animation_data_create()


def reset_pose():
    bpy.ops.object.mode_set(mode="POSE")
    for pb in armature.pose.bones:
        pb.rotation_mode = "XYZ"
        pb.location = (0, 0, 0)
        pb.rotation_euler = (0, 0, 0)
        pb.scale = (1, 1, 1)


def kf(bone_name, frame, rot=None, loc=None):
    """Keyframe a bone at the given frame (rotation in degrees)."""
    pb = armature.pose.bones.get(bone_name)
    if not pb:
        return
    bpy.context.scene.frame_set(frame)
    if rot:
        pb.rotation_euler = Euler([math.radians(r) for r in rot])
        pb.keyframe_insert(data_path="rotation_euler", frame=frame)
    if loc:
        pb.location = loc
        pb.keyframe_insert(data_path="location", frame=frame)


def create_action(name, frame_count):
    """Create a new action, removing old one if exists."""
    old = bpy.data.actions.get(name)
    if old:
        bpy.data.actions.remove(old)
    action = bpy.data.actions.new(name=name)
    armature.animation_data.action = action
    reset_pose()
    return action


# ─── IDLE (3 sec / 90 frames) ───
idle = create_action("idle", 90)

for f in [1, 90]:
    kf("Spine", f, rot=(0, 0, 0))
    kf("Chest", f, rot=(0, 0, 0))
    kf("Head", f, rot=(0, 0, 0))
    kf("Hips", f, loc=(0, 0, 0))

kf("Spine", 23, rot=(-1.5, 0, 0))
kf("Chest", 23, rot=(-2, 0, 0))
kf("Head", 23, rot=(1, 0, 0))
kf("Hips", 23, loc=(0, 0, 0.003))

kf("Spine", 45, rot=(0, 0, 0))
kf("Chest", 45, rot=(0, 0, 0))
kf("Head", 45, rot=(0.5, 0, 0.5))
kf("Hips", 45, loc=(0, 0, 0))

kf("Spine", 67, rot=(1, 0, 0))
kf("Chest", 67, rot=(1.5, 0, 0))
kf("Head", 67, rot=(-0.5, 0, -0.5))
kf("Hips", 67, loc=(0, 0, -0.002))

print(f"IDLE: 90 frames ({90/FPS:.1f}s)")


# ─── WALK (1 sec / 30 frames) ───
walk = create_action("walk", 30)

# Left foot forward contact
for f in [1, 30]:
    kf("Hips", f, loc=(0, 0, 0), rot=(0, 0, 0))
    kf("Spine", f, rot=(2, 0, 0))
    kf("UpperLeg.L", f, rot=(-20, 0, 0))
    kf("LowerLeg.L", f, rot=(5, 0, 0))
    kf("UpperLeg.R", f, rot=(15, 0, 0))
    kf("LowerLeg.R", f, rot=(30, 0, 0))
    kf("UpperArm.L", f, rot=(10, 0, 0))
    kf("UpperArm.R", f, rot=(-15, 0, 0))
    kf("Foot.L", f, rot=(-5, 0, 0))
    kf("Foot.R", f, rot=(10, 0, 0))

# Passing (frame 8)
kf("Hips", 8, loc=(0, 0, 0.01), rot=(0, 0, 0))
kf("UpperLeg.L", 8, rot=(0, 0, 0))
kf("LowerLeg.L", 8, rot=(15, 0, 0))
kf("UpperLeg.R", 8, rot=(0, 0, 0))
kf("LowerLeg.R", 8, rot=(15, 0, 0))
kf("UpperArm.L", 8, rot=(0, 0, 0))
kf("UpperArm.R", 8, rot=(0, 0, 0))
kf("Foot.L", 8, rot=(0, 0, 0))
kf("Foot.R", 8, rot=(0, 0, 0))

# Right foot forward (frame 16)
kf("Hips", 16, loc=(0, 0, 0), rot=(0, 0, 0))
kf("Spine", 16, rot=(2, 0, 0))
kf("UpperLeg.L", 16, rot=(15, 0, 0))
kf("LowerLeg.L", 16, rot=(30, 0, 0))
kf("UpperLeg.R", 16, rot=(-20, 0, 0))
kf("LowerLeg.R", 16, rot=(5, 0, 0))
kf("UpperArm.L", 16, rot=(-15, 0, 0))
kf("UpperArm.R", 16, rot=(10, 0, 0))
kf("Foot.L", 16, rot=(10, 0, 0))
kf("Foot.R", 16, rot=(-5, 0, 0))

# Passing 2 (frame 23)
kf("Hips", 23, loc=(0, 0, 0.01), rot=(0, 0, 0))
kf("UpperLeg.L", 23, rot=(0, 0, 0))
kf("LowerLeg.L", 23, rot=(15, 0, 0))
kf("UpperLeg.R", 23, rot=(0, 0, 0))
kf("LowerLeg.R", 23, rot=(15, 0, 0))
kf("UpperArm.L", 23, rot=(0, 0, 0))
kf("UpperArm.R", 23, rot=(0, 0, 0))

print(f"WALK: 30 frames ({30/FPS:.1f}s)")


# ─── RUN (0.8 sec / 24 frames) ───
run = create_action("run", 24)

# Left foot forward
for f in [1, 24]:
    kf("Hips", f, loc=(0, 0, 0), rot=(5, 0, 0))
    kf("Spine", f, rot=(5, 0, 0))
    kf("Chest", f, rot=(-3, 0, 0))
    kf("UpperLeg.L", f, rot=(-35, 0, 0))
    kf("LowerLeg.L", f, rot=(10, 0, 0))
    kf("UpperLeg.R", f, rot=(25, 0, 0))
    kf("LowerLeg.R", f, rot=(60, 0, 0))
    kf("UpperArm.L", f, rot=(25, 0, 0))
    kf("LowerArm.L", f, rot=(-30, 0, 0))
    kf("UpperArm.R", f, rot=(-30, 0, 0))
    kf("LowerArm.R", f, rot=(-60, 0, 0))
    kf("Foot.L", f, rot=(-10, 0, 0))
    kf("Foot.R", f, rot=(15, 0, 0))

# Flight phase (frame 7)
kf("Hips", 7, loc=(0, 0, 0.025), rot=(3, 0, 0))
kf("UpperLeg.L", 7, rot=(0, 0, 0))
kf("LowerLeg.L", 7, rot=(30, 0, 0))
kf("UpperLeg.R", 7, rot=(0, 0, 0))
kf("LowerLeg.R", 7, rot=(30, 0, 0))
kf("UpperArm.L", 7, rot=(0, 0, 0))
kf("LowerArm.L", 7, rot=(-20, 0, 0))
kf("UpperArm.R", 7, rot=(0, 0, 0))
kf("LowerArm.R", 7, rot=(-20, 0, 0))

# Right foot forward (frame 13)
kf("Hips", 13, loc=(0, 0, 0), rot=(5, 0, 0))
kf("Spine", 13, rot=(5, 0, 0))
kf("Chest", 13, rot=(-3, 0, 0))
kf("UpperLeg.L", 13, rot=(25, 0, 0))
kf("LowerLeg.L", 13, rot=(60, 0, 0))
kf("UpperLeg.R", 13, rot=(-35, 0, 0))
kf("LowerLeg.R", 13, rot=(10, 0, 0))
kf("UpperArm.L", 13, rot=(-30, 0, 0))
kf("LowerArm.L", 13, rot=(-60, 0, 0))
kf("UpperArm.R", 13, rot=(25, 0, 0))
kf("LowerArm.R", 13, rot=(-30, 0, 0))
kf("Foot.L", 13, rot=(15, 0, 0))
kf("Foot.R", 13, rot=(-10, 0, 0))

# Flight phase 2 (frame 19)
kf("Hips", 19, loc=(0, 0, 0.025), rot=(3, 0, 0))
kf("UpperLeg.L", 19, rot=(0, 0, 0))
kf("LowerLeg.L", 19, rot=(30, 0, 0))
kf("UpperLeg.R", 19, rot=(0, 0, 0))
kf("LowerLeg.R", 19, rot=(30, 0, 0))
kf("UpperArm.L", 19, rot=(0, 0, 0))
kf("LowerArm.L", 19, rot=(-20, 0, 0))
kf("UpperArm.R", 19, rot=(0, 0, 0))
kf("LowerArm.R", 19, rot=(-20, 0, 0))

print(f"RUN: 24 frames ({24/FPS:.1f}s)")

bpy.ops.object.mode_set(mode="OBJECT")
print("All 3 animations created: idle, walk, run")
