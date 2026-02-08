"""Apply animation to a rigged model and export to GLB."""

import bpy
import math
import sys

# Animation parameters
ANIMATION_TYPE = 'walk'
DURATION = 1.0
FPS = 30
INTENSITY = 1.0
LOOP = True


def ease_in_out_sine(t):
    return -(math.cos(math.pi * t) - 1) / 2


def smooth_step(t):
    return t * t * (3 - 2 * t)


def lerp(a, b, t):
    return a + (b - a) * t


class RigBones:
    """Helper class for finding bones by role."""

    def __init__(self, armature):
        self.armature = armature
        self.bones = armature.pose.bones
        self._cache = {}

    def find(self, role):
        if role in self._cache:
            return self._cache[role]

        patterns = {
            'hips': ['hip', 'pelvis', 'torso', 'hips', 'root'],
            'spine': ['spine_fk', 'spine', 'spine.001', 'spine1', 'DEF-spine'],
            'spine_upper': ['spine_fk.001', 'spine.002', 'chest', 'spine2', 'DEF-spine.001'],
            'neck': ['neck', 'DEF-neck'],
            'head': ['head', 'DEF-head'],
            'thigh_l': ['thigh_fk.l', 'thigh.l', 'upper_leg.l', 'thigh_fk.L', 'DEF-thigh.L'],
            'thigh_r': ['thigh_fk.r', 'thigh.r', 'upper_leg.r', 'thigh_fk.R', 'DEF-thigh.R'],
            'shin_l': ['shin_fk.l', 'shin.l', 'lower_leg.l', 'shin_fk.L', 'calf.l', 'DEF-shin.L'],
            'shin_r': ['shin_fk.r', 'shin.r', 'lower_leg.r', 'shin_fk.R', 'calf.r', 'DEF-shin.R'],
            'foot_l': ['foot_fk.l', 'foot.l', 'foot_fk.L', 'DEF-foot.L'],
            'foot_r': ['foot_fk.r', 'foot.r', 'foot_fk.R', 'DEF-foot.R'],
            'upper_arm_l': ['upper_arm_fk.l', 'upper_arm.l', 'arm.l', 'upper_arm_fk.L', 'DEF-upper_arm.L'],
            'upper_arm_r': ['upper_arm_fk.r', 'upper_arm.r', 'arm.r', 'upper_arm_fk.R', 'DEF-upper_arm.R'],
            'forearm_l': ['forearm_fk.l', 'forearm.l', 'lower_arm.l', 'forearm_fk.L', 'DEF-forearm.L'],
            'forearm_r': ['forearm_fk.r', 'forearm.r', 'lower_arm.r', 'forearm_fk.R', 'DEF-forearm.R'],
            'shoulder_l': ['shoulder.l', 'clavicle.l', 'shoulder.L', 'DEF-shoulder.L'],
            'shoulder_r': ['shoulder.r', 'clavicle.r', 'shoulder.R', 'DEF-shoulder.R'],
        }

        if role not in patterns:
            return None

        # Exact match first
        for pattern in patterns[role]:
            pattern_lower = pattern.lower()
            for bone in self.bones:
                if pattern_lower == bone.name.lower():
                    self._cache[role] = bone
                    return bone

        # Partial match fallback
        for pattern in patterns[role]:
            pattern_lower = pattern.lower()
            for bone in self.bones:
                if pattern_lower in bone.name.lower():
                    self._cache[role] = bone
                    return bone

        return None


def set_keyframe(bone, frame, location=None, rotation=None, scale=None):
    """Set keyframe on a bone."""
    if location:
        bone.location = location
        bone.keyframe_insert(data_path='location', frame=frame)
    if rotation:
        bone.rotation_mode = 'XYZ'
        bone.rotation_euler = rotation
        bone.keyframe_insert(data_path='rotation_euler', frame=frame)
    if scale:
        bone.scale = scale
        bone.keyframe_insert(data_path='scale', frame=frame)


