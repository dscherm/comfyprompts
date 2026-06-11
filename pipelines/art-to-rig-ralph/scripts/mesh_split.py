"""Blender headless mesh split script for kart GLBs.

Splits a single kart mesh GLB into separate region objects based on
bounding-box fraction analysis, then exports the split hierarchy as GLB.

Usage (headless):
    blender --background --python mesh_split.py -- \
        --input path/to/prepared.glb \
        --output path/to/split.glb \
        --report path/to/split_report.json

Usage (blender-mcp execute_blender_code):
    exec(open('mesh_split.py').read())
    # Set INPUT/OUTPUT/REPORT_PATH module-level vars before exec, or pass via sys.argv.

Region priority order (first match wins):
    Bumper_Front, Bumper_Rear, Hood, Spoiler, Panel_L, Panel_R, Chassis
"""

import bpy
import bmesh
import json
import sys
import os
import argparse
from mathutils import Vector

# ---------------------------------------------------------------------------
# Argument parsing — works both headless and interactive
# ---------------------------------------------------------------------------

argv = sys.argv
if "--" in argv:
    argv = argv[argv.index("--") + 1:]
else:
    argv = []

parser = argparse.ArgumentParser(description="Split kart mesh GLB into regions")
parser.add_argument("--input", required=True, help="Path to prepared input GLB")
parser.add_argument("--output", required=True, help="Path to write split GLB")
parser.add_argument("--report", default=None, help="Path to write JSON report (default: <output>_report.json)")
args = parser.parse_args(argv)

# ---------------------------------------------------------------------------
# Region definitions
# Each entry: (name, length_min, length_max, width_min, width_max, height_min, height_max)
# Process in this order — first match wins per vertex.
# ---------------------------------------------------------------------------

REGION_DEFS = [
    ("Bumper_Front", 0.90, 1.00,  0.10, 0.90,  0.00, 0.40),
    ("Bumper_Rear",  0.00, 0.10,  0.10, 0.90,  0.00, 0.40),
    ("Hood",         0.75, 1.00,  0.15, 0.85,  0.30, 1.00),
    ("Spoiler",      0.00, 0.15,  0.15, 0.85,  0.60, 1.00),
    ("Panel_L",      0.15, 0.85,  0.00, 0.15,  0.20, 0.80),
    ("Panel_R",      0.15, 0.85,  0.85, 1.00,  0.20, 0.80),
    ("Chassis",      0.00, 1.00,  0.00, 1.00,  0.00, 1.00),  # catch-all
]

MIN_REGION_VERTS = 10
MIN_INPUT_FACES = 100

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def get_world_vertices(obj):
    """Return list of world-space vertex coordinates."""
    mw = obj.matrix_world
    return [mw @ v.co for v in obj.data.vertices]


def compute_bounding_box(world_verts):
    """Return (min_co, max_co) as Vector tuples."""
    xs = [v.x for v in world_verts]
    ys = [v.y for v in world_verts]
    zs = [v.z for v in world_verts]
    return (
        Vector((min(xs), min(ys), min(zs))),
        Vector((max(xs), max(ys), max(zs))),
    )


def detect_axes(bb_min, bb_max):
    """Detect length/width/height axes from bounding box extents.

    Returns (length_axis, width_axis, height_axis) as integer indices 0/1/2.
    length = longest extent, height = shortest extent.
    """
    extents = [bb_max[i] - bb_min[i] for i in range(3)]
    sorted_axes = sorted(range(3), key=lambda i: extents[i], reverse=True)
    length_axis = sorted_axes[0]   # longest
    width_axis  = sorted_axes[1]   # second-longest
    height_axis = sorted_axes[2]   # shortest
    return length_axis, width_axis, height_axis


def normalize_coord(value, axis_min, axis_max):
    """Normalize a coordinate to [0, 1] given axis bounds."""
    span = axis_max - axis_min
    if span < 1e-9:
        return 0.5
    return (value - axis_min) / span


