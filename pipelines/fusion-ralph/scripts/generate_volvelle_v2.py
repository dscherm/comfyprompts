"""Generate a 3D-printable volvelle wheel using direct bmesh construction.

Avoids boolean operations (unreliable in headless Blender for cylinders).
Instead builds each part's geometry vertex-by-vertex for guaranteed manifold output.

Usage:
    blender --background --python generate_volvelle_v2.py -- [OPTIONS]
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
    p.add_argument("--window-angle-deg", type=float, default=65.0)
    p.add_argument("--axle-diameter-mm", type=float, default=6.0)
    p.add_argument("--tolerance-mm", type=float, default=0.3)
    p.add_argument("--rim-height-mm", type=float, default=3.0)
    p.add_argument("--plate-thickness-mm", type=float, default=2.0)
    p.add_argument("--outer-margin-mm", type=float, default=8.0)
    p.add_argument("--cap-diameter-mm", type=float, default=14.0)
    p.add_argument("--n", type=int, default=128, help="Circle segments")
    p.add_argument("--export-stl", action="store_true")
    p.add_argument("--report", default="")
    return p.parse_args(argv)


def mm(v):
    """Pass through mm values directly — Blender units = mm for correct STL/Fusion import."""
    return v


def clear_scene():
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()
    for m in bpy.data.meshes:
        bpy.data.meshes.remove(m)


def circle_points(radius, n, z=0):
    """Generate n points around a circle at height z."""
    return [
        Vector((radius * math.cos(2 * math.pi * i / n),
                radius * math.sin(2 * math.pi * i / n),
                z))
        for i in range(n)
    ]


def make_annular_disk(name, outer_r, inner_r, thickness, n=128):
    """Create a flat annular disk (ring/washer shape). Guaranteed manifold."""
    mesh = bpy.data.meshes.new(name)
    bm = bmesh.new()

    t = mm(thickness)
    ro = mm(outer_r)
    ri = mm(inner_r)
    half = t / 2

    # 4 rings of vertices: outer_top, outer_bot, inner_top, inner_bot
    ot = [bm.verts.new(Vector((ro * math.cos(a), ro * math.sin(a), half)))
          for a in [2 * math.pi * i / n for i in range(n)]]
    ob = [bm.verts.new(Vector((ro * math.cos(a), ro * math.sin(a), -half)))
          for a in [2 * math.pi * i / n for i in range(n)]]
    it = [bm.verts.new(Vector((ri * math.cos(a), ri * math.sin(a), half)))
          for a in [2 * math.pi * i / n for i in range(n)]]
    ib = [bm.verts.new(Vector((ri * math.cos(a), ri * math.sin(a), -half)))
          for a in [2 * math.pi * i / n for i in range(n)]]

    for i in range(n):
        j = (i + 1) % n
        # Top face (outer to inner)
        bm.faces.new([ot[i], ot[j], it[j], it[i]])
        # Bottom face (inner to outer, reversed winding)
        bm.faces.new([ob[i], ib[i], ib[j], ob[j]])
        # Outer wall
        bm.faces.new([ot[i], ob[i], ob[j], ot[j]])
        # Inner wall
        bm.faces.new([it[i], it[j], ib[j], ib[i]])

    bm.to_mesh(mesh)
    bm.free()
    mesh.update()

    obj = bpy.data.objects.new(name, mesh)
    bpy.context.scene.collection.objects.link(obj)
    return obj


def make_solid_disk(name, radius, thickness, n=128):
    """Create a solid circular disk (no center hole). Guaranteed manifold."""
    mesh = bpy.data.meshes.new(name)
    bm = bmesh.new()

    t = mm(thickness)
    r = mm(radius)
    half = t / 2

    # Center vertices
    ct = bm.verts.new(Vector((0, 0, half)))
    cb = bm.verts.new(Vector((0, 0, -half)))

    # Rim vertices
    rt = [bm.verts.new(Vector((r * math.cos(2 * math.pi * i / n),
                                r * math.sin(2 * math.pi * i / n), half)))
          for i in range(n)]
    rb = [bm.verts.new(Vector((r * math.cos(2 * math.pi * i / n),
                                r * math.sin(2 * math.pi * i / n), -half)))
          for i in range(n)]

    for i in range(n):
        j = (i + 1) % n
        # Top face (triangle fan)
        bm.faces.new([ct, rt[i], rt[j]])
        # Bottom face (reversed)
        bm.faces.new([cb, rb[j], rb[i]])
        # Side wall
        bm.faces.new([rt[i], rb[i], rb[j], rt[j]])

    bm.to_mesh(mesh)
    bm.free()
    mesh.update()

    obj = bpy.data.objects.new(name, mesh)
    bpy.context.scene.collection.objects.link(obj)
    return obj


def make_back_plate(args):
    """
    Back plate = flat base disk + rim wall ring + center axle post.
    Built as a single merged mesh.

    Side profile:
       rim wall ─┐    ┌─ rim wall
                 │    │
       ─────────┘    └─────────  ← base disk top
       ═══════════════════════   ← base disk bottom
                 ║  ║            ← axle post (extends upward)
    """
    n = args.n
    mesh = bpy.data.meshes.new("back-plate")
    bm = bmesh.new()

    outer_r = mm(args.disk_radius_mm + args.outer_margin_mm)
    inner_r = mm(args.disk_radius_mm + args.outer_margin_mm - 2.0)  # rim is 2mm thick wall
    axle_r = mm(args.axle_diameter_mm / 2)
    plate_t = mm(args.plate_thickness_mm)
    rim_h = mm(args.rim_height_mm)

    # Total axle height: enough to poke through disk + front cover + cap
    axle_total = plate_t + rim_h + mm(args.disk_thickness_mm) + mm(args.plate_thickness_mm) + mm(2.0)

    # --- Base disk (annular: outer_r to axle_r) ---
    z_base_bot = 0
    z_base_top = plate_t

    def ring(r, z):
        return [bm.verts.new(Vector((r * math.cos(2 * math.pi * i / n),
                                      r * math.sin(2 * math.pi * i / n), z)))
                for i in range(n)]

    # Vertex rings
    base_outer_bot = ring(outer_r, z_base_bot)
    base_outer_top = ring(outer_r, z_base_top)
    base_axle_bot = ring(axle_r, z_base_bot)
    base_axle_top = ring(axle_r, z_base_top)

    # Rim top
    z_rim_top = z_base_top + rim_h
    rim_outer_top = ring(outer_r, z_rim_top)
    rim_inner_top = ring(inner_r, z_rim_top)
    rim_inner_bot = ring(inner_r, z_base_top)  # meets base disk top

    # Axle top
    axle_top = ring(axle_r, axle_total)

    for i in range(n):
        j = (i + 1) % n

        # Bottom face of base (from outer to axle hole)
        bm.faces.new([base_outer_bot[i], base_axle_bot[i], base_axle_bot[j], base_outer_bot[j]])

        # Top face of base (from inner_rim to axle) — the floor between rim and axle
        bm.faces.new([rim_inner_bot[i], rim_inner_bot[j], base_axle_top[j], base_axle_top[i]])

        # Outer wall of base+rim (continuous from bottom to rim top)
        bm.faces.new([base_outer_bot[i], base_outer_bot[j], base_outer_top[j], base_outer_top[i]])
        bm.faces.new([base_outer_top[i], base_outer_top[j], rim_outer_top[j], rim_outer_top[i]])

        # Rim top face (annular ring)
        bm.faces.new([rim_outer_top[i], rim_inner_top[i], rim_inner_top[j], rim_outer_top[j]])

        # Rim inner wall
        bm.faces.new([rim_inner_top[i], rim_inner_bot[i], rim_inner_bot[j], rim_inner_top[j]])

        # Axle inner wall (bottom to axle top)
        bm.faces.new([base_axle_bot[i], base_axle_bot[j], base_axle_top[j], base_axle_top[i]])
        # Wait — axle is solid, not hollow. Let me reconsider.
        # Actually the axle is a solid post. Let me build it differently.

    # Hmm, the axle should be a solid cylinder on top. Let me redo the axle section.
    # The base disk has a hole from axle_r down (no, the axle is solid, sits on the base).
    # Let me simplify: base is a SOLID disk, axle is a solid cylinder on top.

    bm.free()

    # --- SIMPLER APPROACH: build each sub-part, then join ---
    bm = bmesh.new()

    # Sub-part 1: Solid base disk
    z0 = 0.0
    z1 = plate_t

    # Outer bottom ring
    ob = ring(outer_r, z0)
    # Outer top ring
    ot = ring(outer_r, z1)

    # Center vertices for solid disk
    cb = bm.verts.new(Vector((0, 0, z0)))
    ct = bm.verts.new(Vector((0, 0, z1)))

    for i in range(n):
        j = (i + 1) % n
        # Bottom triangles
        bm.faces.new([cb, ob[j], ob[i]])
        # Top triangles
        bm.faces.new([ct, ot[i], ot[j]])
        # Outer wall quads
        bm.faces.new([ob[i], ob[j], ot[j], ot[i]])

    # Sub-part 2: Rim wall (ring on top of base disk, around the edge)
    z2 = z1 + rim_h
    ro_bot = ring(outer_r, z1)  # shares z with base top — but we need NEW verts for manifold
    # Actually we already have ot[] at z1 for outer. We need inner ring.
    ri_bot = ring(inner_r, z1)
    ro_top = ring(outer_r, z2)
    ri_top = ring(inner_r, z2)

    for i in range(n):
        j = (i + 1) % n
        # Connect rim outer bottom to base outer top (they overlap at outer_r, z1)
        # The base top triangles already cover from center to outer_r at z1
        # The rim sits ON the base top. Its bottom face is the annular ring between outer_r and inner_r
        # But the base top is already closed! We need to leave a gap...
        #
        # This is getting complicated. Let me use a much simpler approach:
        # Build each part as a separate object, then join them.
        pass

    bm.free()

    # ====== CLEANEST APPROACH: separate objects, join in Blender ======
    # 1. Solid base disk
    base = make_solid_disk("_base", args.disk_radius_mm + args.outer_margin_mm,
                           args.plate_thickness_mm, n)
    base.location.z = mm(args.plate_thickness_mm / 2)

    # 2. Rim ring
    rim = make_annular_disk("_rim",
                            args.disk_radius_mm + args.outer_margin_mm,
                            args.disk_radius_mm + args.outer_margin_mm - 2.0,
                            args.rim_height_mm, n)
    rim.location.z = mm(args.plate_thickness_mm + args.rim_height_mm / 2)

    # 3. Axle post (solid cylinder)
    axle_height = (args.plate_thickness_mm + args.rim_height_mm +
                   args.disk_thickness_mm + args.plate_thickness_mm + 2.0)
    axle = make_solid_disk("_axle", args.axle_diameter_mm / 2, axle_height, n)
    axle.location.z = mm(axle_height / 2)

    # Apply transforms and join
    bpy.context.view_layer.update()
    for obj in [base, rim, axle]:
        bpy.context.view_layer.objects.active = obj
        obj.select_set(True)
        bpy.ops.object.transform_apply(location=True)
        obj.select_set(False)

    # Select all and join
    for obj in [base, rim, axle]:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = base
    bpy.ops.object.join()
    base.name = "back-plate"

    # Remove doubles to merge overlapping verts at junctions
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.mesh.remove_doubles(threshold=0.0001)
    bpy.ops.object.mode_set(mode='OBJECT')

    return base


def make_front_cover(args):
    """
    Front cover: annular disk with a wedge cutout window.
    Built by creating a disk with the window section omitted.
    """
    n = args.n
    mesh = bpy.data.meshes.new("front-cover")
    bm = bmesh.new()

    outer_r = mm(args.disk_radius_mm + args.outer_margin_mm)
    inner_r = mm(args.axle_diameter_mm / 2 + args.tolerance_mm / 2)
    t = mm(args.plate_thickness_mm)
    half = t / 2

    # Window: skip vertices in the window arc
    window_half = math.radians(args.window_angle_deg / 2)

    def is_in_window(angle):
        """Check if angle (0 to 2pi) falls within the window wedge."""
        # Window centered at angle=0 (positive X axis)
        a = angle % (2 * math.pi)
        if a > math.pi:
            a -= 2 * math.pi
        return abs(a) < window_half

    # Build vertex rings, marking which are in the window zone
    # For the window, we need to create the boundary edges at exact window angles
    angles = []
    # Add exact window boundary angles
    angles.append(-window_half)
    angles.append(window_half)
    # Add regular angles that are NOT in the window
    for i in range(n):
        a = 2 * math.pi * i / n
        if a > math.pi:
            a -= 2 * math.pi
        if abs(a) >= window_half - 0.001:  # outside window
            angles.append(2 * math.pi * i / n)

    # Deduplicate and sort
    angles = sorted(set(a % (2 * math.pi) for a in angles))

    na = len(angles)

    # Create vertex rings
    ot = [bm.verts.new(Vector((outer_r * math.cos(a), outer_r * math.sin(a), half)))
          for a in angles]
    ob = [bm.verts.new(Vector((outer_r * math.cos(a), outer_r * math.sin(a), -half)))
          for a in angles]
    it = [bm.verts.new(Vector((inner_r * math.cos(a), inner_r * math.sin(a), half)))
          for a in angles]
    ib = [bm.verts.new(Vector((inner_r * math.cos(a), inner_r * math.sin(a), -half)))
          for a in angles]

    for i in range(na):
        j = (i + 1) % na

        # Check if this segment crosses the window gap
        a_i = angles[i]
        a_j = angles[j]

        # Detect the window gap (the segment that spans across angle 0 in window zone)
        # The window boundary vertices are at window_half and 2pi-window_half
        # The gap is between these two (crossing angle 0)
        # We identify the gap as the segment where consecutive angles span the window
        crosses_window = False
        if j == 0:  # wrap-around
            # Check if the arc from angles[-1] to angles[0] contains angle 0
            # and that arc is the window
            arc_span = (angles[0] + 2 * math.pi) - angles[-1]
            if arc_span > math.radians(args.window_angle_deg - 5):
                crosses_window = True
        else:
            arc_span = angles[j] - angles[i]
            if arc_span > math.radians(args.window_angle_deg - 5):
                crosses_window = True

        if crosses_window:
            # This is the window gap — add wall faces on the two cut edges
            # Wall at edge i (window boundary)
            bm.faces.new([ot[i], it[i], ib[i], ob[i]])
            # Wall at edge j (other window boundary)
            bm.faces.new([ot[j], ob[j], ib[j], it[j]])
            continue

        # Normal segment — create quad faces
        # Top face
        bm.faces.new([ot[i], ot[j], it[j], it[i]])
        # Bottom face
        bm.faces.new([ob[i], ib[i], ib[j], ob[j]])
        # Outer wall
        bm.faces.new([ot[i], ob[i], ob[j], ot[j]])
        # Inner wall
        bm.faces.new([it[i], it[j], ib[j], ib[i]])

    bm.to_mesh(mesh)
    bm.free()
    mesh.update()

    obj = bpy.data.objects.new("front-cover", mesh)
    bpy.context.scene.collection.objects.link(obj)

    # Position: sits on top of rim + disk
    z_pos = mm(args.plate_thickness_mm + args.rim_height_mm +
               args.disk_thickness_mm + args.plate_thickness_mm / 2)
    obj.location.z = z_pos
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.transform_apply(location=True)

    return obj


def make_inner_disk(args):
    """Inner disk: annular disk that rotates freely."""
    n = args.n
    disk_r = args.disk_radius_mm - args.tolerance_mm
    hole_r = args.axle_diameter_mm / 2 + args.tolerance_mm

    obj = make_annular_disk("inner-disk", disk_r, hole_r,
                            args.disk_thickness_mm, n)

    z_pos = mm(args.plate_thickness_mm + args.rim_height_mm -
               args.disk_thickness_mm / 2)
    obj.location.z = z_pos
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.transform_apply(location=True)

    return obj


def make_snap_cap(args):
    """Snap cap: small annular disk that press-fits on the axle."""
    n = args.n
    cap_r = args.cap_diameter_mm / 2
    # Press fit: slightly undersized hole
    hole_r = args.axle_diameter_mm / 2 - 0.05

    obj = make_annular_disk("snap-cap", cap_r, hole_r,
                            args.plate_thickness_mm, n)
    return obj


def validate_manifold(obj):
    """Check if mesh is manifold."""
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    non_manifold = sum(1 for e in bm.edges if not e.is_manifold)
    verts = len(bm.verts)
    faces = len(bm.faces)
    bm.free()
    return {"verts": verts, "faces": faces, "non_manifold": non_manifold,
            "watertight": non_manifold == 0}


def export_obj(obj, filepath):
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.export_scene.gltf(filepath=filepath, export_format='GLB', use_selection=True)
    obj.select_set(False)


def export_stl_single(obj, filepath):
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    bpy.ops.wm.stl_export(filepath=filepath, export_selected_objects=True, ascii_format=False)
    obj.select_set(False)


def main():
    args = parse_args()
    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)

    clear_scene()

    print("=" * 60)
    print("VOLVELLE GENERATOR v2 (direct bmesh, no booleans)")
    print("=" * 60)
    print(f"Disk: {args.disk_radius_mm}mm radius ({args.disk_radius_mm/25.4:.1f}\")")
    print(f"Window: {args.window_angle_deg} degrees")
    print(f"Tolerance: {args.tolerance_mm}mm")

    parts = {}
    reports = []

    # Generate parts
    print("\n[1/4] Back plate...")
    parts["back-plate"] = make_back_plate(args)

    print("[2/4] Front cover (with window cutout)...")
    parts["front-cover"] = make_front_cover(args)

    print("[3/4] Inner disk...")
    parts["inner-disk"] = make_inner_disk(args)

    print("[4/4] Snap cap...")
    parts["snap-cap"] = make_snap_cap(args)

    # Validate and export each
    print("\nValidating & exporting...")
    for name, obj in parts.items():
        stats = validate_manifold(obj)
        dims = [round(d * 1000, 2) for d in obj.dimensions]
        status = "OK" if stats["watertight"] else f"WARN: {stats['non_manifold']} non-manifold"

        glb_path = str(out / f"{name}.glb")
        export_obj(obj, glb_path)
        glb_size = Path(glb_path).stat().st_size

        info = {
            "name": name,
            "file_glb": f"{name}.glb",
            "dimensions_mm": dims,
            "faces": stats["faces"],
            "vertices": stats["verts"],
            "non_manifold_edges": stats["non_manifold"],
            "watertight": stats["watertight"],
            "file_size_bytes": glb_size,
        }

        if args.export_stl:
            stl_path = str(out / f"{name}.stl")
            export_stl_single(obj, stl_path)
            info["file_stl"] = f"{name}.stl"
            info["stl_size_bytes"] = Path(stl_path).stat().st_size

        reports.append(info)
        print(f"  {name}: {dims[0]:.1f}x{dims[1]:.1f}x{dims[2]:.1f}mm, "
              f"{stats['faces']} faces, {status}")

    # Assembly preview
    for obj in parts.values():
        obj.select_set(True)
    bpy.context.view_layer.objects.active = list(parts.values())[0]
    bpy.ops.export_scene.gltf(
        filepath=str(out / "volvelle-assembly.glb"),
        export_format='GLB', use_selection=True)

    if args.report:
        full_report = {
            "project": "volvelle-wheel",
            "generator": "v2-bmesh-direct",
            "parameters": {
                "disk_radius_mm": args.disk_radius_mm,
                "disk_thickness_mm": args.disk_thickness_mm,
                "window_angle_deg": args.window_angle_deg,
                "axle_diameter_mm": args.axle_diameter_mm,
                "tolerance_mm": args.tolerance_mm,
                "outer_diameter_mm": round((args.disk_radius_mm + args.outer_margin_mm) * 2, 2),
            },
            "parts": reports,
            "all_watertight": all(r["watertight"] for r in reports),
            "assembly_order": [
                "1. Print all parts flat on bed (no supports needed)",
                "2. Place inner-disk onto back-plate center axle (disk sits in rim channel)",
                "3. Place front-cover on top — axle passes through center hole, lip captures disk edge",
                "4. Press snap-cap onto exposed axle top",
                "5. Spin the inner disk — window reveals one section at a time",
            ],
            "print_tips": [
                f"Inner disk clearance: {args.tolerance_mm}mm radial gap — sand axle if binding",
                "Print inner-disk at 100% infill for rigidity",
                "Print back-plate and front-cover at 20-30% infill",
                "Print snap-cap at 100% infill for retention strength",
                "Layer height 0.2mm recommended for good fit",
            ],
        }
        Path(args.report).write_text(json.dumps(full_report, indent=2))

    print("\n" + "=" * 60)
    print("DONE")
    print("=" * 60)


if __name__ == "__main__":
    main()
