# Blender snippet: Rig a mesh with a humanoid skeleton (Rigify or biped fallback)
# Parameters: MESH_NAME (name of the mesh object to rig)
#
# Usage via blender-mcp:
#   execute_blender_code(code=snippet.replace("MESH_NAME", obj_name))

import math
import bpy
from mathutils import Vector


# --- Inlined utilities ---

def get_mesh_bounds(obj):
    if obj.type != 'MESH':
        return None
    bbox = [obj.matrix_world @ Vector(corner) for corner in obj.bound_box]
    min_co = Vector((min(v.x for v in bbox), min(v.y for v in bbox), min(v.z for v in bbox)))
    max_co = Vector((max(v.x for v in bbox), max(v.y for v in bbox), max(v.z for v in bbox)))
    center = (min_co + max_co) / 2
    size = max_co - min_co
    return {"min": min_co, "max": max_co, "center": center, "size": size,
            "height": size.z, "width": size.x, "depth": size.y}


def create_armature(name="Armature"):
    armature_data = bpy.data.armatures.new(name)
    armature_obj = bpy.data.objects.new(name, armature_data)
    bpy.context.collection.objects.link(armature_obj)
    return armature_obj


def add_bone(armature_obj, name, head, tail, parent_name=None, connect=False):
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


def add_basic_ik(armature):
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


# --- Main rigging logic ---

mesh_name = "MESH_NAME"
mesh_obj = bpy.data.objects.get(mesh_name)

if mesh_obj is None or mesh_obj.type != 'MESH':
    print(f"ERROR: Object '{mesh_name}' not found or not a mesh")
else:
    bounds = get_mesh_bounds(mesh_obj)
    if not bounds:
        print("ERROR: Could not read mesh bounds")
    else:
        height = bounds["height"]
        center = bounds["center"]
        base_z = bounds["min"].z
        width = bounds["width"]

        # Try Rigify first
        armature = None
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
                generated = bpy.data.objects.get("rig")
                if generated:
                    armature = generated
            except Exception as e:
                print(f"Rigify generate failed (metarig still usable): {e}")
        except Exception as e:
            print(f"Rigify not available, using biped simple rig: {e}")
            armature = None

        # Fallback: biped simple rig
        if armature is None:
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

            # Spine
            add_bone(armature, "root", (center.x, center.y, base_z),
                     (center.x, center.y, base_z + height * 0.1))
            add_bone(armature, "spine", (center.x, center.y, base_z + hip_height * 0.5),
                     (center.x, center.y, base_z + hip_height), parent_name="root")
            add_bone(armature, "spine.001", (center.x, center.y, base_z + hip_height),
                     (center.x, center.y, base_z + chest_height), parent_name="spine", connect=True)
            add_bone(armature, "spine.002", (center.x, center.y, base_z + chest_height),
                     (center.x, center.y, base_z + neck_height), parent_name="spine.001", connect=True)
            add_bone(armature, "neck", (center.x, center.y, base_z + neck_height),
                     (center.x, center.y, base_z + head_height * 0.95), parent_name="spine.002", connect=True)
            add_bone(armature, "head", (center.x, center.y, base_z + head_height * 0.95),
                     (center.x, center.y, base_z + height), parent_name="neck", connect=True)

            # Arms
            for side, sign in [(".L", 1), (".R", -1)]:
                sw = shoulder_width * sign
                shoulder = (center.x + sw, center.y, base_z + neck_height)
                elbow = (center.x + sw + arm_length * 0.5 * sign, center.y, base_z + neck_height - height * 0.05)
                wrist = (center.x + sw + arm_length * sign, center.y, base_z + neck_height - height * 0.1)
                hand_end = (wrist[0] + arm_length * 0.15 * sign, wrist[1], wrist[2])

                add_bone(armature, f"shoulder{side}", (center.x, center.y, base_z + neck_height),
                         shoulder, parent_name="spine.002")
                add_bone(armature, f"upper_arm{side}", shoulder, elbow, parent_name=f"shoulder{side}", connect=True)
                add_bone(armature, f"forearm{side}", elbow, wrist, parent_name=f"upper_arm{side}", connect=True)
                add_bone(armature, f"hand{side}", wrist, hand_end, parent_name=f"forearm{side}", connect=True)

            # Legs
            for side, sign in [(".L", 1), (".R", -1)]:
                hw = hip_width * sign
                hip = (center.x + hw, center.y, base_z + hip_height * 0.5)
                knee = (center.x + hw, center.y + height * 0.02, base_z + leg_length * 0.5)
                ankle = (center.x + hw, center.y, base_z + height * 0.05)
                toe = (ankle[0], ankle[1] - height * 0.1, ankle[2])

                add_bone(armature, f"thigh{side}", hip, knee, parent_name="spine")
                add_bone(armature, f"shin{side}", knee, ankle, parent_name=f"thigh{side}", connect=True)
                add_bone(armature, f"foot{side}", ankle, toe, parent_name=f"shin{side}", connect=True)

            bpy.ops.object.mode_set(mode='OBJECT')
            add_basic_ik(armature)

        # Parent mesh to armature with auto weights
        parent_mesh_to_armature(mesh_obj, armature, auto_weights=True)

        bone_count = len(armature.data.bones)
        print(f"SUCCESS: Rigged '{mesh_name}' with {bone_count} bones -> armature '{armature.name}'")
