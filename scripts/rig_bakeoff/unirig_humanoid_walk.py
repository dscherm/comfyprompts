"""Procedural walk cycle for a UniRig GENERIC humanoid skeleton (bone_N names).

Closes the bake-off's evidence gap: UniRig has no humanoid animation path (its
generic skeleton has no clip library, and cross-skeleton retargeting is this
project's documented failure zone), so its lane was judged on STATIC poses —
exactly the evidence lessons/unirig-skin-weights-melt-use-accurig.md says
HIDES weight melt ("static poses hide weight problems; render mid-motion frames
from front AND side at bent joints").

This builds a real walk on UniRig's own bones using the technique proven on the
bestiary quads (quad_anim_v2.py): identify limbs by WORLD POSITION (UniRig bone
names carry no semantics), and rotate around WORLD axes via quaternion (UniRig
bone-local axes are arbitrary).

Usage:
    blender --background --factory-startup --python unirig_humanoid_walk.py \\
        -- <rigged.glb> <out.glb> [frames]
"""

from __future__ import annotations

import math
import sys

import bpy
from mathutils import Quaternion, Vector

argv = sys.argv[sys.argv.index("--") + 1 :]
SRC, DST = argv[0], argv[1]
FRAMES = int(argv[2]) if len(argv) > 2 else 24

STRIDE = math.radians(28)      # thigh fore/aft swing
KNEE = math.radians(50)        # knee bend during swing (the melt diagnostic)
ARM = math.radians(18)         # counter-swing
BOB = 0.018                    # root vertical bob (metres), 2x cadence

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=SRC)

arm_obj = next(o for o in bpy.data.objects if o.type == "ARMATURE")
arm_obj.animation_data_clear()
bones = arm_obj.pose.bones


def wh(pb) -> Vector:
    """World-space head of a pose bone's rest bone."""
    return arm_obj.matrix_world @ pb.bone.head_local


def axis_in_bone(pb, world_vec: Vector) -> Vector:
    """Express a WORLD axis in the bone's local space (UniRig axes are arbitrary)."""
    R = (arm_obj.matrix_world @ pb.bone.matrix_local).to_3x3()
    return (R.inverted() @ world_vec).normalized()


H = {pb.name: wh(pb) for pb in bones}
zs = [v.z for v in H.values()]
z_min, z_max = min(zs), max(zs)
height = z_max - z_min
xs = [v.x for v in H.values()]
cx = (min(xs) + max(xs)) / 2

root = next((pb for pb in bones if pb.parent is None), None)
if root is None:
    print("ERROR: no root bone", file=sys.stderr)
    sys.exit(1)

# --- legs, STRUCTURALLY: a thigh is a child of the root that descends (the
# spine is the child that ascends). Then calf/foot follow down the chain.
# NOT "lowest bone, trace up" — that finds the TOE and shifts the whole chain
# by one (thigh:=calf, knee:=ankle), which silently animates the wrong joints.
legs = []
for child in root.children:
    if H[child.name].z >= H[root.name].z:
        continue                      # ascending -> spine, not a leg
    thigh = child
    calf = thigh.children[0] if thigh.children else None
    foot = calf.children[0] if calf and calf.children else None
    if not (calf and foot):
        continue
    legs.append({"thigh": thigh, "calf": calf, "foot": foot,
                 "left": H[thigh.name].x >= cx})

# --- upper arms, STRUCTURALLY: walk up from each side's most-lateral bone
# (a fingertip) until the PARENT sits near the body centre — that parent is the
# clavicle, so the bone itself is the upperarm.
arms = []
for side_is_left in (True, False):
    side_bones = [pb for pb in bones
                  if (H[pb.name].x >= cx) == side_is_left
                  and H[pb.name].z > z_min + height * 0.50]
    if not side_bones:
        continue
    node = max(side_bones, key=lambda pb: abs(H[pb.name].x - cx))
    upperarm = None
    while node.parent is not None:
        if abs(H[node.parent.name].x - cx) < height * 0.06:
            upperarm = node
            break
        node = node.parent
    if upperarm:
        arms.append({"upperarm": upperarm, "left": side_is_left})

print("IDENTIFIED legs:", [(l["thigh"].name, l["calf"].name, l["foot"].name, "L" if l["left"] else "R") for l in legs])
print("IDENTIFIED arms:", [(a["upperarm"].name, "L" if a["left"] else "R") for a in arms])
print("IDENTIFIED root:", root.name if root else None)
if len(legs) != 2:
    print(f"ERROR: found {len(legs)} leg chains, need 2", file=sys.stderr)
    sys.exit(1)

SIDE = Vector((1.0, 0.0, 0.0))   # character faces -Y; left-right is world X
UP = Vector((0.0, 0.0, 1.0))

for pb in bones:
    pb.rotation_mode = "QUATERNION"
    pb.rotation_quaternion = Quaternion()
    pb.location = (0.0, 0.0, 0.0)

action = bpy.data.actions.new("walk")
arm_obj.animation_data_create()
arm_obj.animation_data.action = action

for f in range(FRAMES + 1):
    t = f / FRAMES
    th_base = 2 * math.pi * t

    for leg in legs:
        phase = 0.0 if leg["left"] else math.pi
        th = th_base + phase
        swing = STRIDE * math.sin(th)
        bend = KNEE * max(0.0, math.cos(th))   # knee bends through the swing phase
        leg["thigh"].rotation_quaternion = Quaternion(axis_in_bone(leg["thigh"], SIDE), swing)
        leg["calf"].rotation_quaternion = Quaternion(axis_in_bone(leg["calf"], SIDE), -bend)

    for a in arms:
        phase = math.pi if a["left"] else 0.0   # arms counter-swing vs same-side leg
        a["upperarm"].rotation_quaternion = Quaternion(
            axis_in_bone(a["upperarm"], SIDE), ARM * math.sin(th_base + phase))

    if root:
        root.location = (0.0, 0.0, BOB * math.sin(2 * th_base))
        root.keyframe_insert("location", frame=f)

    for pb in bones:
        pb.keyframe_insert("rotation_quaternion", frame=f)

bpy.context.scene.frame_start = 0
bpy.context.scene.frame_end = FRAMES

track = arm_obj.animation_data.nla_tracks.new()
track.name = "walk"
track.strips.new("walk", 0, action)
arm_obj.animation_data.action = None

bpy.ops.export_scene.gltf(filepath=DST, export_format="GLB", export_yup=True,
                          export_animations=True, export_nla_strips=True)
print("EXPORTED", DST, f"({FRAMES} frames)")
