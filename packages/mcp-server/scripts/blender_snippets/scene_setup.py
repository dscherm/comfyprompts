# Blender snippet: Set up a basic 3-point lighting + camera scene
# Parameters: none (or customize TARGET_HEIGHT for camera framing)
#
# Usage via blender-mcp:
#   execute_blender_code(code=snippet)

import bpy
import math

# Clear default objects
for obj in list(bpy.data.objects):
    if obj.type in {'LIGHT', 'CAMERA'}:
        bpy.data.objects.remove(obj, do_unlink=True)

# Find scene bounds from all mesh objects
from mathutils import Vector
all_corners = []
for obj in bpy.data.objects:
    if obj.type == 'MESH':
        all_corners.extend(obj.matrix_world @ Vector(c) for c in obj.bound_box)

if all_corners:
    min_co = Vector((min(v.x for v in all_corners), min(v.y for v in all_corners), min(v.z for v in all_corners)))
    max_co = Vector((max(v.x for v in all_corners), max(v.y for v in all_corners), max(v.z for v in all_corners)))
    center = (min_co + max_co) / 2
    size = max_co - min_co
    max_dim = max(size.x, size.y, size.z)
else:
    center = Vector((0, 0, 0))
    max_dim = 2.0

# Camera
cam_data = bpy.data.cameras.new("Camera")
cam_obj = bpy.data.objects.new("Camera", cam_data)
bpy.context.collection.objects.link(cam_obj)
bpy.context.scene.camera = cam_obj

cam_distance = max_dim * 2.5
cam_obj.location = (center.x + cam_distance * 0.7, center.y - cam_distance * 0.7, center.z + cam_distance * 0.5)

# Point camera at center
direction = center - cam_obj.location
rot_quat = direction.to_track_quat('-Z', 'Y')
cam_obj.rotation_euler = rot_quat.to_euler()

# Key light (warm, strong)
key_data = bpy.data.lights.new("Key_Light", type='AREA')
key_data.energy = 200 * (max_dim ** 2)
key_data.color = (1.0, 0.95, 0.9)
key_data.size = max_dim * 0.8
key_obj = bpy.data.objects.new("Key_Light", key_data)
bpy.context.collection.objects.link(key_obj)
key_obj.location = (center.x + max_dim * 1.5, center.y - max_dim * 1.0, center.z + max_dim * 1.5)
direction = center - key_obj.location
key_obj.rotation_euler = direction.to_track_quat('-Z', 'Y').to_euler()

# Fill light (cool, softer)
fill_data = bpy.data.lights.new("Fill_Light", type='AREA')
fill_data.energy = 80 * (max_dim ** 2)
fill_data.color = (0.85, 0.9, 1.0)
fill_data.size = max_dim * 1.2
fill_obj = bpy.data.objects.new("Fill_Light", fill_data)
bpy.context.collection.objects.link(fill_obj)
fill_obj.location = (center.x - max_dim * 1.2, center.y - max_dim * 0.5, center.z + max_dim * 0.8)
direction = center - fill_obj.location
fill_obj.rotation_euler = direction.to_track_quat('-Z', 'Y').to_euler()

# Rim light (backlight)
rim_data = bpy.data.lights.new("Rim_Light", type='SPOT')
rim_data.energy = 300 * (max_dim ** 2)
rim_data.color = (1.0, 1.0, 1.0)
rim_data.spot_size = math.radians(45)
rim_obj = bpy.data.objects.new("Rim_Light", rim_data)
bpy.context.collection.objects.link(rim_obj)
rim_obj.location = (center.x - max_dim * 0.3, center.y + max_dim * 1.5, center.z + max_dim * 1.2)
direction = center - rim_obj.location
rim_obj.rotation_euler = direction.to_track_quat('-Z', 'Y').to_euler()

# Set render settings
bpy.context.scene.render.engine = 'BLENDER_EEVEE_NEXT' if hasattr(bpy.types, 'ShaderNodeEeveeSpecular') else 'BLENDER_EEVEE'
bpy.context.scene.render.resolution_x = 1024
bpy.context.scene.render.resolution_y = 1024

print(f"SUCCESS: Scene setup complete — camera at {cam_obj.location}, 3 lights, targeting center {center}")
