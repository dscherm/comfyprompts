"""diag_hip_travel — measure the ACTUAL hip world travel of an animated FBX.

Companion to retarget_mocap.py's EXPECTED_TRAVEL line: batch_retarget compares
the two (direction error ~0 deg, magnitude ratio ~1) as the transfer-fidelity
gate. Replaces diag_facing's travel-vs-bind-facing "misalign", which is noise
for in-place clips and unreliable in general.

Prints: ACTUAL_TRAVEL <x> <y> <z> over the file's whole scene frame range.

Usage: blender --background --python diag_hip_travel.py -- <animated.fbx> [hips_name]
"""
import bpy
import sys

a = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
FBX = a[0]
HIPS = a[1] if len(a) > 1 else "hips"

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=FBX)
arm = next(o for o in bpy.data.objects if o.type == "ARMATURE")
sc = bpy.context.scene

hips = arm.pose.bones.get(HIPS)
if hips is None:  # fall back to the root bone
    hips = next((pb for pb in arm.pose.bones if pb.bone.parent is None), None)

sc.frame_set(sc.frame_start)
bpy.context.view_layer.update()
p0 = (arm.matrix_world @ hips.matrix).translation.copy()
sc.frame_set(sc.frame_end)
bpy.context.view_layer.update()
p1 = (arm.matrix_world @ hips.matrix).translation.copy()
tr = p1 - p0
print(f"ACTUAL_TRAVEL {tr.x:.4f} {tr.y:.4f} {tr.z:.4f}")
print(f"ACTUAL_FRAMES {sc.frame_start} {sc.frame_end}  HIPS {hips.name}")
