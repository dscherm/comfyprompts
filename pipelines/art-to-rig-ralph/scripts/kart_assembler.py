"""Blender headless kart assembly script.

Takes split kart mesh objects (from mesh_split.py output) and assembles them into a
Mario Kart-style parent-child hierarchy using Empty objects for wheel mounts, exhaust
points, seat, and particle FX anchors.

Usage:
    blender --background --python kart_assembler.py -- \
        --input path/to/split.glb \
        --output-fbx path/to/kart_unity.fbx \
        --output-glb path/to/kart_blender.glb \
        --report path/to/assembly_report.json

Input:
    GLB containing any subset of: Chassis, Hood, Bumper_Front, Bumper_Rear,
    Panel_L, Panel_R, Spoiler. Chassis is required; all others are optional.

Output hierarchy:
    KartRoot (Empty)
    ├── Chassis (Mesh)
    │   ├── Hood / Bumper_Front / Bumper_Rear / Panel_L / Panel_R / Spoiler (optional Meshes)
    │   ├── Seat (Empty)
    │   └── EngineBay (Empty)
    ├── Axle_Front (Empty)
    │   ├── WheelMount_FL / WheelMount_FR (Empty)
    │   └── SteeringColumn (Empty)
    ├── Axle_Rear (Empty)
    │   ├── WheelMount_RL / WheelMount_RR (Empty)
    │   ├── Exhaust_L / Exhaust_R (Empty)
    ├── FX_Boost_L / FX_Boost_R (Empty)
    └── FX_Drift_L / FX_Drift_R (Empty)
"""

import bpy
import bmesh
import sys
import os
import json
import argparse
from mathutils import Vector

# ---------------------------------------------------------------------------
# Argument parsing — must be after "--" separator
# ---------------------------------------------------------------------------
argv = sys.argv
if "--" in argv:
    argv = argv[argv.index("--") + 1:]
else:
    argv = []

parser = argparse.ArgumentParser(description="Assemble split kart meshes into a hierarchy.")
parser.add_argument("--input", required=True, help="Path to split.glb")
parser.add_argument("--output-fbx", required=True, dest="output_fbx", help="Path for Unity FBX export")
parser.add_argument("--output-glb", required=True, dest="output_glb", help="Path for Blender GLB export")
parser.add_argument("--report", default=None, help="Path for JSON assembly report")
args = parser.parse_args(argv)

# ---------------------------------------------------------------------------
# Scene setup
# ---------------------------------------------------------------------------
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=args.input)

# Collect all imported objects by type
all_objects = list(bpy.data.objects)
mesh_objects_by_name = {o.name: o for o in all_objects if o.type == "MESH"}

print(f"Imported mesh objects: {list(mesh_objects_by_name.keys())}")

# Chassis is required
if "Chassis" not in mesh_objects_by_name:
    # Try case-insensitive fallback before giving up
    for name, obj in mesh_objects_by_name.items():
        if name.lower() == "chassis":
            mesh_objects_by_name["Chassis"] = obj
            break
    if "Chassis" not in mesh_objects_by_name:
        print("ERROR: No 'Chassis' mesh found in the input file.")
        sys.exit(1)

chassis_obj = mesh_objects_by_name["Chassis"]

# Optional detachable parts (parented under Chassis)
DETACHABLE_PARTS = ["Hood", "Bumper_Front", "Bumper_Rear", "Panel_L", "Panel_R", "Spoiler"]

# ---------------------------------------------------------------------------
# Bounding box from Chassis mesh (world-space)
# ---------------------------------------------------------------------------
def get_world_bbox_corners(obj):
    """Return all 8 bounding-box corners in world space."""
    return [obj.matrix_world @ Vector(v) for v in obj.bound_box]

corners = get_world_bbox_corners(chassis_obj)
min_co = Vector((
    min(v.x for v in corners),
    min(v.y for v in corners),
    min(v.z for v in corners),
))
max_co = Vector((
    max(v.x for v in corners),
    max(v.y for v in corners),
    max(v.z for v in corners),
))
dims = max_co - min_co

print(f"Chassis bounds: min={[round(v, 3) for v in min_co]}, max={[round(v, 3) for v in max_co]}")
print(f"Chassis dims: {[round(d, 3) for d in dims]}")

# ---------------------------------------------------------------------------
# Auto-detect orientation
# Longest axis = length (forward), second = width, shortest = height
# ---------------------------------------------------------------------------
axes = sorted(
    [(dims.x, 0, "X"), (dims.y, 1, "Y"), (dims.z, 2, "Z")],
    key=lambda a: a[0],
    reverse=True,
)
length_axis = axes[0][1]
width_axis = axes[1][1]
height_axis = axes[2][1]

print(f"Orientation — length={axes[0][2]}, width={axes[1][2]}, height={axes[2][2]}")


