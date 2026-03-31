"""
Batch assemble all characters into their assigned karts.
Runs via headless Blender.

Each character uses its own rigged GLB from autorig-ralph (not a placeholder).
Arm pose values are per-character since UniRig bone local axes are arbitrary.

ORIENTATION CONVENTION:
  - Kart visual front (hood, steering wheel) = +Y in Blender
  - The 'Axle_Front' empty name is MISLEADING — it sits at -Y (visual rear)
  - Always use hood/steering wheel to determine kart forward, not axle names
  - Hunyuan3D characters face +Y after GLB import — matches kart, NO rotation needed
  - Blender +Y → Unity +Z (forward) via standard FBX axis mapping

FILE FORMAT:
  - FBX is the primary export for Unity (not GLB)
  - FBX settings: FBX_SCALE_ALL, no animation baking, no leaf bones
  - GLB exported as secondary for Blender reference

Usage:
    "C:/Program Files/Blender Foundation/Blender 5.0/blender.exe" \\
        --background --python batch_assemble.py
"""
import bpy
import math
import os
import sys
import json
from mathutils import Vector, Euler

# Paths
TOOLCHAIN = "D:/Projects/comfyui-toolchain"
KART_DIR = f"{TOOLCHAIN}/pipelines/art-to-rig-ralph/output/final"
AUTORIG_DIR = f"{TOOLCHAIN}/pipelines/autorig-ralph/output"
OUTPUT_DIR = f"{TOOLCHAIN}/pipelines/kart-assembly-ralph/output/unity-batch"

# Character-Kart mapping
DRIVER_KART_MAP = {
    "player": "player_kart",
    "bones": "bones_kart",
    "crank": "crank_kart",
    "grit": "grit_kart",
    "pip": "pip_kart",
    "punk_king": "punk_king_kart",
    "rust": "rust_kart",
    "smog": "smog_kart",
    "sparks": "sparks_kart",
    "soup_box": "soup_box_kart",
}

CHARACTER_SCALE = 0.6
Y_OFFSET = -0.12  # Move character back from seat toward rear of kart

# ---------------------------------------------------------------------------
# Per-character arm pose values
# ---------------------------------------------------------------------------
# Legs/spine Euler X rotations work universally across UniRig skeletons.
# Arm rotations are PER-CHARACTER because UniRig bone local axes are arbitrary.
# Each character's arm values must be captured from a manual posing session in Blender.
#
# Format: {bone_name: (rx, ry, rz, loc_x, loc_y, loc_z)}
# If a character has no entry, arms stay in T-pose (needs manual posing session).

UNIVERSAL_POSE = {
    # These work across all characters (Euler X)
    "upperleg.l":  (-90, 0, 0, 0, 0, 0),
    "upperleg.r":  (-90, 0, 0, 0, 0, 0),
    "lowerleg.l":  (90, 0, 0, 0, 0, 0),
    "lowerleg.r":  (90, 0, 0, 0, 0, 0),
    "foot.l":      (-20, 0, 0, 0, 0, 0),
    "foot.r":      (-20, 0, 0, 0, 0, 0),
    "spine":       (-10, 0, 0, 0, 0, 0),
    "chest":       (-5, 0, 0, 0, 0, 0),
    "neck":        (5, 0, 0, 0, 0, 0),
    "head":        (15, 0, 0, 0, 0, 0),
}

