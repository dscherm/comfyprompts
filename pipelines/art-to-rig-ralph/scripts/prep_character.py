"""prep_character — mesh prep for TRELLIS/Hunyuan character GLBs (headless).

The exact sequence proven on The Rookie (2026-07-02): weld FIRST (glTF imports
are split-vertex triangle soup — island analysis before welding sees every
face as its own island and deletes the whole mesh, which is how the kart-era
mesh_prep.py zeroed out three characters), then clean, remove only genuinely
floating debris (<1% of faces, largest island always kept), decimate, scale,
ground, and run a manifold-cleanup pass.

Usage:
    blender --background --python prep_character.py -- \
        --input raw.glb --output prepared.glb [--report r.json] \
        [--target-height 1.8] [--max-faces 80000] [--target-faces 50000]
"""
import argparse
import json
import sys

import bpy
import bmesh

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
ap = argparse.ArgumentParser()
ap.add_argument("--input", required=True)
ap.add_argument("--output", required=True)
ap.add_argument("--report", default=None)
ap.add_argument("--target-height", type=float, default=1.8)
ap.add_argument("--max-faces", type=int, default=80000)
ap.add_argument("--target-faces", type=int, default=50000)
args = ap.parse_args(argv)

ops_log = []
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=args.input)
meshes = [o for o in bpy.data.objects if o.type == "MESH"]
if not meshes:
    print("ERROR: no mesh in", args.input)
    sys.exit(1)
obj = meshes[0]
bpy.ops.object.select_all(action="DESELECT")
bpy.context.view_layer.objects.active = obj
obj.select_set(True)
if len(meshes) > 1:
    for o in meshes:
        o.select_set(True)
    bpy.ops.object.join()
    obj = bpy.context.view_layer.objects.active
    ops_log.append({"op": "join", "objects": len(meshes)})

before = {"vertices": len(obj.data.vertices), "faces": len(obj.data.polygons),
          "bbox": [round(d, 4) for d in obj.dimensions]}

# 1. WELD (true connectivity before any island logic)
bpy.ops.object.mode_set(mode="EDIT")
bpy.ops.mesh.select_all(action="SELECT")
v0 = len(obj.data.vertices)
bpy.ops.mesh.remove_doubles(threshold=0.0005)
bpy.ops.object.mode_set(mode="OBJECT")
ops_log.append({"op": "weld", "merged": v0 - len(obj.data.vertices)})

# 2. fill holes / normals / degenerate
bpy.ops.object.mode_set(mode="EDIT")
bpy.ops.mesh.select_all(action="DESELECT")
bpy.ops.mesh.select_non_manifold()
bpy.ops.mesh.fill_holes(sides=32)
bpy.ops.mesh.select_all(action="SELECT")
bpy.ops.mesh.normals_make_consistent(inside=False)
f0 = len(obj.data.polygons)
bpy.ops.mesh.dissolve_degenerate(threshold=0.0001)
bpy.ops.object.mode_set(mode="OBJECT")
ops_log.append({"op": "clean", "degenerate_removed": f0 - len(obj.data.polygons)})

# 3. floating debris: remove islands <1% of faces; the largest ALWAYS survives
bpy.ops.object.mode_set(mode="EDIT")
bm = bmesh.from_edit_mesh(obj.data)
bm.faces.ensure_lookup_table()
visited = set()
islands = []
for f in bm.faces:
    if f.index in visited:
        continue
    stack, comp = [f], []
    while stack:
        cur = stack.pop()
        if cur.index in visited:
            continue
        visited.add(cur.index)
        comp.append(cur)
        for e in cur.edges:
            for lf in e.link_faces:
                if lf.index not in visited:
                    stack.append(lf)
    islands.append(comp)
total = len(bm.faces)
main = max(islands, key=len) if islands else None
removed = 0
for comp in islands:
    if comp is not main and len(comp) < 0.01 * total:
        bmesh.ops.delete(bm, geom=comp, context="FACES")
        removed += 1
bmesh.update_edit_mesh(obj.data)
bpy.ops.object.mode_set(mode="OBJECT")
ops_log.append({"op": "debris", "islands_total": len(islands), "removed": removed})

# 4. decimate
fc = len(obj.data.polygons)
if fc > args.max_faces:
    mod = obj.modifiers.new("Decimate", "DECIMATE")
    mod.ratio = args.target_faces / fc
    bpy.ops.object.modifier_apply(modifier="Decimate")
    ops_log.append({"op": "decimate", "before": fc, "after": len(obj.data.polygons)})

# 5. scale to height, center, ground
h = obj.dimensions.z
if h > 0:
    s = args.target_height / h
    obj.scale = (s, s, s)
    bpy.ops.object.transform_apply(scale=True)
    ops_log.append({"op": "scale", "factor": round(s, 4)})
bpy.ops.object.origin_set(type="ORIGIN_GEOMETRY", center="BOUNDS")
obj.location.x = obj.location.y = 0.0
mw = obj.matrix_world
lowest = min((mw @ v.co).z for v in obj.data.vertices)
obj.location.z -= lowest
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)

# 6. manifold cleanup pass (post-decimate)
# NOTE: on double-shell TRELLIS meshes the remove_doubles below can fuse the
# shells so that EVERY edge gains >2 face users — select_interior_faces then
# selects the whole mesh (pip 2026-07-05: 50k faces -> 451). Interior-face
# deletion is therefore guarded: skip it when it would remove >10% of faces.
bpy.ops.object.mode_set(mode="EDIT")
bpy.ops.mesh.select_all(action="SELECT")
bpy.ops.mesh.delete_loose(use_verts=True, use_edges=True, use_faces=False)
bpy.ops.mesh.select_all(action="SELECT")
bpy.ops.mesh.remove_doubles(threshold=0.0008)
bpy.ops.mesh.select_all(action="DESELECT")
bpy.ops.mesh.select_interior_faces()
bpy.ops.object.mode_set(mode="OBJECT")
interior = sum(1 for p in obj.data.polygons if p.select)
fc6 = len(obj.data.polygons)
if 0 < interior <= 0.10 * fc6:
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.delete(type="FACE")
    bpy.ops.object.mode_set(mode="OBJECT")
    ops_log.append({"op": "interior_faces", "removed": interior})
else:
    ops_log.append({"op": "interior_faces", "skipped": True,
                    "would_remove": interior, "of": fc6})

after = {"vertices": len(obj.data.vertices), "faces": len(obj.data.polygons),
         "bbox_m": [round(d, 4) for d in obj.dimensions]}
post_decimate = next((o["after"] for o in ops_log if o["op"] == "decimate"),
                     before["faces"])
if (after["vertices"] == 0 or after["faces"] < 0.5 * post_decimate
        or after["bbox_m"][2] < 0.9 * args.target_height):
    print(f"ERROR: prep destroyed the mesh (faces {after['faces']}/{post_decimate}, "
          f"height {after['bbox_m'][2]}) — aborting export")
    sys.exit(1)

bpy.ops.object.select_all(action="DESELECT")
obj.select_set(True)
bpy.ops.export_scene.gltf(filepath=args.output, use_selection=True, export_format="GLB")

report = {"source": args.input, "operations": ops_log,
          "before": before, "after": after}
if args.report:
    with open(args.report, "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=1)
print(f"PREP_DONE {args.output} verts={after['vertices']} faces={after['faces']} "
      f"bbox={after['bbox_m']}")
