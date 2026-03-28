# Blender snippet: Generate a walk cycle animation for a rigged armature
# Parameters: ARMATURE_NAME, DURATION (seconds), FPS, INTENSITY (0.5-1.5)
#
# Usage via blender-mcp:
#   code = snippet.replace("ARMATURE_NAME", name).replace("DURATION", "1.0")...
#   execute_blender_code(code=code)

import math
import bpy
from mathutils import Vector, Euler


def set_keyframe(bone, frame, location=None, rotation=None):
    try:
        if location is not None:
            bone.location = Vector(location)
            bone.keyframe_insert(data_path="location", frame=frame)
        if rotation is not None:
            bone.rotation_mode = 'XYZ'
            bone.rotation_euler = Euler(rotation)
            bone.keyframe_insert(data_path="rotation_euler", frame=frame)
    except Exception:
        pass


def get_fcurves_from_action(action):
    if hasattr(action, 'fcurves') and action.fcurves:
        return list(action.fcurves)
    if hasattr(action, 'layers') and action.layers:
        fcurves = []
        for layer in action.layers:
            if hasattr(layer, 'strips'):
                for strip in layer.strips:
                    if hasattr(strip, 'channelbags'):
                        for cb in strip.channelbags:
                            if hasattr(cb, 'fcurves'):
                                fcurves.extend(cb.fcurves)
        return fcurves
    return []


def make_cyclic(action):
    for fc in get_fcurves_from_action(action):
        mod = fc.modifiers.new(type='CYCLES')
        mod.mode_before = 'REPEAT'
        mod.mode_after = 'REPEAT'


class RigBones:
    PATTERNS = {
        'hips': ['hip', 'pelvis', 'torso', 'hips'],
        'spine': ['spine_fk', 'spine', 'spine.001'], 'spine2': ['spine_fk.001', 'spine.002', 'chest'],
        'shoulder_l': ['shoulder.l', 'shoulder_l', 'clavicle.l', 'shoulder.L'],
        'shoulder_r': ['shoulder.r', 'shoulder_r', 'clavicle.r', 'shoulder.R'],
        'upper_arm_l': ['upper_arm_fk.l', 'upper_arm.l', 'upper_arm_fk.L'],
        'upper_arm_r': ['upper_arm_fk.r', 'upper_arm.r', 'upper_arm_fk.R'],
        'forearm_l': ['forearm_fk.l', 'forearm.l', 'forearm_fk.L'],
        'forearm_r': ['forearm_fk.r', 'forearm.r', 'forearm_fk.R'],
        'thigh_l': ['thigh_fk.l', 'thigh.l', 'thigh_fk.L'],
        'thigh_r': ['thigh_fk.r', 'thigh.r', 'thigh_fk.R'],
        'shin_l': ['shin_fk.l', 'shin.l', 'shin_fk.L'],
        'shin_r': ['shin_fk.r', 'shin.r', 'shin_fk.R'],
        'foot_l': ['foot_fk.l', 'foot.l', 'foot_fk.L'],
        'foot_r': ['foot_fk.r', 'foot.r', 'foot_fk.R'],
        'head': ['head'], 'neck': ['neck'],
    }

    def __init__(self, armature):
        self.bones = armature.pose.bones
        self._cache = {}

    def find(self, role):
        if role in self._cache:
            return self._cache[role]
        for p in self.PATTERNS.get(role, []):
            pl = p.lower()
            for b in self.bones:
                if pl == b.name.lower():
                    self._cache[role] = b
                    return b
            for b in self.bones:
                if pl in b.name.lower():
                    self._cache[role] = b
                    return b
        return None


# --- Parameters ---
armature_name = "ARMATURE_NAME"
duration = float("DURATION") if "DURATION" != "DURATION" else 1.0
fps = int("FPS") if "FPS" != "FPS" else 30
intensity = float("INTENSITY") if "INTENSITY" != "INTENSITY" else 1.0

armature = bpy.data.objects.get(armature_name)
if armature is None or armature.type != 'ARMATURE':
    print(f"ERROR: '{armature_name}' not found or not an armature")
else:
    frame_count = int(fps * duration)
    if armature.animation_data:
        armature.animation_data_clear()
    action = bpy.data.actions.new(name=f"{armature.name}_walk")
    if not armature.animation_data:
        armature.animation_data_create()
    armature.animation_data.action = action
    bpy.context.scene.render.fps = fps
    bpy.context.scene.frame_start = 1
    bpy.context.scene.frame_end = frame_count

    rig = RigBones(armature)
    hip_sway = 0.025 * intensity
    spine_twist = 0.04 * intensity
    arm_swing = 0.35 * intensity
    forearm_bend = 0.25 * intensity
    leg_swing = 0.38 * intensity
    num_keys = max(12, frame_count // 2)

    bpy.context.view_layer.objects.active = armature
    bpy.ops.object.mode_set(mode='POSE')

    for i in range(num_keys + 1):
        t = i / num_keys
        frame = 1 + int(t * (frame_count - 1))
        phase = t * 2 * math.pi
        half = t * 4 * math.pi

        hips = rig.find('hips')
        if hips:
            set_keyframe(hips, frame,
                         location=(math.sin(phase) * hip_sway, 0, -abs(math.sin(half)) * 0.015 * intensity),
                         rotation=(math.sin(phase) * 0.04 * intensity, 0, math.sin(phase) * 0.06 * intensity))

        spine = rig.find('spine')
        if spine:
            set_keyframe(spine, frame, rotation=(0.015 * intensity, 0, -math.sin(phase) * spine_twist))

        for side, sign in [('_l', -1), ('_r', 1)]:
            ua = rig.find(f'upper_arm{side}')
            if ua:
                set_keyframe(ua, frame, rotation=(sign * math.sin(phase) * arm_swing, 0.1 * intensity, 0))
            fa = rig.find(f'forearm{side}')
            if fa:
                bend = forearm_bend * 0.5 + ((-sign * math.sin(phase) + 1) / 2) * forearm_bend
                set_keyframe(fa, frame, rotation=(bend, 0, 0))
            th = rig.find(f'thigh{side}')
            if th:
                set_keyframe(th, frame, rotation=(-sign * math.sin(phase) * leg_swing, 0, 0))
            sh = rig.find(f'shin{side}')
            if sh:
                knee_bend = max(0, -sign * math.sin(phase)) * 0.45 * intensity + 0.1 * intensity
                set_keyframe(sh, frame, rotation=(knee_bend, 0, 0))

    bpy.ops.object.mode_set(mode='OBJECT')
    make_cyclic(action)
    print(f"SUCCESS: Walk cycle on '{armature_name}' — {frame_count} frames at {fps}fps, intensity={intensity}")
