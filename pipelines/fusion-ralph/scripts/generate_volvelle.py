"""Generate a 3D-printable volvelle wheel using Blender's parametric primitives.

This is a precision mechanical assembly — AI mesh generation would produce
lumpy approximations. Instead, we use Blender's exact geometry primitives
to create print-ready parts with proper tolerances.

Usage:
    blender --background --python generate_volvelle.py -- [OPTIONS]

Options:
    --output-dir DIR          Output directory for GLB/STL files
    --disk-radius-mm FLOAT    Inner disk radius (default: 101.6 = 4 inches)
    --disk-thickness-mm FLOAT Inner disk thickness (default: 2.0)
    --window-angle-deg FLOAT  Window cutout angle (default: 65)
    --axle-diameter-mm FLOAT  Center axle diameter (default: 6.0)
    --tolerance-mm FLOAT      Clearance tolerance (default: 0.3)
    --rim-height-mm FLOAT     Back plate rim height (default: 3.0)
    --cover-lip-mm FLOAT      Front cover lip depth (default: 1.5)
    --plate-thickness-mm FLOAT Plate wall thickness (default: 2.0)
    --outer-margin-mm FLOAT   Extra radius beyond disk edge (default: 8.0)
    --export-stl              Also export STL files
    --export-step             Export STEP via FreeCAD (if available)
"""

import json
import math
import sys
import argparse
from pathlib import Path

import bpy
import bmesh
from mathutils import Vector, Matrix


def parse_args():
    argv = sys.argv
    if "--" in argv:
        argv = argv[argv.index("--") + 1:]
    else:
        argv = []

    p = argparse.ArgumentParser(description="Generate parametric volvelle wheel")
    p.add_argument("--output-dir", default=".", help="Output directory")
    p.add_argument("--disk-radius-mm", type=float, default=101.6)
    p.add_argument("--disk-thickness-mm", type=float, default=2.0)
    p.add_argument("--window-angle-deg", type=float, default=65.0)
    p.add_argument("--axle-diameter-mm", type=float, default=6.0)
    p.add_argument("--tolerance-mm", type=float, default=0.3)
    p.add_argument("--rim-height-mm", type=float, default=3.0)
    p.add_argument("--cover-lip-mm", type=float, default=1.5)
    p.add_argument("--plate-thickness-mm", type=float, default=2.0)
    p.add_argument("--outer-margin-mm", type=float, default=8.0)
    p.add_argument("--cap-diameter-mm", type=float, default=14.0)
    p.add_argument("--segments", type=int, default=128, help="Circle smoothness")
    p.add_argument("--export-stl", action="store_true")
    p.add_argument("--report", default="", help="JSON report path")
    return p.parse_args(argv)


# --- Helpers ---

def mm(val):
    """Convert mm to Blender meters."""
    return val / 1000.0


def clear_scene():
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()
    for mesh in bpy.data.meshes:
        bpy.data.meshes.remove(mesh)


def new_collection(name):
    col = bpy.data.collections.new(name)
    bpy.context.scene.collection.children.link(col)
    return col


def move_to_collection(obj, collection):
    for c in obj.users_collection:
        c.objects.unlink(obj)
    collection.objects.link(obj)


def add_cylinder(name, radius_mm, depth_mm, segments=128, location=(0, 0, 0)):
    """Add a cylinder at the given location (mm inputs, converted to meters)."""
    bpy.ops.mesh.primitive_cylinder_add(
        radius=mm(radius_mm),
        depth=mm(depth_mm),
        vertices=segments,
        location=(mm(location[0]), mm(location[1]), mm(location[2])),
    )
    obj = bpy.context.active_object
    obj.name = name
    return obj


def boolean_op(target, tool, operation='DIFFERENCE'):
    """Apply boolean operation: DIFFERENCE, UNION, or INTERSECT."""
    mod = target.modifiers.new(name=f"Bool_{tool.name}", type='BOOLEAN')
    mod.operation = operation
    mod.object = tool
    mod.solver = 'EXACT'
    bpy.context.view_layer.objects.active = target
    bpy.ops.object.modifier_apply(modifier=mod.name)
    bpy.data.objects.remove(tool, do_unlink=True)


