"""Load UniRig model and apply walk animation."""

import os

import bpy
import math

# Load the rigged model
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=os.path.join(os.path.dirname(__file__), '..', 'TripoSG_unirig_rigged.glb'))

# Animation parameters
DURATION = 1.0
FPS = 30
INTENSITY = 1.0
OUTPUT = os.path.join(os.path.dirname(__file__), '..', 'TripoSG_unirig_animated.glb')

# Find armature
armature = None
for obj in bpy.data.objects:
    if obj.type == 'ARMATURE':
        armature = obj
        break

print(f"Armature: {armature.name} ({len(armature.data.bones)} bones)")

# Create action
action = bpy.data.actions.new(name='walk')
armature.animation_data_create()
armature.animation_data.action = action

num_frames = int(DURATION * FPS)
bones = armature.pose.bones

# Animate each frame
for i in range(num_frames):
    t = i / (num_frames - 1)
    frame = i + 1
    phase = t * 2 * math.pi
    half = phase * 2

    # bone_0: hips
    if 'bone_0' in bones:
        b = bones['bone_0']
        b.rotation_mode = 'XYZ'
        b.location = (math.sin(phase) * 0.02, 0, -abs(math.sin(half)) * 0.01)
        b.rotation_euler = (math.sin(half) * 0.02, 0, math.sin(phase) * 0.025)
        b.keyframe_insert('location', frame=frame)
        b.keyframe_insert('rotation_euler', frame=frame)

    # bone_1, bone_2: spine
    for bn in ['bone_1', 'bone_2']:
        if bn in bones:
            b = bones[bn]
            b.rotation_mode = 'XYZ'
            b.rotation_euler = (0.015, math.sin(phase) * 0.02, 0)
            b.keyframe_insert('rotation_euler', frame=frame)

    # bone_3: chest
    if 'bone_3' in bones:
        b = bones['bone_3']
        b.rotation_mode = 'XYZ'
        b.rotation_euler = (0, -math.sin(phase) * 0.015, 0)
        b.keyframe_insert('rotation_euler', frame=frame)

    # bone_5: head
    if 'bone_5' in bones:
        b = bones['bone_5']
        b.rotation_mode = 'XYZ'
        b.rotation_euler = (math.sin(half) * 0.01, 0, 0)
        b.keyframe_insert('rotation_euler', frame=frame)

    # Right leg: bone_14 (thigh), bone_15 (shin), bone_16 (foot)
    if 'bone_14' in bones:
        b = bones['bone_14']
        b.rotation_mode = 'XYZ'
        b.rotation_euler = (math.sin(phase) * 0.35, 0, 0)
        b.keyframe_insert('rotation_euler', frame=frame)
    if 'bone_15' in bones:
        b = bones['bone_15']
        b.rotation_mode = 'XYZ'
        b.rotation_euler = (max(0, math.sin(phase - 0.5)) * 0.4, 0, 0)
        b.keyframe_insert('rotation_euler', frame=frame)
    if 'bone_16' in bones:
        b = bones['bone_16']
        b.rotation_mode = 'XYZ'
        b.rotation_euler = (-math.sin(phase) * 0.15, 0, 0)
        b.keyframe_insert('rotation_euler', frame=frame)

    # Left leg: bone_18 (thigh), bone_19 (shin), bone_20 (foot) - opposite phase
    if 'bone_18' in bones:
        b = bones['bone_18']
        b.rotation_mode = 'XYZ'
        b.rotation_euler = (-math.sin(phase) * 0.35, 0, 0)
        b.keyframe_insert('rotation_euler', frame=frame)
    if 'bone_19' in bones:
        b = bones['bone_19']
        b.rotation_mode = 'XYZ'
        b.rotation_euler = (max(0, -math.sin(phase - 0.5)) * 0.4, 0, 0)
        b.keyframe_insert('rotation_euler', frame=frame)
    if 'bone_20' in bones:
        b = bones['bone_20']
        b.rotation_mode = 'XYZ'
        b.rotation_euler = (math.sin(phase) * 0.15, 0, 0)
        b.keyframe_insert('rotation_euler', frame=frame)

    # Right arm: bone_7 (upper), bone_8 (forearm) - opposite to right leg
    if 'bone_7' in bones:
        b = bones['bone_7']
        b.rotation_mode = 'XYZ'
        b.rotation_euler = (-math.sin(phase) * 0.3, 0, 0)
        b.keyframe_insert('rotation_euler', frame=frame)
    if 'bone_8' in bones:
        b = bones['bone_8']
        b.rotation_mode = 'XYZ'
        b.rotation_euler = (0.25 + max(0, -math.sin(phase)) * 0.15, 0, 0)
        b.keyframe_insert('rotation_euler', frame=frame)

    # Left arm: bone_11 (upper), bone_12 (forearm) - opposite to left leg
    if 'bone_11' in bones:
        b = bones['bone_11']
        b.rotation_mode = 'XYZ'
        b.rotation_euler = (math.sin(phase) * 0.3, 0, 0)
        b.keyframe_insert('rotation_euler', frame=frame)
    if 'bone_12' in bones:
        b = bones['bone_12']
        b.rotation_mode = 'XYZ'
        b.rotation_euler = (0.25 + max(0, math.sin(phase)) * 0.15, 0, 0)
        b.keyframe_insert('rotation_euler', frame=frame)

# Set frame range
bpy.context.scene.frame_start = 1
bpy.context.scene.frame_end = num_frames

print(f"Animation applied: {num_frames} frames")

# Export
bpy.ops.export_scene.gltf(
    filepath=OUTPUT,
    export_format='GLB',
    export_animations=True,
    export_skins=True
)
print(f"Exported to: {OUTPUT}")
