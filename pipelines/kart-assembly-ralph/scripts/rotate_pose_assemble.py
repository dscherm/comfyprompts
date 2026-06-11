"""
Rotate UniRig-skinned character to face -Y, apply driving pose, assemble into kart.
Run via headless Blender:
    blender --background --python rotate_pose_assemble.py
"""
import bpy
import math
import os
from mathutils import Vector


# Clear
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete()
for d in [bpy.data.armatures, bpy.data.meshes, bpy.data.materials, bpy.data.images, bpy.data.actions]:
    for item in list(d):
        d.remove(item)

# Import UniRig-skinned FBX
bpy.ops.import_scene.fbx(
    filepath="D:/Projects/comfyui-toolchain/pipelines/character-ralph/output/rigged/character-unirig-skinned.fbx"
)
bpy.context.view_layer.update()

armature = [o for o in bpy.data.objects if o.type == 'ARMATURE'][0]
char_mesh = [o for o in bpy.data.objects if o.type == 'MESH' and len(o.data.vertices) > 50][0]

print(f"Imported: {armature.name} ({len(armature.data.bones)} bones), {char_mesh.name} ({len(char_mesh.data.vertices)} verts)")

# Rotate armature 180Z (mesh follows as child)
armature.rotation_euler.z = math.radians(180)
bpy.ops.object.select_all(action='DESELECT')
armature.select_set(True)
bpy.context.view_layer.objects.active = armature
bpy.ops.object.transform_apply(rotation=True)
bpy.context.view_layer.update()

# Scale 0.8
armature.scale = (0.8, 0.8, 0.8)
bpy.ops.object.transform_apply(scale=True)

# Verify facing
vw = [char_mesh.matrix_world @ v.co for v in char_mesh.data.vertices]
h = max(v.z for v in vw) - min(v.z for v in vw)
min_z = min(v.z for v in vw)
head = [v for v in vw if v.z > min_z + h * 0.85]
body = [v for v in vw if min_z + h * 0.3 < v.z < min_z + h * 0.6]
hy = sum(v.y for v in head) / len(head)
by = sum(v.y for v in body) / len(body)
print(f"Facing: head_y={hy:.3f} body_y={by:.3f} -> {'MINUS_Y (correct)' if hy < by else 'PLUS_Y (needs fix)'}")

# Pose legs + spine via Euler
bpy.ops.object.mode_set(mode='POSE')
for name, (rx, ry, rz) in {
    "bone_2": (-15, 0, 0), "bone_3": (-10, 0, 0),
    "bone_4": (5, 0, 0), "bone_5": (15, 0, 0),
    "bone_44": (-90, 0, 0), "bone_45": (90, 0, 0), "bone_46": (-30, 0, 0),
    "bone_48": (-90, 0, 0), "bone_49": (90, 0, 0), "bone_50": (-30, 0, 0),
}.items():
    pb = armature.pose.bones.get(name)
    if pb:
        pb.rotation_mode = 'XYZ'
        pb.rotation_euler = (math.radians(rx), math.radians(ry), math.radians(rz))
bpy.ops.object.mode_set(mode='OBJECT')

# IK for arms — targets at steering wheel position
# After 180Z rotation, character forward is now -Y
# Hands should reach toward -Y (forward)
bpy.ops.object.empty_add(type='PLAIN_AXES', location=(0.15, -0.6, 0.45))
bpy.context.active_object.name = 'IK_R'
bpy.ops.object.empty_add(type='PLAIN_AXES', location=(-0.15, -0.6, 0.45))
bpy.context.active_object.name = 'IK_L'

bpy.ops.object.select_all(action='DESELECT')
armature.select_set(True)
bpy.context.view_layer.objects.active = armature
bpy.ops.object.mode_set(mode='POSE')
for bn, tn in [("bone_9", "IK_R"), ("bone_28", "IK_L")]:
    pb = armature.pose.bones.get(bn)
    tgt = bpy.data.objects.get(tn)
    if pb and tgt:
        ik = pb.constraints.new('IK')
        ik.target = tgt
        ik.chain_count = 3
        ik.iterations = 200
bpy.ops.object.mode_set(mode='OBJECT')
bpy.context.view_layer.update()

# Export rotated+posed character as GLB
out_glb = "D:/Projects/comfyui-toolchain/pipelines/character-ralph/output/rigged/character-posed-facing-minusY.glb"
bpy.ops.object.select_all(action='SELECT')
bpy.ops.export_scene.gltf(
    filepath=out_glb, export_format='GLB',
    use_selection=True, export_animations=False, export_skins=True
)
print(f"Posed character exported: {os.path.getsize(out_glb):,} bytes")

# Now import kart and assemble
bpy.ops.import_scene.gltf(
    filepath="D:/Projects/comfyui-toolchain/pipelines/art-to-rig-ralph/output/final/player_kart/player_kart_blender.glb"
)
bpy.context.view_layer.update()

# Find seat
seat_pos = Vector((0.0185, 0.148, 0.538))
for obj in bpy.data.objects:
    if 'seat' in obj.name.lower() and obj.type == 'EMPTY':
        seat_pos = obj.matrix_world.translation.copy()
        break

# Position hips at seat
hips = armature.data.bones[0]
bpy.context.view_layer.update()
hips_world = armature.matrix_world @ hips.head_local
offset = seat_pos - hips_world
offset.z += 0.02
armature.location += offset

# Move IK targets relative to kart steering column
steer_pos = Vector((0.018, -0.342, 0.538))
for obj in bpy.data.objects:
    if 'steeringcolumn' in obj.name.lower().replace('_', '') and obj.type == 'EMPTY':
        steer_pos = obj.matrix_world.translation.copy()
        break

ik_r = bpy.data.objects.get('IK_R')
ik_l = bpy.data.objects.get('IK_L')
if ik_r:
    ik_r.location = (steer_pos.x + 0.12, steer_pos.y, steer_pos.z + 0.05)
if ik_l:
    ik_l.location = (steer_pos.x - 0.12, steer_pos.y, steer_pos.z + 0.05)

bpy.context.view_layer.update()

# Export assembly
out_dir = "D:/Projects/comfyui-toolchain/pipelines/kart-assembly-ralph/output"
os.makedirs(out_dir, exist_ok=True)

bpy.ops.object.select_all(action='SELECT')
bpy.ops.export_scene.gltf(
    filepath=out_dir + "/player_in_kart_v2.glb",
    export_format='GLB', use_selection=True,
    export_animations=False, export_skins=True
)

bpy.ops.export_scene.fbx(
    filepath=out_dir + "/player_in_kart_v2.fbx",
    use_selection=True, apply_scale_options='FBX_SCALE_ALL',
    bake_anim=False, add_leaf_bones=False
)

print(f"Assembly GLB: {os.path.getsize(out_dir + '/player_in_kart_v2.glb'):,} bytes")
print(f"Assembly FBX: {os.path.getsize(out_dir + '/player_in_kart_v2.fbx'):,} bytes")
print("ASSEMBLY_COMPLETE")
