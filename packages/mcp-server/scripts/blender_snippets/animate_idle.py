# Blender snippet: Generate an idle/breathing animation for a rigged armature
# Parameters: ARMATURE_NAME, DURATION (seconds), FPS, INTENSITY (0.5-1.5)
#
# Usage via blender-mcp:
#   code = snippet.replace("ARMATURE_NAME", name).replace("DURATION", "3.0")...

import math
import bpy
from mathutils import Vector, Euler


def set_keyframe(bone, frame, location=None, rotation=None, scale=None):
    try:
        if location is not None:
            bone.location = Vector(location)
            bone.keyframe_insert(data_path="location", frame=frame)
        if rotation is not None:
            bone.rotation_mode = 'XYZ'
            bone.rotation_euler = Euler(rotation)
            bone.keyframe_insert(data_path="rotation_euler", frame=frame)
        if scale is not None:
            bone.scale = Vector(scale)
            bone.keyframe_insert(data_path="scale", frame=frame)
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
        'spine': ['spine_fk', 'spine', 'spine.001'],
        'spine2': ['spine_fk.001', 'spine.002', 'chest'],
        'neck': ['neck'], 'head': ['head'],
        'shoulder_l': ['shoulder.l', 'shoulder_l', 'shoulder.L'],
        'shoulder_r': ['shoulder.r', 'shoulder_r', 'shoulder.R'],
        'upper_arm_l': ['upper_arm_fk.l', 'upper_arm.l', 'upper_arm_fk.L'],
        'upper_arm_r': ['upper_arm_fk.r', 'upper_arm.r', 'upper_arm_fk.R'],
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
duration = float("DURATION") if "DURATION" != "DURATION" else 3.0
fps = int("FPS") if "FPS" != "FPS" else 30
intensity = float("INTENSITY") if "INTENSITY" != "INTENSITY" else 1.0

armature = bpy.data.objects.get(armature_name)
if armature is None or armature.type != 'ARMATURE':
    print(f"ERROR: '{armature_name}' not found or not an armature")
else:
    frame_count = int(fps * duration)
    if armature.animation_data:
        armature.animation_data_clear()
    action = bpy.data.actions.new(name=f"{armature.name}_idle")
    if not armature.animation_data:
        armature.animation_data_create()
    armature.animation_data.action = action
    bpy.context.scene.render.fps = fps
    bpy.context.scene.frame_start = 1
    bpy.context.scene.frame_end = frame_count

    rig = RigBones(armature)
    breath_amp = 0.008 * intensity
    sway_amp = 0.01 * intensity
    head_drift = 0.02 * intensity
    num_keys = max(8, frame_count // 4)

    bpy.context.view_layer.objects.active = armature
    bpy.ops.object.mode_set(mode='POSE')

    for i in range(num_keys + 1):
        t = i / num_keys
        frame = 1 + int(t * (frame_count - 1))
        breath = math.sin(t * 2 * math.pi)       # one full breath cycle
        sway = math.sin(t * 1.3 * math.pi)        # slow weight shift

        hips = rig.find('hips')
        if hips:
            set_keyframe(hips, frame,
                         location=(sway * sway_amp, 0, breath * breath_amp * 0.5),
                         rotation=(0, 0, sway * 0.01 * intensity))

        spine = rig.find('spine')
        if spine:
            set_keyframe(spine, frame, rotation=(breath * 0.01 * intensity, 0, 0))

        spine2 = rig.find('spine2')
        if spine2:
            set_keyframe(spine2, frame,
                         rotation=(breath * 0.008 * intensity, 0, 0),
                         scale=(1, 1, 1 + breath * breath_amp))

        neck = rig.find('neck')
        if neck:
            set_keyframe(neck, frame, rotation=(breath * 0.005 * intensity, 0, 0))

        head = rig.find('head')
        if head:
            head_phase = math.sin(t * 0.7 * math.pi)
            set_keyframe(head, frame, rotation=(head_phase * head_drift * 0.3, head_phase * head_drift, 0))

        for side, sign in [('_l', 1), ('_r', -1)]:
            sh = rig.find(f'shoulder{side}')
            if sh:
                set_keyframe(sh, frame, rotation=(breath * 0.005 * intensity, 0, sign * breath * 0.008 * intensity))
            ua = rig.find(f'upper_arm{side}')
            if ua:
                set_keyframe(ua, frame, rotation=(0, sign * sway * 0.02 * intensity, 0))

    bpy.ops.object.mode_set(mode='OBJECT')
    make_cyclic(action)
    print(f"SUCCESS: Idle animation on '{armature_name}' — {frame_count} frames at {fps}fps")