def add_wedge(name, radius_mm, depth_mm, angle_deg, segments=128):
    """Create a wedge (pie slice) shape for the window cutout."""
    r = mm(radius_mm)
    d = mm(depth_mm)

    mesh = bpy.data.meshes.new(name)
    bm = bmesh.new()

    # Build a pie-slice shape
    half_angle = math.radians(angle_deg / 2)
    n_arc = max(4, int(segments * angle_deg / 360))

    # Center vertex (top and bottom)
    center_top = bm.verts.new((0, 0, d / 2))
    center_bot = bm.verts.new((0, 0, -d / 2))

    top_verts = [center_top]
    bot_verts = [center_bot]

    for i in range(n_arc + 1):
        angle = -half_angle + (angle_deg / n_arc) * i
        angle_rad = math.radians(angle) if isinstance(angle, (int, float)) else angle
        # Recalculate since angle is already in radians from half_angle
        frac = i / n_arc
        a = -half_angle + frac * 2 * half_angle

        x = r * math.cos(a)
        y = r * math.sin(a)
        top_verts.append(bm.verts.new((x, y, d / 2)))
        bot_verts.append(bm.verts.new((x, y, -d / 2)))

    # Top face (fan from center)
    for i in range(1, len(top_verts) - 1):
        bm.faces.new([top_verts[0], top_verts[i], top_verts[i + 1]])

    # Bottom face (fan from center, reversed winding)
    for i in range(1, len(bot_verts) - 1):
        bm.faces.new([bot_verts[0], bot_verts[i + 1], bot_verts[i]])

    # Side faces (connect top and bottom arcs)
    for i in range(1, len(top_verts) - 1):
        bm.faces.new([top_verts[i], bot_verts[i], bot_verts[i + 1], top_verts[i + 1]])

    # Two straight side walls (center to arc endpoints)
    bm.faces.new([top_verts[0], top_verts[1], bot_verts[1], bot_verts[0]])
    bm.faces.new([top_verts[0], bot_verts[0], bot_verts[-1], top_verts[-1]])

    bm.to_mesh(mesh)
    bm.free()

    obj = bpy.data.objects.new(name, mesh)
    bpy.context.scene.collection.objects.link(obj)
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    return obj


def export_glb(objects, filepath):
    """Export specific objects as GLB."""
    bpy.ops.object.select_all(action='DESELECT')
    for obj in objects:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = objects[0]
    bpy.ops.export_scene.gltf(
        filepath=filepath,
        export_format='GLB',
        use_selection=True,
    )
    bpy.ops.object.select_all(action='DESELECT')


def export_stl(objects, filepath):
    """Export specific objects as binary STL."""
    bpy.ops.object.select_all(action='DESELECT')
    for obj in objects:
        obj.select_set(True)
    bpy.ops.wm.stl_export(
        filepath=filepath,
        export_selected_objects=True,
        ascii_format=False,
    )
    bpy.ops.object.select_all(action='DESELECT')


# --- Part Generators ---

def make_back_plate(args):
    """
    Back plate: large disc with center axle post and rim around edge.

    Cross-section (side view):
        ___________________________
       |  rim                      |  rim
       |   _______________________  |
       |  |  plate (flat base)    | |
       |__|___________|___________|_|
                      |axle|
                      |    |
                      |____|
    """
    seg = args.segments
    outer_r = args.disk_radius_mm + args.outer_margin_mm
    plate_t = args.plate_thickness_mm
    rim_h = args.rim_height_mm
    axle_r = args.axle_diameter_mm / 2
    axle_h = plate_t + rim_h + args.disk_thickness_mm + args.cover_lip_mm + plate_t + 1.0
    # axle needs to be tall enough to poke through: plate + rim + disk + cover + cap clearance

    # Base disc
    base = add_cylinder("back_plate_base", outer_r, plate_t, seg,
                        location=(0, 0, plate_t / 2))

    # Rim ring (hollow cylinder around edge)
    rim_outer = add_cylinder("rim_outer", outer_r, rim_h, seg,
                             location=(0, 0, plate_t + rim_h / 2))
    rim_inner = add_cylinder("rim_cut", outer_r - 2.0, rim_h + 0.2, seg,
                             location=(0, 0, plate_t + rim_h / 2))
    boolean_op(rim_outer, rim_inner, 'DIFFERENCE')

    # Union rim onto base
    boolean_op(base, rim_outer, 'UNION')

    # Center axle post
    axle = add_cylinder("axle_post", axle_r, axle_h, seg,
                        location=(0, 0, axle_h / 2))
    boolean_op(base, axle, 'UNION')

    base.name = "back-plate"
    return base


