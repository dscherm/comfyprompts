"""Interactive kart pipeline wrapper.

Two usage modes:

1. Via blender-mcp (interactive, step-by-step):
   Copy-paste each stage call into execute_blender_code.
   See the BLENDER-MCP SNIPPETS section at the bottom of this file.

2. As a standalone orchestrator inside Blender headless:
   blender --background --python kart_pipeline_interactive.py -- \\
       --input path/to/prepared.glb \\
       --output-dir path/to/output \\
       --kart-name player_kart

Stage functions can be called independently as long as prerequisites are met:
  - stage_import_mk_reference() — no prerequisites
  - stage_import_and_analyze(glb_path) — no prerequisites (clears scene except MK_Reference)
  - stage_split_regions() — requires active mesh object in scene
  - stage_assemble_hierarchy() — requires region objects from stage_split_regions
  - stage_export(output_dir, kart_name) — requires hierarchy from stage_assemble_hierarchy
"""

import bpy
import bmesh
import json
import sys
import os
import argparse
import random
from collections import defaultdict
from mathutils import Vector

# ---------------------------------------------------------------------------
# Region definitions (same priority order as mesh_split.py)
# Each entry: (name, length_min, length_max, width_min, width_max, height_min, height_max)
# ---------------------------------------------------------------------------

REGION_DEFS = [
    ("Bumper_Front", 0.90, 1.00, 0.10, 0.90, 0.00, 0.40),
    ("Bumper_Rear",  0.00, 0.10, 0.10, 0.90, 0.00, 0.40),
    ("Hood",         0.75, 1.00, 0.15, 0.85, 0.30, 1.00),
    ("Spoiler",      0.00, 0.15, 0.15, 0.85, 0.60, 1.00),
    ("Panel_L",      0.15, 0.85, 0.00, 0.15, 0.20, 0.80),
    ("Panel_R",      0.15, 0.85, 0.85, 1.00, 0.20, 0.80),
    ("Chassis",      0.00, 1.00, 0.00, 1.00, 0.00, 1.00),  # catch-all
]

DETACHABLE_PARTS = ["Hood", "Bumper_Front", "Bumper_Rear", "Panel_L", "Panel_R", "Spoiler"]

# Distinct colors per region for visual inspection (RGBA, linear)
REGION_COLORS = {
    "Chassis":      (0.35, 0.35, 0.35, 1.0),
    "Hood":         (0.18, 0.55, 0.18, 1.0),
    "Bumper_Front": (0.80, 0.25, 0.10, 1.0),
    "Bumper_Rear":  (0.80, 0.55, 0.10, 1.0),
    "Panel_L":      (0.12, 0.35, 0.75, 1.0),
    "Panel_R":      (0.55, 0.12, 0.75, 1.0),
    "Spoiler":      (0.80, 0.80, 0.10, 1.0),
}

MK_REFERENCE_PATH = (
    "D:/Projects/mario-kart-reference/3D Mario Kart/Assets/Models/Kart/StandardKart.fbx"
)
MK_REFERENCE_COLLECTION = "MK_Reference"


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def _log(msg: str) -> None:
    print(f"[kart_pipeline] {msg}")


def _get_world_vertices(obj):
    """Return list of world-space vertex coordinates."""
    mw = obj.matrix_world
    return [mw @ v.co for v in obj.data.vertices]


def _compute_bounding_box(world_verts):
    """Return (min_co, max_co) as Vectors."""
    xs = [v.x for v in world_verts]
    ys = [v.y for v in world_verts]
    zs = [v.z for v in world_verts]
    return (
        Vector((min(xs), min(ys), min(zs))),
        Vector((max(xs), max(ys), max(zs))),
    )


def _detect_axes(bb_min, bb_max):
    """Return (length_axis, width_axis, height_axis) as integer indices 0/1/2.
    length = longest extent, height = shortest extent.
    """
    extents = [bb_max[i] - bb_min[i] for i in range(3)]
    sorted_axes = sorted(range(3), key=lambda i: extents[i], reverse=True)
    return sorted_axes[0], sorted_axes[1], sorted_axes[2]


def _normalize(value, axis_min, axis_max):
    span = axis_max - axis_min
    if span < 1e-9:
        return 0.5
    return (value - axis_min) / span


