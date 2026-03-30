"""
Apply driving pose to a UniRig-skinned character.

Strategy: Rename UniRig's generic bone_XX names to standard Blender names,
then apply the proven kart-assembly Euler rotation approach.

The kart-assembly-ralph script (assemble_driver_kart.py) uses simple Euler
rotations with standard bone names and works correctly. The issue was never
about bone local axes -- it was that UniRig's bone_XX names don't match
what posing scripts expect.

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


def auto_detect_and_rename(armature):
    """Auto-detect bone roles and rename to standard Blender names."""
    bones = armature.data.bones
    roles = {}

    # Find root
    root = [b for b in bones if b.parent is None]
    if not root:
        return {}
    roles["root"] = root[0].name

    # Build spine chain (going UP in Z)
    spine_chain = [root[0]]
    current = root[0]
    while True:
        up = sorted(
            [c for c in current.children
             if (armature.matrix_world @ c.head_local).z >
                (armature.matrix_world @ current.head_local).z],
            key=lambda c: (armature.matrix_world @ c.head_local).z,
            reverse=True)
        if not up:
            break
        spine_chain.append(up[0])
        current = up[0]

    spine_names = set(b.name for b in spine_chain)

    # Find legs (children of spine bones that go DOWN, excluding spine itself)
    for sp in spine_chain[:3]:
        for child in sp.children:
            if child.name in spine_names:
                continue
            chain = [child]
            cur = child
            while True:
                down = [c for c in cur.children
                        if (armature.matrix_world @ c.head_local).z <
                           (armature.matrix_world @ cur.head_local).z - 0.05]
                if down:
                    chain.append(down[0])
                    cur = down[0]
                else:
                    break
            if len(chain) >= 3:
                x = (armature.matrix_world @ child.head_local).x
                side = "R" if x > 0 else "L"
                if f"hip_{side}" not in roles:
                    for i, label in enumerate(["hip", "upperleg", "lowerleg", "foot"]):
                        if i < len(chain):
                            roles[f"{label}_{side}"] = chain[i].name

    # Assign spine roles
    if len(spine_chain) >= 2: roles["spine"] = spine_chain[1].name
    if len(spine_chain) >= 3: roles["chest"] = spine_chain[2].name

    # Find head and arms from the highest spine bone with multiple children
    for sp_bone in reversed(spine_chain[2:]):
        if len(sp_bone.children) >= 2:
            for child in sp_bone.children:
                if child.name in spine_names:
                    continue
                ch = armature.matrix_world @ child.head_local
                sp_h = armature.matrix_world @ sp_bone.head_local
                # Goes up = neck/head
                if ch.z > sp_h.z + 0.02 and abs(ch.x) < 0.1:
                    if "neck" not in roles:
                        roles["neck"] = child.name
                        for gc in child.children:
                            if (armature.matrix_world @ gc.head_local).z > ch.z:
                                roles["head"] = gc.name
                # Goes sideways = arm
                elif abs(ch.x - sp_h.x) > 0.02:
                    side = "R" if ch.x > sp_h.x else "L"
                    if f"shoulder_{side}" not in roles:
                        roles[f"shoulder_{side}"] = child.name
                        arm_chain = []
                        cur = child
                        for _ in range(5):
                            if cur.children:
                                best = max(cur.children, key=lambda c: len(c.children))
                                arm_chain.append(best)
                                cur = best
                            else:
                                break
                        if len(arm_chain) >= 1:
                            roles[f"upperarm_{side}"] = arm_chain[0].name
                        if len(arm_chain) >= 2:
                            roles[f"lowerarm_{side}"] = arm_chain[1].name
                        if len(arm_chain) >= 3:
                            roles[f"hand_{side}"] = arm_chain[2].name
            break  # only process the first branching spine bone

    # Now rename bones in edit mode
    bpy.context.view_layer.objects.active = armature
    armature.select_set(True)
    bpy.ops.object.mode_set(mode='EDIT')

    rename_map = {
        "root": "hips",
        "spine": "spine",
        "chest": "chest",
        "neck": "neck",
        "head": "head",
    }

    for side_label, side_suffix in [("R", ".r"), ("L", ".l")]:
        rename_map[f"hip_{side_label}"] = f"hip_connector{side_suffix}"
        rename_map[f"upperleg_{side_label}"] = f"upperleg{side_suffix}"
        rename_map[f"lowerleg_{side_label}"] = f"lowerleg{side_suffix}"
        rename_map[f"foot_{side_label}"] = f"foot{side_suffix}"
        rename_map[f"shoulder_{side_label}"] = f"shoulder{side_suffix}"
        rename_map[f"upperarm_{side_label}"] = f"upperarm{side_suffix}"
        rename_map[f"lowerarm_{side_label}"] = f"lowerarm{side_suffix}"
        rename_map[f"hand_{side_label}"] = f"hand{side_suffix}"

    renamed = {}
    for role, old_name in roles.items():
        new_name = rename_map.get(role)
        if new_name and old_name in armature.data.edit_bones:
            eb = armature.data.edit_bones[old_name]
            eb.name = new_name
            renamed[role] = (old_name, new_name)

    bpy.ops.object.mode_set(mode='OBJECT')

    # Also rename vertex groups on the mesh to match
    for obj in bpy.data.objects:
        if obj.type == 'MESH' and obj.parent == armature:
            for role, (old_name, new_name) in renamed.items():
                vg = obj.vertex_groups.get(old_name)
                if vg:
                    vg.name = new_name

    return renamed


def main():
    print(f"Input:  {input_path}")
    print(f"Output: {output_path}")

    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()
    bpy.ops.import_scene.fbx(filepath=input_path)

    armature = None
    for obj in bpy.data.objects:
        if obj.type == 'ARMATURE':
            armature = obj
            break
    if not armature:
        print("ERROR: No armature")
        return

    print(f"Armature: {len(armature.data.bones)} bones")

    # Step 1: Auto-detect and rename bones
    print("\n=== Renaming bones ===")
    renamed = auto_detect_and_rename(armature)
    for role, (old, new) in sorted(renamed.items()):
        print(f"  {old:10s} -> {new:20s} ({role})")

    # Step 2: Apply driving pose using the kart-assembly approach
    # (proven to work with standard bone names + simple Euler rotation)
    print("\n=== Applying driving pose ===")
    bpy.context.view_layer.objects.active = armature
    armature.select_set(True)
    bpy.ops.object.mode_set(mode='POSE')

    def pose_bone(name_contains, rot_degrees, axis='X'):
        """Find and rotate a pose bone by name substring (case-insensitive)."""
        for pb in armature.pose.bones:
            if name_contains.lower() in pb.name.lower():
                pb.rotation_mode = 'XYZ'
                rad = math.radians(rot_degrees)
                if axis == 'X':
                    pb.rotation_euler.x = rad
                elif axis == 'Y':
                    pb.rotation_euler.y = rad
                elif axis == 'Z':
                    pb.rotation_euler.z = rad
                print(f"  {pb.name}: {rot_degrees}° {axis}")
                return pb
        print(f"  SKIP: '{name_contains}' not found")
        return None

    # Driving pose (from kart-assembly-ralph proven values)
    pose_bone("upperleg.l", -90)
    pose_bone("upperleg.r", -90)
    pose_bone("lowerleg.l", 90)
    pose_bone("lowerleg.r", 90)
    pose_bone("foot.l", -20)
    pose_bone("foot.r", -20)
    pose_bone("spine", -10)
    pose_bone("chest", -5)
    pose_bone("upperarm.l", -60)
    pose_bone("upperarm.r", -60)
    pose_bone("lowerarm.l", -30)
    pose_bone("lowerarm.r", -30)
    pose_bone("hand.l", -10)
    pose_bone("hand.r", -10)
    pose_bone("head", 15)
    pose_bone("neck", 5)

    bpy.ops.object.mode_set(mode='OBJECT')
    print("Driving pose applied")

    # Step 3: Keyframe for export
    print("\n=== Keyframing ===")
    bpy.context.view_layer.objects.active = armature
    bpy.ops.object.mode_set(mode='POSE')
    bpy.context.scene.frame_set(1)
    for pb in armature.pose.bones:
        pb.keyframe_insert(data_path="rotation_euler", frame=1)
        pb.keyframe_insert(data_path="location", frame=1)
    if armature.animation_data and armature.animation_data.action:
        armature.animation_data.action.name = "DrivingPose"
    bpy.ops.object.mode_set(mode='OBJECT')

    # Step 4: Clean up strays
    mesh_obj = None
    for obj in bpy.data.objects:
        if obj.type == 'MESH' and obj.parent == armature:
            mesh_obj = obj
    for obj in list(bpy.data.objects):
        if obj.type not in ('MESH', 'ARMATURE'):
            bpy.data.objects.remove(obj, do_unlink=True)
        elif obj.type == 'MESH' and obj.parent is None and obj != mesh_obj:
            bpy.data.objects.remove(obj, do_unlink=True)

    # Step 5: Export
    print(f"\n=== Exporting ===")
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    bpy.ops.object.select_all(action='DESELECT')
    for obj in bpy.data.objects:
        if obj.type in ('MESH', 'ARMATURE'):
            obj.select_set(True)

    bpy.context.scene.frame_set(1)
    if output_path.endswith('.glb') or output_path.endswith('.gltf'):
        bpy.ops.export_scene.gltf(
            filepath=output_path, export_format='GLB',
            use_selection=True, export_animations=True,
            export_skins=True, export_current_frame=True)
    elif output_path.endswith('.fbx'):
        bpy.ops.export_scene.fbx(
            filepath=output_path, use_selection=True,
            use_armature_deform_only=True, add_leaf_bones=False, bake_anim=True)

    print(f"Exported: {output_path} ({os.path.getsize(output_path):,} bytes)")
    print("DONE")


main()
