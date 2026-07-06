"""Weld coincident verts + dissolve degenerate faces on every finished low-poly
GLB in a dir, in place, preserving the baked albedo texture (UV material, not
COLOR_0 — so glTF import/export keeps it). Zeroes the few sliver faces the
voxel-remesh decimate leaves so the productize quality gate sees degenerate=0.

    blender -b --python clean_finals.py -- <dir_of_glb> [dist]

Prints CLEAN <name> degen <before>-><after> tris <n> per file. Idempotent.
"""
import glob
import os
import sys

import bmesh
import bpy

argv = sys.argv[sys.argv.index("--") + 1:]
D = argv[0]
DIST = float(argv[1]) if len(argv) > 1 else 1e-5


def degen_count(me):
    from mathutils import Vector
    n = 0
    for poly in me.polygons:
        vs = [me.vertices[i].co for i in poly.vertices]
        o = vs[0]
        if (vs[1] - o).cross(vs[2] - o).length < 1e-6:
            n += 1
    return n


def tri_count(me):
    return sum(len(p.vertices) - 2 for p in me.polygons)


for p in sorted(glob.glob(os.path.join(D, "*.glb"))):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=p)
    meshes = [o for o in bpy.context.scene.objects if o.type == "MESH"]
    if not meshes:
        print(f"CLEAN {os.path.basename(p)} SKIP no-mesh", flush=True)
        continue
    obj = meshes[0]
    if len(meshes) > 1:
        bpy.ops.object.select_all(action="DESELECT")
        for o in meshes:
            o.select_set(True)
        bpy.context.view_layer.objects.active = meshes[0]
        bpy.ops.object.join()
        obj = bpy.context.active_object
    me = obj.data
    before = degen_count(me)
    bm = bmesh.new()
    bm.from_mesh(me)
    bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=DIST)
    bmesh.ops.dissolve_degenerate(bm, dist=DIST, edges=bm.edges[:])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(me)
    bm.free()
    me.update()
    after = degen_count(me)
    for poly in me.polygons:
        poly.use_smooth = False
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.export_scene.gltf(filepath=p, export_format="GLB", use_selection=True)
    print(f"CLEAN {os.path.basename(p)} degen {before}->{after} tris {tri_count(me)}", flush=True)

print("CLEAN_ALL_DONE", flush=True)