def _vertex_in_region(nL, nW, nH, region_def):
    _, lmin, lmax, wmin, wmax, hmin, hmax = region_def
    return lmin <= nL <= lmax and wmin <= nW <= wmax and hmin <= nH <= hmax


def _set_origin_bbox_center(obj):
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.ops.object.origin_set(type="ORIGIN_GEOMETRY", center="BOUNDS")


def _bbox_dict(obj):
    verts = _get_world_vertices(obj)
    if not verts:
        return None
    bb_min, bb_max = _compute_bounding_box(verts)
    return {
        "min": [round(bb_min.x, 5), round(bb_min.y, 5), round(bb_min.z, 5)],
        "max": [round(bb_max.x, 5), round(bb_max.y, 5), round(bb_max.z, 5)],
        "size": [
            round(bb_max.x - bb_min.x, 5),
            round(bb_max.y - bb_min.y, 5),
            round(bb_max.z - bb_min.z, 5),
        ],
    }


def _assign_region_color(obj, region_name: str) -> None:
    """Assign a distinct solid material color to a region object."""
    mat_name = f"Mat_{region_name}"
    mat = bpy.data.materials.get(mat_name)
    if mat is None:
        mat = bpy.data.materials.new(name=mat_name)
        mat.use_nodes = False
        color = REGION_COLORS.get(
            region_name,
            (random.random(), random.random(), random.random(), 1.0),
        )
        mat.diffuse_color = color
    if obj.data.materials:
        obj.data.materials[0] = mat
    else:
        obj.data.materials.append(mat)


def _pos_from_bounds(bb_min, dims, length_axis, width_axis, height_axis,
                     length_frac, width_frac, height_frac):
    """Convert bounding-box fractions to a world-space Vector."""
    p = [0.0, 0.0, 0.0]
    p[length_axis] = bb_min[length_axis] + dims[length_axis] * length_frac
    p[width_axis]  = bb_min[width_axis]  + dims[width_axis]  * width_frac
    p[height_axis] = bb_min[height_axis] + dims[height_axis] * height_frac
    return Vector(p)


def _make_empty(name, location, display_size, display_type="ARROWS"):
    bpy.ops.object.empty_add(type=display_type, location=location)
    empty = bpy.context.active_object
    empty.name = name
    empty.empty_display_size = display_size
    return empty


def _set_parent(child, parent_obj):
    child.parent = parent_obj
    child.matrix_parent_inverse = parent_obj.matrix_world.inverted()


def _build_flat_hierarchy(root):
    result = {}
    queue = [root]
    while queue:
        obj = queue.pop(0)
        entry = {"type": obj.type, "children": [c.name for c in obj.children]}
        if obj.type == "MESH":
            entry["vertices"] = len(obj.data.vertices)
            entry["faces"] = len(obj.data.polygons)
        result[obj.name] = entry
        queue.extend(obj.children)
    return result


def _get_mk_reference_collection():
    return bpy.data.collections.get(MK_REFERENCE_COLLECTION)


def _get_scene_mesh_objects(exclude_collection=None):
    """Return mesh objects in the scene, optionally skipping those in a collection."""
    result = []
    skip_names = set()
    if exclude_collection is not None:
        col = bpy.data.collections.get(exclude_collection)
        if col:
            skip_names = {o.name for o in col.all_objects}
    for obj in bpy.data.objects:
        if obj.type == "MESH" and obj.name not in skip_names:
            result.append(obj)
    return result


# ---------------------------------------------------------------------------
# Stage 0: Import MK Reference
# ---------------------------------------------------------------------------