def pos(length_frac, width_frac, height_frac):
    """Convert bounding-box fractions (0=min, 1=max) to a world-space Vector."""
    p = [0.0, 0.0, 0.0]
    p[length_axis] = min_co[length_axis] + dims[length_axis] * length_frac
    p[width_axis]  = min_co[width_axis]  + dims[width_axis]  * width_frac
    p[height_axis] = min_co[height_axis] + dims[height_axis] * height_frac
    return Vector(p)


# ---------------------------------------------------------------------------
# Empty creation helper
# ---------------------------------------------------------------------------
# Display size scales with bounding box so it looks reasonable across kart sizes
EMPTY_SIZE_LARGE  = max(dims) * 0.06   # root, axles
EMPTY_SIZE_MEDIUM = max(dims) * 0.045  # mounts, seat, engine
EMPTY_SIZE_SMALL  = max(dims) * 0.03   # FX, exhaust


def make_empty(name, location, display_size=None, display_type="ARROWS"):
    """Create a plain-axes Empty at the given location and return it."""
    bpy.ops.object.empty_add(type=display_type, location=location)
    empty = bpy.context.active_object
    empty.name = name
    empty.empty_display_size = display_size or EMPTY_SIZE_MEDIUM
    return empty


def set_parent(child, parent_obj, keep_transform=True):
    """Parent child to parent_obj without moving it in world space."""
    child.parent = parent_obj
    if keep_transform:
        child.matrix_parent_inverse = parent_obj.matrix_world.inverted()


# ---------------------------------------------------------------------------
# 1. KartRoot — bottom center of chassis bbox
# ---------------------------------------------------------------------------
kart_root = make_empty("KartRoot", pos(0.5, 0.5, 0.0), display_size=EMPTY_SIZE_LARGE)
print("Created KartRoot")

# ---------------------------------------------------------------------------
# 2. Parent Chassis to KartRoot
# ---------------------------------------------------------------------------
set_parent(chassis_obj, kart_root)
print(f"Parented Chassis to KartRoot")

# ---------------------------------------------------------------------------
# 3. Parent optional detachable meshes to Chassis
# ---------------------------------------------------------------------------
for part_name in DETACHABLE_PARTS:
    part_obj = mesh_objects_by_name.get(part_name)
    if part_obj is not None:
        set_parent(part_obj, chassis_obj)
        print(f"Parented {part_name} to Chassis")
    else:
        print(f"Skipping {part_name} (not present in input)")

# ---------------------------------------------------------------------------
# 4. Chassis-attached empties: Seat and EngineBay
# ---------------------------------------------------------------------------
seat = make_empty("Seat", pos(0.45, 0.5, 0.55), display_size=EMPTY_SIZE_MEDIUM)
set_parent(seat, chassis_obj)

engine_bay = make_empty("EngineBay", pos(0.15, 0.5, 0.35), display_size=EMPTY_SIZE_MEDIUM)
set_parent(engine_bay, chassis_obj)

print("Created Seat, EngineBay under Chassis")

# ---------------------------------------------------------------------------
# 5. Axle_Front hierarchy
# ---------------------------------------------------------------------------
axle_front = make_empty("Axle_Front", pos(0.85, 0.5, 0.12), display_size=EMPTY_SIZE_LARGE)
set_parent(axle_front, kart_root)

wm_fl = make_empty("WheelMount_FL", pos(0.85, 0.0, 0.12), display_size=EMPTY_SIZE_MEDIUM)
set_parent(wm_fl, axle_front)

wm_fr = make_empty("WheelMount_FR", pos(0.85, 1.0, 0.12), display_size=EMPTY_SIZE_MEDIUM)
set_parent(wm_fr, axle_front)

steering = make_empty("SteeringColumn", pos(0.75, 0.5, 0.55), display_size=EMPTY_SIZE_MEDIUM)
set_parent(steering, axle_front)

print("Created Axle_Front hierarchy (WheelMount_FL, WheelMount_FR, SteeringColumn)")

# ---------------------------------------------------------------------------
# 6. Axle_Rear hierarchy
# ---------------------------------------------------------------------------
axle_rear = make_empty("Axle_Rear", pos(0.15, 0.5, 0.12), display_size=EMPTY_SIZE_LARGE)
set_parent(axle_rear, kart_root)

wm_rl = make_empty("WheelMount_RL", pos(0.15, 0.0, 0.12), display_size=EMPTY_SIZE_MEDIUM)
set_parent(wm_rl, axle_rear)

wm_rr = make_empty("WheelMount_RR", pos(0.15, 1.0, 0.12), display_size=EMPTY_SIZE_MEDIUM)
set_parent(wm_rr, axle_rear)

exhaust_l = make_empty("Exhaust_L", pos(0.05, 0.2, 0.25), display_size=EMPTY_SIZE_SMALL)
set_parent(exhaust_l, axle_rear)

exhaust_r = make_empty("Exhaust_R", pos(0.05, 0.8, 0.25), display_size=EMPTY_SIZE_SMALL)
set_parent(exhaust_r, axle_rear)

print("Created Axle_Rear hierarchy (WheelMount_RL, WheelMount_RR, Exhaust_L, Exhaust_R)")

