"""
Apply driving pose to a UniRig-skinned character.
Auto-detects bone roles by analyzing skeleton hierarchy and positions.
Uses IK for arms (UniRig bone axes are arbitrary) and Euler for legs/spine.

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
# Optional: skip mesh bake (export with pose but don't flatten mesh)
no_bake = "--no-bake" in sys.argv


def auto_detect_bones(armature):
    """Auto-detect bone roles by analyzing hierarchy and world-space positions."""
    bones = armature.data.bones
    roles = {}

    # Find root (no parent)
    root = [b for b in bones if b.parent is None]
    if not root:
        return roles
    roles["root"] = root[0].name

    # Build position map
    bone_z = {}
    for b in bones:
        head = armature.matrix_world @ b.head_local
        bone_z[b.name] = head.z

    # Find spine chain: root -> children going UP (increasing Z)
    def find_chain_up(start_bone):
        chain = [start_bone]
        current = start_bone
        while True:
            up_children = [c for c in current.children
                          if (armature.matrix_world @ c.head_local).z > (armature.matrix_world @ current.head_local).z]
            if not up_children:
                break
            # Pick the child that goes most straight up
            best = max(up_children, key=lambda c: (armature.matrix_world @ c.head_local).z)
            chain.append(best)
            current = best
        return chain

    # Find leg chains: root children going DOWN (decreasing Z)
    def find_legs_from(parent_bone):
        """Find leg chains from a parent bone."""
        legs = []
        for child in parent_bone.children:
            child_head = armature.matrix_world @ child.head_local
            # Leg connector bones are at roughly same Z as parent
            # Their children go DOWN
            down_chain = []
            current = child
            while current:
                down_chain.append(current)
                down_children = [c for c in current.children
                               if (armature.matrix_world @ c.head_local).z < (armature.matrix_world @ current.head_local).z - 0.05]
                if down_children:
                    current = down_children[0]
                else:
                    break
            if len(down_chain) >= 3:  # hip + thigh + shin minimum
                x = (armature.matrix_world @ child.head_local).x
                side = "R" if x > 0 else "L"
                legs.append((side, down_chain))
        return legs

    # Spine chain from root
    root_bone = root[0]
    spine_chain = find_chain_up(root_bone)

    # The first spine bone with multiple children that go UP is the chest/branch point
    spine_bone = spine_chain[0] if spine_chain else root_bone

    # Find legs -- search all spine chain bones for children that go DOWN
    legs = []
    for sp_bone in spine_chain[:3]:  # check root, spine1, spine2
        legs.extend(find_legs_from(sp_bone))
    # Deduplicate by side
    seen_sides = set()
    unique_legs = []
    for side, chain in legs:
        if side not in seen_sides:
            seen_sides.add(side)
            unique_legs.append((side, chain))
    legs = unique_legs

    # Assign spine roles
    if len(spine_chain) >= 2:
        roles["spine_low"] = spine_chain[1].name
    if len(spine_chain) >= 3:
        roles["spine_mid"] = spine_chain[2].name
    if len(spine_chain) >= 4:
        # Find head vs arms -- head is the one that keeps going up with no wide branching
        chest = spine_chain[3]
        roles["chest"] = chest.name

        # From chest, find the child highest up = head chain
        # Children going sideways = arm chains
        for child in chest.children:
            child_head = armature.matrix_world @ child.head_local
            chest_head = armature.matrix_world @ chest.head_local
            if child_head.z > chest_head.z + 0.05:
                # Goes up -- probably head or neck
                roles["neck"] = child.name
                head_children = [c for c in child.children if
                                (armature.matrix_world @ c.head_local).z > child_head.z]
                if head_children:
                    roles["head"] = head_children[0].name

    # Assign leg roles
    for side, chain in legs:
        if len(chain) >= 1:
            roles[f"hip_{side}"] = chain[0].name
        if len(chain) >= 2:
            roles[f"thigh_{side}"] = chain[1].name
        if len(chain) >= 3:
            roles[f"shin_{side}"] = chain[2].name
        if len(chain) >= 4:
            roles[f"foot_{side}"] = chain[3].name

    # Find hands (deepest bones in arm chains from chest)
    # Arms branch from chest and go sideways (large X displacement)
    if "chest" in roles:
        chest_bone = bones[roles["chest"]]
        # Also check head: find highest child from chest
        for child in chest_bone.children:
            child_head = armature.matrix_world @ child.head_local
            chest_head = armature.matrix_world @ chest_bone.head_local
            if child_head.z > chest_head.z + 0.02 and abs(child_head.x) < 0.05:
                # Goes straight up, near center = head/neck
                if "neck" not in roles:
                    roles["neck"] = child.name
                    for gc in child.children:
                        gc_head = armature.matrix_world @ gc.head_local
                        if gc_head.z > child_head.z:
                            roles["head"] = gc.name

        for child in chest_bone.children:
            child_head = armature.matrix_world @ child.head_local
            chest_head = armature.matrix_world @ chest_bone.head_local
            # Arm: goes sideways (X changes significantly)
            if abs(child_head.x - chest_head.x) > 0.02:
                side = "R" if child_head.x > chest_head.x else "L"
                # Walk down to find the hand (3rd bone in arm chain typically)
                arm_chain = [child]
                current = child
                for _ in range(10):
                    if current.children:
                        # Pick child with most children (hand has fingers)
                        best = max(current.children, key=lambda c: len(c.children))
                        arm_chain.append(best)
                        current = best
                    else:
                        break
                # Hand is typically the bone with 4-5 finger children
                for b in arm_chain:
                    if len(b.children) >= 3:
                        roles[f"hand_{side}"] = b.name
                        break
                if f"hand_{side}" not in roles and len(arm_chain) >= 3:
                    roles[f"hand_{side}"] = arm_chain[2].name

    return roles


def main():
    print(f"Input:  {input_path}")
    print(f"Output: {output_path}")

    # Clear and import
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()
    bpy.ops.import_scene.fbx(filepath=input_path)

    armature = None
    for obj in bpy.data.objects:
        if obj.type == 'ARMATURE':
            armature = obj
            break

    if not armature:
        print("ERROR: No armature found")
        return

    print(f"Armature: {armature.name}, {len(armature.data.bones)} bones")

    # Auto-detect bone roles
    roles = auto_detect_bones(armature)
    print("\n=== Auto-detected bone roles ===")
    for role, name in sorted(roles.items()):
        print(f"  {role:15s} -> {name}")

    # Enter pose mode
    bpy.context.view_layer.objects.active = armature
    armature.select_set(True)
    bpy.ops.object.mode_set(mode='POSE')

    def pose_euler(role, x=0, y=0, z=0):
        bone_name = roles.get(role)
        if not bone_name:
            print(f"  SKIP {role}: not detected")
            return
        pb = armature.pose.bones.get(bone_name)
        if not pb:
            print(f"  SKIP {role}: bone '{bone_name}' not in pose")
            return
        pb.rotation_mode = 'XYZ'
        pb.rotation_euler = (math.radians(x), math.radians(y), math.radians(z))
        print(f"  {role:15s} ({bone_name}): ({x}, {y}, {z}) deg")

    # === LEGS ===
    print("\n=== Legs (Euler) ===")
    pose_euler("thigh_R", x=-90)
    pose_euler("shin_R", x=90)
    pose_euler("foot_R", x=-30)
    pose_euler("thigh_L", x=-90)
    pose_euler("shin_L", x=90)
    pose_euler("foot_L", x=-30)

    # === SPINE ===
    print("\n=== Spine (Euler) ===")
    pose_euler("spine_low", x=-15)
    pose_euler("spine_mid", x=-10)
    pose_euler("neck", x=5)
    pose_euler("head", x=15)

    # === ARMS (IK) ===
    print("\n=== Arms (IK) ===")
    hand_r_name = roles.get("hand_R")
    hand_l_name = roles.get("hand_L")

    bpy.ops.object.mode_set(mode='OBJECT')

    # Create IK targets
    targets = {}
    for name, pos in [("IK_R", Vector((0.15, -0.6, 0.45))),
                       ("IK_L", Vector((-0.15, -0.6, 0.45)))]:
        bpy.ops.object.empty_add(type='PLAIN_AXES', radius=0.02, location=pos)
        targets[name] = bpy.context.active_object
        targets[name].name = name
        print(f"  Target {name} at {pos}")

    bpy.context.view_layer.objects.active = armature
    armature.select_set(True)
    bpy.ops.object.mode_set(mode='POSE')

    for hand_name, target_name in [(hand_r_name, "IK_R"), (hand_l_name, "IK_L")]:
        if hand_name:
            pb = armature.pose.bones.get(hand_name)
            if pb:
                ik = pb.constraints.new(type='IK')
                ik.target = targets[target_name]
                ik.chain_count = 3
                ik.iterations = 200
                print(f"  IK on {hand_name} -> {target_name}")

    # Update scene so IK solves
    bpy.context.view_layer.update()

    # === BAKE ===
    print("\n=== Baking ===")
    bpy.ops.object.mode_set(mode='OBJECT')

    mesh_obj = None
    for obj in bpy.data.objects:
        if obj.type == 'MESH' and obj.parent == armature:
            mesh_obj = obj
            break

    if mesh_obj and not no_bake:
        depsgraph = bpy.context.evaluated_depsgraph_get()
        eval_obj = mesh_obj.evaluated_get(depsgraph)
        eval_mesh = bpy.data.meshes.new_from_object(eval_obj)
        old_mesh = mesh_obj.data
        mesh_obj.data = eval_mesh
        eval_mesh.name = old_mesh.name
        bpy.data.meshes.remove(old_mesh)
        print(f"  Baked deformed mesh: {len(eval_mesh.vertices)} verts")

    # Apply armature rest pose
    bpy.context.view_layer.objects.active = armature
    armature.select_set(True)
    bpy.ops.object.mode_set(mode='POSE')
    bpy.ops.pose.armature_apply(selected=False)
    print("  Applied skeleton rest pose")

    # Remove IK constraints
    for hand_name in [hand_r_name, hand_l_name]:
        if hand_name:
            pb = armature.pose.bones.get(hand_name)
            if pb:
                for c in list(pb.constraints):
                    pb.constraints.remove(c)

    bpy.ops.object.mode_set(mode='OBJECT')

    # Cleanup empties and strays
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
