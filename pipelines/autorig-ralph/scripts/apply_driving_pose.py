"""
Apply driving pose to a UniRig-skinned character.
Uses IK constraints for arms (UniRig bone axes are arbitrary)
and Euler rotation for legs/spine (roughly world-Z aligned).

Usage:
    blender --background --python apply_driving_pose.py -- input.fbx output.glb
"""

import bpy
import math
import sys
import os
from mathutils import Vector

argv = sys.argv
if "--" in argv:
    argv = argv[argv.index("--") + 1:]
else:
    argv = []

if len(argv) < 2:
    print("Usage: blender --background --python apply_driving_pose.py -- input.fbx output.glb")
    sys.exit(1)

input_path = argv[0]
output_path = argv[1]

print(f"Input:  {input_path}")
print(f"Output: {output_path}")


def main():
    # Clear scene
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()

    # Import FBX
    bpy.ops.import_scene.fbx(filepath=input_path)
    print("Imported FBX")

    # Find armature
    armature = None
    for obj in bpy.data.objects:
        if obj.type == 'ARMATURE':
            armature = obj
            break

    if not armature:
        print("ERROR: No armature found")
        return

    print(f"Armature: {armature.name}, {len(armature.data.bones)} bones")

    # Enter pose mode
    bpy.context.view_layer.objects.active = armature
    armature.select_set(True)
    bpy.ops.object.mode_set(mode='POSE')

    def get_pb(name):
        return armature.pose.bones.get(name)

    # === LEGS (Euler) ===
    print("\n=== Legs ===")
    for bone_name, x_deg in [
        ("bone_44", -90), ("bone_45", 90), ("bone_46", -30),  # R leg
        ("bone_48", -90), ("bone_49", 90), ("bone_50", -30),  # L leg
    ]:
        pb = get_pb(bone_name)
        if pb:
            pb.rotation_mode = 'XYZ'
            pb.rotation_euler = (math.radians(x_deg), 0, 0)
            print(f"  {bone_name}: {x_deg} deg X")

    # === SPINE ===
    print("\n=== Spine ===")
    for bone_name, x_deg in [
        ("bone_2", -15), ("bone_3", -10), ("bone_4", 5), ("bone_5", 15),
    ]:
        pb = get_pb(bone_name)
        if pb:
            pb.rotation_mode = 'XYZ'
            pb.rotation_euler = (math.radians(x_deg), 0, 0)
            print(f"  {bone_name}: {x_deg} deg X")

    # === ARMS (IK) ===
    print("\n=== Arms (IK) ===")
    hand_r = get_pb("bone_9")
    hand_l = get_pb("bone_28")

    # Switch to object mode to create empties
    bpy.ops.object.mode_set(mode='OBJECT')

    # Create IK targets
    targets = {}
    for name, pos in [("IK_R", Vector((0.15, -0.6, 0.45))),
                       ("IK_L", Vector((-0.15, -0.6, 0.45)))]:
        bpy.ops.object.empty_add(type='PLAIN_AXES', radius=0.02, location=pos)
        targets[name] = bpy.context.active_object
        targets[name].name = name
        print(f"  Target {name} at {pos}")

    # Back to pose mode on armature
    bpy.context.view_layer.objects.active = armature
    armature.select_set(True)
    bpy.ops.object.mode_set(mode='POSE')

    if hand_r:
        ik = hand_r.constraints.new(type='IK')
        ik.target = targets["IK_R"]
        ik.chain_count = 3
        ik.iterations = 200
        print(f"  IK on {hand_r.name} -> IK_R")

    if hand_l:
        ik = hand_l.constraints.new(type='IK')
        ik.target = targets["IK_L"]
        ik.chain_count = 3
        ik.iterations = 200
        print(f"  IK on {hand_l.name} -> IK_L")

    # Update scene so IK solves
    bpy.context.view_layer.update()

    # === BAKE: Apply pose with mesh deformation ===
    print("\n=== Baking pose into mesh ===")

    # Step 1: Evaluate the deformed mesh in the current pose
    bpy.ops.object.mode_set(mode='OBJECT')

    # Find the mesh
    mesh_obj = None
    for obj in bpy.data.objects:
        if obj.type == 'MESH' and obj.parent == armature:
            mesh_obj = obj
            break

    if mesh_obj:
        # Evaluate the depsgraph to get the posed mesh
        depsgraph = bpy.context.evaluated_depsgraph_get()
        eval_obj = mesh_obj.evaluated_get(depsgraph)
        eval_mesh = bpy.data.meshes.new_from_object(eval_obj)

        # Replace the original mesh data with the deformed version
        old_mesh = mesh_obj.data
        mesh_obj.data = eval_mesh
        eval_mesh.name = old_mesh.name
        bpy.data.meshes.remove(old_mesh)
        print(f"  Baked deformed mesh: {len(eval_mesh.vertices)} verts")

        # Transfer vertex groups from old mesh (they were lost in new_from_object)
        # Actually vertex groups live on the Object, not the Mesh, so they're preserved
        print(f"  Vertex groups preserved: {len(mesh_obj.vertex_groups)}")
    else:
        print("  WARN: No mesh found parented to armature")

    # Step 2: Apply the armature pose as new rest pose
    bpy.context.view_layer.objects.active = armature
    armature.select_set(True)
    bpy.ops.object.mode_set(mode='POSE')
    bpy.ops.pose.armature_apply(selected=False)
    print("  Applied skeleton rest pose")

    # Step 3: Remove IK constraints
    bpy.ops.object.mode_set(mode='POSE')
    for pb in [hand_r, hand_l]:
        if pb:
            for c in list(pb.constraints):
                pb.constraints.remove(c)

    bpy.ops.object.mode_set(mode='OBJECT')

    # Step 4: Delete IK empties and stray objects
    for name in ["IK_R", "IK_L"]:
        obj = bpy.data.objects.get(name)
        if obj:
            bpy.data.objects.remove(obj, do_unlink=True)

    # Remove any stray icospheres or empties
    for obj in list(bpy.data.objects):
        if obj.type not in ('MESH', 'ARMATURE'):
            bpy.data.objects.remove(obj, do_unlink=True)
        elif obj.type == 'MESH' and obj.parent is None and obj != mesh_obj:
            bpy.data.objects.remove(obj, do_unlink=True)

    print("  Cleaned up")

    # === EXPORT ===
    print(f"\n=== Exporting ===")
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

    bpy.ops.object.select_all(action='DESELECT')
    for obj in bpy.data.objects:
        if obj.type in ('MESH', 'ARMATURE'):
            obj.select_set(True)

    if output_path.endswith('.glb') or output_path.endswith('.gltf'):
        bpy.ops.export_scene.gltf(
            filepath=output_path,
            export_format='GLB',
            use_selection=True,
            export_animations=False,
            export_skins=True,
        )
    elif output_path.endswith('.fbx'):
        bpy.ops.export_scene.fbx(
            filepath=output_path,
            use_selection=True,
            use_armature_deform_only=True,
            add_leaf_bones=False,
        )

    size = os.path.getsize(output_path)
    print(f"Exported: {output_path} ({size:,} bytes)")
    print("DONE")


main()
