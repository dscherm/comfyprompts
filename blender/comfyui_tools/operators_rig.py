"""Rigging operators for ComfyUI Blender addon."""

import bpy
from bpy.types import Operator

from .utils import (
    add_bone,
    create_armature,
    get_mesh_bounds,
    parent_mesh_to_armature,
)


def _add_basic_ik(armature):
    """Add basic IK constraints to arms and legs."""
    bpy.context.view_layer.objects.active = armature
    bpy.ops.object.mode_set(mode='POSE')

    for side in [".L", ".R"]:
        for bone_name in [f"forearm{side}", f"shin{side}"]:
            bone = armature.pose.bones.get(bone_name)
            if bone:
                try:
                    ik = bone.constraints.new('IK')
                    ik.chain_count = 2
                    ik.use_tail = True
                except Exception:
                    pass

    bpy.ops.object.mode_set(mode='OBJECT')


def _create_humanoid_rig(mesh_obj, auto_weights, generate_ik):
    """Create a humanoid rig using Rigify metarig, falling back to biped simple."""
    bounds = get_mesh_bounds(mesh_obj)
    if not bounds:
        return None

    height = bounds["height"]
    center = bounds["center"]
    base_z = bounds["min"].z

    try:
        if "rigify" not in bpy.context.preferences.addons:
            bpy.ops.preferences.addon_enable(module="rigify")

        bpy.ops.object.armature_human_metarig_add()
        armature = bpy.context.active_object

        armature.location = (center.x, center.y, base_z)
        scale_factor = height / 2.0
        armature.scale = (scale_factor, scale_factor, scale_factor)
        bpy.ops.object.transform_apply(scale=True)
        armature.name = "Humanoid_Rig"

        bpy.context.view_layer.objects.active = armature
        try:
            bpy.ops.pose.rigify_generate()
            generated_rig = bpy.data.objects.get("rig")
            if generated_rig:
                armature = generated_rig
        except Exception as e:
            print(f"Rigify generate failed (metarig still usable): {e}")

        return armature

    except Exception as e:
        print(f"Rigify not available, falling back to biped simple rig: {e}")
        return _create_biped_simple_rig(mesh_obj, generate_ik)


