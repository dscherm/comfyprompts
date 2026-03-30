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
    # But EXCLUDE children that are part of the spine chain itself
    spine_names = set(b.name for b in spine_chain)
    legs = []
    for sp_bone in spine_chain[:3]:  # check root, spine1, spine2
        for child in sp_bone.children:
            if child.name in spine_names:
                continue  # skip spine continuation
            child_head = armature.matrix_world @ child.head_local
            # Leg candidates: children whose own children go DOWN
            down_chain = [child]
            current = child
            while current:
                down_children = [c for c in current.children
                               if (armature.matrix_world @ c.head_local).z < (armature.matrix_world @ current.head_local).z - 0.05]
                if down_children:
                    current = down_children[0]
                    down_chain.append(current)
                else:
                    break
            if len(down_chain) >= 3:  # hip connector + thigh + shin minimum
                x = child_head.x
                side = "R" if x > 0 else "L"
                legs.append((side, down_chain))
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

    # Compute IK targets from ACTUAL bone rest positions (not mesh bounding box)
    # This ensures targets are proportional to the specific skeleton
    bones = armature.data.bones

    def bone_head(name):
        b = bones.get(name)
        return armature.matrix_world @ b.head_local if b else Vector((0, 0, 0))

    def bone_tail(name):
        b = bones.get(name)
        return armature.matrix_world @ b.tail_local if b else Vector((0, 0, 0))

    # Get actual thigh positions for each leg
    thigh_r = roles.get("thigh_R", "")
    thigh_l = roles.get("thigh_L", "")
    foot_r = roles.get("foot_R", "")
    foot_l = roles.get("foot_L", "")

    # For 90-degree seated driving pose:
    # - Thighs horizontal (pointing forward from hip)
    # - Shins vertical (hanging down from knees)
    # - Feet directly below knees at pedal level
    #
    # Target placement:
    #   knee position = thigh_head + forward * thigh_length
    #   foot position = knee + down * shin_length

    def compute_foot_target(side):
        hip_name = roles.get(f"hip_{side}")
        thigh_name = roles.get(f"thigh_{side}")
        shin_name = roles.get(f"shin_{side}")
        foot_name = roles.get(f"foot_{side}")
        if not thigh_name:
            x = 0.2 if side == "R" else -0.2
            return Vector((x, -0.4, -0.4))

        # Use hip connector head as the seat point (where the leg originates)
        hip_head = bone_head(hip_name) if hip_name else bone_head(thigh_name)
        thigh_len = (bone_tail(thigh_name) - bone_head(thigh_name)).length
        shin_len = (bone_tail(shin_name) - bone_head(shin_name)).length if shin_name else thigh_len * 0.8

        # 90-degree seated pose:
        # The thigh goes FORWARD from hip (in -Y direction, same Z as hip)
        # The shin hangs DOWN from the knee (same X,Y as knee, lower Z)
        #
        # Hip connector bone goes straight down in rest pose.
        # For seated: rotate hip so thigh points forward.
        # Foot target = hip position + forward(thigh_len) + down(shin_len)

        foot_x = hip_head.x                    # same X as hip (no crossing)
        foot_y = hip_head.y - shin_len * 0.8    # forward (gentle, not extreme)
        foot_z = hip_head.z - thigh_len         # down by full thigh length (shin hangs vertical)

        print(f"  {side}: hip=({hip_head.x:.3f},{hip_head.y:.3f},{hip_head.z:.3f})"
              f" thigh={thigh_len:.3f} shin={shin_len:.3f}")
        print(f"  {side}: foot target=({foot_x:.3f},{foot_y:.3f},{foot_z:.3f})")

        return Vector((foot_x, foot_y, foot_z))

    ik_foot_r = compute_foot_target("R")
    ik_foot_l = compute_foot_target("L")

    # Hands: forward at chest height, shoulder width apart
    hand_r_bone = roles.get("hand_R", "")
    hand_l_bone = roles.get("hand_L", "")
    chest_name = roles.get("chest", "")

    if chest_name:
        chest_pos = bone_head(chest_name)
        thigh_r_name = roles.get("thigh_R", "")
        hand_spread = abs(bone_head(thigh_r_name).x) * 1.2 if thigh_r_name else 0.15
        # Hands at chest height but forward -- NOT at knee level
        hand_z = chest_pos.z * 0.7  # below chest but well above knees
        ik_hand_r = Vector((hand_spread, chest_pos.y - 0.35, hand_z))
        ik_hand_l = Vector((-hand_spread, chest_pos.y - 0.35, hand_z))
    else:
        ik_hand_r = Vector((0.15, -0.6, 0.14))
        ik_hand_l = Vector((-0.15, -0.6, 0.14))

    ik_positions = {
        "IK_Foot_R": ik_foot_r,
        "IK_Foot_L": ik_foot_l,
        "IK_Hand_R": ik_hand_r,
        "IK_Hand_L": ik_hand_l,
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

    # Create knee pole targets (force knees to point FORWARD, not outward)
    bpy.ops.object.mode_set(mode='OBJECT')
    for side, foot_target in [("R", ik_foot_r), ("L", ik_foot_l)]:
        hip_name = roles.get(f"hip_{side}")
        if hip_name:
            hip_pos = bone_head(hip_name)
            # Pole target: in front of knee, at knee height
            pole_pos = Vector((hip_pos.x, hip_pos.y - 1.0, (hip_pos.z + foot_target.z) / 2))
            bpy.ops.object.empty_add(type='PLAIN_AXES', radius=0.02, location=pole_pos)
            pole = bpy.context.active_object
            pole.name = f"Pole_Knee_{side}"
            targets[f"Pole_Knee_{side}"] = pole
            print(f"  Pole_Knee_{side} at ({pole_pos.x:.3f}, {pole_pos.y:.3f}, {pole_pos.z:.3f})")

    bpy.context.view_layer.objects.active = armature
    armature.select_set(True)
    bpy.ops.object.mode_set(mode='POSE')

    for foot_name, target_name, side in [(foot_r_name, "IK_Foot_R", "R"), (foot_l_name, "IK_Foot_L", "L")]:
        if foot_name:
            pb = armature.pose.bones.get(foot_name)
            if pb:
                ik = pb.constraints.new(type='IK')
                ik.target = targets[target_name]
                ik.chain_count = 4  # foot -> shin -> thigh -> hip_connector
                ik.iterations = 200
                # Add pole target to force knees forward
                pole_name = f"Pole_Knee_{side}"
                if pole_name in targets:
                    ik.pole_target = targets[pole_name]
                    ik.pole_angle = 0
                print(f"  IK on {foot_name} -> {target_name} (chain=4, pole={pole_name})")

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

    # === BAKE IK INTO KEYFRAMES ===
    # Strategy: Keep the original rest pose (T-pose). Bake the IK-solved
    # driving pose as keyframes on frame 1. Export with animation.
    # The GLTF exporter will include both the bind-pose mesh AND the
    # driving pose animation. Viewers/engines show the posed result.
    print("\n=== Baking IK into keyframes ===")

    # Update depsgraph so IK fully solves
    bpy.context.view_layer.update()
    bpy.context.evaluated_depsgraph_get()

    # Bake visual transforms to keyframes (captures IK solution)
    bpy.context.scene.frame_set(1)
    bpy.ops.object.mode_set(mode='POSE')
    bpy.ops.pose.select_all(action='SELECT')

    # Use visual keying to bake the IK-solved transforms
    bpy.context.scene.tool_settings.use_keyframe_insert_auto = False
    for pb in armature.pose.bones:
        # Insert keyframes using the visual transform (includes IK)
        pb.keyframe_insert(data_path="location", frame=1, options={'INSERTKEY_VISUAL'})
        pb.keyframe_insert(data_path="rotation_quaternion", frame=1, options={'INSERTKEY_VISUAL'})
        pb.keyframe_insert(data_path="rotation_euler", frame=1, options={'INSERTKEY_VISUAL'})
        pb.keyframe_insert(data_path="scale", frame=1, options={'INSERTKEY_VISUAL'})
    print("  Keyframed all bones at frame 1 (visual transform)")

    # Remove IK constraints (keyframes now hold the pose)
    for bone_name in [hand_r_name, hand_l_name, foot_r_name, foot_l_name]:
        if bone_name:
            pb = armature.pose.bones.get(bone_name)
            if pb:
                for c in list(pb.constraints):
                    pb.constraints.remove(c)
    print("  Removed IK constraints (keyframes preserve pose)")

    # Name the action
    if armature.animation_data and armature.animation_data.action:
        armature.animation_data.action.name = "DrivingPose"

    bpy.ops.object.mode_set(mode='OBJECT')

    # Cleanup empties and strays
    mesh_obj = None
    for obj in bpy.data.objects:
        if obj.type == 'MESH' and obj.parent == armature:
            mesh_obj = obj
            break

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

    # Set frame to 1 so the posed state is active during export
    bpy.context.scene.frame_set(1)

    if output_path.endswith('.glb') or output_path.endswith('.gltf'):
        bpy.ops.export_scene.gltf(
            filepath=output_path,
            export_format='GLB',
            use_selection=True,
            export_animations=True,
            export_skins=True,
            export_current_frame=True,
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
