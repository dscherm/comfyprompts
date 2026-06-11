"""Fix back plate: build as a single watertight solid of revolution.

The cross-section boundary (revolved 360 degrees):

     z (axle_total)
     ^       P7
     |       |  (axle wall)
     |       P6----P5        plate_t + rim_h
     |              |   P4---P3
     |              |   |     |
     |       (base) |   |rim  |
     |       P1----P0   |     |    z = plate_t
     |              ..........|    (base top hidden behind profile)
     |                        |
     POLE_BOT          POLE_BOT... wait

Actually: closed profile boundary going clockwise:

    POLE_TOP (r=0, z=axle_total)  ← single vertex (top pole)
        |
        P7 (axle_r, axle_total)   axle top edge
        |
        P6 (axle_r, plate_t)      axle meets base top
        |
        P5 (rim_inner_r, plate_t) base top meets rim inner
        |
        P4 (rim_inner_r, plate_t+rim_h)  rim inner top
        |
        P3 (outer_r, plate_t+rim_h)      rim outer top
        |
        P2 (outer_r, 0)                  outer bottom
        |
        P1 (axle_r, 0)                   axle bottom
        |
    POLE_BOT (r=0, z=0)           ← single vertex (bottom pole)

Triangle fans at poles, quad strips between rings.
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
    p = argparse.ArgumentParser()
    p.add_argument("--output-dir", default=".")
    p.add_argument("--disk-radius-mm", type=float, default=101.6)
    p.add_argument("--disk-thickness-mm", type=float, default=2.0)
    p.add_argument("--axle-diameter-mm", type=float, default=6.0)
    p.add_argument("--tolerance-mm", type=float, default=0.3)
    p.add_argument("--rim-height-mm", type=float, default=3.0)
    p.add_argument("--plate-thickness-mm", type=float, default=2.0)
    p.add_argument("--outer-margin-mm", type=float, default=8.0)
    p.add_argument("--n", type=int, default=128)
    p.add_argument("--export-stl", action="store_true")
    return p.parse_args(argv)


def mm(v):
    """Pass through mm values directly — Blender units = mm for correct STL/Fusion import."""
    return v


def main():
    args = parse_args()
    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)

    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()

    n = args.n
    outer_r = mm(args.disk_radius_mm + args.outer_margin_mm)
    rim_inner_r = mm(args.disk_radius_mm + args.outer_margin_mm - 2.0)
    axle_r = mm(args.axle_diameter_mm / 2)
    plate_t = mm(args.plate_thickness_mm)
    rim_h = mm(args.rim_height_mm)
    axle_total = mm(args.plate_thickness_mm + args.rim_height_mm +
                    args.disk_thickness_mm + args.plate_thickness_mm + 2.0)

    # Closed profile boundary (r, z) going from top-pole down and around to bottom-pole
    # The winding order determines face normals (outward for CW when viewed from outside)
    profile = [
        # Going DOWN the axle, then RIGHT along bottom, UP the outer wall,
        # LEFT along rim top, DOWN rim inner, LEFT along base top, UP axle
        (axle_r, axle_total),                    # P7: axle top edge
        (axle_r, plate_t),                       # P6: axle meets base top
        (rim_inner_r, plate_t),                  # P5: base top meets rim
        (rim_inner_r, plate_t + rim_h),          # P4: rim inner top corner
        (outer_r, plate_t + rim_h),              # P3: rim outer top corner
        (outer_r, 0),                            # P2: outer bottom corner
        (axle_r, 0),                             # P1: axle bottom edge
    ]

    mesh = bpy.data.meshes.new("back-plate")
    bm = bmesh.new()

    # Create pole vertices
    pole_top = bm.verts.new(Vector((0, 0, axle_total)))
    pole_bot = bm.verts.new(Vector((0, 0, 0)))

    # Create vertex rings for each profile point
    rings = []
    for r, z in profile:
        ring = []
        for i in range(n):
            angle = 2 * math.pi * i / n
            ring.append(bm.verts.new(Vector((r * math.cos(angle),
                                              r * math.sin(angle), z))))
        rings.append(ring)

    # Triangle fan: pole_top → rings[0] (axle top cap)
    for i in range(n):
        j = (i + 1) % n
        bm.faces.new([pole_top, rings[0][i], rings[0][j]])

    # Quad strips between consecutive rings
    for ri in range(len(rings) - 1):
        r0 = rings[ri]
        r1 = rings[ri + 1]
        for i in range(n):
            j = (i + 1) % n
            bm.faces.new([r0[i], r1[i], r1[j], r0[j]])

    # Triangle fan: rings[-1] → pole_bot (axle bottom cap)
    for i in range(n):
        j = (i + 1) % n
        bm.faces.new([rings[-1][i], pole_bot, rings[-1][j]])

    bm.to_mesh(mesh)
    bm.free()
    mesh.update()

    obj = bpy.data.objects.new("back-plate", mesh)
    bpy.context.scene.collection.objects.link(obj)
    bpy.context.view_layer.objects.active = obj

    # Validate
    bm2 = bmesh.new()
    bm2.from_mesh(obj.data)
    nm = sum(1 for e in bm2.edges if not e.is_manifold)
    dims = [round(d * 1000, 2) for d in obj.dimensions]
    faces = len(bm2.faces)
    verts = len(bm2.verts)
    print(f"back-plate: {dims[0]:.1f}x{dims[1]:.1f}x{dims[2]:.1f}mm, "
          f"{verts} verts, {faces} faces, {nm} non-manifold, watertight={nm == 0}")
    bm2.free()

    # Export GLB
    glb_path = str(out / "back-plate.glb")
    obj.select_set(True)
    bpy.ops.export_scene.gltf(filepath=glb_path, export_format='GLB', use_selection=True)
    print(f"GLB: {Path(glb_path).stat().st_size} bytes")

    if args.export_stl:
        stl_path = str(out / "back-plate.stl")
        bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
        bpy.ops.wm.stl_export(filepath=stl_path, export_selected_objects=True, ascii_format=False)
        print(f"STL: {Path(stl_path).stat().st_size} bytes")

    print("DONE")


if __name__ == "__main__":
    main()
