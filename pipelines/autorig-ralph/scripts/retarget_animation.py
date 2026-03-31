"""
Retarget a mocap animation (Rokoko/Mixamo FBX) onto a UniRig-skinned character.

Instead of hardcoded Euler rotations (fragile, axis-dependent), this script:
1. Imports the source animation FBX to extract bone rotations per frame
2. Imports the target UniRig-skinned FBX
3. Auto-detects and renames UniRig bones to standard names
4. Copies rotation keyframes from source bones to matching target bones
5. Exports the posed character as GLB

Usage:
    blender --background --python retarget_animation.py -- \
        --source <mocap.fbx> \
        --target <unirig_skinned.fbx> \
        --output <posed_character.glb> \
        [--frame <frame_number>]  # single frame for static pose (default: all frames)
        [--map <retarget_map.json>]  # bone name mapping file
"""

import bpy
import json
import math
import os
import sys
from mathutils import Matrix, Quaternion, Vector

# ---------------------------------------------------------------------------
# CLI args
# ---------------------------------------------------------------------------
argv = sys.argv
if "--" in argv:
    argv = argv[argv.index("--") + 1:]
else:
    argv = []

import argparse
parser = argparse.ArgumentParser()
parser.add_argument("--source", required=True, help="Source animation FBX (Rokoko/Mixamo)")
parser.add_argument("--target", required=True, help="Target UniRig-skinned FBX")
parser.add_argument("--output", required=True, help="Output GLB path")
parser.add_argument("--frame", type=int, default=None, help="Extract single frame (static pose)")
parser.add_argument("--map", default=None, help="Retarget bone map JSON")
args = parser.parse_args(argv)

# ---------------------------------------------------------------------------
# Default bone map (Rokoko/Mixamo -> UniRig standard names)
# ---------------------------------------------------------------------------
DEFAULT_BONE_MAP = {
    "Character1_Hips": "hips",
    "Character1_Spine": "spine",
    "Character1_Spine1": "chest",
    "Character1_Spine2": "chest",
    "Character1_Neck": "neck",
    "Character1_Head": "head",
    "Character1_LeftShoulder": "shoulder.l",
    "Character1_LeftArm": "upperarm.l",
    "Character1_LeftForeArm": "lowerarm.l",
    "Character1_LeftHand": "hand.l",
    "Character1_RightShoulder": "shoulder.r",
    "Character1_RightArm": "upperarm.r",
    "Character1_RightForeArm": "lowerarm.r",
    "Character1_RightHand": "hand.r",
    "Character1_LeftUpLeg": "upperleg.l",
    "Character1_LeftLeg": "lowerleg.l",
    "Character1_LeftFoot": "foot.l",
    "Character1_RightUpLeg": "upperleg.r",
    "Character1_RightLeg": "lowerleg.r",
    "Character1_RightFoot": "foot.r",
    # Mixamo naming (no Character1_ prefix)
    "mixamorig:Hips": "hips",
    "mixamorig:Spine": "spine",
    "mixamorig:Spine1": "chest",
    "mixamorig:Spine2": "chest",
    "mixamorig:Neck": "neck",
    "mixamorig:Head": "head",
    "mixamorig:LeftShoulder": "shoulder.l",
    "mixamorig:LeftArm": "upperarm.l",
    "mixamorig:LeftForeArm": "lowerarm.l",
    "mixamorig:LeftHand": "hand.l",
    "mixamorig:RightShoulder": "shoulder.r",
    "mixamorig:RightArm": "upperarm.r",
    "mixamorig:RightForeArm": "lowerarm.r",
    "mixamorig:RightHand": "hand.r",
    "mixamorig:LeftUpLeg": "upperleg.l",
    "mixamorig:LeftLeg": "lowerleg.l",
    "mixamorig:LeftFoot": "foot.l",
    "mixamorig:RightUpLeg": "upperleg.r",
    "mixamorig:RightLeg": "lowerleg.r",
    "mixamorig:RightFoot": "foot.r",
}


def auto_detect_and_rename(armature):
    """Auto-detect bone roles from UniRig hierarchy and rename to standard names.

    Reused from apply_driving_pose.py but extracted here for retargeting.
    """
    bones = armature.data.bones
    roles = {}

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

    # Find legs
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

    if len(spine_chain) >= 2:
        roles["spine"] = spine_chain[1].name
    if len(spine_chain) >= 3:
        roles["chest"] = spine_chain[2].name

    # Find head and arms
    for sp_bone in reversed(spine_chain[2:]):
        if len(sp_bone.children) >= 2:
            for child in sp_bone.children:
                if child.name in spine_names:
                    continue
                ch = armature.matrix_world @ child.head_local
                sp_h = armature.matrix_world @ sp_bone.head_local
                if ch.z > sp_h.z + 0.02 and abs(ch.x) < 0.1:
                    if "neck" not in roles:
                        roles["neck"] = child.name
                        for gc in child.children:
                            if (armature.matrix_world @ gc.head_local).z > ch.z:
                                roles["head"] = gc.name
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
            break

    # Rename in edit mode
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

    # Rename vertex groups
    for obj in bpy.data.objects:
        if obj.type == 'MESH' and obj.parent == armature:
            for role, (old_name, new_name) in renamed.items():
                vg = obj.vertex_groups.get(old_name)
                if vg:
                    vg.name = new_name

    return renamed