def stage_import_mk_reference() -> dict:
    """Import the MK reference kart for visual proportion comparison.

    Imports StandardKart.fbx into a dedicated 'MK_Reference' collection.
    Does not clear the existing scene.

    Returns:
        dict with keys: collection, objects, mesh_info
    """
    if not os.path.isfile(MK_REFERENCE_PATH):
        msg = f"MK reference not found: {MK_REFERENCE_PATH}"
        _log(f"WARNING: {msg}")
        return {"status": "skipped", "reason": msg}

    # Create or retrieve the reference collection
    col = bpy.data.collections.get(MK_REFERENCE_COLLECTION)
    if col is None:
        col = bpy.data.collections.new(MK_REFERENCE_COLLECTION)
        bpy.context.scene.collection.children.link(col)

    # Track objects before import
    before = set(bpy.data.objects.keys())

    bpy.ops.import_scene.fbx(filepath=MK_REFERENCE_PATH)

    # Move newly imported objects into the MK_Reference collection
    new_objects = [o for o in bpy.data.objects if o.name not in before]
    for obj in new_objects:
        # Unlink from current collections first
        for c in list(obj.users_collection):
            c.objects.unlink(obj)
        col.objects.link(obj)

    _log(f"Imported {len(new_objects)} objects into {MK_REFERENCE_COLLECTION}")

    mesh_info = []
    for obj in new_objects:
        if obj.type == "MESH":
            bb = _bbox_dict(obj)
            mesh_info.append({
                "name": obj.name,
                "vertices": len(obj.data.vertices),
                "faces": len(obj.data.polygons),
                "dims": bb["size"] if bb else None,
            })

    return {
        "status": "ok",
        "collection": MK_REFERENCE_COLLECTION,
        "objects_imported": len(new_objects),
        "mesh_info": mesh_info,
    }


# ---------------------------------------------------------------------------
# Stage 1: Import and Analyze
# ---------------------------------------------------------------------------


def stage_import_and_analyze(glb_path: str) -> dict:
    """Clear scene (preserving MK_Reference), import GLB, join meshes, analyze.

    Args:
        glb_path: Absolute path to the prepared GLB file.

    Returns:
        dict with keys: mesh_name, vertices, faces, orientation, bounds, dims_m
    """
    if not os.path.isfile(glb_path):
        raise FileNotFoundError(f"Input GLB not found: {glb_path}")

    # Collect MK reference objects to preserve
    mk_col = _get_mk_reference_collection()
    preserve = set()
    if mk_col:
        preserve = {o.name for o in mk_col.all_objects}

    # Delete all non-reference objects
    bpy.ops.object.select_all(action="DESELECT")
    for obj in list(bpy.data.objects):
        if obj.name not in preserve:
            obj.select_set(True)
    bpy.ops.object.delete()

    _log(f"Importing {glb_path}")
    bpy.ops.import_scene.gltf(filepath=glb_path)

    mesh_objects = _get_scene_mesh_objects(exclude_collection=MK_REFERENCE_COLLECTION)

    if not mesh_objects:
        raise RuntimeError(f"No mesh objects found in {glb_path}")

    _log(f"Found {len(mesh_objects)} mesh object(s)")

    # Join all meshes into one
    bpy.ops.object.select_all(action="DESELECT")
    for obj in mesh_objects:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = mesh_objects[0]

    if len(mesh_objects) > 1:
        bpy.ops.object.join()
        _log(f"Joined {len(mesh_objects)} objects into one")

    source = bpy.context.active_object
    source.name = "KartMesh_Source"

    # Apply all transforms
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)

    total_verts = len(source.data.vertices)
    total_faces = len(source.data.polygons)
    _log(f"Mesh: {total_verts} verts, {total_faces} faces")

    # Bounding box and axis detection
    world_verts = _get_world_vertices(source)
    bb_min, bb_max = _compute_bounding_box(world_verts)
    length_axis, width_axis, height_axis = _detect_axes(bb_min, bb_max)

    axis_names = ["X", "Y", "Z"]
    dims = [bb_max[i] - bb_min[i] for i in range(3)]

    _log(
        f"Axes — length:{axis_names[length_axis]} "
        f"width:{axis_names[width_axis]} "
        f"height:{axis_names[height_axis]}"
    )
    _log(f"Dims (m): L={dims[length_axis]:.4f} W={dims[width_axis]:.4f} H={dims[height_axis]:.4f}")
    _log(f"Bounds min:{[round(v, 4) for v in bb_min]} max:{[round(v, 4) for v in bb_max]}")

    return {
        "status": "ok",
        "mesh_name": source.name,
        "vertices": total_verts,
        "faces": total_faces,
        "orientation": {
            "length_axis": axis_names[length_axis],
            "width_axis": axis_names[width_axis],
            "height_axis": axis_names[height_axis],
        },
        "bounds": {
            "min": [round(bb_min.x, 5), round(bb_min.y, 5), round(bb_min.z, 5)],
            "max": [round(bb_max.x, 5), round(bb_max.y, 5), round(bb_max.z, 5)],
        },
        "dims_m": {
            "length": round(dims[length_axis], 5),
            "width":  round(dims[width_axis], 5),
            "height": round(dims[height_axis], 5),
        },
    }