def generate_walk_cycle(armature, duration, fps, intensity, loop):
    """Generate walk cycle animation."""
    rig = RigBones(armature)
    num_frames = int(duration * fps)
    num_keys = num_frames if not loop else num_frames - 1

    # Animation parameters
    hip_sway = 0.025 * intensity
    arm_swing = 0.35 * intensity
    leg_swing = 0.38 * intensity
    spine_twist = 0.03 * intensity
    head_bob = 0.015 * intensity

    animated_bones = []

    for i in range(num_keys + 1):
        t = i / num_keys
        frame = i + 1
        walk_phase = t * 2 * math.pi
        half_phase = walk_phase * 2

        # Hips - sway, bounce, rotation
        hips = rig.find('hips')
        if hips:
            sway_x = math.sin(walk_phase) * hip_sway
            bounce_z = -abs(math.sin(half_phase)) * 0.015 * intensity
            rot_x = math.sin(half_phase) * 0.02 * intensity
            rot_z = math.sin(walk_phase) * 0.03 * intensity
            set_keyframe(hips, frame, location=(sway_x, 0, bounce_z), rotation=(rot_x, 0, rot_z))
            if 'hips' not in animated_bones:
                animated_bones.append('hips')

        # Spine - twist with walk
        spine = rig.find('spine')
        if spine:
            twist = math.sin(walk_phase) * spine_twist
            set_keyframe(spine, frame, rotation=(0.02 * intensity, twist, 0))
            if 'spine' not in animated_bones:
                animated_bones.append('spine')

        spine_upper = rig.find('spine_upper')
        if spine_upper:
            counter_twist = -math.sin(walk_phase) * spine_twist * 0.5
            set_keyframe(spine_upper, frame, rotation=(0, counter_twist, 0))
            if 'spine_upper' not in animated_bones:
                animated_bones.append('spine_upper')

        # Head - subtle bob
        head = rig.find('head')
        if head:
            nod = math.sin(half_phase) * head_bob
            set_keyframe(head, frame, rotation=(nod, 0, 0))
            if 'head' not in animated_bones:
                animated_bones.append('head')

        # Left leg
        thigh_l = rig.find('thigh_l')
        if thigh_l:
            swing = math.sin(walk_phase) * leg_swing
            set_keyframe(thigh_l, frame, rotation=(swing, 0, 0))
            if 'thigh_l' not in animated_bones:
                animated_bones.append('thigh_l')

        shin_l = rig.find('shin_l')
        if shin_l:
            bend = max(0, math.sin(walk_phase - 0.5)) * leg_swing * 1.2
            set_keyframe(shin_l, frame, rotation=(bend, 0, 0))
            if 'shin_l' not in animated_bones:
                animated_bones.append('shin_l')

        foot_l = rig.find('foot_l')
        if foot_l:
            flex = -math.sin(walk_phase) * 0.2 * intensity
            set_keyframe(foot_l, frame, rotation=(flex, 0, 0))
            if 'foot_l' not in animated_bones:
                animated_bones.append('foot_l')

        # Right leg (opposite phase)
        thigh_r = rig.find('thigh_r')
        if thigh_r:
            swing = -math.sin(walk_phase) * leg_swing
            set_keyframe(thigh_r, frame, rotation=(swing, 0, 0))
            if 'thigh_r' not in animated_bones:
                animated_bones.append('thigh_r')

        shin_r = rig.find('shin_r')
        if shin_r:
            bend = max(0, -math.sin(walk_phase - 0.5)) * leg_swing * 1.2
            set_keyframe(shin_r, frame, rotation=(bend, 0, 0))
            if 'shin_r' not in animated_bones:
                animated_bones.append('shin_r')

        foot_r = rig.find('foot_r')
        if foot_r:
            flex = math.sin(walk_phase) * 0.2 * intensity
            set_keyframe(foot_r, frame, rotation=(flex, 0, 0))
            if 'foot_r' not in animated_bones:
                animated_bones.append('foot_r')

        # Left arm (opposite to left leg for natural motion)
        upper_arm_l = rig.find('upper_arm_l')
        if upper_arm_l:
            swing = -math.sin(walk_phase) * arm_swing
            set_keyframe(upper_arm_l, frame, rotation=(swing, 0.1 * intensity, 0))
            if 'upper_arm_l' not in animated_bones:
                animated_bones.append('upper_arm_l')

        forearm_l = rig.find('forearm_l')
        if forearm_l:
            bend = 0.3 + max(0, -math.sin(walk_phase)) * 0.2 * intensity
            set_keyframe(forearm_l, frame, rotation=(bend, 0, 0))
            if 'forearm_l' not in animated_bones:
                animated_bones.append('forearm_l')

        shoulder_l = rig.find('shoulder_l')
        if shoulder_l:
            shrug = math.sin(walk_phase) * 0.05 * intensity
            set_keyframe(shoulder_l, frame, rotation=(0, shrug, 0))
            if 'shoulder_l' not in animated_bones:
                animated_bones.append('shoulder_l')

        # Right arm (opposite to right leg)
        upper_arm_r = rig.find('upper_arm_r')
        if upper_arm_r:
            swing = math.sin(walk_phase) * arm_swing
            set_keyframe(upper_arm_r, frame, rotation=(swing, -0.1 * intensity, 0))
            if 'upper_arm_r' not in animated_bones:
                animated_bones.append('upper_arm_r')

        forearm_r = rig.find('forearm_r')
        if forearm_r:
            bend = 0.3 + max(0, math.sin(walk_phase)) * 0.2 * intensity
            set_keyframe(forearm_r, frame, rotation=(bend, 0, 0))
            if 'forearm_r' not in animated_bones:
                animated_bones.append('forearm_r')

        shoulder_r = rig.find('shoulder_r')
        if shoulder_r:
            shrug = -math.sin(walk_phase) * 0.05 * intensity
            set_keyframe(shoulder_r, frame, rotation=(0, shrug, 0))
            if 'shoulder_r' not in animated_bones:
                animated_bones.append('shoulder_r')

    return animated_bones, num_frames


