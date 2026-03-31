"""
Assemble a rigged character into a kart in driving pose.

Usage (headless Blender):
    blender --background --python assemble_driver_kart.py -- \
        --character <character_rigged.glb> \
        --kart <kart_blender.glb> \
        --output-glb <output.glb> \
        --output-fbx <output.fbx> \
        --character-scale <float>

Usage (via blender-mcp socket):
    Run this script's content via execute_code with parameters injected.
"""
import bpy
import math
import sys
import os
import json
from mathutils import Vector, Euler, Matrix


def parse_args():
    """Parse command-line args after '--'."""
    argv = sys.argv
    if "--" in argv:
        argv = argv[argv.index("--") + 1:]
    else:
        return {}

    args = {}
    i = 0
    while i < len(argv):
        if argv[i] == "--character":
            args["character"] = argv[i + 1]; i += 2
        elif argv[i] == "--kart":
            args["kart"] = argv[i + 1]; i += 2
        elif argv[i] == "--output-glb":
            args["output_glb"] = argv[i + 1]; i += 2
        elif argv[i] == "--output-fbx":
            args["output_fbx"] = argv[i + 1]; i += 2
        elif argv[i] == "--character-scale":
            args["character_scale"] = float(argv[i + 1]); i += 2
        elif argv[i] == "--report":
            args["report"] = argv[i + 1]; i += 2
        elif argv[i] == "--hybrid-baked":
            args["hybrid_baked"] = True; i += 1
        elif argv[i] == "--y-offset":
            args["y_offset"] = float(argv[i + 1]); i += 2
        else:
            i += 1
    return args


def clear_scene():
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()
    for collection in bpy.data.collections:
        bpy.data.collections.remove(collection)
    for armature in bpy.data.armatures:
        bpy.data.armatures.remove(armature)
    for mesh in bpy.data.meshes:
        bpy.data.meshes.remove(mesh)


def find_empty(name_contains):
    """Find an empty object whose name contains the given string (case-insensitive)."""
    for obj in bpy.data.objects:
        if obj.type == 'EMPTY' and name_contains.lower() in obj.name.lower():
            return obj
    return None


def find_armature():
    for obj in bpy.data.objects:
        if obj.type == 'ARMATURE':
            return obj
    return None


def get_world_pos(obj):
    """Get object's world-space location."""
    return obj.matrix_world.translation.copy()


BONE_MAP = {
    "Character1_Hips": "hips",
    "Character1_Spine": "spine",
    "Character1_Spine1": "chest",
    "Character1_Spine2": "chest_upper",
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
}


def _retarget_driving_pose(armature, source_fbx, frame=50):
    """Retarget a driving animation frame from a Rokoko/Mixamo FBX onto the character."""
    # Import source animation
    before = set(bpy.data.objects)
    bpy.ops.import_scene.fbx(filepath=source_fbx)
    after = set(bpy.data.objects)
    new_objs = after - before

    source_arm = None
    for obj in new_objs:
        if obj.type == 'ARMATURE':
            source_arm = obj
            break

    if not source_arm:
        print("WARNING: No armature in driving animation FBX, falling back to Euler")
        _apply_euler_driving_pose(armature)
        return

    # Extract rotations at the target frame
    bpy.context.scene.frame_set(frame)
    bpy.context.view_layer.objects.active = source_arm
    source_arm.select_set(True)
    bpy.ops.object.mode_set(mode='POSE')

    rotations = {}
    for pb in source_arm.pose.bones:
        target_name = BONE_MAP.get(pb.name)
        if target_name:
            rotations[target_name] = pb.matrix_basis.to_quaternion()

    bpy.ops.object.mode_set(mode='OBJECT')

    # Delete source armature and its meshes
    for obj in new_objs:
        bpy.data.objects.remove(obj, do_unlink=True)

    # Apply rotations to target
    bpy.context.view_layer.objects.active = armature
    armature.select_set(True)
    bpy.ops.object.mode_set(mode='POSE')

    applied = 0
    for pb in armature.pose.bones:
        if pb.name in rotations:
            pb.rotation_mode = 'QUATERNION'
            pb.rotation_quaternion = rotations[pb.name]
            applied += 1

    bpy.ops.object.mode_set(mode='OBJECT')
    print(f"Retargeted driving pose: {applied} bones from {os.path.basename(source_fbx)} frame {frame}")


def _apply_euler_driving_pose(armature):
    """Fallback: hardcoded Euler driving pose (deprecated, kept for compatibility)."""
    bpy.context.view_layer.objects.active = armature
    armature.select_set(True)
    bpy.ops.object.mode_set(mode='POSE')

    def pose_bone(name_contains, rot_degrees, axis='X'):
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
                return pb
        return None

    pose_bone("upperleg.l", -90)
    pose_bone("upperleg.r", -90)
    pose_bone("lowerleg.l", 90)
    pose_bone("lowerleg.r", 90)
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
    pose_bone("foot.l", -20)
    pose_bone("foot.r", -20)

    bpy.ops.object.mode_set(mode='OBJECT')
    print("Fallback Euler driving pose applied (deprecated)")