# ---------------------------------------------------------------------------
# Stage 2: Split Regions
# ---------------------------------------------------------------------------


def stage_split_regions(min_region_verts: int = 10) -> dict:
    """Split the active mesh into named region objects.

    Expects the scene to contain a mesh object named 'KartMesh_Source'
    (created by stage_import_and_analyze). Falls back to the first mesh
    found in the scene if 'KartMesh_Source' is not present.

    Args:
        min_region_verts: Regions with fewer vertices are merged into Chassis.

    Returns:
        dict with region names, vertex/face counts, and color assignments.
    """
    # Find the source mesh
    source = bpy.data.objects.get("KartMesh_Source")
    if source is None:
        candidates = _get_scene_mesh_objects(exclude_collection=MK_REFERENCE_COLLECTION)
        if not candidates:
            raise RuntimeError("No mesh object found. Run stage_import_and_analyze first.")
        source = candidates[0]
        _log(f"'KartMesh_Source' not found; using '{source.name}' as source")

    bpy.context.view_layer.objects.active = source
    bpy.ops.object.select_all(action="DESELECT")
    source.select_set(True)
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)

    total_verts = len(source.data.vertices)
    total_faces = len(source.data.polygons)
    _log(f"Source mesh: {total_verts} verts, {total_faces} faces")

    # --- Bounding box and axis detection ---
    world_verts = _get_world_vertices(source)
    bb_min, bb_max = _compute_bounding_box(world_verts)
    length_axis, width_axis, height_axis = _detect_axes(bb_min, bb_max)

    axis_names = ["X", "Y", "Z"]
    _log(
        f"Axes — length:{axis_names[length_axis]} "
        f"width:{axis_names[width_axis]} "
        f"height:{axis_names[height_axis]}"
    )

    # --- Assign each vertex to a region ---
    vertex_region = {}
    for vi, wv in enumerate(world_verts):
        nL = _normalize(wv[length_axis], bb_min[length_axis], bb_max[length_axis])
        nW = _normalize(wv[width_axis],  bb_min[width_axis],  bb_max[width_axis])
        nH = _normalize(wv[height_axis], bb_min[height_axis], bb_max[height_axis])
        for rdef in REGION_DEFS:
            if _vertex_in_region(nL, nW, nH, rdef):
                vertex_region[vi] = rdef[0]
                break

    # --- Count vertices per region ---
    region_verts = defaultdict(set)
    for vi, rname in vertex_region.items():
        region_verts[rname].add(vi)

    _log("Vertex counts per region before merge-back:")
    for rdef in REGION_DEFS:
        count = len(region_verts.get(rdef[0], set()))
        _log(f"  {rdef[0]}: {count}")

    # --- Merge small regions into Chassis ---
    for rdef in REGION_DEFS:
        rname = rdef[0]
        if rname == "Chassis":
            continue
        vcount = len(region_verts.get(rname, set()))
        if 0 < vcount < min_region_verts:
            _log(
                f"Region {rname} has only {vcount} verts "
                f"(< {min_region_verts}), merging into Chassis"
            )
            for vi in list(region_verts.get(rname, set())):
                vertex_region[vi] = "Chassis"
            region_verts["Chassis"].update(region_verts.pop(rname))

    # Recompute after merge-back
    region_verts = defaultdict(set)
    for vi, rname in vertex_region.items():
        region_verts[rname].add(vi)

    active_regions = [r for r in region_verts if len(region_verts[r]) >= min_region_verts]
    _log(f"Active regions: {active_regions}")

    # --- Build face-to-region mapping (majority vote) ---
    face_region = {}
    for poly in source.data.polygons:
        counts = defaultdict(int)
        for vi in poly.vertices:
            counts[vertex_region.get(vi, "Chassis")] += 1
        face_region[poly.index] = max(counts, key=lambda r: counts[r])

    region_faces = defaultdict(set)
    for fi, rname in face_region.items():
        region_faces[rname].add(fi)

    # --- Create one object per region ---
    result_objects = {}

    for rname in active_regions:
        target_faces = region_faces.get(rname, set())
        if not target_faces:
            _log(f"Region {rname}: no faces, skipping")
            continue

        _log(f"Creating object for region: {rname} ({len(target_faces)} faces)")

        # Duplicate source
        bpy.ops.object.select_all(action="DESELECT")
        source.select_set(True)
        bpy.context.view_layer.objects.active = source
        bpy.ops.object.duplicate(linked=False)
        region_obj = bpy.context.active_object
        region_obj.name = rname

        # Delete faces not in this region via bmesh
        bpy.ops.object.mode_set(mode="EDIT")
        bm = bmesh.from_edit_mesh(region_obj.data)
        bm.faces.ensure_lookup_table()

        faces_to_delete = [f for f in bm.faces if f.index not in target_faces]
        bmesh.ops.delete(bm, geom=faces_to_delete, context="FACES")
        bmesh.update_edit_mesh(region_obj.data)
        bpy.ops.object.mode_set(mode="OBJECT")

        # Remove loose geometry
        bpy.ops.object.mode_set(mode="EDIT")
        bm2 = bmesh.from_edit_mesh(region_obj.data)
        loose_verts = [v for v in bm2.verts if len(v.link_faces) == 0]
        bmesh.ops.delete(bm2, geom=loose_verts, context="VERTS")
        bmesh.update_edit_mesh(region_obj.data)
        bpy.ops.object.mode_set(mode="OBJECT")

        final_v = len(region_obj.data.vertices)
        final_f = len(region_obj.data.polygons)

        if final_f == 0:
            _log(f"Region {rname}: 0 faces after separation, removing")
            bpy.data.objects.remove(region_obj, do_unlink=True)
            continue

        _log(f"  {rname}: {final_v} verts, {final_f} faces")

        _set_origin_bbox_center(region_obj)
        _assign_region_color(region_obj, rname)

        result_objects[rname] = region_obj

    # Remove source
    bpy.data.objects.remove(source, do_unlink=True)

    if not result_objects:
        _log("WARNING: No regions created — scene unchanged")

    regions_report = {}
    for rname, obj in result_objects.items():
        regions_report[rname] = {
            "vertices": len(obj.data.vertices),
            "faces": len(obj.data.polygons),
            "bbox": _bbox_dict(obj),
            "color": REGION_COLORS.get(rname, "random"),
        }

    _log(f"Split complete: {list(result_objects.keys())}")
    return {
        "status": "ok",
        "active_regions": active_regions,
        "regions": regions_report,
        "min_region_verts": min_region_verts,
    }


