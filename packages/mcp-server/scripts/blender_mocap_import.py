"""Blender Python script for importing motion capture data.

This script imports BVH or FBX motion capture files and retargets them
to the character's rig.

Usage (called by external_app_manager.py):
    blender --background <blend_file> --python blender_mocap_import.py -- <mocap_file> [options_json]

Supported Formats:
    - BVH (Biovision Hierarchy) - Common mocap format, used by Mixamo
    - FBX with animation data

Options (JSON):
    {
        "scale": 1.0,              # Scale factor for the mocap
        "start_frame": 1,          # Start frame for the animation
        "use_fps_scale": true,     # Scale animation to match scene FPS
        "output_path": "out.glb",  # Export path
        "output_format": "glb"     # glb, fbx, or blend
    }
"""

import sys
import os
import json
import math
from pathlib import Path

try:
    import bpy
    from mathutils import Vector, Euler, Matrix, Quaternion
except ImportError:
    print("ERROR: This script must be run from within Blender")
    sys.exit(1)


# Common bone name mappings between Mixamo and standard rigs
MIXAMO_TO_STANDARD = {
    'mixamorig:Hips': ['hips', 'pelvis', 'root'],
    'mixamorig:Spine': ['spine', 'spine.001'],
    'mixamorig:Spine1': ['spine.001', 'spine1', 'spine2'],
    'mixamorig:Spine2': ['spine.002', 'spine2', 'chest'],
    'mixamorig:Neck': ['neck', 'neck.001'],
    'mixamorig:Head': ['head'],
    'mixamorig:LeftShoulder': ['shoulder.L', 'shoulder.l', 'clavicle.L'],
    'mixamorig:LeftArm': ['upper_arm.L', 'upper_arm_fk.L', 'upperarm.L'],
    'mixamorig:LeftForeArm': ['forearm.L', 'forearm_fk.L', 'lowerarm.L'],
    'mixamorig:LeftHand': ['hand.L', 'hand_fk.L', 'wrist.L'],
    'mixamorig:RightShoulder': ['shoulder.R', 'shoulder.r', 'clavicle.R'],
    'mixamorig:RightArm': ['upper_arm.R', 'upper_arm_fk.R', 'upperarm.R'],
    'mixamorig:RightForeArm': ['forearm.R', 'forearm_fk.R', 'lowerarm.R'],
    'mixamorig:RightHand': ['hand.R', 'hand_fk.R', 'wrist.R'],
    'mixamorig:LeftUpLeg': ['thigh.L', 'thigh_fk.L', 'upperleg.L'],
    'mixamorig:LeftLeg': ['shin.L', 'shin_fk.L', 'lowerleg.L', 'calf.L'],
    'mixamorig:LeftFoot': ['foot.L', 'foot_fk.L', 'ankle.L'],
    'mixamorig:LeftToeBase': ['toe.L', 'toes.L'],
    'mixamorig:RightUpLeg': ['thigh.R', 'thigh_fk.R', 'upperleg.R'],
    'mixamorig:RightLeg': ['shin.R', 'shin_fk.R', 'lowerleg.R', 'calf.R'],
    'mixamorig:RightFoot': ['foot.R', 'foot_fk.R', 'ankle.R'],
    'mixamorig:RightToeBase': ['toe.R', 'toes.R'],
}

# CMU/BVH standard bone names
CMU_TO_STANDARD = {
    'Hips': ['hips', 'pelvis', 'root'],
    'LHipJoint': ['thigh.L', 'thigh_fk.L'],
    'LeftUpLeg': ['thigh.L', 'thigh_fk.L'],
    'LeftLeg': ['shin.L', 'shin_fk.L'],
    'LeftFoot': ['foot.L', 'foot_fk.L'],
    'LeftToeBase': ['toe.L'],
    'RHipJoint': ['thigh.R', 'thigh_fk.R'],
    'RightUpLeg': ['thigh.R', 'thigh_fk.R'],
    'RightLeg': ['shin.R', 'shin_fk.R'],
    'RightFoot': ['foot.R', 'foot_fk.R'],
    'RightToeBase': ['toe.R'],
    'LowerBack': ['spine', 'spine.001'],
    'Spine': ['spine.001', 'spine1'],
    'Spine1': ['spine.002', 'chest'],
    'Neck': ['neck'],
    'Neck1': ['neck.001'],
    'Head': ['head'],
    'LeftShoulder': ['shoulder.L', 'clavicle.L'],
    'LeftArm': ['upper_arm.L', 'upper_arm_fk.L'],
    'LeftForeArm': ['forearm.L', 'forearm_fk.L'],
    'LeftHand': ['hand.L', 'hand_fk.L'],
    'RightShoulder': ['shoulder.R', 'clavicle.R'],
    'RightArm': ['upper_arm.R', 'upper_arm_fk.R'],
    'RightForeArm': ['forearm.R', 'forearm_fk.R'],
    'RightHand': ['hand.R', 'hand_fk.R'],
}