def _create_biped_simple_rig(mesh_obj, generate_ik):
    """Create a simplified biped rig without Rigify."""
    bounds = get_mesh_bounds(mesh_obj)
    if not bounds:
        return None

    height = bounds["height"]
    center = bounds["center"]
    base_z = bounds["min"].z
    width = bounds["width"]

    hip_height = height * 0.5
    chest_height = height * 0.7
    neck_height = height * 0.85
    head_height = height * 0.95
    shoulder_width = width * 0.4
    hip_width = width * 0.15
    arm_length = height * 0.35
    leg_length = height * 0.45

    armature = create_armature("Biped_Rig")
    bpy.context.view_layer.objects.active = armature
    bpy.ops.object.mode_set(mode='EDIT')

    # Spine chain
    add_bone(armature, "root",
             (center.x, center.y, base_z),
             (center.x, center.y, base_z + height * 0.1))

    add_bone(armature, "spine",
             (center.x, center.y, base_z + hip_height * 0.5),
             (center.x, center.y, base_z + hip_height),
             parent_name="root")

    add_bone(armature, "spine.001",
             (center.x, center.y, base_z + hip_height),
             (center.x, center.y, base_z + chest_height),
             parent_name="spine", connect=True)

    add_bone(armature, "spine.002",
             (center.x, center.y, base_z + chest_height),
             (center.x, center.y, base_z + neck_height),
             parent_name="spine.001", connect=True)

    add_bone(armature, "neck",
             (center.x, center.y, base_z + neck_height),
             (center.x, center.y, base_z + head_height * 0.95),
             parent_name="spine.002", connect=True)

    add_bone(armature, "head",
             (center.x, center.y, base_z + head_height * 0.95),
             (center.x, center.y, base_z + height),
             parent_name="neck", connect=True)

    # Left arm
    shoulder_l = (center.x + shoulder_width, center.y, base_z + neck_height)
    elbow_l = (center.x + shoulder_width + arm_length * 0.5, center.y, base_z + neck_height - height * 0.05)
    wrist_l = (center.x + shoulder_width + arm_length, center.y, base_z + neck_height - height * 0.1)

    add_bone(armature, "shoulder.L",
             (center.x, center.y, base_z + neck_height),
             shoulder_l, parent_name="spine.002")
    add_bone(armature, "upper_arm.L", shoulder_l, elbow_l, parent_name="shoulder.L", connect=True)
    add_bone(armature, "forearm.L", elbow_l, wrist_l, parent_name="upper_arm.L", connect=True)
    add_bone(armature, "hand.L", wrist_l,
             (wrist_l[0] + arm_length * 0.15, wrist_l[1], wrist_l[2]),
             parent_name="forearm.L", connect=True)

    # Right arm
    shoulder_r = (center.x - shoulder_width, center.y, base_z + neck_height)
    elbow_r = (center.x - shoulder_width - arm_length * 0.5, center.y, base_z + neck_height - height * 0.05)
    wrist_r = (center.x - shoulder_width - arm_length, center.y, base_z + neck_height - height * 0.1)

    add_bone(armature, "shoulder.R",
             (center.x, center.y, base_z + neck_height),
             shoulder_r, parent_name="spine.002")
    add_bone(armature, "upper_arm.R", shoulder_r, elbow_r, parent_name="shoulder.R", connect=True)
    add_bone(armature, "forearm.R", elbow_r, wrist_r, parent_name="upper_arm.R", connect=True)
    add_bone(armature, "hand.R", wrist_r,
             (wrist_r[0] - arm_length * 0.15, wrist_r[1], wrist_r[2]),
             parent_name="forearm.R", connect=True)

    # Left leg
    hip_l = (center.x + hip_width, center.y, base_z + hip_height * 0.5)
    knee_l = (center.x + hip_width, center.y + height * 0.02, base_z + leg_length * 0.5)
    ankle_l = (center.x + hip_width, center.y, base_z + height * 0.05)

    add_bone(armature, "thigh.L", hip_l, knee_l, parent_name="spine")
    add_bone(armature, "shin.L", knee_l, ankle_l, parent_name="thigh.L", connect=True)
    add_bone(armature, "foot.L", ankle_l,
             (ankle_l[0], ankle_l[1] - height * 0.1, ankle_l[2]),
             parent_name="shin.L", connect=True)

    # Right leg
    hip_r = (center.x - hip_width, center.y, base_z + hip_height * 0.5)
    knee_r = (center.x - hip_width, center.y + height * 0.02, base_z + leg_length * 0.5)
    ankle_r = (center.x - hip_width, center.y, base_z + height * 0.05)

    add_bone(armature, "thigh.R", hip_r, knee_r, parent_name="spine")
    add_bone(armature, "shin.R", knee_r, ankle_r, parent_name="thigh.R", connect=True)
    add_bone(armature, "foot.R", ankle_r,
             (ankle_r[0], ankle_r[1] - height * 0.1, ankle_r[2]),
             parent_name="shin.R", connect=True)

    bpy.ops.object.mode_set(mode='OBJECT')

    if generate_ik:
        _add_basic_ik(armature)

    return armature


def _create_quadruped_rig(mesh_obj, generate_ik):
    """Create a quadruped rig for four-legged animals."""
    bounds = get_mesh_bounds(mesh_obj)
    if not bounds:
        return None

    height = bounds["height"]
    length = bounds["depth"]
    width = bounds["width"]
    center = bounds["center"]
    base_z = bounds["min"].z

    armature = create_armature("Quadruped_Rig")
    bpy.context.view_layer.objects.active = armature
    bpy.ops.object.mode_set(mode='EDIT')

    spine_y_start = center.y - length * 0.4
    spine_y_end = center.y + length * 0.35
    spine_z = base_z + height * 0.7

    add_bone(armature, "root",
             (center.x, center.y, base_z),
             (center.x, center.y, base_z + height * 0.3))

    add_bone(armature, "spine",
             (center.x, spine_y_start, spine_z),
             (center.x, center.y - length * 0.1, spine_z),
             parent_name="root")

    add_bone(armature, "spine.001",
             (center.x, center.y - length * 0.1, spine_z),
             (center.x, center.y + length * 0.1, spine_z),
             parent_name="spine", connect=True)

    add_bone(armature, "spine.002",
             (center.x, center.y + length * 0.1, spine_z),
             (center.x, spine_y_end, spine_z),
             parent_name="spine.001", connect=True)

    # Neck and head
    neck_start = (center.x, spine_y_end, spine_z)
    neck_end = (center.x, spine_y_end + length * 0.15, spine_z + height * 0.2)
    head_end = (center.x, spine_y_end + length * 0.3, spine_z + height * 0.25)

    add_bone(armature, "neck", neck_start, neck_end, parent_name="spine.002", connect=True)
    add_bone(armature, "head", neck_end, head_end, parent_name="neck", connect=True)

    # Tail
    tail_start = (center.x, spine_y_start, spine_z)
    add_bone(armature, "tail", tail_start,
             (center.x, spine_y_start - length * 0.15, spine_z - height * 0.1),
             parent_name="spine")
    add_bone(armature, "tail.001",
             (center.x, spine_y_start - length * 0.15, spine_z - height * 0.1),
             (center.x, spine_y_start - length * 0.3, spine_z - height * 0.2),
             parent_name="tail", connect=True)

    # Legs
    leg_width = width * 0.3
    front_y = spine_y_end - length * 0.1
    back_y = spine_y_start + length * 0.1

    for side, x_offset in [(".L", leg_width), (".R", -leg_width)]:
        shoulder = (center.x + x_offset, front_y, spine_z)
        elbow = (center.x + x_offset, front_y, spine_z - height * 0.35)
        paw_front = (center.x + x_offset, front_y, base_z + height * 0.05)

        add_bone(armature, f"front_upper{side}", shoulder, elbow, parent_name="spine.002")
        add_bone(armature, f"front_lower{side}", elbow, paw_front, parent_name=f"front_upper{side}", connect=True)
        add_bone(armature, f"front_paw{side}", paw_front,
                 (paw_front[0], paw_front[1] + length * 0.05, paw_front[2]),
                 parent_name=f"front_lower{side}", connect=True)

        hip = (center.x + x_offset, back_y, spine_z)
        knee = (center.x + x_offset, back_y - length * 0.05, spine_z - height * 0.35)
        paw_back = (center.x + x_offset, back_y, base_z + height * 0.05)

        add_bone(armature, f"back_upper{side}", hip, knee, parent_name="spine")
        add_bone(armature, f"back_lower{side}", knee, paw_back, parent_name=f"back_upper{side}", connect=True)
        add_bone(armature, f"back_paw{side}", paw_back,
                 (paw_back[0], paw_back[1] + length * 0.05, paw_back[2]),
                 parent_name=f"back_lower{side}", connect=True)

    bpy.ops.object.mode_set(mode='OBJECT')
    return armature