# Per-character poses (captured from manual Blender posing sessions)
# Format: {"bone_name": ("EULER", rx, ry, rz, lx, ly, lz)} or
#          {"bone_name": ("QUAT", w, x, y, z, lx, ly, lz)}
# These OVERRIDE the universal pose for matching bones.
# Each character may need different leg angles too (soapbox karts vary).
CHARACTER_POSES = {
    "player": {
        # Captured 2026-03-30 — manual arm posing session
        "upperarm.r":  ("EULER", -3.8, 1.6, -4.7, 0.0201, 0.0063, -0.0138),
        "lowerarm.r":  ("EULER", -17.8, -26.9, -93.7, 0.0223, 0.0087, -0.0064),
        "hand.r":      ("EULER", -10, 0, 0, 0, 0, 0),
        "upperarm.l":  ("EULER", -2.0, -1.0, 2.4, -0.0113, 0.0029, -0.0079),
        "lowerarm.l":  ("EULER", -23.7, 16.8, 93.6, -0.0189, 0.0074, -0.0054),
        "hand.l":      ("EULER", -10, 0, 0, 0, 0, 0),
    },
    "bones": {
        # Captured 2026-03-30 — full driving pose (relaxed legs, ~24° not 90°)
        # Arms
        "upperarm.r":  ("QUAT", 0.9769, -0.1559, -0.0361, 0.1420, 0.0001, -0.0001, 0.0002),
        "lowerarm.r":  ("QUAT", 0.6744, -0.6098, 0.0529, -0.4127, 0, 0, 0),
        "upperarm.l":  ("QUAT", 0.9907, -0.0976, 0.0160, -0.0930, 0.0001, 0.0001, -0.0002),
        "lowerarm.l":  ("QUAT", 0.5076, -0.2508, -0.3598, 0.7409, 0, 0, 0),
        # Fingers (right hand)
        "bone_13":     ("QUAT", 0.9385, -0.2597, 0.2184, -0.0638, 0.0050, 0.0021, -0.0123),
        "bone_16":     ("QUAT", 0.9385, -0.2448, 0.2432, 0.0170, 0.0008, 0.0012, -0.0070),
        "bone_19":     ("QUAT", 0.9385, -0.2704, 0.2146, -0.0136, -0.0007, -0.0006, 0.0034),
        "bone_22":     ("QUAT", 0.9385, -0.2287, 0.2567, -0.0344, -0.0048, -0.0018, 0.0163),
        # Legs (relaxed, not 90° seated)
        "hip_connector.r": ("QUAT", 0.8556, -0.4980, -0.0923, -0.1069, -0.0003, -0.0025, 0.0033),
        "upperleg.r":  ("EULER", -24.0, 5.1, 19.7, -0.0017, 0.0070, -0.0001),
        "hip_connector.l": ("QUAT", 0.8556, -0.5092, 0.0723, 0.0582, 0, 0.0024, -0.0034),
        "upperleg.l":  ("EULER", -23.2, -5.8, -15.4, -0.0015, -0.0071, 0.0002),
    },
    "grit": {
        # Captured 2026-03-31 — 28-bone skeleton (different numbering from 52-bone characters)
        # NOTE: Must use original FBX for grit — GLB export lost weight data
        # Arms
        "bone_8":      ("QUAT", 0.8126, -0.5418, 0.1764, -0.1225, 0, 0, 0),
        "bone_14":     ("QUAT", 0.9391, -0.0843, 0.2795, 0.1815, 0, 0, 0),
        "bone_15":     ("QUAT", 0.8572, -0.3483, -0.0691, -0.3730, 0, 0, 0),
        # Legs (adjusted from universal)
        "bone_20":     ("QUAT", 0.8010, -0.5873, -0.0604, -0.0990, 0.0249, 0.0002, -0.0565),
        "bone_21":     ("QUAT", 0.9746, -0.2076, 0.0718, -0.0448, 0, 0, 0),
        "bone_24":     ("QUAT", 0.8349, -0.5372, -0.0764, 0.0925, 0, 0, 0),
    },
    "pip": {
        # Captured 2026-03-31 — 52-bone skeleton, full driving pose
        # Right arm + fingers
        "bone_7":      ("EULER", -32.4, 14.9, -44.4, 0, 0, 0),
        "bone_8":      ("EULER", 3.7, 17.4, -51.5, 0, 0, 0),
        "bone_13":     ("EULER", -14.1, 15.0, -60.6, 0, 0, 0),
        "bone_14":     ("EULER", -17.5, 13.9, -61.4, 0, 0, 0),
        "bone_16":     ("EULER", -52.7, 18.0, -94.6, 0, 0, 0),
        "bone_19":     ("EULER", -17.3, 21.1, -39.0, 0, 0, 0),
        "bone_20":     ("EULER", 4.5, -6.0, -6.9, 0, 0, 0),
        "bone_22":     ("EULER", -14.7, -28.4, -25.6, 0, 0, 0),
        # Left arm + fingers
        "bone_25":     ("EULER", 2.2, 1.2, -3.9, 0, 0, 0),
        "bone_26":     ("EULER", -11.0, -12.9, 22.6, 0, 0, 0),
        "bone_27":     ("EULER", -17.4, 0.6, 84.9, 0, 0, 0),
        "bone_32":     ("EULER", -33.1, -13.9, 84.4, 0, 0, 0),
        "bone_35":     ("EULER", -61.7, -21.1, 76.4, 0, 0, 0),
        "bone_38":     ("EULER", -55.1, -30.5, 74.4, 0, 0, 0),
        "bone_41":     ("EULER", -15.6, 46.6, 55.7, 0, 0, 0),
        # Legs (adjusted from universal -90)
        "bone_44":     ("EULER", -84.6, -22.8, -0.2, 0, 0, 0),
        "bone_45":     ("EULER", -12.9, 4.7, 35.5, 0, 0, 0),
        "bone_48":     ("EULER", -83.1, 22.2, 0.2, 0, 0, 0),
        "bone_49":     ("EULER", -24.3, -5.2, -22.1, 0, 0, 0),
    },
    "punk_king": {
        # Captured 2026-03-31 — 58-bone skeleton
        # Arms + fingers
        "bone_6":      ("EULER", -28.4, 4.7, 35.0, 0, 0, 0),
        "bone_7":      ("EULER", -39.5, 2.5, -55.7, 0, 0, 0),
        "bone_9":      ("EULER", -51.5, -18.3, -42.5, 0, 0, 0),
        "bone_12":     ("EULER", -41.6, -6.8, -38.6, 0, 0, 0),
        "bone_15":     ("EULER", -44.6, -1.9, -41.2, 0, 0, 0),
        "bone_18":     ("EULER", -61.2, 8.4, -37.5, 0, 0, 0),
        "bone_25":     ("EULER", -19.3, -36.2, -3.4, 0, 0, 0),
        "bone_26":     ("EULER", -19.2, -23.6, 47.4, 0, 0, 0),
        "bone_31":     ("EULER", -7.6, 18.2, 125.7, 0, 0, 0),
        "bone_34":     ("EULER", -12.7, 6.6, 65.3, 0, 0, 0),
        # Legs (adjusted)
        "bone_46":     ("EULER", -76.4, -1.0, -1.3, 0, 0, 0),
        "bone_50":     ("EULER", -68.3, -25.8, 25.3, 0, 0, 0),
        "bone_51":     ("EULER", 16.8, 10.4, -18.6, 0, 0, 0),
        "bone_52":     ("EULER", -90.0, 0, 0, 0, 0, 0),
        "bone_53":     ("EULER", 90.0, 0, 0, 0, 0, 0),
        "bone_54":     ("EULER", -20.0, 0, 0, 0, 0, 0),
        "bone_55":     ("EULER", -87.6, -0.4, -0.4, 0, 0, 0),
        "bone_56":     ("EULER", 90.0, 0, 0, 0, 0, 0),
        "bone_57":     ("EULER", -20.0, 0, 0, 0, 0, 0),
    },
    "rust": {
        # Captured 2026-03-31 — 46-bone skeleton
        # Arms + fingers
        "bone_7":      ("QUAT", 0.9408, -0.2045, -0.2134, -0.1658, 0, 0, 0),
        "bone_8":      ("QUAT", 0.9051, -0.3416, 0.1361, 0.2135, 0, 0, 0),
        "bone_11":     ("QUAT", 0.9665, -0.2045, 0.0102, -0.1547, 0, 0, 0),
        "bone_13":     ("QUAT", 0.9039, 0.2079, 0.1640, 0.3360, 0, 0, 0),
        "bone_16":     ("QUAT", 0.8278, 0.2817, 0.1578, 0.4588, 0, 0, 0),
        "bone_19":     ("QUAT", 0.9274, -0.0057, -0.0904, 0.3630, 0, 0, 0),
        "bone_23":     ("QUAT", 0.9757, -0.1221, 0.1459, 0.1089, 0, 0, 0),
        "bone_24":     ("QUAT", 0.8681, -0.4838, 0.0792, -0.0782, 0, 0, 0),
        "bone_27":     ("QUAT", 0.9536, 0.2683, -0.1217, 0.0621, 0, 0, 0),
        "bone_32":     ("QUAT", 0.9278, 0.1766, 0.0536, -0.3241, 0, 0, 0),
        "bone_35":     ("QUAT", 0.8957, 0.1482, -0.0818, -0.4112, 0, 0, 0),
        # Legs
        "bone_38":     ("QUAT", 0.8090, -0.5154, 0.2694, -0.0859, 0, 0, 0),
        "bone_39":     ("QUAT", 0.9321, -0.2140, 0.0204, -0.2915, 0, 0, 0),
        "bone_42":     ("QUAT", 0.8622, -0.5031, -0.0500, 0.0318, 0, 0, 0),
        "bone_43":     ("QUAT", 0.9615, -0.2428, -0.0105, 0.1282, 0, 0, 0),
    },
    "smog": {
        # Captured 2026-03-31 — 58-bone skeleton
        # Arms + fingers
        "bone_8":      ("EULER", -6.6, -5.3, 1.5, 0, 0, 0),
        "bone_9":      ("EULER", -51.6, 0.3, 20.3, 0, 0, 0),
        "bone_10":     ("EULER", 10.4, -15.4, 0.3, 0, 0, 0),
        "bone_15":     ("EULER", -16.9, -0.9, -15.5, 0, 0, 0),
        "bone_16":     ("EULER", 34.5, -36.6, 30.8, 0, 0, 0),
        "bone_19":     ("EULER", 38.2, -7.3, 2.9, 0, 0, 0),
        "bone_21":     ("EULER", 9.1, -2.2, 15.7, 0, 0, 0),
        "bone_24":     ("EULER", -10.1, -9.2, 13.2, 0, 0, 0),
        "bone_29":     ("EULER", -3.3, 2.3, -2.5, 0, 0, 0),
        "bone_30":     ("EULER", -51.4, -0.7, -13.8, 0, 0, 0),
        "bone_33":     ("EULER", -18.1, -3.9, 9.6, 0, 0, 0),
        "bone_36":     ("EULER", 20.1, 10.6, -46.9, 0, 0, 0),
        "bone_40":     ("EULER", 14.0, -8.5, -24.5, 0, 0, 0),
        "bone_43":     ("EULER", 7.9, -8.2, -63.0, 0, 0, 0),
        "bone_46":     ("EULER", 7.6, -12.0, -37.4, 0, 0, 0),
    },
    "sparks": {
        # Captured 2026-03-31 — 57-bone skeleton
        # Root adjustment
        "bone_0":      ("QUAT", 0.9999, 0.0112, -0.0015, 0.0009, 0, 0, 0),
        # Arms + fingers
        "bone_6":      ("QUAT", 0.9936, 0.0722, 0.0646, -0.0582, 0, 0, 0),
        "bone_7":      ("QUAT", 0.8965, -0.3008, 0.1585, -0.2842, 0.0496, -0.0086, -0.0247),
        "bone_8":      ("QUAT", 0.8958, -0.1010, -0.0932, -0.4228, 0, 0, 0),
        "bone_9":      ("QUAT", 0.9671, -0.0693, -0.1432, -0.1985, 0, 0, 0),
        "bone_12":     ("QUAT", 0.5622, 0.7966, -0.1977, -0.0994, 0, 0, 0),
        "bone_13":     ("QUAT", 0.8594, 0.1084, -0.1935, -0.4606, 0, 0, 0),
        "bone_14":     ("QUAT", 0.9739, -0.0721, -0.0307, -0.2129, 0, 0, 0),
        "bone_16":     ("QUAT", 0.9824, -0.0522, -0.0639, -0.1678, 0, 0, 0),
        "bone_17":     ("QUAT", 0.5849, -0.1137, -0.1377, -0.7912, 0, 0, 0),
        "bone_19":     ("QUAT", 0.7101, -0.2512, -0.0411, -0.6565, 0, 0, 0),
        "bone_22":     ("QUAT", 0.6426, -0.4774, 0.3695, -0.4719, 0, 0, 0),
        "bone_26":     ("QUAT", 0.9994, 0.0228, 0.0136, -0.0211, 0, 0, 0),
        "bone_27":     ("QUAT", 0.9471, -0.2085, 0.1663, 0.1788, -0.0487, 0.0013, -0.0302),
        "bone_28":     ("QUAT", 0.7719, -0.5026, -0.0028, 0.3882, -0.0237, 0.0094, -0.0452),
        "bone_29":     ("QUAT", 0.9973, -0.0388, -0.0064, 0.0610, 0, 0, 0),
        "bone_36":     ("QUAT", 0.8445, 0.0192, 0.1672, 0.5084, -0.0028, -0.0114, 0.0088),
        "bone_39":     ("QUAT", 0.7900, -0.2171, 0.0964, 0.5652, 0, 0, 0),
        "bone_42":     ("QUAT", 0.6733, -0.6066, -0.4168, 0.0679, 0, 0, 0),
        "bone_43":     ("QUAT", 0.8842, 0.4161, 0.0014, 0.2120, 0, 0, 0),
        # Legs (heavily adjusted)
        "bone_45":     ("EULER", -45.1, 17.0, 58.9, 0.0242, 0.0053, 0.0190),
        "bone_46":     ("EULER", 87.5, -6.8, -18.7, 0.0121, -0.0194, -0.0213),
        "bone_48":     ("QUAT", 0.7413, -0.5111, -0.3246, -0.2897, 0, 0, 0),
        "bone_49":     ("EULER", 20.0, 66.1, 70.3, 0, 0, 0),
        "bone_50":     ("EULER", 48.5, 45.6, -18.3, -0.0136, -0.0456, 0.0086),
        "bone_52":     ("QUAT", 0.6946, -0.5878, 0.3750, 0.1773, 0, 0, 0),
        "bone_53":     ("QUAT", 0.9662, 0.0604, -0.0866, -0.2352, 0, 0, 0),
    },
}


