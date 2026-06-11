"""Blender headless part splitting script for fusion-ralph pipeline.

Usage:
    blender --background --python part_split.py -- \
        --input INPUT.glb --output-dir OUTPUT_DIR/ \
        [--split-axis Z] [--split-at 0.5] \
        [--pin-radius 1.5] [--pin-clearance 0.15] [--pin-depth 6.0]

Splits a mesh along a plane and adds alignment pin/hole features.
Runs in Blender's bundled Python — no pip dependencies.
"""

import json
import math
import sys
import argparse
from pathlib import Path

import bpy
import bmesh
from mathutils import Vector


def parse_args():
    argv = sys.argv
    if "--" in argv:
        argv = argv[argv.index("--") + 1:]
    else:
        argv = []

    parser = argparse.ArgumentParser(description="Split mesh into parts with alignment joints")
    parser.add_argument("--input", required=True, help="Input GLB path")
    parser.add_argument("--output-dir", required=True, help="Output directory for parts")
    parser.add_argument("--split-axis", default="Z", choices=["X", "Y", "Z"], help="Axis to split along")
    parser.add_argument("--split-at", type=float, default=0.5, help="Split position (0-1 fraction along axis)")
    parser.add_argument("--pin-radius", type=float, default=1.5, help="Alignment pin radius in mm")
    parser.add_argument("--pin-clearance", type=float, default=0.15, help="Pin/hole clearance in mm")
    parser.add_argument("--pin-depth", type=float, default=6.0, help="Pin depth in mm")
    parser.add_argument("--num-pins", type=int, default=2, help="Number of alignment pins")
    parser.add_argument("--no-pins", action="store_true", help="Skip adding alignment pins")
    parser.add_argument("--report", default="", help="Path to write JSON split report")
    return parser.parse_args(argv)


AXIS_MAP = {"X": 0, "Y": 1, "Z": 2}
AXIS_NORMAL = {"X": (1, 0, 0), "Y": (0, 1, 0), "Z": (0, 0, 1)}


def clear_scene():
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()


def import_glb(filepath):
    bpy.ops.import_scene.gltf(filepath=filepath)
    meshes = [o for o in bpy.data.objects if o.type == 'MESH']
    if not meshes:
        print("ERROR: No mesh objects found")
        sys.exit(1)

    if len(meshes) > 1:
        bpy.ops.object.select_all(action='DESELECT')
        for m in meshes:
            m.select_set(True)
        bpy.context.view_layer.objects.active = meshes[0]
        bpy.ops.object.join()

    return bpy.context.active_object


def get_split_point(obj, axis_idx, fraction):
    """Calculate the world-space split coordinate."""
    bbox = [obj.matrix_world @ Vector(corner) for corner in obj.bound_box]
    axis_vals = [v[axis_idx] for v in bbox]
    min_val, max_val = min(axis_vals), max(axis_vals)
    return min_val + (max_val - min_val) * fraction


def split_mesh(obj, axis, split_coord):
    """Bisect mesh at the given coordinate along the given axis."""
    axis_idx = AXIS_MAP[axis]
    normal = list(AXIS_NORMAL[axis])
    plane_co = [0, 0, 0]
    plane_co[axis_idx] = split_coord

    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)

    # Duplicate for the two halves
    bpy.ops.object.duplicate()
    obj_upper = bpy.context.active_object

    # Cut lower half (keep below split plane)
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.mesh.bisect(
        plane_co=plane_co,
        plane_no=normal,
        use_fill=True,
        clear_inner=False,
        clear_outer=True,
    )
    bpy.ops.object.mode_set(mode='OBJECT')

    # Cut upper half (keep above split plane)
    bpy.context.view_layer.objects.active = obj_upper
    obj_upper.select_set(True)
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.mesh.bisect(
        plane_co=plane_co,
        plane_no=normal,
        use_fill=True,
        clear_inner=True,
        clear_outer=False,
    )
    bpy.ops.object.mode_set(mode='OBJECT')

    obj.name = "part-001"
    obj_upper.name = "part-002"

    return [obj, obj_upper]