def get_armature():
    """Find the main armature in the scene."""
    armatures = [obj for obj in bpy.data.objects if obj.type == 'ARMATURE']

    if not armatures:
        return None

    # Prefer RIG- prefixed armatures (Rigify)
    for arm in armatures:
        if arm.name.startswith("RIG-"):
            return arm

    # Return the one with most bones
    return max(armatures, key=lambda a: len(a.pose.bones))


def find_matching_bone(target_armature, source_bone_name):
    """Find the matching bone in the target armature for a source bone name."""
    pose_bones = target_armature.pose.bones

    # Check direct name match first
    if source_bone_name in pose_bones:
        return pose_bones[source_bone_name]

    # Try lowercase
    source_lower = source_bone_name.lower()
    for bone in pose_bones:
        if bone.name.lower() == source_lower:
            return bone

    # Try Mixamo mapping
    if source_bone_name in MIXAMO_TO_STANDARD:
        for target_name in MIXAMO_TO_STANDARD[source_bone_name]:
            target_lower = target_name.lower()
            for bone in pose_bones:
                if bone.name.lower() == target_lower or target_lower in bone.name.lower():
                    return bone

    # Try CMU mapping
    if source_bone_name in CMU_TO_STANDARD:
        for target_name in CMU_TO_STANDARD[source_bone_name]:
            target_lower = target_name.lower()
            for bone in pose_bones:
                if bone.name.lower() == target_lower or target_lower in bone.name.lower():
                    return bone

    # Try partial match
    source_parts = source_bone_name.lower().replace('mixamorig:', '').split('_')
    for bone in pose_bones:
        bone_lower = bone.name.lower()
        if all(part in bone_lower for part in source_parts if len(part) > 2):
            return bone

    return None


def import_bvh(filepath, options):
    """Import a BVH motion capture file."""
    scale = options.get('scale', 1.0)
    start_frame = options.get('start_frame', 1)
    use_fps_scale = options.get('use_fps_scale', True)

    # Import BVH
    bpy.ops.import_anim.bvh(
        filepath=filepath,
        filter_glob="*.bvh",
        target='ARMATURE',
        global_scale=scale,
        frame_start=start_frame,
        use_fps_scale=use_fps_scale,
        update_scene_fps=False,
        update_scene_duration=True,
        use_cyclic=False,
        rotate_mode='NATIVE'
    )

    # Find the imported armature (most recently added)
    imported_armature = None
    for obj in bpy.context.selected_objects:
        if obj.type == 'ARMATURE':
            imported_armature = obj
            break

    if not imported_armature:
        # Find by checking what's new
        for obj in bpy.data.objects:
            if obj.type == 'ARMATURE' and obj.animation_data and obj.animation_data.action:
                imported_armature = obj
                break

    return imported_armature


def import_fbx_animation(filepath, options):
    """Import an FBX file with animation."""
    scale = options.get('scale', 1.0)

    bpy.ops.import_scene.fbx(
        filepath=filepath,
        use_anim=True,
        anim_offset=options.get('start_frame', 1),
        global_scale=scale
    )

    # Find imported armature
    imported_armature = None
    for obj in bpy.context.selected_objects:
        if obj.type == 'ARMATURE':
            imported_armature = obj
            break

    return imported_armature


