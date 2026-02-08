"""Utility functions for ComfyUI Blender addon.

Easing functions, animation helpers, rig bone finder, and rigging utilities.
"""

import math

import bpy
from mathutils import Euler, Quaternion, Vector


# =============================================================================
# EASING FUNCTIONS
# =============================================================================

def ease_in_out_sine(t):
    """Sine ease in/out - smooth acceleration and deceleration."""
    return -(math.cos(math.pi * t) - 1) / 2


def ease_in_out_quad(t):
    """Quadratic ease in/out."""
    if t < 0.5:
        return 2 * t * t
    return 1 - pow(-2 * t + 2, 2) / 2


def ease_out_elastic(t):
    """Elastic ease out - bouncy overshoot."""
    if t == 0 or t == 1:
        return t
    return pow(2, -10 * t) * math.sin((t * 10 - 0.75) * (2 * math.pi) / 3) + 1


def ease_out_back(t):
    """Back ease out - slight overshoot."""
    c1 = 1.70158
    c3 = c1 + 1
    return 1 + c3 * pow(t - 1, 3) + c1 * pow(t - 1, 2)


def smooth_step(t):
    """Smooth step function."""
    return t * t * (3 - 2 * t)


def lerp(a, b, t):
    """Linear interpolation."""
    return a + (b - a) * t


# =============================================================================
# ANIMATION UTILITIES
# =============================================================================

def get_fcurves_from_action(action):
    """Get fcurves from an action, handling both legacy and layered actions."""
    if hasattr(action, 'fcurves') and action.fcurves:
        return list(action.fcurves)
    if hasattr(action, 'layers') and action.layers:
        fcurves = []
        for layer in action.layers:
            if hasattr(layer, 'strips'):
                for strip in layer.strips:
                    if hasattr(strip, 'channelbags'):
                        for channelbag in strip.channelbags:
                            if hasattr(channelbag, 'fcurves'):
                                fcurves.extend(channelbag.fcurves)
        return fcurves
    return []


def set_keyframe(bone, frame, location=None, rotation=None, scale=None):
    """Set keyframes for a bone."""
    try:
        if location is not None:
            bone.location = Vector(location)
            bone.keyframe_insert(data_path="location", frame=frame)
        if rotation is not None:
            if len(rotation) == 3:
                bone.rotation_mode = 'XYZ'
                bone.rotation_euler = Euler(rotation)
                bone.keyframe_insert(data_path="rotation_euler", frame=frame)
            elif len(rotation) == 4:
                bone.rotation_mode = 'QUATERNION'
                bone.rotation_quaternion = Quaternion(rotation)
                bone.keyframe_insert(data_path="rotation_quaternion", frame=frame)
        if scale is not None:
            bone.scale = Vector(scale)
            bone.keyframe_insert(data_path="scale", frame=frame)
    except Exception:
        pass  # Silently skip bones that can't be keyframed


def make_cyclic(action):
    """Make animation curves cyclic for looping."""
    fcurves = get_fcurves_from_action(action)
    for fcurve in fcurves:
        mod = fcurve.modifiers.new(type='CYCLES')
        mod.mode_before = 'REPEAT'
        mod.mode_after = 'REPEAT'


def set_interpolation(action, interpolation='BEZIER'):
    """Set interpolation type for all keyframes."""
    fcurves = get_fcurves_from_action(action)
    for fcurve in fcurves:
        for keyframe in fcurve.keyframe_points:
            keyframe.interpolation = interpolation
            if interpolation == 'BEZIER':
                keyframe.handle_left_type = 'AUTO_CLAMPED'
                keyframe.handle_right_type = 'AUTO_CLAMPED'


# =============================================================================
# RIG BONES HELPER
# =============================================================================

