"""mesh_to_solid — turn a raw TRELLIS/Hunyuan image-to-3D export into a clean,
workable solid mesh, then write it out in GLB / OBJ / STL.

The problem this solves (hardened on the dog run, 2026-07-11): TRELLIS.2's
Cumesh simplifier ships meshes that LOOK continuous but are actually thousands
of UNWELDED fragments — coincident-but-separate vertices, tons of boundary
edges. They render fine flat, but any per-vertex op (a Smooth modifier) pulls
the duplicates apart into visible surface cracks, and the "mesh" is really
triangle soup. Fix order MATTERS: weld FIRST, then fill holes, then smooth.
See memory `project_trellis_unwelded_mesh_weld_before_smooth`.

Run with Blender's bundled Python:
  "C:/Program Files/Blender Foundation/Blender 5.0/blender.exe" --background \
     --python mesh_to_solid.py -- --input raw.glb --output-dir out --name dog \
     [--watertight] [--longest-mm 120] [--formats glb,obj,stl] \
     [--smooth-iters 10] [--smooth-factor 0.5] [--weld-dist 0.001] \
     [--keep-textures] [--render] [--report out/dog_report.json]

Prints one status line per stage and `DONE`; exit 0 on success.
"""
import bpy, bmesh, math, os, sys, json, argparse


def get_args():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True, help="raw image-to-3D glb")
    ap.add_argument("--output-dir", required=True)
    ap.add_argument("--name", required=True, help="output basename")
    ap.add_argument("--formats", default="glb,obj,stl")
    ap.add_argument("--weld-dist", type=float, default=0.001,
                    help="merge-by-distance threshold (mesh normalized to ~1 unit)")
    ap.add_argument("--smooth-iters", type=int, default=10)
    ap.add_argument("--smooth-factor", type=float, default=0.5)
    ap.add_argument("--min-part-faces", type=int, default=100,
                    help="drop disconnected parts smaller than this many faces")
    ap.add_argument("--watertight", action="store_true",
                    help="keep only the largest shell + close ALL holes (best-effort)")
    ap.add_argument("--voxel-remesh", type=float, default=None,
                    help="voxel size (mesh normalized ~1u) — GUARANTEES a watertight "
                         "manifold by resampling the volume; e.g. 0.004. Best for printing; "
                         "resamples topology so fine detail softens.")
    ap.add_argument("--longest-mm", type=float, default=None,
                    help="scale the STL so the longest bbox axis = this many mm "
                         "(STL only; GLB/OBJ stay normalized). See feedback_stl_units.")
    ap.add_argument("--keep-textures", action="store_true",
                    help="keep material/vertex color instead of stripping to pure geometry")
    ap.add_argument("--render", action="store_true", help="write clay turntable PNGs")
    ap.add_argument("--report", default=None)
    return ap.parse_args(argv)


def boundary_edges(bm):
    return sum(1 for e in bm.edges if len(e.link_faces) == 1)