def vertex_in_region(nL, nW, nH, region):
    """Return True if normalized coords fall within region bounds."""
    _, lmin, lmax, wmin, wmax, hmin, hmax = region
    return (lmin <= nL <= lmax and
            wmin <= nW <= wmax and
            hmin <= nH <= hmax)


def set_origin_to_bbox_center(obj):
    """Move object origin to its bounding-box center."""
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.ops.object.origin_set(type="ORIGIN_GEOMETRY", center="BOUNDS")


def bbox_of_object(obj):
    """Return dict with min/max/size for an object in world space."""
    verts = get_world_vertices(obj)
    if not verts:
        return None
    bb_min, bb_max = compute_bounding_box(verts)
    return {
        "min": [round(bb_min.x, 5), round(bb_min.y, 5), round(bb_min.z, 5)],
        "max": [round(bb_max.x, 5), round(bb_max.y, 5), round(bb_max.z, 5)],
        "size": [round(bb_max.x - bb_min.x, 5),
                 round(bb_max.y - bb_min.y, 5),
                 round(bb_max.z - bb_min.z, 5)],
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

log = []


def log_info(msg):
    print(f"[mesh_split] {msg}")
    log.append({"level": "INFO", "msg": msg})


def log_warn(msg):
    print(f"[mesh_split] WARNING: {msg}")
    log.append({"level": "WARNING", "msg": msg})


# 1. Clear and import
bpy.ops.wm.read_factory_settings(use_empty=True)
log_info(f"Importing {args.input}")
bpy.ops.import_scene.gltf(filepath=args.input)

mesh_objects = [o for o in bpy.data.objects if o.type == "MESH"]
if not mesh_objects:
    print(f"ERROR: No mesh objects found in {args.input}")
    sys.exit(1)

log_info(f"Found {len(mesh_objects)} mesh object(s)")

# 2. Join all meshes into one
bpy.ops.object.select_all(action="DESELECT")
for o in mesh_objects:
    o.select_set(True)
bpy.context.view_layer.objects.active = mesh_objects[0]

if len(mesh_objects) > 1:
    bpy.ops.object.join()
    log_info(f"Joined {len(mesh_objects)} objects into one")

source = bpy.context.active_object
source.name = "KartMesh_Source"

# Apply all transforms before analysis
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)

total_faces = len(source.data.polygons)
total_verts = len(source.data.vertices)
log_info(f"Source mesh: {total_verts} verts, {total_faces} faces")

# 3. Graceful degradation — too few faces, skip splitting
if total_faces < MIN_INPUT_FACES:
    log_warn(
        f"Input mesh has only {total_faces} faces (minimum {MIN_INPUT_FACES}). "
        "Skipping split, renaming to Chassis."
    )
    source.name = "Chassis"
    set_origin_to_bbox_center(source)

    os.makedirs(os.path.dirname(os.path.abspath(args.output)), exist_ok=True)
    bpy.ops.export_scene.gltf(filepath=args.output, export_format="GLB", export_materials="EXPORT")
    log_info(f"Exported (no-split fallback) to {args.output}")

    report = {
        "source": args.input,
        "output": args.output,
        "split_performed": False,
        "reason": f"too_few_faces ({total_faces} < {MIN_INPUT_FACES})",
        "log": log,
        "regions": {"Chassis": {"vertices": total_verts, "faces": total_faces,
                                "bbox": bbox_of_object(source)}},
    }
    report_path = args.report or args.output.replace(".glb", "_report.json")
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2)
    log_info(f"Report: {report_path}")
    sys.exit(0)

# 4. Bounding box and axis detection
world_verts = get_world_vertices(source)
bb_min, bb_max = compute_bounding_box(world_verts)
length_axis, width_axis, height_axis = detect_axes(bb_min, bb_max)