def _create_simple_rig(mesh_obj):
    """Create a simple spine-only rig."""
    bounds = get_mesh_bounds(mesh_obj)
    if not bounds:
        return None

    height = bounds["height"]
    center = bounds["center"]
    base_z = bounds["min"].z
    num_bones = 5
    bone_height = height / num_bones

    armature = create_armature("Simple_Rig")
    bpy.context.view_layer.objects.active = armature
    bpy.ops.object.mode_set(mode='EDIT')

    for i in range(num_bones):
        bone_name = f"bone.{i:03d}" if i > 0 else "root"
        parent_name = f"bone.{i-1:03d}" if i > 1 else ("root" if i > 0 else None)

        head_z = base_z + (i * bone_height)
        tail_z = base_z + ((i + 1) * bone_height)

        add_bone(armature, bone_name,
                 (center.x, center.y, head_z),
                 (center.x, center.y, tail_z),
                 parent_name=parent_name,
                 connect=(i > 0))

    bpy.ops.object.mode_set(mode='OBJECT')
    return armature


class COMFYUI_OT_auto_rig(Operator):
    """Auto-rig the selected mesh using the chosen rig type and backend"""
    bl_idname = "comfyui.auto_rig"
    bl_label = "Auto-Rig Model"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return obj is not None and obj.type == 'MESH'

    def execute(self, context):
        props = context.scene.comfyui_rig
        mesh_obj = context.active_object

        rig_type = props.rig_type
        backend = props.rig_backend
        auto_weights = props.auto_weights
        generate_ik = props.generate_ik

        if backend == 'UNIRIG':
            self.report({'WARNING'}, "UniRig backend runs via MCP server. Use Rigify for in-Blender rigging.")
            return {'CANCELLED'}
        if backend == 'TRIPO':
            self.report({'WARNING'}, "Tripo3D backend runs via MCP server. Use Rigify for in-Blender rigging.")
            return {'CANCELLED'}

        if rig_type == 'HUMANOID':
            armature = _create_humanoid_rig(mesh_obj, auto_weights, generate_ik)
        elif rig_type == 'BIPED_SIMPLE':
            armature = _create_biped_simple_rig(mesh_obj, generate_ik)
        elif rig_type == 'QUADRUPED':
            armature = _create_quadruped_rig(mesh_obj, generate_ik)
        elif rig_type == 'SIMPLE':
            armature = _create_simple_rig(mesh_obj)
        else:
            self.report({'ERROR'}, f"Unknown rig type: {rig_type}")
            return {'CANCELLED'}

        if armature is None:
            self.report({'ERROR'}, "Failed to create armature (could not read mesh bounds)")
            return {'CANCELLED'}

        parent_mesh_to_armature(mesh_obj, armature, auto_weights)

        self.report({'INFO'}, f"Created {rig_type} rig: {armature.name} ({len(armature.data.bones)} bones)")
        return {'FINISHED'}