def retarget_animation(source_armature, target_armature, options):
    """Retarget animation from source armature to target armature."""
    if not source_armature.animation_data or not source_armature.animation_data.action:
        print("ERROR: Source armature has no animation data")
        return None

    source_action = source_armature.animation_data.action

    # Create new action for target
    action_name = f"{source_action.name}_retargeted"
    target_action = bpy.data.actions.new(name=action_name)

    # Assign to target armature
    if not target_armature.animation_data:
        target_armature.animation_data_create()
    target_armature.animation_data.action = target_action

    # Make target active and enter pose mode
    bpy.ops.object.select_all(action='DESELECT')
    target_armature.select_set(True)
    bpy.context.view_layer.objects.active = target_armature
    bpy.ops.object.mode_set(mode='POSE')

    # Get frame range from source action
    frame_start = int(source_action.frame_range[0])
    frame_end = int(source_action.frame_range[1])

    print(f"Retargeting frames {frame_start} to {frame_end}")

    # Build bone mapping
    bone_mapping = {}
    for source_bone in source_armature.pose.bones:
        target_bone = find_matching_bone(target_armature, source_bone.name)
        if target_bone:
            bone_mapping[source_bone.name] = target_bone.name
            print(f"  Mapped: {source_bone.name} -> {target_bone.name}")

    if not bone_mapping:
        print("WARNING: No bone mappings found!")
        return target_action

    # Copy animation data
    # We need to sample the animation and apply it to the target
    bpy.context.scene.frame_start = frame_start
    bpy.context.scene.frame_end = frame_end

    step = options.get('sample_rate', 1)  # Sample every N frames

    for frame in range(frame_start, frame_end + 1, step):
        bpy.context.scene.frame_set(frame)

        for source_bone_name, target_bone_name in bone_mapping.items():
            source_bone = source_armature.pose.bones.get(source_bone_name)
            target_bone = target_armature.pose.bones.get(target_bone_name)

            if not source_bone or not target_bone:
                continue

            # Copy rotation
            try:
                # Convert rotation to euler
                if source_bone.rotation_mode == 'QUATERNION':
                    rot = source_bone.rotation_quaternion.to_euler()
                else:
                    rot = source_bone.rotation_euler.copy()

                target_bone.rotation_mode = 'XYZ'
                target_bone.rotation_euler = rot
                target_bone.keyframe_insert(data_path="rotation_euler", frame=frame)
            except Exception as e:
                print(f"  Error copying rotation for {source_bone_name}: {e}")

            # Copy location for root bone only
            if 'hip' in source_bone_name.lower() or 'root' in source_bone_name.lower():
                try:
                    target_bone.location = source_bone.location.copy()
                    target_bone.keyframe_insert(data_path="location", frame=frame)
                except Exception as e:
                    print(f"  Error copying location for {source_bone_name}: {e}")

    print(f"Created retargeted action: {action_name}")
    return target_action


def export_animation(output_path, output_format):
    """Export the animated model."""
    ext = output_format.lower()

    if ext in ['glb', 'gltf']:
        bpy.ops.export_scene.gltf(
            filepath=output_path,
            export_format='GLB' if ext == 'glb' else 'GLTF_SEPARATE',
            export_animations=True,
            export_animation_mode='ACTIONS',
        )
    elif ext == 'fbx':
        bpy.ops.export_scene.fbx(
            filepath=output_path,
            bake_anim=True,
            bake_anim_use_all_actions=False,
        )
    elif ext == 'blend':
        bpy.ops.wm.save_as_mainfile(filepath=output_path)
    else:
        raise ValueError(f"Unsupported export format: {ext}")


def main():
    argv = sys.argv
    try:
        idx = argv.index("--") + 1
        args = argv[idx:]
    except (ValueError, IndexError):
        print("Usage: blender <file.blend> --python blender_mocap_import.py -- <mocap_file> [options_json]")
        sys.exit(1)

    if len(args) < 1:
        print("ERROR: Missing mocap file path")
        sys.exit(1)

    mocap_path = args[0]

    # Parse options
    options = {}
    if len(args) > 1:
        try:
            options = json.loads(args[1])
        except json.JSONDecodeError as e:
            print(f"Warning: Failed to parse options JSON: {e}")

    print(f"ComfyUI Mocap Import: {mocap_path}")
    print(f"Options: {options}")

    # Check mocap file exists
    if not os.path.exists(mocap_path):
        print(f"ERROR: Mocap file not found: {mocap_path}")
        sys.exit(1)

    # Find target armature (the character rig)
    target_armature = get_armature()
    if not target_armature:
        print("ERROR: No armature found in the blend file")
        sys.exit(1)

    print(f"Target armature: {target_armature.name} ({len(target_armature.pose.bones)} bones)")

    # Import mocap file
    ext = Path(mocap_path).suffix.lower()

    if ext == '.bvh':
        print("Importing BVH motion capture...")
        source_armature = import_bvh(mocap_path, options)
    elif ext == '.fbx':
        print("Importing FBX animation...")
        source_armature = import_fbx_animation(mocap_path, options)
    else:
        print(f"ERROR: Unsupported mocap format: {ext}")
        sys.exit(1)

    if not source_armature:
        print("ERROR: Failed to import mocap file")
        sys.exit(1)

    print(f"Imported armature: {source_armature.name} ({len(source_armature.pose.bones)} bones)")

    # Retarget animation
    print("Retargeting animation...")
    action = retarget_animation(source_armature, target_armature, options)

    if action:
        print(f"Created action: {action.name}")

    # Delete the imported armature (we only needed its animation)
    bpy.ops.object.select_all(action='DESELECT')
    source_armature.select_set(True)
    bpy.ops.object.delete()

    # Export if requested
    output_path = options.get('output_path')
    if output_path:
        output_format = options.get('output_format', 'glb')
        if not output_path.endswith(f'.{output_format}'):
            output_path = f"{output_path}.{output_format}"

        export_animation(output_path, output_format)
        print(f"Exported to: {output_path}")
    else:
        # Save blend file
        bpy.ops.wm.save_mainfile()
        print("Saved to blend file")

    print("Successfully imported mocap animation")


if __name__ == "__main__":
    main()