axis_names = ["X", "Y", "Z"]
log_info(
    f"Axes detected — length:{axis_names[length_axis]} "
    f"width:{axis_names[width_axis]} "
    f"height:{axis_names[height_axis]}"
)
log_info(f"Bounding box min:{list(bb_min)} max:{list(bb_max)}")

# 5. Assign each vertex to a region (priority order, first match wins)
# vertex_region[vert_index] = region_name
vertex_region = {}

for vi, wv in enumerate(world_verts):
    nL = normalize_coord(wv[length_axis], bb_min[length_axis], bb_max[length_axis])
    nW = normalize_coord(wv[width_axis],  bb_min[width_axis],  bb_max[width_axis])
    nH = normalize_coord(wv[height_axis], bb_min[height_axis], bb_max[height_axis])

    for region in REGION_DEFS:
        if vertex_in_region(nL, nW, nH, region):
            vertex_region[vi] = region[0]
            break

# 6. Count vertices per region
from collections import defaultdict
region_verts = defaultdict(set)
for vi, rname in vertex_region.items():
    region_verts[rname].add(vi)

log_info("Vertex counts per region before merge-back:")
for rdef in REGION_DEFS:
    rname = rdef[0]
    count = len(region_verts.get(rname, set()))
    log_info(f"  {rname}: {count} verts")

# 7. Merge regions with fewer than MIN_REGION_VERTS into Chassis
for rdef in REGION_DEFS:
    rname = rdef[0]
    if rname == "Chassis":
        continue
    vcount = len(region_verts.get(rname, set()))
    if 0 < vcount < MIN_REGION_VERTS:
        log_warn(
            f"Region {rname} has only {vcount} vertices (< {MIN_REGION_VERTS}), "
            "merging back into Chassis."
        )
        for vi in list(region_verts.get(rname, set())):
            vertex_region[vi] = "Chassis"
        if rname in region_verts:
            region_verts["Chassis"].update(region_verts.pop(rname))

# Recompute final region sets after merge-back
region_verts = defaultdict(set)
for vi, rname in vertex_region.items():
    region_verts[rname].add(vi)

active_regions = [r for r in region_verts if len(region_verts[r]) >= MIN_REGION_VERTS]
log_info(f"Active regions after merge-back: {active_regions}")

# ---------------------------------------------------------------------------
# 8. Separate faces into new objects per region
#    Strategy: duplicate source for each region, delete unwanted faces.
#    We do one region at a time for checkpointing.
# ---------------------------------------------------------------------------

# Build face->region mapping.
# A face belongs to a region if the majority of its vertices belong to that region.
# We use the mode (most common region among face verts).

source.data.calc_loop_triangles()
face_region = {}
for poly in source.data.polygons:
    vert_regions = [vertex_region.get(vi, "Chassis") for vi in poly.vertices]
    # Find the majority region for this face
    counts = defaultdict(int)
    for r in vert_regions:
        counts[r] += 1
    dominant = max(counts, key=lambda r: counts[r])
    face_region[poly.index] = dominant

# Count faces per region
region_faces = defaultdict(set)
for fi, rname in face_region.items():
    region_faces[rname].add(fi)

log_info("Face counts per region:")
for rname in active_regions:
    log_info(f"  {rname}: {len(region_faces.get(rname, set()))} faces")

# ---------------------------------------------------------------------------
# Separate using bmesh: for each region, duplicate source and delete
# all faces that don't belong to that region.
# ---------------------------------------------------------------------------

result_objects = {}

