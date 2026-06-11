"""Blender headless GLB to STL converter for fusion-ralph pipeline.

Usage:
    blender --background --python glb_to_stl.py -- \
        --input INPUT.glb --output OUTPUT.stl [--binary]

Runs in Blender's bundled Python — no pip dependencies.
"""

import json
import sys
import argparse
from pathlib import Path

import bpy


def parse_args():
    argv = sys.argv
    if "--" in argv:
        argv = argv[argv.index("--") + 1:]
    else:
        argv = []

    parser = argparse.ArgumentParser(description="Convert GLB to STL")
    parser.add_argument("--input", required=True, help="Input GLB path")
    parser.add_argument("--output", required=True, help="Output STL path")
    parser.add_argument("--ascii", action="store_true", help="Use ASCII STL format (default: binary)")
    parser.add_argument("--report", default="", help="Path to write JSON conversion report")
    return parser.parse_args(argv)


def main():
    args = parse_args()

    # Clear scene
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()

    # Import GLB
    bpy.ops.import_scene.gltf(filepath=args.input)

    # Select all mesh objects
    mesh_objects = [o for o in bpy.data.objects if o.type == 'MESH']
    if not mesh_objects:
        print("ERROR: No mesh objects found")
        sys.exit(1)

    total_faces = 0
    for obj in mesh_objects:
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj
        total_faces += len(obj.data.polygons)

    # Apply all transforms
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)

    # Get dimensions before export
    # Use bounding box of all selected objects
    min_coords = [float('inf')] * 3
    max_coords = [float('-inf')] * 3
    for obj in mesh_objects:
        for corner in obj.bound_box:
            world_corner = obj.matrix_world @ bpy.app.driver_namespace.get("Vector", __import__("mathutils").Vector)(corner)
            for i in range(3):
                min_coords[i] = min(min_coords[i], world_corner[i])
                max_coords[i] = max(max_coords[i], world_corner[i])

    dims_mm = [(max_coords[i] - min_coords[i]) * 1000 for i in range(3)]

    # Export STL
    bpy.ops.wm.stl_export(
        filepath=args.output,
        export_selected_objects=True,
        ascii_format=args.ascii,
    )

    output_size = Path(args.output).stat().st_size

    print(f"Exported: {args.output}")
    print(f"  Faces: {total_faces}")
    print(f"  Dimensions (mm): {[round(d, 2) for d in dims_mm]}")
    print(f"  File size: {output_size} bytes")
    print(f"  Format: {'ASCII' if args.ascii else 'Binary'}")

    if args.report:
        report = {
            "input": args.input,
            "output": args.output,
            "faces": total_faces,
            "dimensions_mm": [round(d, 2) for d in dims_mm],
            "file_size_bytes": output_size,
            "format": "ascii" if args.ascii else "binary",
        }
        Path(args.report).write_text(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