def make_front_cover(args):
    """
    Front cover: disc with wedge window cutout and center hole.
    Has a small inner lip that overlaps the disk edge.
    """
    seg = args.segments
    outer_r = args.disk_radius_mm + args.outer_margin_mm
    plate_t = args.plate_thickness_mm
    lip = args.cover_lip_mm
    hole_r = (args.axle_diameter_mm + args.tolerance_mm) / 2

    # Z position: sits on top of the rim + disk
    z_base = args.plate_thickness_mm + args.rim_height_mm + args.disk_thickness_mm

    # Main disc
    cover = add_cylinder("front_cover_base", outer_r, plate_t, seg,
                         location=(0, 0, z_base + plate_t / 2))

    # Inner lip ring (extends downward to capture disk edge)
    lip_ring_outer = add_cylinder("lip_outer", args.disk_radius_mm + 1.0, lip, seg,
                                  location=(0, 0, z_base - lip / 2))
    lip_ring_inner = add_cylinder("lip_cut", args.disk_radius_mm - 1.5, lip + 0.2, seg,
                                  location=(0, 0, z_base - lip / 2))
    boolean_op(lip_ring_outer, lip_ring_inner, 'DIFFERENCE')
    boolean_op(cover, lip_ring_outer, 'UNION')

    # Window cutout (wedge through full thickness + lip)
    window_depth = plate_t + lip + 2.0  # extra clearance
    window = add_wedge("window_wedge",
                       args.disk_radius_mm - 2.0,  # slightly smaller than disk
                       window_depth,
                       args.window_angle_deg, seg)
    window.location.z = mm(z_base + plate_t / 2 - lip / 2)
    bpy.context.view_layer.update()
    boolean_op(cover, window, 'DIFFERENCE')

    # Center hole for axle
    hole = add_cylinder("axle_hole", hole_r, plate_t + lip + 2.0, seg,
                        location=(0, 0, z_base))
    boolean_op(cover, hole, 'DIFFERENCE')

    cover.name = "front-cover"
    return cover


def make_snap_cap(args):
    """
    Snap cap: small disc that press-fits onto the axle top.
    Has a slightly undersized hole for press-fit retention.
    """
    seg = args.segments
    cap_r = args.cap_diameter_mm / 2
    cap_t = args.plate_thickness_mm
    # Press-fit: hole is axle diameter - tolerance (tight fit)
    hole_r = (args.axle_diameter_mm - 0.1) / 2

    # Z position: on top of front cover
    z_base = (args.plate_thickness_mm + args.rim_height_mm +
              args.disk_thickness_mm + args.plate_thickness_mm)

    cap = add_cylinder("snap_cap_base", cap_r, cap_t, seg,
                       location=(0, 0, z_base + cap_t / 2 + 0.5))

    # Press-fit hole
    hole = add_cylinder("cap_hole", hole_r, cap_t + 1.0, seg,
                        location=(0, 0, z_base + cap_t / 2 + 0.5))
    boolean_op(cap, hole, 'DIFFERENCE')

    cap.name = "snap-cap"
    return cap


