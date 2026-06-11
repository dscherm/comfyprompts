"""Blender headless mesh preparation script for kart/character GLBs.

Usage:
    blender --background --python mesh_prep.py -- \
        --input path/to/raw.glb \
        --output path/to/prepared.glb \
        --target-height 0.7 \
        --max-faces 20000
"""

import bpy
import bmesh
import json
import sys
import os
from mathutils import Vector

# Parse args after "--"
argv = sys.argv
if "--" in argv:
    argv = argv[argv.index("--") + 1:]
else:
    argv = []

import argparse
parser = argparse.ArgumentParser()
parser.add_argument("--input", required=True)
parser.add_argument("--output", required=True)
parser.add_argument("--report", default=None)
parser.add_argument("--target-height", type=float, default=0.7)
parser.add_argument("--max-faces", type=int, default=20000)
parser.add_argument("--target-faces", type=int, default=None)
args = parser.parse_args(argv)

if args.target_faces is None:
    args.target_faces = args.max_faces

ops_log = []

# 1. Clear and import
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=args.input)

# Find mesh objects
mesh_objects = [o for o in bpy.data.objects if o.type == "MESH"]
if not mesh_objects:
    print("ERROR: No mesh objects found in", args.input)
    sys.exit(1)

print(f"Found {len(mesh_objects)} mesh object(s)")

# Deselect all first, then select mesh objects
bpy.ops.object.select_all(action="DESELECT")

# Set the first mesh object as active
obj = mesh_objects[0]
bpy.context.view_layer.objects.active = obj
obj.select_set(True)

# Join if multiple
if len(mesh_objects) > 1:
    for o in mesh_objects:
        o.select_set(True)
    bpy.ops.object.join()
    ops_log.append({"op": "join_meshes", "objects_joined": len(mesh_objects)})
    obj = bpy.context.active_object

print(f"Active object: {obj.name}, type: {obj.type}")

# Record before metrics
before_verts = len(obj.data.vertices)
before_faces = len(obj.data.polygons)
before_bbox = list(obj.dimensions)
print(f"Before: {before_verts} verts, {before_faces} faces, bbox {before_bbox}")

# 2. Remove doubles
bpy.ops.object.mode_set(mode="EDIT")
bpy.ops.mesh.select_all(action="SELECT")
bpy.ops.mesh.remove_doubles(threshold=0.001)
bpy.ops.object.mode_set(mode="OBJECT")
merged = before_verts - len(obj.data.vertices)
ops_log.append({"op": "remove_doubles", "vertices_merged": merged})
print(f"Remove doubles: merged {merged} vertices")

# 3. Fill holes (only if <50% of verts are non-manifold, otherwise skip — mesh is just rough)
bpy.ops.object.mode_set(mode="EDIT")
bpy.ops.mesh.select_all(action="DESELECT")
bpy.ops.mesh.select_non_manifold()
non_manifold_before = sum(1 for v in obj.data.vertices if v.select)
total_verts = len(obj.data.vertices)
if 0 < non_manifold_before < total_verts * 0.5:
    bpy.ops.mesh.fill_holes(sides=32)
    ops_log.append({"op": "fill_holes", "non_manifold_verts_before": non_manifold_before})
    print(f"Fill holes: {non_manifold_before} non-manifold verts addressed")
else:
    bpy.ops.mesh.select_all(action="DESELECT")
    ops_log.append({"op": "fill_holes", "skipped": True,
                    "reason": f"{non_manifold_before}/{total_verts} non-manifold (too many, skip)"})
    print(f"Fill holes: SKIPPED ({non_manifold_before}/{total_verts} non-manifold)")
bpy.ops.object.mode_set(mode="OBJECT")

# 4. Recalculate normals
bpy.ops.object.mode_set(mode="EDIT")
bpy.ops.mesh.select_all(action="SELECT")
bpy.ops.mesh.normals_make_consistent(inside=False)
bpy.ops.object.mode_set(mode="OBJECT")
ops_log.append({"op": "normals_recalc"})

# 5. Remove degenerate geometry
bpy.ops.object.mode_set(mode="EDIT")
bpy.ops.mesh.select_all(action="SELECT")
bpy.ops.mesh.dissolve_degenerate(threshold=0.0001)
bpy.ops.object.mode_set(mode="OBJECT")
degen_removed = before_faces - len(obj.data.polygons)
ops_log.append({"op": "dissolve_degenerate", "faces_removed": max(0, degen_removed)})

# 6. Remove floating geometry (islands < 1% of total faces)
bpy.ops.object.mode_set(mode="EDIT")
bm = bmesh.from_edit_mesh(obj.data)
bm.verts.ensure_lookup_table()
bm.faces.ensure_lookup_table()

