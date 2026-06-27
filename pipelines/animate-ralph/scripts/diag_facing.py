"""diag_facing.py — measure body facing vs root-motion travel for a retargeted FBX.

Facing is taken from the FEET (each foot bone's +Y axis = head->toe = forward), which
disambiguates front/back (toes point front) independent of travel direction, averaged
over the clip for robustness. Travel is the hips' horizontal world displacement.
Prints both angles (deg, world XY) and the signed misalignment.

Usage: blender --background --python diag_facing.py -- <animated.fbx>
"""
import bpy, sys, math
from mathutils import Vector

a = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
FBX = a[0]

bpy.ops.object.select_all(action='SELECT'); bpy.ops.object.delete()
bpy.ops.import_scene.fbx(filepath=FBX)
arm = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
sc = bpy.context.scene
f0, f1 = sc.frame_start, sc.frame_end

hip = arm.pose.bones.get("hips")
fl = arm.pose.bones.get("foot.l")
fr = arm.pose.bones.get("foot.r")


def yaxis(pb):
    return ((arm.matrix_world @ pb.matrix).to_3x3() @ Vector((0, 1, 0)))


fwd = Vector((0, 0, 0))
hip0 = hipN = None
for f in range(f0, f1 + 1):
    sc.frame_set(f)
    if fl and fr:
        v = yaxis(fl) + yaxis(fr)
        v.z = 0.0
        if v.length > 1e-6:
            fwd += v.normalized()
    p = (arm.matrix_world @ hip.matrix).translation.copy()
    if f == f0:
        hip0 = p
    hipN = p

fwd.z = 0.0
th_f = math.degrees(math.atan2(fwd.y, fwd.x)) if fwd.length > 1e-6 else float('nan')
tr = hipN - hip0
th_t = math.degrees(math.atan2(tr.y, tr.x))
delta = (th_t - th_f + 180.0) % 360.0 - 180.0   # signed, [-180,180]

print(f"FACING_DEG {th_f:.1f}  (feet-forward XY)")
print(f"TRAVEL_DEG {th_t:.1f}  len={tr.length:.3f}  vec=({tr.x:.3f},{tr.y:.3f},{tr.z:.3f})")
print(f"MISALIGN_DEG {delta:.1f}  (travel - facing; 0 = faces its travel)")
