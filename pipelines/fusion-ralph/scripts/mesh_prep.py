"""Blender headless mesh preparation script for fusion-ralph pipeline.

Usage:
    blender --background --python mesh_prep.py -- \
        --input INPUT.glb --output OUTPUT.glb \
        [--min-wall 1.2] [--target-faces 50000] \
        [--fix-manifold] [--fix-normals] [--remove-degenerate] \
        [--scale-height-mm 100]

Runs in Blender's bundled Python — no pip dependencies.
"""

import json
import sys
import argparse
from pathlib import Path

import bpy
import bmesh


def parse_args():
    """Parse arguments after '--' separator."""
    argv = sys.argv
    if "--" in argv:
        argv = argv[argv.index("--") + 1:]
    else:
        argv = []

    parser = argparse.ArgumentParser(description="Mesh preparation for 3D printing")
    parser.add_argument("--input", required=True, help="Input GLB path")
    parser.add_argument("--output", required=True, help="Output GLB path")
    parser.add_argument("--min-wall", type=float, default=1.2, help="Minimum wall thickness in mm")
    parser.add_argument("--target-faces", type=int, default=50000, help="Target face count")
    parser.add_argument("--fix-manifold", action="store_true", help="Repair non-manifold edges")
    parser.add_argument("--fix-normals", action="store_true", help="Recalculate normals outward")
    parser.add_argument("--remove-degenerate", action="store_true", help="Remove degenerate faces")
    parser.add_argument("--scale-height-mm", type=float, default=0, help="Scale model to this height in mm (0=no scale)")
    parser.add_argument("--report", default="", help="Path to write JSON prep report")
    return parser.parse_args(argv)


def clear_scene():
    """Remove all objects from the scene."""
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()


def import_glb(filepath):
    """Import GLB and return the first mesh object."""
    bpy.ops.import_scene.gltf(filepath=filepath)
    meshes = [o for o in bpy.data.objects if o.type == 'MESH']
    if not meshes:
        print("ERROR: No mesh objects found in GLB")
        sys.exit(1)

    # Join all meshes into one if multiple
    if len(meshes) > 1:
        bpy.ops.object.select_all(action='DESELECT')
        for m in meshes:
            m.select_set(True)
        bpy.context.view_layer.objects.active = meshes[0]
        bpy.ops.object.join()

    obj = bpy.context.active_object
    return obj


def get_mesh_stats(obj):
    """Return mesh statistics dict."""
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    non_manifold = [e for e in bm.edges if not e.is_manifold]
    degenerate = 0
    for f in bm.faces:
        if f.calc_area() < 1e-8:
            degenerate += 1

    stats = {
        "vertices": len(bm.verts),
        "faces": len(bm.faces),
        "edges": len(bm.edges),
        "non_manifold_edges": len(non_manifold),
        "degenerate_faces": degenerate,
        "dimensions_mm": [d * 1000 for d in obj.dimensions],
        "is_manifold": len(non_manifold) == 0,
    }
    bm.free()
    return stats


def fix_manifold(obj):
    """Repair non-manifold edges by filling holes and merging doubles."""
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode='EDIT')

    # Merge by distance first
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.mesh.remove_doubles(threshold=0.0001)

    # Select and fill non-manifold
    bpy.ops.mesh.select_all(action='DESELECT')
    bpy.ops.mesh.select_non_manifold()
    bpy.ops.mesh.fill_holes(sides=32)

    # One more merge pass
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.mesh.remove_doubles(threshold=0.0001)

    bpy.ops.object.mode_set(mode='OBJECT')


def fix_normals(obj):
    """Recalculate normals to face outward consistently."""
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.mesh.normals_make_consistent(inside=False)
    bpy.ops.object.mode_set(mode='OBJECT')


def remove_degenerate(obj):
    """Remove degenerate (zero-area) faces."""
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.mesh.dissolve_degenerate(threshold=0.0001)
    bpy.ops.object.mode_set(mode='OBJECT')


def decimate(obj, target_faces):
    """Decimate mesh to target face count."""
    current_faces = len(obj.data.polygons)
    if current_faces <= target_faces:
        return current_faces, current_faces  # No decimation needed

    ratio = target_faces / current_faces
    mod = obj.modifiers.new(name="Decimate", type='DECIMATE')
    mod.ratio = max(ratio, 0.01)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.modifier_apply(modifier="Decimate")

    return current_faces, len(obj.data.polygons)


def scale_to_height(obj, target_height_mm):
    """Scale model so its Z dimension matches target height in mm."""
    if target_height_mm <= 0:
        return

    current_height_m = obj.dimensions.z
    if current_height_m < 1e-6:
        print("WARNING: Model has near-zero height, skipping scale")
        return

    scale_factor = (target_height_mm / 1000) / current_height_m
    obj.scale = (scale_factor, scale_factor, scale_factor)
    bpy.ops.object.transform_apply(scale=True)


def export_glb(filepath):
    """Export all mesh objects as GLB."""
    bpy.ops.export_scene.gltf(
        filepath=filepath,
        export_format='GLB',
        use_selection=False,
    )


def main():
    args = parse_args()
    operations = []

    clear_scene()
    obj = import_glb(args.input)
    before_stats = get_mesh_stats(obj)
    print(f"BEFORE: {json.dumps(before_stats, indent=2)}")

    # Apply repairs in order
    if args.remove_degenerate:
        before_deg = before_stats["degenerate_faces"]
        remove_degenerate(obj)
        after_stats = get_mesh_stats(obj)
        operations.append({
            "op": "remove_degenerate",
            "before": before_deg,
            "after": after_stats["degenerate_faces"],
        })

    if args.fix_manifold:
        before_nm = get_mesh_stats(obj)["non_manifold_edges"]
        fix_manifold(obj)
        after_nm = get_mesh_stats(obj)["non_manifold_edges"]
        operations.append({
            "op": "manifold_repair",
            "before": before_nm,
            "after": after_nm,
        })

    if args.fix_normals:
        fix_normals(obj)
        operations.append({"op": "normal_recalc"})

    # Decimation
    before_faces, after_faces = decimate(obj, args.target_faces)
    if before_faces != after_faces:
        operations.append({
            "op": "decimation",
            "before_faces": before_faces,
            "after_faces": after_faces,
            "ratio": round(after_faces / before_faces, 3),
        })

    # Scale
    if args.scale_height_mm > 0:
        before_dims = [d * 1000 for d in obj.dimensions]
        scale_to_height(obj, args.scale_height_mm)
        after_dims = [d * 1000 for d in obj.dimensions]
        operations.append({
            "op": "scale",
            "before_mm": [round(d, 2) for d in before_dims],
            "after_mm": [round(d, 2) for d in after_dims],
        })

    # Export
    export_glb(args.output)

    after_stats = get_mesh_stats(obj)
    print(f"AFTER: {json.dumps(after_stats, indent=2)}")

    # Write report if requested
    if args.report:
        report = {
            "stage": "4-mesh-prep",
            "input": args.input,
            "output": args.output,
            "operations_applied": operations,
            "before_metrics": before_stats,
            "final_metrics": after_stats,
        }
        Path(args.report).write_text(json.dumps(report, indent=2))
        print(f"Report written to {args.report}")


if __name__ == "__main__":
    main()