total_faces = len(bm.faces)
threshold = max(10, int(total_faces * 0.01))

# Find connected components via flood fill
visited = set()
islands = []
for v in bm.verts:
    if v.index in visited:
        continue
    island = set()
    stack = [v]
    while stack:
        current = stack.pop()
        if current.index in visited:
            continue
        visited.add(current.index)
        island.add(current.index)
        for edge in current.link_edges:
            other = edge.other_vert(current)
            if other.index not in visited:
                stack.append(other)
    islands.append(island)

# Sort by size, remove small ones
islands.sort(key=len, reverse=True)
removed_count = 0
removed_faces = 0
if len(islands) > 1:
    for island in islands[1:]:
        if len(island) < threshold:
            for vi in island:
                bm.verts[vi].select = True
            removed_count += 1
            removed_faces += len(island)

    if removed_count > 0:
        bpy.ops.mesh.delete(type="VERT")
        bm = bmesh.from_edit_mesh(obj.data)

ops_log.append({"op": "remove_floating", "islands_found": len(islands),
                "islands_removed": removed_count, "verts_removed": removed_faces})
print(f"Islands: {len(islands)} found, {removed_count} removed ({removed_faces} verts)")

bpy.ops.object.mode_set(mode="OBJECT")

# 7. Decimation if needed
current_faces = len(obj.data.polygons)
if current_faces > args.max_faces:
    ratio = args.target_faces / current_faces
    mod = obj.modifiers.new(name="Decimate", type="DECIMATE")
    mod.ratio = ratio
    bpy.ops.object.modifier_apply(modifier="Decimate")
    after_decimate = len(obj.data.polygons)
    ops_log.append({"op": "decimation", "before_faces": current_faces,
                    "after_faces": after_decimate, "ratio": round(ratio, 3)})
    print(f"Decimated: {current_faces} -> {after_decimate} faces (ratio {ratio:.3f})")

# 8. Scale to target dimensions
current_height = obj.dimensions.z
if current_height > 0:
    # For karts, target height is the Y dimension (height of the kart)
    # Use the largest dimension for scaling reference
    max_dim = max(obj.dimensions)
    scale_factor = args.target_height / max_dim
    obj.scale = (scale_factor, scale_factor, scale_factor)
    bpy.ops.object.transform_apply(scale=True)
    ops_log.append({"op": "scale", "target_height_m": args.target_height,
                    "scale_factor": round(scale_factor, 4)})
    print(f"Scaled: factor {scale_factor:.4f}, new dims {list(obj.dimensions)}")

# 9. Center and ground
if len(obj.data.vertices) > 0:
    bpy.ops.object.origin_set(type="ORIGIN_GEOMETRY", center="BOUNDS")
    lowest_z = min((obj.matrix_world @ v.co).z for v in obj.data.vertices)
    obj.location.z -= lowest_z
    bpy.ops.object.transform_apply(location=True)
    ops_log.append({"op": "center_ground", "z_offset": round(-lowest_z, 4)})
else:
    print("WARNING: No vertices remaining after cleanup")
    ops_log.append({"op": "center_ground", "skipped": True, "reason": "no vertices"})

# 10. Apply all transforms
bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)

# Final metrics
after_verts = len(obj.data.vertices)
after_faces = len(obj.data.polygons)
after_bbox = [round(d, 4) for d in obj.dimensions]

# Check manifold
bpy.ops.object.mode_set(mode="EDIT")
bpy.ops.mesh.select_all(action="DESELECT")
bpy.ops.mesh.select_non_manifold()
non_manifold_after = sum(1 for v in obj.data.vertices if v.select)
bpy.ops.object.mode_set(mode="OBJECT")

print(f"After: {after_verts} verts, {after_faces} faces, bbox {after_bbox}")
print(f"Non-manifold edges: {non_manifold_after}")

# Export
os.makedirs(os.path.dirname(os.path.abspath(args.output)), exist_ok=True)
bpy.ops.export_scene.gltf(
    filepath=args.output,
    export_format="GLB",
    export_materials="EXPORT",
)
print(f"Exported to {args.output}")

# Write report
report = {
    "source": args.input,
    "output": args.output,
    "operations": ops_log,
    "before": {
        "vertices": before_verts,
        "faces": before_faces,
        "bounding_box": before_bbox,
    },
    "after": {
        "vertices": after_verts,
        "faces": after_faces,
        "bounding_box": after_bbox,
        "non_manifold_verts": non_manifold_after,
        "is_manifold": non_manifold_after == 0,
    },
}

report_path = args.report or args.output.replace(".glb", "_report.json")
with open(report_path, "w") as f:
    json.dump(report, f, indent=2)
print(f"Report: {report_path}")