# ---------------------------------------------------------------------------
# Stage 3: Assemble Hierarchy
# ---------------------------------------------------------------------------


def stage_assemble_hierarchy() -> dict:
    """Assemble region mesh objects into the full kart empty hierarchy.

    Expects objects named: Chassis (required), and optionally Hood, Bumper_Front,
    Bumper_Rear, Panel_L, Panel_R, Spoiler.

    Creates empties at attachment points derived from the Chassis bounding box
    and builds the full parent-child hierarchy.

    Returns:
        dict with hierarchy tree, empty positions, and found/missing parts.
    """
    # Find Chassis
    chassis_obj = bpy.data.objects.get("Chassis")
    if chassis_obj is None:
        # Case-insensitive fallback
        for obj in bpy.data.objects:
            if obj.type == "MESH" and obj.name.lower() == "chassis":
                chassis_obj = obj
                break
        if chassis_obj is None:
            raise RuntimeError("No 'Chassis' mesh found. Run stage_split_regions first.")

    # Bounding box from Chassis
    corners = [chassis_obj.matrix_world @ Vector(v) for v in chassis_obj.bound_box]
    bb_min = Vector((
        min(v.x for v in corners),
        min(v.y for v in corners),
        min(v.z for v in corners),
    ))
    bb_max = Vector((
        max(v.x for v in corners),
        max(v.y for v in corners),
        max(v.z for v in corners),
    ))
    dims = bb_max - bb_min

    # Axis detection
    axes_sorted = sorted(
        [(dims.x, 0, "X"), (dims.y, 1, "Y"), (dims.z, 2, "Z")],
        key=lambda a: a[0],
        reverse=True,
    )
    length_axis = axes_sorted[0][1]
    width_axis  = axes_sorted[1][1]
    height_axis = axes_sorted[2][1]

    _log(
        f"Chassis dims: L={dims[length_axis]:.4f} W={dims[width_axis]:.4f} H={dims[height_axis]:.4f}"
    )
    _log(f"Axes — length:{axes_sorted[0][2]} width:{axes_sorted[1][2]} height:{axes_sorted[2][2]}")

    # Scaled empty display sizes
    LARGE  = max(dims) * 0.06
    MEDIUM = max(dims) * 0.045
    SMALL  = max(dims) * 0.03

    def pos(lf, wf, hf):
        return _pos_from_bounds(bb_min, dims, length_axis, width_axis, height_axis, lf, wf, hf)

    # --- KartRoot ---
    kart_root = _make_empty("KartRoot", pos(0.5, 0.5, 0.0), LARGE)

    # --- Chassis under KartRoot ---
    _set_parent(chassis_obj, kart_root)

    # --- Detachable parts under Chassis ---
    parts_found = []
    parts_missing = []
    for part_name in DETACHABLE_PARTS:
        part_obj = bpy.data.objects.get(part_name)
        if part_obj is not None and part_obj.type == "MESH":
            _set_parent(part_obj, chassis_obj)
            parts_found.append(part_name)
            _log(f"Parented {part_name} to Chassis")
        else:
            parts_missing.append(part_name)

    # --- Chassis-attached empties ---
    seat = _make_empty("Seat", pos(0.45, 0.5, 0.55), MEDIUM)
    _set_parent(seat, chassis_obj)

    engine_bay = _make_empty("EngineBay", pos(0.15, 0.5, 0.35), MEDIUM)
    _set_parent(engine_bay, chassis_obj)

    # --- Axle_Front hierarchy ---
    axle_front = _make_empty("Axle_Front", pos(0.85, 0.5, 0.12), LARGE)
    _set_parent(axle_front, kart_root)

    wm_fl = _make_empty("WheelMount_FL", pos(0.85, 0.0, 0.12), MEDIUM)
    _set_parent(wm_fl, axle_front)

    wm_fr = _make_empty("WheelMount_FR", pos(0.85, 1.0, 0.12), MEDIUM)
    _set_parent(wm_fr, axle_front)

    steering = _make_empty("SteeringColumn", pos(0.75, 0.5, 0.55), MEDIUM)
    _set_parent(steering, axle_front)

    # --- Axle_Rear hierarchy ---
    axle_rear = _make_empty("Axle_Rear", pos(0.15, 0.5, 0.12), LARGE)
    _set_parent(axle_rear, kart_root)

    wm_rl = _make_empty("WheelMount_RL", pos(0.15, 0.0, 0.12), MEDIUM)
    _set_parent(wm_rl, axle_rear)

    wm_rr = _make_empty("WheelMount_RR", pos(0.15, 1.0, 0.12), MEDIUM)
    _set_parent(wm_rr, axle_rear)

    exhaust_l = _make_empty("Exhaust_L", pos(0.05, 0.2, 0.25), SMALL)
    _set_parent(exhaust_l, axle_rear)

    exhaust_r = _make_empty("Exhaust_R", pos(0.05, 0.8, 0.25), SMALL)
    _set_parent(exhaust_r, axle_rear)

    # --- Root-level FX empties ---
    fx_boost_l = _make_empty("FX_Boost_L", pos(0.0, 0.25, 0.2), SMALL)
    _set_parent(fx_boost_l, kart_root)

    fx_boost_r = _make_empty("FX_Boost_R", pos(0.0, 0.75, 0.2), SMALL)
    _set_parent(fx_boost_r, kart_root)

    fx_drift_l = _make_empty("FX_Drift_L", pos(0.15, 0.0, 0.1), SMALL)
    _set_parent(fx_drift_l, kart_root)

    fx_drift_r = _make_empty("FX_Drift_R", pos(0.15, 1.0, 0.1), SMALL)
    _set_parent(fx_drift_r, kart_root)

    _log("Hierarchy assembled")

    hierarchy = _build_flat_hierarchy(kart_root)

    return {
        "status": "ok",
        "root": "KartRoot",
        "hierarchy": hierarchy,
        "parts_found": parts_found,
        "parts_missing": parts_missing,
        "chassis_dims": {
            "length": round(dims[length_axis], 5),
            "width":  round(dims[width_axis], 5),
            "height": round(dims[height_axis], 5),
        },
    }


