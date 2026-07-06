"""Convert finished low-poly biped GLBs into AccuRIG-ready OBJs — one per file,
looped in a single headless Blender. AccuRIG wants a plain OBJ in CENTIMETRES
(a metre-scaled OBJ imports as a ~2 cm miniature — memory project_accurig_input_format)
with UVs present BEFORE rigging (so the rigged FBX keeps them for texturing in
Unity). We scale each mesh to ~175 cm tall (height axis), weld, and export OBJ
with UVs (materials dropped — AccuRIG ignores them; texture re-binds later).

    blender -b --python prep_accurig_batch.py -- <models_dir> <out_dir> [target_cm] [exclude_csv]

Prints  ACCURIG_OBJ <name> h_cm=<..> verts=<..> uv=<True/False>  per file, then
ACCURIG_PREP_DONE <n>.  Quadrupeds/non-humanoids should be passed in exclude_csv.
"""
import glob
import os
import sys

import bmesh
import bpy
from mathutils import Vector

argv = sys.argv[sys.argv.index("--") + 1:]
MODELS, OUT = argv[0], argv[1]
TARGET_CM = float(argv[2]) if len(argv) > 2 else 175.0
EXCLUDE = set(x.strip() for x in argv[3].split(",")) if len(argv) > 3 and argv[3] else set()

os.makedirs(OUT, exist_ok=True)


def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def import_join(p):
    bpy.ops.import_scene.gltf(filepath=p)
    ms = [o for o in bpy.context.scene.objects if o.type == "MESH"]
    if not ms:
        return None
    o = ms[0]
    if len(ms) > 1:
        bpy.ops.object.select_all(action="DESELECT")
        for m in ms:
            m.select_set(True)
        bpy.context.view_layer.objects.active = ms[0]
        bpy.ops.object.join()
        o = bpy.context.active_object
    return o


def sel(o):
    bpy.ops.object.select_all(action="DESELECT")
    o.select_set(True)
    bpy.context.view_layer.objects.active = o


done = 0
for p in sorted(glob.glob(os.path.join(MODELS, "*.glb"))):
    name = os.path.splitext(os.path.basename(p))[0]
    if name in EXCLUDE:
        continue
    reset()
    o = import_join(p)
    if o is None:
        print(f"ACCURIG_OBJ {name} SKIP no-mesh", flush=True)
        continue
    sel(o)
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    # weld coincident verts
    me = o.data
    bm = bmesh.new()
    bm.from_mesh(me)
    bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=1e-5)
    bm.to_mesh(me)
    bm.free()
    me.update()
    # scale to ~TARGET_CM tall on the standing (Z) axis
    zmin = min(v.co.z for v in me.vertices)
    zmax = max(v.co.z for v in me.vertices)
    h = (zmax - zmin) or 1.0
    s = TARGET_CM / h
    o.scale = (s, s, s)
    sel(o)
    bpy.ops.object.transform_apply(scale=True)
    # drop to floor + centre in XY (AccuRIG likes a grounded, centred figure)
    me = o.data
    xs = [v.co.x for v in me.vertices]
    ys = [v.co.y for v in me.vertices]
    zs = [v.co.z for v in me.vertices]
    o.location -= Vector(((min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2, min(zs)))
    sel(o)
    bpy.ops.object.transform_apply(location=True)
    has_uv = bool(me.uv_layers)
    out = os.path.join(OUT, name + ".obj")
    bpy.ops.wm.obj_export(filepath=out, export_selected_objects=True,
                          export_uv=True, export_materials=False,
                          export_triangulated_mesh=True, forward_axis="NEGATIVE_Z",
                          up_axis="Y")
    zmin2 = min(v.co.z for v in me.vertices)
    zmax2 = max(v.co.z for v in me.vertices)
    print(f"ACCURIG_OBJ {name} h_cm={zmax2 - zmin2:.1f} verts={len(me.vertices)} uv={has_uv}", flush=True)
    done += 1

print(f"ACCURIG_PREP_DONE {done}", flush=True)
