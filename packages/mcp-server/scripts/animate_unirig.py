"""Apply walk animation to UniRig-rigged models."""

import bpy
import math
import sys

# Get output path from command line
argv = sys.argv
output_glb = "animated_unirig.glb"
try:
    idx = argv.index("--") + 1
    if idx < len(argv):
        output_glb = argv[idx]
except ValueError:
    pass

# Animation parameters
DURATION = 1.0  # seconds
FPS = 30
INTENSITY = 1.0

# UniRig bone mapping (based on typical humanoid hierarchy)
# bone_0: hips, bone_1-5: spine chain, bone_6-9: right arm, bone_10-13: left arm
# bone_14-17: right leg, bone_18-21: left leg
BONE_MAP = {
    'hips': 'bone_0',
    'spine1': 'bone_1',
    'spine2': 'bone_2',
    'chest': 'bone_3',
    'neck': 'bone_4',
    'head': 'bone_5',
    'shoulder_r': 'bone_6',
    'upper_arm_r': 'bone_7',
    'forearm_r': 'bone_8',
    'hand_r': 'bone_9',
    'shoulder_l': 'bone_10',
    'upper_arm_l': 'bone_11',
    'forearm_l': 'bone_12',
    'hand_l': 'bone_13',
    'thigh_r': 'bone_14',
    'shin_r': 'bone_15',
    'foot_r': 'bone_16',
    'toe_r': 'bone_17',
    'thigh_l': 'bone_18',
    'shin_l': 'bone_19',
    'foot_l': 'bone_20',
    'toe_l': 'bone_21',
}


def get_bone(armature, role):
    """Get bone by role name."""
    bone_name = BONE_MAP.get(role)
    if bone_name and bone_name in armature.pose.bones:
        return armature.pose.bones[bone_name]
    return None


def set_keyframe(bone, frame, rotation=None, location=None):
    """Set keyframe on bone."""
    if rotation:
        bone.rotation_mode = 'XYZ'
        bone.rotation_euler = rotation
        bone.keyframe_insert(data_path='rotation_euler', frame=frame)
    if location:
        bone.location = location
        bone.keyframe_insert(data_path='location', frame=frame)


def apply_walk_animation(armature):
    """Apply walk cycle animation."""
    num_frames = int(DURATION * FPS)
    animated = []

    # Create action
    action = bpy.data.actions.new(name=f'{armature.name}_walk')
    armature.animation_data_create()
    armature.animation_data.action = action

    for i in range(num_frames):
        t = i / (num_frames - 1)
        frame = i + 1
        phase = t * 2 * math.pi
        half = phase * 2

        # Hips - sway and bounce
        hips = get_bone(armature, 'hips')
        if hips:
            set_keyframe(hips, frame,
                location=(math.sin(phase) * 0.02 * INTENSITY, 0, -abs(math.sin(half)) * 0.01 * INTENSITY),
                rotation=(math.sin(half) * 0.02 * INTENSITY, 0, math.sin(phase) * 0.025 * INTENSITY))
            if 'hips' not in animated: animated.append('hips')

        # Spine twist
        for spine_name in ['spine1', 'spine2']:
            spine = get_bone(armature, spine_name)
            if spine:
                set_keyframe(spine, frame, rotation=(0.015 * INTENSITY, math.sin(phase) * 0.02 * INTENSITY, 0))
                if spine_name not in animated: animated.append(spine_name)

        # Chest counter-twist
        chest = get_bone(armature, 'chest')
        if chest:
            set_keyframe(chest, frame, rotation=(0, -math.sin(phase) * 0.015 * INTENSITY, 0))
            if 'chest' not in animated: animated.append('chest')

        # Head bob
        head = get_bone(armature, 'head')
        if head:
            set_keyframe(head, frame, rotation=(math.sin(half) * 0.01 * INTENSITY, 0, 0))
            if 'head' not in animated: animated.append('head')

        # Legs - opposite phase
        for side, sign in [('_r', 1), ('_l', -1)]:
            # Thigh swing
            thigh = get_bone(armature, f'thigh{side}')
            if thigh:
                swing = sign * math.sin(phase) * 0.35 * INTENSITY
                set_keyframe(thigh, frame, rotation=(swing, 0, 0))
                if f'thigh{side}' not in animated: animated.append(f'thigh{side}')

            # Shin bend (only when leg is back)
            shin = get_bone(armature, f'shin{side}')
            if shin:
                bend = max(0, sign * math.sin(phase - 0.5)) * 0.4 * INTENSITY
                set_keyframe(shin, frame, rotation=(bend, 0, 0))
                if f'shin{side}' not in animated: animated.append(f'shin{side}')

            # Foot flex
            foot = get_bone(armature, f'foot{side}')
            if foot:
                flex = -sign * math.sin(phase) * 0.15 * INTENSITY
                set_keyframe(foot, frame, rotation=(flex, 0, 0))
                if f'foot{side}' not in animated: animated.append(f'foot{side}')

        # Arms - opposite to legs
        for side, sign in [('_r', -1), ('_l', 1)]:
            # Upper arm swing
            upper = get_bone(armature, f'upper_arm{side}')
            if upper:
                swing = sign * math.sin(phase) * 0.3 * INTENSITY
                set_keyframe(upper, frame, rotation=(swing, 0, 0))
                if f'upper_arm{side}' not in animated: animated.append(f'upper_arm{side}')

            # Forearm bend
            forearm = get_bone(armature, f'forearm{side}')
            if forearm:
                bend = 0.25 + max(0, sign * math.sin(phase)) * 0.15 * INTENSITY
                set_keyframe(forearm, frame, rotation=(bend, 0, 0))
                if f'forearm{side}' not in animated: animated.append(f'forearm{side}')

    return animated, num_frames


# Find armature
armature = None
for obj in bpy.data.objects:
    if obj.type == 'ARMATURE':
        armature = obj
        break

if not armature:
    print("ERROR: No armature found")
    sys.exit(1)

print(f"Armature: {armature.name} ({len(armature.data.bones)} bones)")

# Apply animation
animated, num_frames = apply_walk_animation(armature)

# Set frame range
bpy.context.scene.frame_start = 1
bpy.context.scene.frame_end = num_frames

print(f"Animated {len(animated)} bones: {animated}")
print(f"Frames: 1-{num_frames}")

# Export
bpy.ops.export_scene.gltf(
    filepath=output_glb,
    export_format='GLB',
    export_animations=True,
    export_skins=True
)
print(f"Exported to: {output_glb}")
