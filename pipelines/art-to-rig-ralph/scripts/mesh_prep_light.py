"""Light mesh prep: scale + center only. For meshes that fail aggressive cleanup."""
import bpy
import sys
import os

argv = sys.argv
if "--" in argv:
    argv = argv[argv.index("--") + 1:]
else:
    argv = []

import argparse
parser = argparse.ArgumentParser()
parser.add_argument("--input", required=True)
parser.add_argument("--output", required=True)
parser.add_argument("--target-height", type=float, default=1.7)
args = parser.parse_args(argv)

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=args.input)

mesh_objects = [o for o in bpy.data.objects if o.type == "MESH"]
if not mesh_objects:
    print("ERROR: No mesh objects")
    sys.exit(1)

obj = mesh_objects[0]
bpy.context.view_layer.objects.active = obj
obj.select_set(True)

# Join if multiple
if len(mesh_objects) > 1:
    for o in mesh_objects:
        o.select_set(True)
    bpy.ops.object.join()
    obj = bpy.context.active_object

print(f"Before: {len(obj.data.vertices)} verts, {len(obj.data.polygons)} faces")

# Scale
max_dim = max(obj.dimensions)
if max_dim > 0:
    sf = args.target_height / max_dim
    obj.scale = (sf, sf, sf)
    bpy.ops.object.transform_apply(scale=True)

# Center and ground
bpy.ops.object.origin_set(type="ORIGIN_GEOMETRY", center="BOUNDS")
lowest_z = min((obj.matrix_world @ v.co).z for v in obj.data.vertices)
obj.location.z -= lowest_z
bpy.ops.object.transform_apply(location=True)

print(f"After: {len(obj.data.vertices)} verts, {len(obj.data.polygons)} faces, dims={[round(d,3) for d in obj.dimensions]}")

os.makedirs(os.path.dirname(os.path.abspath(args.output)), exist_ok=True)
bpy.ops.export_scene.gltf(filepath=args.output, export_format="GLB", export_materials="EXPORT")
print(f"Exported: {args.output}")