def extract_pose_at_frame(source_armature, frame, bone_map):
    """Extract bone rotations from source armature at a given frame.

    Returns dict of {target_bone_name: quaternion_rotation}.
    """
    bpy.context.scene.frame_set(frame)
    rotations = {}

    for pb in source_armature.pose.bones:
        target_name = bone_map.get(pb.name)
        if target_name:
            # Get the bone's pose-space rotation as quaternion
            rot = pb.rotation_quaternion.copy() if pb.rotation_mode == 'QUATERNION' else pb.matrix_basis.to_quaternion()
            rotations[target_name] = rot

    return rotations


def apply_pose(target_armature, rotations):
    """Apply extracted rotations to target armature pose bones."""
    bpy.context.view_layer.objects.active = target_armature
    target_armature.select_set(True)
    bpy.ops.object.mode_set(mode='POSE')

    applied = 0
    for pb in target_armature.pose.bones:
        if pb.name in rotations:
            pb.rotation_mode = 'QUATERNION'
            pb.rotation_quaternion = rotations[pb.name]
            applied += 1

    bpy.ops.object.mode_set(mode='OBJECT')
    return applied


def main():
    print(f"Source animation: {args.source}")
    print(f"Target character: {args.target}")
    print(f"Output:           {args.output}")
    print(f"Frame:            {args.frame or 'all'}")

    # Load bone map
    if args.map:
        with open(args.map) as f:
            map_data = json.load(f)
            bone_map = map_data.get("bone_map", map_data)
    else:
        bone_map = DEFAULT_BONE_MAP

    # --- Step 1: Import source animation ---
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()

    bpy.ops.import_scene.fbx(filepath=args.source)
    source_arm = None
    for obj in bpy.data.objects:
        if obj.type == 'ARMATURE':
            source_arm = obj
            break

    if not source_arm:
        print("ERROR: No armature in source FBX")
        sys.exit(1)

    print(f"Source skeleton: {len(source_arm.data.bones)} bones")

    # Get animation frame range
    source_action = None
    if source_arm.animation_data:
        source_action = source_arm.animation_data.action
    if source_action:
        frame_start, frame_end = int(source_action.frame_range[0]), int(source_action.frame_range[1])
        print(f"Source animation: {source_action.name}, frames {frame_start}-{frame_end}")
    else:
        frame_start, frame_end = 1, 1
        print("WARNING: No animation found in source, using rest pose")

    # Extract poses from source
    if args.frame is not None:
        frames_to_extract = [args.frame]
    else:
        frames_to_extract = list(range(frame_start, frame_end + 1))

    poses = {}
    for frame in frames_to_extract:
        poses[frame] = extract_pose_at_frame(source_arm, frame, bone_map)

    print(f"Extracted {len(poses)} frame(s), {len(poses[frames_to_extract[0]])} bones mapped per frame")

    # --- Step 2: Remove source, import target ---
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()
    for mesh in list(bpy.data.meshes):
        bpy.data.meshes.remove(mesh)
    for arm in list(bpy.data.armatures):
        bpy.data.armatures.remove(arm)

    bpy.ops.import_scene.fbx(filepath=args.target)
    target_arm = None
    for obj in bpy.data.objects:
        if obj.type == 'ARMATURE':
            target_arm = obj
            break

    if not target_arm:
        print("ERROR: No armature in target FBX")
        sys.exit(1)

    print(f"Target skeleton: {len(target_arm.data.bones)} bones")

    # --- Step 3: Rename UniRig bones ---
    renamed = auto_detect_and_rename(target_arm)
    print(f"Renamed {len(renamed)} bones:")
    for role, (old, new) in sorted(renamed.items()):
        print(f"  {old:10s} -> {new:20s} ({role})")

    # --- Step 4: Apply animation ---
    bpy.context.view_layer.objects.active = target_arm
    target_arm.select_set(True)
    bpy.ops.object.mode_set(mode='POSE')

    for frame in frames_to_extract:
        bpy.context.scene.frame_set(frame)
        rotations = poses[frame]
        for pb in target_arm.pose.bones:
            if pb.name in rotations:
                pb.rotation_mode = 'QUATERNION'
                pb.rotation_quaternion = rotations[pb.name]
                pb.keyframe_insert(data_path="rotation_quaternion", frame=frame)

    if target_arm.animation_data and target_arm.animation_data.action:
        target_arm.animation_data.action.name = "RetargetedAnimation"

    bpy.ops.object.mode_set(mode='OBJECT')
    print(f"Applied {len(frames_to_extract)} keyframe(s)")

    # --- Step 5: Clean up and export ---
    for obj in list(bpy.data.objects):
        if obj.type not in ('MESH', 'ARMATURE'):
            bpy.data.objects.remove(obj, do_unlink=True)
        elif obj.type == 'MESH' and obj.parent is None:
            bpy.data.objects.remove(obj, do_unlink=True)

    os.makedirs(os.path.dirname(os.path.abspath(args.output)), exist_ok=True)

    bpy.ops.object.select_all(action='SELECT')
    bpy.context.scene.frame_set(frames_to_extract[0])

    if args.output.endswith('.glb') or args.output.endswith('.gltf'):
        bpy.ops.export_scene.gltf(
            filepath=args.output, export_format='GLB',
            use_selection=True, export_animations=True,
            export_skins=True)
    elif args.output.endswith('.fbx'):
        bpy.ops.export_scene.fbx(
            filepath=args.output, use_selection=True,
            use_armature_deform_only=True, add_leaf_bones=False, bake_anim=True)

    size = os.path.getsize(args.output)
    print(f"Exported: {args.output} ({size:,} bytes)")
    print("DONE")


main()