for rname in active_regions:
    target_faces = region_faces.get(rname, set())
    if not target_faces:
        log_warn(f"Region {rname}: no faces, skipping object creation.")
        continue

    log_info(f"Creating object for region: {rname} ({len(target_faces)} faces)")

    # Duplicate source object
    bpy.ops.object.select_all(action="DESELECT")
    source.select_set(True)
    bpy.context.view_layer.objects.active = source
    bpy.ops.object.duplicate(linked=False)
    region_obj = bpy.context.active_object
    region_obj.name = rname

    # Enter edit mode on the duplicate
    bpy.ops.object.mode_set(mode="EDIT")
    bm = bmesh.from_edit_mesh(region_obj.data)
    bm.faces.ensure_lookup_table()

    # Select faces that do NOT belong to this region
    faces_to_delete = [f for f in bm.faces if f.index not in target_faces]
    for f in faces_to_delete:
        f.select = True
    for f in bm.faces:
        if f.index in target_faces:
            f.select = False

    # Delete unwanted faces
    bmesh.ops.delete(bm, geom=faces_to_delete, context="FACES")
    bmesh.update_edit_mesh(region_obj.data)

    bpy.ops.object.mode_set(mode="OBJECT")

    # Remove loose vertices/edges left after face deletion
    bpy.ops.object.mode_set(mode="EDIT")
    bm2 = bmesh.from_edit_mesh(region_obj.data)
    # Remove verts with no linked faces
    loose_verts = [v for v in bm2.verts if len(v.link_faces) == 0]
    bmesh.ops.delete(bm2, geom=loose_verts, context="VERTS")
    bmesh.update_edit_mesh(region_obj.data)
    bpy.ops.object.mode_set(mode="OBJECT")

    final_v = len(region_obj.data.vertices)
    final_f = len(region_obj.data.polygons)

    if final_f == 0:
        log_warn(f"Region {rname}: resulted in 0 faces after separation, removing object.")
        bpy.data.objects.remove(region_obj, do_unlink=True)
        continue

    log_info(f"  {rname}: {final_v} verts, {final_f} faces after separation")

    # Set origin to bounding box center
    set_origin_to_bbox_center(region_obj)

    result_objects[rname] = region_obj

# Remove the source object (no longer needed)
bpy.data.objects.remove(source, do_unlink=True)

if not result_objects:
    log_warn("No regions were successfully created. Falling back: re-importing as Chassis.")
    bpy.ops.import_scene.gltf(filepath=args.input)
    fallback = bpy.context.active_object
    fallback.name = "Chassis"
    set_origin_to_bbox_center(fallback)
    result_objects["Chassis"] = fallback

log_info(f"Final objects: {list(result_objects.keys())}")

# ---------------------------------------------------------------------------
# 9. Export as GLB
# ---------------------------------------------------------------------------

os.makedirs(os.path.dirname(os.path.abspath(args.output)), exist_ok=True)

# Select only result objects for export
bpy.ops.object.select_all(action="DESELECT")
for obj in result_objects.values():
    obj.select_set(True)

bpy.ops.export_scene.gltf(
    filepath=args.output,
    export_format="GLB",
    export_materials="EXPORT",
    use_selection=True,
)
log_info(f"Exported split GLB to {args.output}")

# ---------------------------------------------------------------------------
# 10. Write JSON report
# ---------------------------------------------------------------------------

regions_report = {}
for rname, obj in result_objects.items():
    regions_report[rname] = {
        "vertices": len(obj.data.vertices),
        "faces": len(obj.data.polygons),
        "bbox": bbox_of_object(obj),
    }

report = {
    "source": args.input,
    "output": args.output,
    "split_performed": True,
    "axis_detection": {
        "length_axis": axis_names[length_axis],
        "width_axis":  axis_names[width_axis],
        "height_axis": axis_names[height_axis],
        "bounding_box_min": [round(bb_min.x, 5), round(bb_min.y, 5), round(bb_min.z, 5)],
        "bounding_box_max": [round(bb_max.x, 5), round(bb_max.y, 5), round(bb_max.z, 5)],
    },
    "source_mesh": {
        "vertices": total_verts,
        "faces": total_faces,
    },
    "regions": regions_report,
    "log": log,
}

report_path = args.report or args.output.replace(".glb", "_report.json")
with open(report_path, "w") as f:
    json.dump(report, f, indent=2)
log_info(f"Report written to {report_path}")