def get_character_glb(char_id):
    """Get the rigged GLB path for a character from autorig-ralph output."""
    return f"{AUTORIG_DIR}/{char_id}/rigged/{char_id}-rigged-tpose.glb"


def clear_scene():
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()
    for d in [bpy.data.armatures, bpy.data.meshes, bpy.data.materials,
              bpy.data.images, bpy.data.actions]:
        for item in list(d):
            d.remove(item)


def assemble_one(character_id, kart_id, char_glb, kart_glb, output_fbx, output_glb):
    """Assemble one character into one kart and export."""
    clear_scene()

    # Import kart
    # NOTE: Kart visual front (hood) = +Y. The 'Axle_Front' name is misleading.
    bpy.ops.import_scene.gltf(filepath=kart_glb)

    # Find Seat empty
    seat = None
    steering = None
    for obj in bpy.data.objects:
        if "seat" in obj.name.lower() and obj.type == 'EMPTY':
            seat = obj
        if "steering" in obj.name.lower() and obj.type == 'EMPTY':
            steering = obj

    seat_pos = seat.matrix_world.translation.copy() if seat else Vector((0, 0, 0.3))

    # Import character
    # NOTE: Characters face +Y after import (matches kart hood). NO rotation needed.
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=char_glb)
    new_objs = set(bpy.data.objects) - before

    armature = None
    for obj in new_objs:
        if obj.type == 'ARMATURE':
            armature = obj
    if not armature:
        for obj in bpy.data.objects:
            if obj.type == 'ARMATURE':
                armature = obj

    if not armature:
        print(f"  ERROR: No armature for {character_id}")
        return False

    # Scale
    armature.scale = (CHARACTER_SCALE, CHARACTER_SCALE, CHARACTER_SCALE)
    bpy.ops.object.select_all(action='DESELECT')
    armature.select_set(True)
    bpy.context.view_layer.objects.active = armature
    bpy.ops.object.transform_apply(scale=True)

    # Position at seat
    hips = None
    for bone in armature.data.bones:
        if "hip" in bone.name.lower():
            hips = bone
            break

    if hips:
        hips_world = armature.matrix_world @ hips.head_local
        offset = seat_pos - hips_world
        offset.z += 0.05
        offset.y += Y_OFFSET
        armature.location += offset

    # Apply driving pose
    bpy.ops.object.mode_set(mode='POSE')

    def apply_bone_euler(name, rx, ry, rz, lx=0, ly=0, lz=0):
        pb = armature.pose.bones.get(name)
        if pb:
            pb.rotation_mode = 'XYZ'
            pb.rotation_euler = (math.radians(rx), math.radians(ry), math.radians(rz))
            if abs(lx) > 0.0001 or abs(ly) > 0.0001 or abs(lz) > 0.0001:
                pb.location = (lx, ly, lz)

    def apply_bone_pose(name, values):
        """Apply a pose entry — supports ("EULER", rx,ry,rz,lx,ly,lz) or ("QUAT", w,x,y,z,lx,ly,lz)."""
        pb = armature.pose.bones.get(name)
        if not pb:
            return
        mode = values[0]
        if mode == "EULER":
            rx, ry, rz = values[1], values[2], values[3]
            lx, ly, lz = values[4], values[5], values[6]
            pb.rotation_mode = 'XYZ'
            pb.rotation_euler = (math.radians(rx), math.radians(ry), math.radians(rz))
            if abs(lx) > 0.0001 or abs(ly) > 0.0001 or abs(lz) > 0.0001:
                pb.location = (lx, ly, lz)
        elif mode == "QUAT":
            w, x, y, z = values[1], values[2], values[3], values[4]
            lx, ly, lz = values[5], values[6], values[7]
            pb.rotation_mode = 'QUATERNION'
            pb.rotation_quaternion = (w, x, y, z)
            if abs(lx) > 0.0001 or abs(ly) > 0.0001 or abs(lz) > 0.0001:
                pb.location = (lx, ly, lz)

    # Apply universal pose first (legs, spine, head)
    for bone_name, values in UNIVERSAL_POSE.items():
        apply_bone_euler(bone_name, *values)

    # Per-character overrides (arms, fingers, adjusted legs)
    char_pose = CHARACTER_POSES.get(character_id)
    if char_pose:
        for bone_name, values in char_pose.items():
            apply_bone_pose(bone_name, values)
        print(f"  Applied {character_id}-specific pose ({len(char_pose)} bones)")
    else:
        # Fallback: generic arm pose (won't look perfect but usable)
        print(f"  WARNING: No pose data for {character_id}, using generic arm fallback")
        apply_bone_euler("upperarm.l", -60, 0, 0)
        apply_bone_euler("upperarm.r", -60, 0, 0)
        apply_bone_euler("lowerarm.l", -30, 0, 0)
        apply_bone_euler("lowerarm.r", -30, 0, 0)
        apply_bone_euler("hand.l", -10, 0, 0)
        apply_bone_euler("hand.r", -10, 0, 0)

    bpy.ops.object.mode_set(mode='OBJECT')

    # Parent to seat
    if seat:
        armature.parent = seat
        armature.matrix_parent_inverse = seat.matrix_world.inverted()

    # Export FBX (primary for Unity)
    os.makedirs(os.path.dirname(output_fbx), exist_ok=True)
    bpy.ops.object.select_all(action='SELECT')

    bpy.ops.export_scene.fbx(
        filepath=output_fbx,
        use_selection=True,
        apply_scale_options='FBX_SCALE_ALL',
        bake_anim=False,
        add_leaf_bones=False,
        path_mode='COPY',
        embed_textures=True,
    )

    # Export GLB (secondary for Blender reference)
    bpy.ops.export_scene.gltf(
        filepath=output_glb,
        export_format='GLB',
        use_selection=True,
        export_animations=False,
        export_skins=True,
    )

    fbx_sz = os.path.getsize(output_fbx)
    glb_sz = os.path.getsize(output_glb)
    print(f"  Exported: FBX={fbx_sz:,}B, GLB={glb_sz:,}B")
    return True


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    results = {}

    for char_id, kart_id in DRIVER_KART_MAP.items():
        kart_glb = f"{KART_DIR}/{kart_id}/{kart_id}_blender.glb"
        if not os.path.exists(kart_glb):
            print(f"SKIP {char_id}: kart {kart_glb} not found")
            results[char_id] = "skip_no_kart"
            continue

        char_glb = get_character_glb(char_id)
        if not os.path.exists(char_glb):
            print(f"SKIP {char_id}: character {char_glb} not found (needs autorig-ralph)")
            results[char_id] = "skip_no_character"
            continue

        output_fbx = f"{OUTPUT_DIR}/{char_id}_in_{kart_id}.fbx"
        output_glb = f"{OUTPUT_DIR}/{char_id}_in_{kart_id}.glb"

        print(f"\nAssembling: {char_id} -> {kart_id}")
        print(f"  Character: {char_glb}")
        print(f"  Kart: {kart_glb}")
        ok = assemble_one(char_id, kart_id, char_glb, kart_glb, output_fbx, output_glb)
        results[char_id] = "ok" if ok else "error"

    # Write batch report
    report = {
        "total": len(DRIVER_KART_MAP),
        "completed": sum(1 for v in results.values() if v == "ok"),
        "skipped_no_character": sum(1 for v in results.values() if v == "skip_no_character"),
        "results": results,
        "character_source": "autorig-ralph per-character rigged GLBs",
        "character_scale": CHARACTER_SCALE,
        "pose": "seated_driving (universal legs/spine + per-character arms)",
        "orientation": "kart hood = +Y, characters face +Y, no rotation needed",
    }
    report_path = f"{OUTPUT_DIR}/batch-report.json"
    with open(report_path, 'w') as f:
        json.dump(report, f, indent=2)
    print(f"\nBatch complete: {report['completed']}/{report['total']} "
          f"({report['skipped_no_character']} skipped, need rigging)")
    print(f"Report: {report_path}")


if __name__ == "__main__":
    main()