# ---------------------------------------------------------------------------
# 7. Root-level FX empties
# ---------------------------------------------------------------------------
fx_boost_l = make_empty("FX_Boost_L", pos(0.0, 0.25, 0.2), display_size=EMPTY_SIZE_SMALL)
set_parent(fx_boost_l, kart_root)

fx_boost_r = make_empty("FX_Boost_R", pos(0.0, 0.75, 0.2), display_size=EMPTY_SIZE_SMALL)
set_parent(fx_boost_r, kart_root)

fx_drift_l = make_empty("FX_Drift_L", pos(0.15, 0.0, 0.1), display_size=EMPTY_SIZE_SMALL)
set_parent(fx_drift_l, kart_root)

fx_drift_r = make_empty("FX_Drift_R", pos(0.15, 1.0, 0.1), display_size=EMPTY_SIZE_SMALL)
set_parent(fx_drift_r, kart_root)

print("Created FX empties (FX_Boost_L/R, FX_Drift_L/R)")

# ---------------------------------------------------------------------------
# 8. Count stats for report
# ---------------------------------------------------------------------------
all_scene_objects = list(bpy.data.objects)
empty_objects = [o for o in all_scene_objects if o.type == "EMPTY"]
mesh_objects_final = [o for o in all_scene_objects if o.type == "MESH"]

total_vertices = sum(len(o.data.vertices) for o in mesh_objects_final)
total_faces = sum(len(o.data.polygons) for o in mesh_objects_final)

print(f"Scene totals: {len(empty_objects)} empties, {len(mesh_objects_final)} meshes, "
      f"{total_vertices} verts, {total_faces} faces")

# ---------------------------------------------------------------------------
# 9. Build hierarchy dict for report
# ---------------------------------------------------------------------------
def build_hierarchy(obj):
    """Recursively build a dict describing an object and its children."""
    entry = {
        "type": obj.type,
        "children": [],
    }
    if obj.type == "MESH":
        entry["vertices"] = len(obj.data.vertices)
        entry["faces"] = len(obj.data.polygons)
    for child in obj.children:
        child_entry = build_hierarchy(child)
        entry["children"].append(child.name)
        # Nested objects will appear at their own key in the flat hierarchy dict
    return entry


def build_flat_hierarchy(root):
    """Walk the full tree and return a flat {name: entry} dict."""
    result = {}
    queue = [root]
    while queue:
        obj = queue.pop(0)
        entry = {
            "type": obj.type,
            "children": [c.name for c in obj.children],
        }
        if obj.type == "MESH":
            entry["vertices"] = len(obj.data.vertices)
            entry["faces"] = len(obj.data.polygons)
        result[obj.name] = entry
        queue.extend(obj.children)
    return result


hierarchy = build_flat_hierarchy(kart_root)

# ---------------------------------------------------------------------------
# 10. Export — FBX (Unity primary)
# ---------------------------------------------------------------------------
os.makedirs(os.path.dirname(os.path.abspath(args.output_fbx)), exist_ok=True)
bpy.ops.export_scene.fbx(
    filepath=args.output_fbx,
    use_selection=False,
    apply_scale_options="FBX_SCALE_ALL",
    axis_forward="-Z",
    axis_up="Y",
    object_types={"MESH", "EMPTY"},
    mesh_smooth_type="FACE",
    add_leaf_bones=False,
)
print(f"Exported FBX (Unity): {args.output_fbx}")

# ---------------------------------------------------------------------------
# 11. Export — GLB (Blender)
# ---------------------------------------------------------------------------
os.makedirs(os.path.dirname(os.path.abspath(args.output_glb)), exist_ok=True)
bpy.ops.export_scene.gltf(
    filepath=args.output_glb,
    export_format="GLB",
    export_materials="EXPORT",
)
print(f"Exported GLB (Blender): {args.output_glb}")

# ---------------------------------------------------------------------------
# 12. Write report JSON
# ---------------------------------------------------------------------------
report = {
    "source": args.input,
    "output_fbx": args.output_fbx,
    "output_glb": args.output_glb,
    "hierarchy": hierarchy,
    "empty_count": len(empty_objects),
    "mesh_count": len(mesh_objects_final),
    "total_vertices": total_vertices,
    "total_faces": total_faces,
    "chassis_dims": [round(d, 4) for d in dims],
    "orientation": {
        "length_axis": axes[0][2],
        "width_axis": axes[1][2],
        "height_axis": axes[2][2],
    },
    "optional_parts_found": [p for p in DETACHABLE_PARTS if p in mesh_objects_by_name],
    "optional_parts_missing": [p for p in DETACHABLE_PARTS if p not in mesh_objects_by_name],
}

report_path = args.report or args.output_glb.replace(".glb", "_assembly_report.json")
os.makedirs(os.path.dirname(os.path.abspath(report_path)), exist_ok=True)
with open(report_path, "w") as f:
    json.dump(report, f, indent=2)
print(f"Assembly report: {report_path}")