# ---------------------------------------------------------------------------
# Stage 4: Export
# ---------------------------------------------------------------------------


def stage_export(output_dir: str, kart_name: str) -> dict:
    """Export the assembled kart in FBX (Unity), GLB (Blender), and FBX (Unreal) formats.

    Expects the scene to contain the assembled hierarchy (KartRoot + children).

    Args:
        output_dir: Directory to write output files into (created if absent).
        kart_name:  Base name for output files (e.g. 'player_kart').

    Returns:
        dict with output file paths and a summary.
    """
    os.makedirs(output_dir, exist_ok=True)

    path_unity   = os.path.join(output_dir, f"{kart_name}_unity.fbx")
    path_blender = os.path.join(output_dir, f"{kart_name}_blender.glb")
    path_unreal  = os.path.join(output_dir, f"{kart_name}_unreal.fbx")
    path_report  = os.path.join(output_dir, f"{kart_name}_assembly_report.json")

    # Deselect MK reference so it is not included in exports
    bpy.ops.object.select_all(action="DESELECT")
    mk_col = _get_mk_reference_collection()
    mk_names = set()
    if mk_col:
        mk_names = {o.name for o in mk_col.all_objects}

    for obj in bpy.data.objects:
        if obj.name not in mk_names:
            obj.select_set(True)

    # FBX Unity (Y-up, -Z forward)
    bpy.ops.export_scene.fbx(
        filepath=path_unity,
        use_selection=True,
        apply_scale_options="FBX_SCALE_ALL",
        axis_forward="-Z",
        axis_up="Y",
        object_types={"MESH", "EMPTY"},
        mesh_smooth_type="FACE",
        add_leaf_bones=False,
    )
    _log(f"Exported Unity FBX: {path_unity}")

    # GLB Blender
    bpy.ops.export_scene.gltf(
        filepath=path_blender,
        export_format="GLB",
        export_materials="EXPORT",
        use_selection=True,
    )
    _log(f"Exported Blender GLB: {path_blender}")

    # FBX Unreal (Z-up, X forward)
    bpy.ops.export_scene.fbx(
        filepath=path_unreal,
        use_selection=True,
        apply_scale_options="FBX_SCALE_ALL",
        axis_forward="X",
        axis_up="Z",
        object_types={"MESH", "EMPTY"},
        mesh_smooth_type="FACE",
        add_leaf_bones=False,
    )
    _log(f"Exported Unreal FBX: {path_unreal}")

    # Assembly report
    kart_root = bpy.data.objects.get("KartRoot")
    hierarchy = _build_flat_hierarchy(kart_root) if kart_root else {}

    mesh_objects = [o for o in bpy.data.objects
                    if o.type == "MESH" and o.name not in mk_names]
    total_verts = sum(len(o.data.vertices) for o in mesh_objects)
    total_faces = sum(len(o.data.polygons) for o in mesh_objects)

    report = {
        "kart_name": kart_name,
        "output_dir": output_dir,
        "exports": {
            "unity_fbx":   path_unity,
            "blender_glb": path_blender,
            "unreal_fbx":  path_unreal,
        },
        "mesh_count": len(mesh_objects),
        "total_vertices": total_verts,
        "total_faces": total_faces,
        "hierarchy": hierarchy,
    }

    with open(path_report, "w") as f:
        json.dump(report, f, indent=2)
    _log(f"Assembly report: {path_report}")

    return {
        "status": "ok",
        "unity_fbx":   path_unity,
        "blender_glb": path_blender,
        "unreal_fbx":  path_unreal,
        "report":      path_report,
        "mesh_count":  len(mesh_objects),
        "total_vertices": total_verts,
        "total_faces": total_faces,
    }


