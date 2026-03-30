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

    # === ALL LIMBS USE IK (UniRig bone axes are arbitrary) ===
    # Euler rotation does NOT work reliably on UniRig skeletons --
    # bone local axes are based on ML prediction, not standard conventions.
    # IK with world-space targets is the only reliable posing method.

    print("\n=== Creating IK targets (all limbs) ===")
    bpy.ops.object.mode_set(mode='OBJECT')

    # Get mesh bounding box for proportional positioning
    mesh_obj_tmp = None
    for obj in bpy.data.objects:
        if obj.type == 'MESH' and obj.parent == armature:
            mesh_obj_tmp = obj
            break

    if mesh_obj_tmp:
        bb = [mesh_obj_tmp.matrix_world @ Vector(c) for c in mesh_obj_tmp.bound_box]
        mesh_min_z = min(v.z for v in bb)
        mesh_max_z = max(v.z for v in bb)
        mesh_height = mesh_max_z - mesh_min_z
        mesh_center_x = (min(v.x for v in bb) + max(v.x for v in bb)) / 2
        hip_z = mesh_min_z + mesh_height * 0.42
        print(f"  Mesh height: {mesh_height:.3f}m, hip_z: {hip_z:.3f}")
    else:
        mesh_height = 2.0
        hip_z = 0.0
        mesh_min_z = -1.0

    # IK target positions for driving pose:
    # Feet: forward and slightly down from hip level (seated, legs bent ~90°)
    # Hands: forward at steering wheel height
    foot_y = -mesh_height * 0.25   # forward
    foot_z = mesh_min_z + 0.02     # near ground
    hip_x = mesh_height * 0.08     # hip width

    hand_y = -mesh_height * 0.30   # forward (steering wheel)
    hand_z = hip_z + mesh_height * 0.15  # chest height
    hand_x = mesh_height * 0.08    # shoulder width

    ik_positions = {
        "IK_Foot_R": Vector((hip_x, foot_y, foot_z)),
        "IK_Foot_L": Vector((-hip_x, foot_y, foot_z)),
        "IK_Hand_R": Vector((hand_x, hand_y, hand_z)),
        "IK_Hand_L": Vector((-hand_x, hand_y, hand_z)),
    }

    targets = {}
    for name, pos in ik_positions.items():
        bpy.ops.object.empty_add(type='PLAIN_AXES', radius=0.02, location=pos)
        targets[name] = bpy.context.active_object
        targets[name].name = name
        print(f"  {name} at ({pos.x:.3f}, {pos.y:.3f}, {pos.z:.3f})")

    # Apply IK constraints
    bpy.context.view_layer.objects.active = armature
    armature.select_set(True)
    bpy.ops.object.mode_set(mode='POSE')

    # Legs IK
    print("\n=== Legs (IK) ===")
    foot_r_name = roles.get("foot_R")
    foot_l_name = roles.get("foot_L")

    for foot_name, target_name in [(foot_r_name, "IK_Foot_R"), (foot_l_name, "IK_Foot_L")]:
        if foot_name:
            pb = armature.pose.bones.get(foot_name)
            if pb:
                ik = pb.constraints.new(type='IK')
                ik.target = targets[target_name]
                ik.chain_count = 3  # foot -> shin -> thigh
                ik.iterations = 200
                print(f"  IK on {foot_name} -> {target_name} (chain=3)")

    # Arms IK
    print("\n=== Arms (IK) ===")
    hand_r_name = roles.get("hand_R")
    hand_l_name = roles.get("hand_L")

    for hand_name, target_name in [(hand_r_name, "IK_Hand_R"), (hand_l_name, "IK_Hand_L")]:
        if hand_name:
            pb = armature.pose.bones.get(hand_name)
            if pb:
                ik = pb.constraints.new(type='IK')
                ik.target = targets[target_name]
                ik.chain_count = 3  # hand -> forearm -> upper_arm
                ik.iterations = 200
                print(f"  IK on {hand_name} -> {target_name} (chain=3)")

    # Spine still uses Euler (spine bones are roughly Z-aligned, Euler works)
    print("\n=== Spine (Euler -- Z-aligned, Euler safe) ===")
    for role, x_deg in [("spine_low", -10), ("spine_mid", -5), ("neck", 3), ("head", 8)]:
        bone_name = roles.get(role)
        if bone_name:
            pb = armature.pose.bones.get(bone_name)
            if pb:
                pb.rotation_mode = 'XYZ'
                pb.rotation_euler = (math.radians(x_deg), 0, 0)
                print(f"  {role:15s} ({bone_name}): {x_deg} deg X")

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
        # Bake deformed positions INTO the original mesh (preserves topology)
        depsgraph = bpy.context.evaluated_depsgraph_get()
        eval_obj = mesh_obj.evaluated_get(depsgraph)
        eval_mesh = eval_obj.data  # evaluated mesh with same vert count

        # Copy deformed vertex positions back to original mesh
        orig_mesh = mesh_obj.data
        if len(eval_mesh.vertices) == len(orig_mesh.vertices):
            for i, v in enumerate(eval_mesh.vertices):
                orig_mesh.vertices[i].co = v.co
            orig_mesh.update()
            print(f"  Baked {len(orig_mesh.vertices)} vertex positions in-place (topology preserved)")
        else:
            print(f"  WARN: vert count mismatch orig={len(orig_mesh.vertices)} eval={len(eval_mesh.vertices)}")
            print(f"  Falling back to armature_apply only (no mesh deform bake)")

    # Apply armature rest pose
    bpy.context.view_layer.objects.active = armature
    armature.select_set(True)
    bpy.ops.object.mode_set(mode='POSE')
    bpy.ops.pose.armature_apply(selected=False)
    print("  Applied skeleton rest pose")

    # Remove all IK constraints (arms + legs)
    for bone_name in [hand_r_name, hand_l_name, foot_r_name, foot_l_name]:
        if bone_name:
            pb = armature.pose.bones.get(bone_name)
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