def main():
    a = get_args()
    os.makedirs(a.output_dir, exist_ok=True)
    stats = {"input": a.input}

    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=a.input)
    meshes = [o for o in bpy.context.scene.objects if o.type == "MESH"]
    if not meshes:
        print("ERROR no mesh in input"); return 1
    # join multi-object imports
    bpy.ops.object.select_all(action="DESELECT")
    for o in meshes:
        o.select_set(True)
    bpy.context.view_layer.objects.active = meshes[0]
    if len(meshes) > 1:
        bpy.ops.object.join()
    obj = bpy.context.view_layer.objects.active
    me = obj.data

    if not a.keep_textures:
        me.materials.clear()
        for ca in list(me.color_attributes):
            me.color_attributes.remove(ca)

    bm = bmesh.new(); bm.from_mesh(me)
    stats["before"] = {"verts": len(bm.verts), "faces": len(bm.faces),
                       "boundary": boundary_edges(bm)}
    print(f"BEFORE  verts={len(bm.verts)} faces={len(bm.faces)} "
          f"boundary={stats['before']['boundary']}")

    # 1) WELD coincident vertices (the core fix)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=a.weld_dist)
    print(f"WELDED  verts={len(bm.verts)} faces={len(bm.faces)} "
          f"boundary={boundary_edges(bm)}")

    # 2) fill residual holes, triangulate n-gons, recalc normals
    bmesh.ops.holes_fill(bm, edges=[e for e in bm.edges if len(e.link_faces) == 1], sides=0)
    ngons = [f for f in bm.faces if len(f.verts) > 3]
    if ngons:
        bmesh.ops.triangulate(bm, faces=ngons)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    print(f"FILLED  boundary={boundary_edges(bm)}")
    bm.to_mesh(me); bm.free()

    # 3) drop tiny floaters (and, if watertight, keep only the largest shell)
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True); bpy.context.view_layer.objects.active = obj
    bpy.ops.mesh.separate(type="LOOSE")
    parts = [o for o in bpy.context.scene.objects if o.type == "MESH"]
    parts.sort(key=lambda o: len(o.data.polygons), reverse=True)
    stats["loose_parts_after_weld"] = len(parts)
    if a.watertight:
        keep = parts[:1]
    else:
        keep = [p for p in parts if len(p.data.polygons) >= a.min_part_faces] or parts[:1]
    for p in parts:
        if p not in keep:
            bpy.data.objects.remove(p, do_unlink=True)
    print(f"PARTS   total={len(parts)} kept={len(keep)}")
    bpy.ops.object.select_all(action="DESELECT")
    for p in keep:
        p.select_set(True)
    bpy.context.view_layer.objects.active = keep[0]
    if len(keep) > 1:
        bpy.ops.object.join()
    obj = bpy.context.view_layer.objects.active
    me = obj.data

    # 3b) watertight: close any holes the trimming re-exposed
    if a.watertight:
        bm = bmesh.new(); bm.from_mesh(me)
        bmesh.ops.holes_fill(bm, edges=[e for e in bm.edges if len(e.link_faces) == 1], sides=0)
        ngons = [f for f in bm.faces if len(f.verts) > 3]
        if ngons:
            bmesh.ops.triangulate(bm, faces=ngons)
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        print(f"SEAL    boundary={boundary_edges(bm)}")
        bm.to_mesh(me); bm.free()

    # 3c) optional voxel remesh -> guaranteed watertight manifold (printing)
    if a.voxel_remesh:
        rm = obj.modifiers.new("Remesh", "REMESH")
        rm.mode = "VOXEL"; rm.voxel_size = a.voxel_remesh
        bpy.ops.object.modifier_apply(modifier=rm.name)
        me = obj.data
        # OpenVDB output is closed + manifold, but recalc so face winding is
        # unambiguously outward — downstream QuadriFlow refuses inconsistent normals.
        bm = bmesh.new(); bm.from_mesh(me)
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        bm.to_mesh(me); bm.free()
        print(f"REMESH  voxel={a.voxel_remesh} faces={len(me.polygons)}")

    # 4) NOW smooth (welded -> shared verts move together, no cracks)
    if a.smooth_iters > 0:
        mod = obj.modifiers.new("Relax", "SMOOTH")
        mod.factor = a.smooth_factor; mod.iterations = a.smooth_iters
        bpy.ops.object.modifier_apply(modifier=mod.name)
    try:
        bpy.ops.object.shade_auto_smooth(angle=math.radians(40))
    except Exception:
        bpy.ops.object.shade_smooth()

    # 5) apply transforms, center on origin
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    bpy.context.view_layer.update()
    bb = [obj.matrix_world @ v.co for v in me.vertices]
    cx = (min(p.x for p in bb) + max(p.x for p in bb)) / 2
    cy = (min(p.y for p in bb) + max(p.y for p in bb)) / 2
    cz = (min(p.z for p in bb) + max(p.z for p in bb)) / 2
    for v in me.vertices:
        v.co.x -= cx; v.co.y -= cy; v.co.z -= cz
    me.update()

    bm = bmesh.new(); bm.from_mesh(me)
    stats["after"] = {"verts": len(bm.verts), "faces": len(bm.faces),
                      "boundary": boundary_edges(bm),
                      "watertight": boundary_edges(bm) == 0}
    bb = [v.co for v in bm.verts]
    dims = [max(p[i] for p in bb) - min(p[i] for p in bb) for i in range(3)]
    stats["bbox_units"] = dims
    bm.free()
    print(f"FINAL   verts={stats['after']['verts']} faces={stats['after']['faces']} "
          f"boundary={stats['after']['boundary']} watertight={stats['after']['watertight']}")

    # 6) export
    fmts = [f.strip().lower() for f in a.formats.split(",") if f.strip()]
    base = os.path.join(a.output_dir, a.name)
    bpy.ops.object.select_all(action="DESELECT"); obj.select_set(True)
    written = []
    if "glb" in fmts:
        bpy.ops.export_scene.gltf(filepath=base + ".glb", use_selection=True,
                                  export_format="GLB",
                                  export_materials="EXPORT" if a.keep_textures else "NONE")
        written.append(base + ".glb")
    if "obj" in fmts:
        try:
            bpy.ops.wm.obj_export(filepath=base + ".obj", export_selected_objects=True,
                                  export_materials=a.keep_textures)
            written.append(base + ".obj")
        except Exception as e:
            print("OBJ_ERR", e)
    if "stl" in fmts:
        # STL wants mm coordinates for correct CAD/slicer import (feedback_stl_units)
        longest = max(dims) or 1.0
        if a.longest_mm:
            f = a.longest_mm / longest
            for v in me.vertices:
                v.co *= f
            me.update()
            print(f"STL_SCALE longest {longest:.3f}u -> {a.longest_mm}mm (x{f:.2f})")
        else:
            print("STL_WARN no --longest-mm; STL exported at normalized units "
                  "(~1u); set a real size for printing")
        try:
            bpy.ops.wm.stl_export(filepath=base + ".stl", export_selected_objects=True)
        except Exception:
            bpy.ops.export_mesh.stl(filepath=base + ".stl", use_selection=True)
        written.append(base + ".stl")
        if a.longest_mm:  # undo scale so render/report stay in normalized units
            for v in me.vertices:
                v.co /= f
            me.update()
    stats["written"] = written
    for w in written:
        print("WROTE", w)

    # 7) optional clay render
    if a.render:
        sc = bpy.context.scene
        sc.render.engine = "BLENDER_WORKBENCH"
        sc.display.shading.light = "STUDIO"; sc.display.shading.color_type = "SINGLE"
        sc.display.shading.single_color = (0.6, 0.6, 0.62)
        sc.display.shading.show_cavity = True
        sc.render.resolution_x = 900; sc.render.resolution_y = 900
        cam_d = bpy.data.cameras.new("Cam"); cam = bpy.data.objects.new("Cam", cam_d)
        bpy.context.collection.objects.link(cam); sc.camera = cam
        r = max(dims) * 1.9 or 1.9

        def look(c, t):
            import mathutils
            d = mathutils.Vector(t) - c.location
            c.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
        for nm, ang in {"front_right": 45, "right": 0, "left": 180, "back_left": 225}.items():
            aa = math.radians(ang)
            cam.location = (math.cos(aa) * r, math.sin(aa) * r, max(dims) * 0.35)
            look(cam, (0, 0, 0))
            sc.render.filepath = os.path.join(a.output_dir, f"{a.name}_clay_{nm}.png")
            bpy.ops.render.render(write_still=True)
            print("RENDERED", nm)

    if a.report:
        json.dump(stats, open(a.report, "w"), indent=2)
        print("REPORT", a.report)
    print("DONE")
    return 0


if __name__ == "__main__":
    sys.exit(main())
