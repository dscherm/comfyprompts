"""Take a raw image-to-3D mesh down to a game-ready low-poly budget, then export
GLB. Path chosen by source density:

* TEXTURED (UV + image, e.g. Hunyuan PBR / kart meshes): pre-weld exact-coincident
  verts, then iterative collapse-decimate (preserves UVs).
* DENSE scan mesh (TRELLIS reconstructions, >100k faces): non-manifold / tiny-island
  topology that collapse can't reduce past a ~11k floor and that slivers badly —
  VOXEL-REMESH to clean manifold topology first, then collapse to target. These
  arrive uncoloured (Blender's glTF importer drops COLOR_0); colour is added
  downstream by a TRELLIS texture-paint + UV/bake pass, not here.

Common tail: base-centre pivot, bake scale+rotation (identity glTF node), flat
shading, export, self-verify. Headless so a factory-reset scene can't wipe the
user's live session.

    blender -b --python decimate_lowpoly.py -- <in.glb> <out.glb> <target_tris>
"""
import sys

import bmesh
import bpy
from mathutils import Vector

argv = sys.argv[sys.argv.index("--") + 1:]
SRC, DST = argv[0], argv[1]
TARGET = int(argv[2]) if len(argv) > 2 else 1500


def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def import_glb(p):
    bpy.ops.import_scene.gltf(filepath=p)
    return [o for o in bpy.context.scene.objects if o.type == "MESH"]


def select_only(o):
    bpy.ops.object.select_all(action="DESELECT")
    o.select_set(True)
    bpy.context.view_layer.objects.active = o


def tri_count(obj):
    return sum(len(p.vertices) - 2 for p in obj.data.polygons)


def clean(obj):
    me = obj.data
    bm = bmesh.new()
    bm.from_mesh(me)
    bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=1e-5)
    bmesh.ops.dissolve_degenerate(bm, dist=1e-5, edges=bm.edges[:])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(me)
    bm.free()
    me.update()


def collapse_to(obj, target):
    """Iterative collapse (<=8x per pass, clean between) to `target`, stopping on a
    topological floor."""
    for _ in range(10):
        n = tri_count(obj)
        if n <= target * 1.05:
            break
        select_only(obj)
        dec = obj.modifiers.new("dec", "DECIMATE")
        dec.decimate_type = "COLLAPSE"
        dec.ratio = max(0.125, target / n)
        dec.use_collapse_triangulate = True
        bpy.ops.object.modifier_apply(modifier="dec")
        clean(obj)
        if tri_count(obj) >= n:
            break


def base_origin(obj):
    me = obj.data
    xs = [v.co.x for v in me.vertices]
    ys = [v.co.y for v in me.vertices]
    zs = [v.co.z for v in me.vertices]
    if not xs:
        return
    c = Vector(((min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2, min(zs)))
    select_only(obj)
    bpy.context.scene.cursor.location = obj.matrix_world @ c
    bpy.ops.object.origin_set(type="ORIGIN_CURSOR")
    bpy.context.scene.cursor.location = (0, 0, 0)


# --- run ---
reset()
meshes = import_glb(SRC)
assert meshes, f"no mesh in {SRC}"
obj = meshes[0]
if len(meshes) > 1:
    select_only(meshes[0])
    for m in meshes[1:]:
        m.select_set(True)
    bpy.ops.object.join()
    obj = bpy.context.active_object

before = tri_count(obj)
has_tex = any(n.type == "TEX_IMAGE"
              for m in obj.data.materials if m and m.use_nodes
              for n in m.node_tree.nodes)
# Dense scan meshes (TRELLIS/Hunyuan reconstructions) have non-manifold / tiny-
# island topology that collapse can't reduce past a floor and that slivers badly —
# voxel-remesh to clean manifold first. Detected by source density, NOT colour:
# Blender's glTF importer drops COLOR_0, so colour is added downstream by the
# TRELLIS texture-paint + UV/bake pass, not here.
mode = "textured" if has_tex else ("dense" if before > 100_000 else "plain")

if mode == "dense":
    select_only(obj)
    diag = (Vector(obj.dimensions)).length or 1.0
    rem = obj.modifiers.new("remesh", "REMESH")
    rem.mode = "VOXEL"
    rem.voxel_size = max(diag / 220.0, 1e-4)   # ~medium-poly manifold, then collapse
    rem.adaptivity = 0.0
    bpy.ops.object.modifier_apply(modifier="remesh")
    clean(obj)
    collapse_to(obj, TARGET)
else:
    # textured / plain: weld exact-coincident verts then iterative collapse
    clean(obj)
    collapse_to(obj, TARGET)

base_origin(obj)
select_only(obj)
bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
for p in obj.data.polygons:
    p.use_smooth = False

after = tri_count(obj)
select_only(obj)
bpy.ops.export_scene.gltf(filepath=DST, export_format="GLB", use_selection=True)

# --- self-verify ---
reset()
v = import_glb(DST)[0]
me = v.data
degen = 0
for poly in me.polygons:
    vs = [me.vertices[i].co for i in poly.vertices]
    o = vs[0]
    n = (vs[1] - o).cross(vs[2] - o)
    if n.length < 1e-6:
        degen += 1
has_vc = bool(me.color_attributes)
scale = tuple(round(s, 4) for s in v.scale)
print(f"DECIMATE_OK mode={mode} src_tris={before} -> out_tris={after} target={TARGET} "
      f"degenerate={degen} node_scale={scale} vertex_colors={has_vc}")
