# Blender snippet: Rig a mesh with a quadruped skeleton (4-legged animal)
# Parameters: MESH_NAME (name of the mesh object to rig)
#
# Usage via blender-mcp:
#   execute_blender_code(code=snippet.replace("MESH_NAME", obj_name))

import bpy
from mathutils import Vector


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


def parent_mesh_to_armature(mesh_obj, armature_obj):
    bpy.ops.object.select_all(action='DESELECT')
    mesh_obj.select_set(True)
    armature_obj.select_set(True)
    bpy.context.view_layer.objects.active = armature_obj
    try:
        bpy.ops.object.parent_set(type='ARMATURE_AUTO')
    except Exception:
        bpy.ops.object.parent_set(type='ARMATURE_ENVELOPE')


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

        add_bone(armature, "root", (center.x, center.y, base_z),
                 (center.x, center.y, base_z + height * 0.3))
        add_bone(armature, "spine", (center.x, spine_y_start, spine_z),
                 (center.x, center.y - length * 0.1, spine_z), parent_name="root")
        add_bone(armature, "spine.001", (center.x, center.y - length * 0.1, spine_z),
                 (center.x, center.y + length * 0.1, spine_z), parent_name="spine", connect=True)
        add_bone(armature, "spine.002", (center.x, center.y + length * 0.1, spine_z),
                 (center.x, spine_y_end, spine_z), parent_name="spine.001", connect=True)

        # Neck and head
        add_bone(armature, "neck", (center.x, spine_y_end, spine_z),
                 (center.x, spine_y_end + length * 0.15, spine_z + height * 0.2),
                 parent_name="spine.002", connect=True)
        add_bone(armature, "head",
                 (center.x, spine_y_end + length * 0.15, spine_z + height * 0.2),
                 (center.x, spine_y_end + length * 0.3, spine_z + height * 0.25),
                 parent_name="neck", connect=True)

        # Tail
        add_bone(armature, "tail", (center.x, spine_y_start, spine_z),
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
            # Front legs
            shoulder = (center.x + x_offset, front_y, spine_z)
            elbow = (center.x + x_offset, front_y, spine_z - height * 0.35)
            paw = (center.x + x_offset, front_y, base_z + height * 0.05)
            add_bone(armature, f"front_upper{side}", shoulder, elbow, parent_name="spine.002")
            add_bone(armature, f"front_lower{side}", elbow, paw, parent_name=f"front_upper{side}", connect=True)
            add_bone(armature, f"front_paw{side}", paw,
                     (paw[0], paw[1] + length * 0.05, paw[2]),
                     parent_name=f"front_lower{side}", connect=True)

            # Back legs
            hip = (center.x + x_offset, back_y, spine_z)
            knee = (center.x + x_offset, back_y - length * 0.05, spine_z - height * 0.35)
            paw_b = (center.x + x_offset, back_y, base_z + height * 0.05)
            add_bone(armature, f"back_upper{side}", hip, knee, parent_name="spine")
            add_bone(armature, f"back_lower{side}", knee, paw_b, parent_name=f"back_upper{side}", connect=True)
            add_bone(armature, f"back_paw{side}", paw_b,
                     (paw_b[0], paw_b[1] + length * 0.05, paw_b[2]),
                     parent_name=f"back_lower{side}", connect=True)

        bpy.ops.object.mode_set(mode='OBJECT')
        parent_mesh_to_armature(mesh_obj, armature)

        bone_count = len(armature.data.bones)
        print(f"SUCCESS: Quadruped rigged '{mesh_name}' with {bone_count} bones -> '{armature.name}'")