# ---------------------------------------------------------------------------
# Full pipeline
# ---------------------------------------------------------------------------


def run_full_pipeline(input_glb: str, output_dir: str, kart_name: str) -> dict:
    """Run all pipeline stages in sequence.

    Stages:
      1. stage_import_and_analyze
      2. stage_split_regions
      3. stage_assemble_hierarchy
      4. stage_export

    Args:
        input_glb:  Path to the prepared input GLB.
        output_dir: Directory for output files.
        kart_name:  Base name for outputs.

    Returns:
        Combined report dict from all stages.
    """
    _log("=== run_full_pipeline START ===")

    result_analyze = stage_import_and_analyze(input_glb)
    _log(f"Stage 1 done: {result_analyze['vertices']} verts, {result_analyze['faces']} faces")

    result_split = stage_split_regions()
    _log(f"Stage 2 done: regions={result_split['active_regions']}")

    result_hierarchy = stage_assemble_hierarchy()
    _log(f"Stage 3 done: root={result_hierarchy['root']}")

    result_export = stage_export(output_dir, kart_name)
    _log(f"Stage 4 done: {result_export['unity_fbx']}")

    _log("=== run_full_pipeline DONE ===")

    return {
        "status": "ok",
        "kart_name": kart_name,
        "input_glb": input_glb,
        "analyze": result_analyze,
        "split": result_split,
        "hierarchy": result_hierarchy,
        "export": result_export,
    }