def make_inner_disk(args):
    """
    Inner disk template: flat disc with center hole.
    This is the rotating content disc that slides in.
    """
    seg = args.segments
    disk_r = args.disk_radius_mm - args.tolerance_mm  # slightly smaller for clearance
    disk_t = args.disk_thickness_mm
    hole_r = (args.axle_diameter_mm + args.tolerance_mm * 2) / 2  # loose fit for spinning

    # Z position: sits on back plate, inside rim
    z_base = args.plate_thickness_mm + args.rim_height_mm

    disk = add_cylinder("inner_disk_base", disk_r, disk_t, seg,
                        location=(0, 0, z_base - disk_t / 2))

    # Center hole (loose fit for rotation)
    hole = add_cylinder("disk_hole", hole_r, disk_t + 1.0, seg,
                        location=(0, 0, z_base - disk_t / 2))
    boolean_op(disk, hole, 'DIFFERENCE')

    # Add section divider lines (shallow grooves) for reference
    # These help the user know where to put content
    n_sections = int(360 / args.window_angle_deg)
    # Skip dividers for now — user can add content in Fusion

    disk.name = "inner-disk"
    return disk


def main():
    args = parse_args()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    clear_scene()

    # Generate all parts
    print("=" * 60)
    print("GENERATING VOLVELLE PARTS")
    print("=" * 60)

    print(f"\nDisk radius: {args.disk_radius_mm}mm ({args.disk_radius_mm / 25.4:.1f} inches)")
    print(f"Window angle: {args.window_angle_deg} degrees")
    print(f"Tolerance: {args.tolerance_mm}mm")
    print(f"Segments: {args.segments}")

    parts = {}

    print("\n[1/4] Generating back plate...")
    parts["back-plate"] = make_back_plate(args)

    print("[2/4] Generating front cover...")
    parts["front-cover"] = make_front_cover(args)

    print("[3/4] Generating snap cap...")
    parts["snap-cap"] = make_snap_cap(args)

    print("[4/4] Generating inner disk template...")
    parts["inner-disk"] = make_inner_disk(args)

    # Export each part individually
    part_info = []
    for name, obj in parts.items():
        glb_path = str(output_dir / f"{name}.glb")
        export_glb([obj], glb_path)
        dims = [round(d * 1000, 2) for d in obj.dimensions]
        faces = len(obj.data.polygons)
        size = Path(glb_path).stat().st_size

        info = {
            "name": name,
            "file_glb": f"{name}.glb",
            "dimensions_mm": dims,
            "faces": faces,
            "file_size_bytes": size,
        }

        if args.export_stl:
            stl_path = str(output_dir / f"{name}.stl")
            export_stl([obj], stl_path)
            info["file_stl"] = f"{name}.stl"
            info["stl_size_bytes"] = Path(stl_path).stat().st_size

        part_info.append(info)
        print(f"  {name}: {dims[0]:.1f} x {dims[1]:.1f} x {dims[2]:.1f} mm, {faces} faces")

    # Also export full assembly as one GLB for preview
    all_objs = list(parts.values())
    export_glb(all_objs, str(output_dir / "volvelle-assembly.glb"))
    print(f"\nAssembly preview: volvelle-assembly.glb")

    # Write report
    if args.report:
        report = {
            "project": "volvelle-wheel",
            "parameters": {
                "disk_radius_mm": args.disk_radius_mm,
                "disk_thickness_mm": args.disk_thickness_mm,
                "window_angle_deg": args.window_angle_deg,
                "axle_diameter_mm": args.axle_diameter_mm,
                "tolerance_mm": args.tolerance_mm,
                "outer_diameter_mm": (args.disk_radius_mm + args.outer_margin_mm) * 2,
            },
            "parts": part_info,
            "assembly_notes": {
                "order": [
                    "1. Print all parts flat on bed",
                    "2. Place inner-disk on back-plate (disk sits in rim)",
                    "3. Place front-cover on top (axle passes through center hole)",
                    "4. Press snap-cap onto axle top",
                    "5. Disk should spin freely — sand axle if too tight",
                ],
                "tips": [
                    f"Axle hole clearance: {args.tolerance_mm}mm — adjust if too tight/loose",
                    "Print inner-disk at 100% infill for rigidity",
                    "Print back-plate and front-cover at 20-30% infill",
                    "No supports needed for any part",
                ],
            },
        }
        Path(args.report).write_text(json.dumps(report, indent=2))

    print("\n" + "=" * 60)
    print("DONE — All volvelle parts generated")
    print("=" * 60)


if __name__ == "__main__":
    main()