def assemble(character_path, kart_path, output_glb, output_fbx=None,
             character_scale=1.0, report_path=None, hybrid_baked=False,
             y_offset=0.0):
    """Main assembly: import kart + character, pose character seated in kart."""

    clear_scene()

    # --- Import kart ---
    bpy.ops.import_scene.gltf(filepath=kart_path)
    kart_objects = list(bpy.data.objects)
    kart_root = None
    for obj in kart_objects:
        if "kartroot" in obj.name.lower() or (obj.parent is None and obj.type == 'EMPTY'):
            kart_root = obj
            break

    seat = find_empty("seat")
    steering = find_empty("steering")

    if not seat:
        print("WARNING: No Seat empty found in kart, using origin")
        seat_pos = Vector((0, 0, 0.3))
    else:
        seat_pos = get_world_pos(seat)

    if not steering:
        print("WARNING: No SteeringColumn empty found, estimating position")
        steering_pos = seat_pos + Vector((0, 0.4, 0.15))
    else:
        steering_pos = get_world_pos(steering)

    print(f"Kart loaded: Seat at {seat_pos}, Steering at {steering_pos}")

    # --- Import character ---
    before_import = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=character_path)
    after_import = set(bpy.data.objects)
    new_objects = after_import - before_import

    armature = None
    char_meshes = []
    for obj in new_objects:
        if obj.type == 'ARMATURE':
            armature = obj
        elif obj.type == 'MESH':
            char_meshes.append(obj)

    if not armature:
        armature = find_armature()
    if not armature:
        print("ERROR: No armature found in character file")
        return

    print(f"Character loaded: {armature.name}, {len(armature.data.bones)} bones")

    # --- Scale character to fit kart ---
    if character_scale != 1.0:
        armature.scale = (character_scale, character_scale, character_scale)
        bpy.ops.object.select_all(action='DESELECT')
        armature.select_set(True)
        bpy.context.view_layer.objects.active = armature
        bpy.ops.object.transform_apply(scale=True)

    # --- Get character dimensions ---
    # Find hips bone position for alignment
    hips_bone = None
    for bone in armature.data.bones:
        if "hip" in bone.name.lower():
            hips_bone = bone
            break

    if hips_bone:
        hips_world = armature.matrix_world @ hips_bone.head_local
    else:
        hips_world = armature.location.copy()

    # --- Position character: hips on seat ---
    offset = seat_pos - hips_world
    # Raise slightly so character sits ON the seat, not inside it
    offset.z += 0.05
    offset.y += y_offset  # User-tunable Y offset (negative = toward rear)
    armature.location += offset

    # Apply location
    bpy.ops.object.select_all(action='DESELECT')
    armature.select_set(True)
    bpy.context.view_layer.objects.active = armature

    print(f"Character positioned at seat, offset: {offset}")

    # --- Pose character in driving position via animation retargeting ---
    if not hybrid_baked:
        # Retarget a driving animation from a reference FBX onto this skeleton.
        # This replaces the old hardcoded Euler rotation approach which was fragile
        # and broke when bone local axes differed between characters.
        driving_anim = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            "animate-ralph", "references", "humanoid", "driving",
            "rokoko_legacy_sitting_idle01.fbx"
        )
        # Fallback: try gesture folder for the F1 driving animation
        if not os.path.exists(driving_anim):
            driving_anim = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                "animate-ralph", "references", "humanoid", "gesture",
                "rokoko_legacy_driving_formula1.fbx"
            )

        if os.path.exists(driving_anim):
            print(f"Retargeting driving animation from: {os.path.basename(driving_anim)}")
            _retarget_driving_pose(armature, driving_anim, frame=50)
        else:
            print("WARNING: No driving animation found, falling back to Euler pose")
            _apply_euler_driving_pose(armature)
    else:
        print("Hybrid-baked mode: skipping pose (already baked)")

    # --- Parent character to kart Seat ---
    if seat:
        armature.parent = seat
        armature.matrix_parent_inverse = seat.matrix_world.inverted()

    # --- Export GLB ---
    os.makedirs(os.path.dirname(output_glb), exist_ok=True)
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.export_scene.gltf(
        filepath=output_glb,
        export_format='GLB',
        use_selection=True,
        export_animations=False,
        export_skins=True,
    )
    glb_size = os.path.getsize(output_glb)
    print(f"Exported GLB: {output_glb} ({glb_size:,} bytes)")

    # --- Export FBX ---
    if output_fbx:
        os.makedirs(os.path.dirname(output_fbx), exist_ok=True)
        bpy.ops.export_scene.fbx(
            filepath=output_fbx,
            use_selection=True,
            apply_scale_options='FBX_SCALE_ALL',
            bake_anim=False,
            add_leaf_bones=False,
        )
        fbx_size = os.path.getsize(output_fbx)
        print(f"Exported FBX: {output_fbx} ({fbx_size:,} bytes)")

    # --- Write report ---
    if report_path:
        report = {
            "character": os.path.basename(character_path),
            "kart": os.path.basename(kart_path),
            "character_scale": character_scale,
            "seat_position": list(seat_pos),
            "steering_position": list(steering_pos),
            "bone_count": len(armature.data.bones),
            "output_glb": output_glb,
            "output_fbx": output_fbx,
            "glb_size": glb_size,
            "fbx_size": os.path.getsize(output_fbx) if output_fbx else 0,
            "pose": "seated_driving",
        }
        os.makedirs(os.path.dirname(report_path), exist_ok=True)
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2)
        print(f"Report: {report_path}")

    print("ASSEMBLY COMPLETE")


if __name__ == "__main__":
    args = parse_args()
    if args:
        assemble(
            character_path=args["character"],
            kart_path=args["kart"],
            output_glb=args.get("output_glb", "/tmp/assembled.glb"),
            output_fbx=args.get("output_fbx"),
            character_scale=args.get("character_scale", 1.0),
            report_path=args.get("report"),
            hybrid_baked=args.get("hybrid_baked", False),
            y_offset=args.get("y_offset", 0.0),
        )