# ---------------------------------------------------------------------------
# CLI / headless entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    argv = sys.argv
    if "--" in argv:
        argv = argv[argv.index("--") + 1:]
    else:
        argv = []

    parser = argparse.ArgumentParser(
        description="Kart pipeline interactive wrapper (headless or blender-mcp)"
    )
    parser.add_argument("--input", required=True, help="Path to prepared input GLB")
    parser.add_argument("--output-dir", required=True, dest="output_dir",
                        help="Directory for output files")
    parser.add_argument("--kart-name", required=True, dest="kart_name",
                        help="Base name for output files (e.g. player_kart)")
    args = parser.parse_args(argv)

    report = run_full_pipeline(args.input, args.output_dir, args.kart_name)

    report_path = os.path.join(args.output_dir, f"{args.kart_name}_pipeline_report.json")
    os.makedirs(args.output_dir, exist_ok=True)
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2)
    print(f"[kart_pipeline] Full report: {report_path}")


# =============================================================================
# BLENDER-MCP SNIPPETS
# Copy these into execute_blender_code for interactive step-by-step use.
# Run exec() once to load all stage functions, then call stages individually.
# =============================================================================

# -- Load all stage functions into the session --------------------------------
# exec(open("D:/Projects/comfyui-toolchain/pipelines/art-to-rig-ralph/scripts/kart_pipeline_interactive.py").read())

# -- Step 1: Import MK kart reference for proportion comparison ---------------
# result = stage_import_mk_reference()
# print(result)

# -- Step 2: Import and analyze the prepared kart GLB -------------------------
# result = stage_import_and_analyze(
#     "D:/Projects/comfyui-toolchain/pipelines/art-to-rig-ralph/output/prepared/player_kart_v1_prepared.glb"
# )
# print(result)

# -- Step 3: Split mesh into named regions with color coding ------------------
# result = stage_split_regions()
# print(result)
#
# Optionally pass a custom threshold:
# result = stage_split_regions(min_region_verts=20)
# print(result)

# -- Step 4: Build parent-child empty hierarchy -------------------------------
# result = stage_assemble_hierarchy()
# print(result)

# -- Step 5: Export FBX/GLB for Unity, Blender, Unreal -----------------------
# result = stage_export(
#     "D:/Projects/comfyui-toolchain/pipelines/art-to-rig-ralph/output/final/player_kart",
#     "player_kart"
# )
# print(result)

# -- Full pipeline in one call (headless) ------------------------------------
# result = run_full_pipeline(
#     "D:/Projects/comfyui-toolchain/pipelines/art-to-rig-ralph/output/prepared/player_kart_v1_prepared.glb",
#     "D:/Projects/comfyui-toolchain/pipelines/art-to-rig-ralph/output/final/player_kart",
#     "player_kart"
# )
# print(result)