def add_pin(target_obj, location, radius_m, depth_m, is_hole=False):
    """Add a cylindrical pin (boolean union) or hole (boolean difference)."""
    clearance = 0.00015 if is_hole else 0  # 0.15mm in meters
    actual_radius = radius_m + clearance
    actual_depth = depth_m + (0.0005 if is_hole else 0)  # extra 0.5mm depth for holes

    bpy.ops.mesh.primitive_cylinder_add(
        radius=actual_radius,
        depth=actual_depth,
        location=location,
        vertices=32,
    )
    pin = bpy.context.active_object

    # Boolean operation
    bpy.context.view_layer.objects.active = target_obj
    mod = target_obj.modifiers.new(name="Pin", type='BOOLEAN')
    mod.operation = 'DIFFERENCE' if is_hole else 'UNION'
    mod.object = pin
    bpy.ops.object.modifier_apply(modifier="Pin")

    # Remove the tool object
    bpy.data.objects.remove(pin, do_unlink=True)


def add_alignment_pins(parts, axis, split_coord, pin_radius_mm, pin_depth_mm, num_pins):
    """Add alignment pins to the lower part and matching holes to the upper part."""
    axis_idx = AXIS_MAP[axis]
    lower_part, upper_part = parts[0], parts[1]

    # Get bounding box of lower part to place pins on the split face
    bbox = [lower_part.matrix_world @ Vector(corner) for corner in lower_part.bound_box]

    # Find the extent of the split face (perpendicular axes)
    perp_axes = [i for i in range(3) if i != axis_idx]
    centers = []
    for ax in perp_axes:
        vals = [v[ax] for v in bbox]
        centers.append((min(vals) + max(vals)) / 2)

    radius_m = pin_radius_mm / 1000
    depth_m = pin_depth_mm / 1000

    # Place pins evenly spaced along the longer perpendicular axis
    perp_vals = []
    for ax in perp_axes:
        vals = [v[ax] for v in bbox]
        perp_vals.append((min(vals), max(vals)))

    # Use the first perpendicular axis for pin spacing
    span = perp_vals[0][1] - perp_vals[0][0]
    spacing = span / (num_pins + 1)

    for i in range(num_pins):
        pin_loc = [0, 0, 0]
        pin_loc[axis_idx] = split_coord
        pin_loc[perp_axes[0]] = perp_vals[0][0] + spacing * (i + 1)
        pin_loc[perp_axes[1]] = centers[1] if len(centers) > 1 else 0

        # Pin on lower part (protruding up from split face)
        pin_offset = list(pin_loc)
        pin_offset[axis_idx] += depth_m / 2
        add_pin(lower_part, pin_offset, radius_m, depth_m, is_hole=False)

        # Hole on upper part (recessed into split face)
        hole_offset = list(pin_loc)
        hole_offset[axis_idx] -= depth_m / 2
        add_pin(upper_part, hole_offset, radius_m, depth_m, is_hole=True)


def export_part(obj, filepath):
    """Export a single object as GLB."""
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    bpy.ops.export_scene.gltf(
        filepath=filepath,
        export_format='GLB',
        use_selection=True,
    )


def main():
    args = parse_args()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    clear_scene()
    obj = import_glb(args.input)

    axis_idx = AXIS_MAP[args.split_axis]
    split_coord = get_split_point(obj, axis_idx, args.split_at)

    print(f"Splitting along {args.split_axis} at {split_coord:.4f}m "
          f"({split_coord * 1000:.1f}mm)")

    parts = split_mesh(obj, args.split_axis, split_coord)

    if not args.no_pins and len(parts) == 2:
        print(f"Adding {args.num_pins} alignment pins (r={args.pin_radius}mm, d={args.pin_depth}mm)")
        add_alignment_pins(
            parts, args.split_axis, split_coord,
            args.pin_radius, args.pin_depth, args.num_pins,
        )

    # Export each part
    part_files = []
    for i, part in enumerate(parts):
        part_path = str(output_dir / f"part-{i + 1:03d}.glb")
        export_part(part, part_path)
        face_count = len(part.data.polygons)
        dims = [d * 1000 for d in part.dimensions]
        part_files.append({
            "file": f"part-{i + 1:03d}.glb",
            "faces": face_count,
            "dimensions_mm": [round(d, 2) for d in dims],
        })
        print(f"Exported {part_path}: {face_count} faces, {[round(d, 1) for d in dims]}mm")

    # Write report
    if args.report:
        report = {
            "stage": "5-part-split",
            "input": args.input,
            "split_axis": args.split_axis,
            "split_position": args.split_at,
            "split_coord_mm": round(split_coord * 1000, 2),
            "num_parts": len(parts),
            "pins": {
                "count": args.num_pins if not args.no_pins else 0,
                "radius_mm": args.pin_radius,
                "clearance_mm": args.pin_clearance,
                "depth_mm": args.pin_depth,
            },
            "parts": part_files,
        }
        Path(args.report).write_text(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