def main():
    # Parse command line arguments
    argv = sys.argv
    output_glb = None

    try:
        idx = argv.index("--") + 1
        if idx < len(argv):
            output_glb = argv[idx]
    except ValueError:
        pass

    if not output_glb:
        output_glb = "animated_output.glb"

    # Find armature - try generated rig first
    armature = bpy.data.objects.get('RIG-Humanoid_Rig') or bpy.data.objects.get('rig')
    if not armature:
        for obj in bpy.data.objects:
            if obj.type == 'ARMATURE':
                armature = obj
                break

    if not armature:
        print('ERROR: No armature found')
        sys.exit(1)

    print(f'Using armature: {armature.name} ({len(armature.data.bones)} bones)')

    # Create new action
    action_name = f'{armature.name}_{ANIMATION_TYPE}'
    action = bpy.data.actions.new(name=action_name)
    armature.animation_data_create()
    armature.animation_data.action = action

    # Generate animation
    animated_bones, num_frames = generate_walk_cycle(armature, DURATION, FPS, INTENSITY, LOOP)

    # Set frame range
    bpy.context.scene.frame_start = 1
    bpy.context.scene.frame_end = num_frames

    print(f'Generated {ANIMATION_TYPE} animation: {num_frames} frames')
    print(f'Animated bones ({len(animated_bones)}): {animated_bones}')

    # Save blend file
    bpy.ops.wm.save_mainfile()

    # Export to GLB
    bpy.ops.export_scene.gltf(
        filepath=output_glb,
        export_format='GLB',
        export_animations=True,
        export_skins=True
    )
    print(f'Exported to: {output_glb}')


if __name__ == "__main__":
    main()