class RigBones:
    """Helper class to find bones in different rig types."""

    def __init__(self, armature):
        self.armature = armature
        self.bones = armature.pose.bones
        self._cache = {}

    def find(self, role):
        """Find bone by role (spine, hips, head, etc.)."""
        if role in self._cache:
            return self._cache[role]

        patterns = {
            'root': ['root', 'master', 'main', 'torso'],
            'hips': ['hip', 'pelvis', 'torso', 'hips'],
            'spine': ['spine_fk', 'spine', 'spine.001', 'spine1'],
            'spine2': ['spine_fk.001', 'spine.002', 'spine2', 'chest'],
            'chest': ['chest', 'spine_fk.002', 'spine.003', 'spine3'],
            'neck': ['neck'],
            'head': ['head'],
            'shoulder_l': ['shoulder.l', 'shoulder_l', 'clavicle.l', 'shoulder.L'],
            'shoulder_r': ['shoulder.r', 'shoulder_r', 'clavicle.r', 'shoulder.R'],
            'upper_arm_l': ['upper_arm_fk.l', 'upper_arm.l', 'upperarm.l', 'arm.l', 'upper_arm_fk.L'],
            'upper_arm_r': ['upper_arm_fk.r', 'upper_arm.r', 'upperarm.r', 'arm.r', 'upper_arm_fk.R'],
            'forearm_l': ['forearm_fk.l', 'forearm.l', 'lower_arm.l', 'lowerarm.l', 'forearm_fk.L'],
            'forearm_r': ['forearm_fk.r', 'forearm.r', 'lower_arm.r', 'lowerarm.r', 'forearm_fk.R'],
            'hand_l': ['hand_fk.l', 'hand.l', 'wrist.l', 'hand_fk.L'],
            'hand_r': ['hand_fk.r', 'hand.r', 'wrist.r', 'hand_fk.R'],
            'thigh_l': ['thigh_fk.l', 'thigh.l', 'upper_leg.l', 'upperleg.l', 'leg.l', 'thigh_fk.L'],
            'thigh_r': ['thigh_fk.r', 'thigh.r', 'upper_leg.r', 'upperleg.r', 'leg.r', 'thigh_fk.R'],
            'shin_l': ['shin_fk.l', 'shin.l', 'lower_leg.l', 'lowerleg.l', 'calf.l', 'shin_fk.L'],
            'shin_r': ['shin_fk.r', 'shin.r', 'lower_leg.r', 'lowerleg.r', 'calf.r', 'shin_fk.R'],
            'foot_l': ['foot_fk.l', 'foot.l', 'ankle.l', 'foot_fk.L'],
            'foot_r': ['foot_fk.r', 'foot.r', 'ankle.r', 'foot_fk.R'],
            'toe_l': ['toe.l', 'toes.l', 'toe.L'],
            'toe_r': ['toe.r', 'toes.r', 'toe.R'],
        }

        if role not in patterns:
            return None

        for pattern in patterns[role]:
            pattern_lower = pattern.lower()
            for bone in self.bones:
                if pattern_lower == bone.name.lower():
                    self._cache[role] = bone
                    return bone
            for bone in self.bones:
                if pattern_lower in bone.name.lower():
                    self._cache[role] = bone
                    return bone
        return None


# =============================================================================
# RIGGING UTILITIES
# =============================================================================

def get_mesh_bounds(obj):
    """Get bounding box of a mesh object in world space."""
    if obj.type != 'MESH':
        return None

    bbox = [obj.matrix_world @ Vector(corner) for corner in obj.bound_box]

    min_co = Vector((min(v.x for v in bbox), min(v.y for v in bbox), min(v.z for v in bbox)))
    max_co = Vector((max(v.x for v in bbox), max(v.y for v in bbox), max(v.z for v in bbox)))
    center = (min_co + max_co) / 2
    size = max_co - min_co

    return {
        "min": min_co,
        "max": max_co,
        "center": center,
        "size": size,
        "height": size.z,
        "width": size.x,
        "depth": size.y,
    }


def create_armature(name="Armature"):
    """Create a new armature object."""
    armature_data = bpy.data.armatures.new(name)
    armature_obj = bpy.data.objects.new(name, armature_data)
    bpy.context.collection.objects.link(armature_obj)
    return armature_obj


def add_bone(armature_obj, name, head, tail, parent_name=None, connect=False):
    """Add a bone to an armature. Must be in edit mode on the armature."""
    bone = armature_obj.data.edit_bones.new(name)
    bone.head = head
    bone.tail = tail

    if parent_name:
        parent = armature_obj.data.edit_bones.get(parent_name)
        if parent:
            bone.parent = parent
            bone.use_connect = connect

    return bone


def parent_mesh_to_armature(mesh_obj, armature_obj, auto_weights=True):
    """Parent mesh to armature with automatic weights."""
    bpy.ops.object.select_all(action='DESELECT')
    mesh_obj.select_set(True)
    armature_obj.select_set(True)
    bpy.context.view_layer.objects.active = armature_obj

    if auto_weights:
        try:
            bpy.ops.object.parent_set(type='ARMATURE_AUTO')
        except Exception:
            bpy.ops.object.parent_set(type='ARMATURE_ENVELOPE')
    else:
        bpy.ops.object.parent_set(type='ARMATURE_NAME')
