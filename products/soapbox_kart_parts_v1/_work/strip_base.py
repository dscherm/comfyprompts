"""strip_base.py — remove the fused ground slab TRELLIS builds under a part.

TRELLIS reconstructs the 2D drop-shadow/white-ground as a thin flat plate FUSED to the
part's bottom (one connected shell, so loose-part removal misses it). This detects the
slab by its cross-section signature — the bottom of the mesh is a wide flat plate whose
XY radius is much larger than the part above it — and cuts the mesh just above the slab.

Auto method: scan thin Z-bands from the bottom up; the slab bands have a large XY radius,
the part bands a smaller one. The cut is the lowest Z where the radius has dropped below
`ratio` * (slab radius) and stays down — i.e. where the plate ends and the part begins.
If no clear plate is found (radius never drops), nothing is cut (fail-safe: keep the part).

Run with Blender's Python:
  blender --background --python strip_base.py -- --input raw.glb --output out.glb [--ratio 0.7] [--max-frac 0.25] [--render-dir DIR --name NAME]
"""
import bpy, bmesh, math, sys, argparse
import mathutils


def get_args():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True)
    ap.add_argument("--output", required=True)
    ap.add_argument("--ratio", type=float, default=0.7,
                    help="cut where band XY-radius falls below this * slab radius")
    ap.add_argument("--max-frac", type=float, default=0.25,
                    help="only look for the slab within the bottom this fraction of height")
    ap.add_argument("--weld-dist", type=float, default=0.001)
    ap.add_argument("--render-dir", default=None)
    ap.add_argument("--name", default="part")
    return ap.parse_args(argv)


def load_join(path):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=path)
    ms = [o for o in bpy.context.scene.objects if o.type == "MESH"]
    bpy.ops.object.select_all(action="DESELECT")
    for o in ms:
        o.select_set(True)
    bpy.context.view_layer.objects.active = ms[0]
    if len(ms) > 1:
        bpy.ops.object.join()
    return bpy.context.view_layer.objects.active


def find_slab_top(bm, max_frac, ratio):
    zs = [v.co.z for v in bm.verts]
    minz, maxz = min(zs), max(zs)
    h = maxz - minz or 1.0
    cx = sum(v.co.x for v in bm.verts) / len(bm.verts)
    cy = sum(v.co.y for v in bm.verts) / len(bm.verts)
    nb = 40
    top = minz + max_frac * h
    band_h = (top - minz) / nb
    radii = []
    for i in range(nb):
        z0 = minz + i * band_h
        rr = [math.hypot(v.co.x - cx, v.co.y - cy) for v in bm.verts if z0 <= v.co.z < z0 + band_h]
        radii.append(max(rr) if rr else 0.0)
    slab_r = radii[0] or max(radii) or 1.0
    # first band (from bottom) whose radius has dropped below ratio*slab_r
    for i in range(1, nb):
        if radii[i] < ratio * slab_r:
            return minz + i * band_h, slab_r, radii
    return None, slab_r, radii  # no clear plate


def main():
    a = get_args()
    obj = load_join(a.input)
    me = obj.data
    me.materials.clear()
    for ca in list(me.color_attributes):
        me.color_attributes.remove(ca)

    bm = bmesh.new(); bm.from_mesh(me)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=a.weld_dist)
    cut_z, slab_r, radii = find_slab_top(bm, a.max_frac, a.ratio)
    if cut_z is None:
        print("NO_SLAB_DETECTED (radius never drops) — keeping mesh as-is", flush=True)
    else:
        kill = [v for v in bm.verts if v.co.z < cut_z]
        bmesh.ops.delete(bm, geom=kill, context="VERTS")
        print(f"CUT z<{cut_z:.4f} removed {len(kill)} verts (slab_r={slab_r:.3f})", flush=True)
        # cap the freshly-opened bottom
        bmesh.ops.holes_fill(bm, edges=[e for e in bm.edges if len(e.link_faces) == 1], sides=0)
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(me); bm.free()

    # drop any freed floaters, keep largest shell(s) >=100 faces
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True); bpy.context.view_layer.objects.active = obj
    bpy.ops.mesh.separate(type="LOOSE")
    parts = sorted([o for o in bpy.context.scene.objects if o.type == "MESH"],
                   key=lambda o: len(o.data.polygons), reverse=True)
    keep = [p for p in parts if len(p.data.polygons) >= 100] or parts[:1]
    for p in parts:
        if p not in keep:
            bpy.data.objects.remove(p, do_unlink=True)
    bpy.ops.object.select_all(action="DESELECT")
    for p in keep:
        p.select_set(True)
    bpy.context.view_layer.objects.active = keep[0]
    if len(keep) > 1:
        bpy.ops.object.join()
    obj = bpy.context.view_layer.objects.active
    me = obj.data
    print(f"KEPT {len(keep)}/{len(parts)} shells, faces={len(me.polygons)}", flush=True)

    # center on origin
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    bb = [v.co for v in me.vertices]
    c = mathutils.Vector((
        (min(p.x for p in bb) + max(p.x for p in bb)) / 2,
        (min(p.y for p in bb) + max(p.y for p in bb)) / 2,
        (min(p.z for p in bb) + max(p.z for p in bb)) / 2))
    for v in me.vertices:
        v.co -= c
    me.update()

    bpy.ops.object.select_all(action="DESELECT"); obj.select_set(True)
    bpy.ops.export_scene.gltf(filepath=a.output, use_selection=True,
                              export_format="GLB", export_materials="NONE")
    print(f"WROTE {a.output}", flush=True)

    if a.render_dir:
        import os
        os.makedirs(a.render_dir, exist_ok=True)
        sc = bpy.context.scene
        sc.render.engine = "BLENDER_WORKBENCH"
        sc.display.shading.light = "STUDIO"; sc.display.shading.color_type = "SINGLE"
        sc.display.shading.single_color = (0.6, 0.6, 0.62); sc.display.shading.show_cavity = True
        sc.render.resolution_x = 640; sc.render.resolution_y = 640
        dims = [max(p[i] for p in bb) - min(p[i] for p in bb) for i in range(3)]
        r = max(dims) * 1.9 or 1.9
        cam_d = bpy.data.cameras.new("Cam"); cam = bpy.data.objects.new("Cam", cam_d)
        bpy.context.collection.objects.link(cam); sc.camera = cam
        for nm, ang in {"front": 0, "tq": 45, "side": 90}.items():
            aa = math.radians(ang)
            cam.location = (math.sin(aa) * r, -math.cos(aa) * r, max(dims) * 0.45)
            d = mathutils.Vector((0, 0, 0)) - cam.location
            cam.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
            sc.render.filepath = os.path.join(a.render_dir, f"{a.name}_strip_{nm}.png")
            bpy.ops.render.render(write_still=True)
    print("DONE", flush=True)


if __name__ == "__main__":
    main()
