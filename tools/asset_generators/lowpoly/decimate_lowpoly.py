"""Decimate a raw image-to-3D mesh (TRELLIS/Hunyuan3D, ~20k+ tris) down to a
game-ready low-poly budget, with the full cleanup the low-poly skill's Stage 3
requires: join -> collapse-decimate to target -> merge-by-distance -> recalc
normals -> degenerate scrub -> base-centre pivot -> bake scale/rotation ->
export GLB (baked texture preserved). Headless so a factory-reset scene can't
touch the user's live Blender session.

    blender -b --python decimate_lowpoly.py -- <in.glb> <out.glb> <target_tris>

Prints DECIMATE_OK with before/after tris, degenerate count, node scale, and
whether an image texture survived — self-verification for the pipeline.
"""
import sys

import bmesh
import bpy

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
    # drop zero-area faces (same criterion as kitlib._clean_degenerate)
    degen = [f for f in bm.faces if f.calc_area() < 1e-9]
    if degen:
        bmesh.ops.delete(bm, geom=degen, context="FACES")
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(me)
    bm.free()
    me.update()


def set_base_origin(obj):
    import mathutils
    me = obj.data
    xs = [v.co.x for v in me.vertices]
    ys = [v.co.y for v in me.vertices]
    zs = [v.co.z for v in me.vertices]
    if not xs:
        return
    c = mathutils.Vector(((min(xs)+max(xs))/2, (min(ys)+max(ys))/2, min(zs)))
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
mat = obj.data.materials[0].name if obj.data.materials else None
has_tex_before = any(
    n.type == "TEX_IMAGE"
    for m in obj.data.materials if m and m.use_nodes
    for n in m.node_tree.nodes)

# PRE-WELD: image-to-3D shells ship split/unwelded verts; collapse-decimate
# tears those into shards. Welding first (larger dist) makes collapse behave.
pre = bmesh.new()
pre.from_mesh(obj.data)
bmesh.ops.remove_doubles(pre, verts=pre.verts[:], dist=1e-3)
pre.to_mesh(obj.data)
pre.free()
obj.data.update()

# collapse-decimate to the target ratio (organic image-to-3D meshes)
select_only(obj)
if tri_count(obj) > TARGET:
    dec = obj.modifiers.new("dec", "DECIMATE")
    dec.decimate_type = "COLLAPSE"
    dec.ratio = max(0.01, min(1.0, TARGET / tri_count(obj)))
    dec.use_collapse_triangulate = True
    bpy.ops.object.modifier_apply(modifier="dec")

clean(obj)
set_base_origin(obj)
# bake scale+rotation so glTF ships an identity node (matches kitlib exporters)
select_only(obj)
bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
for p in obj.data.polygons:
    p.use_smooth = False  # flat low-poly shading

after = tri_count(obj)
select_only(obj)
bpy.ops.export_scene.gltf(filepath=DST, export_format="GLB", use_selection=True)

# --- self-verify ---
reset()
v = import_glb(DST)[0]
degen = 0
me = v.data
for poly in me.polygons:
    vs = [me.vertices[i].co for i in poly.vertices]
    o = vs[0]
    n = (vs[1] - o).cross(vs[2] - o)
    if n.length < 1e-6:
        degen += 1
has_tex = any(n.type == "TEX_IMAGE" for m in v.data.materials if m and m.use_nodes
              for n in m.node_tree.nodes)
scale = tuple(round(s, 4) for s in v.scale)
print(f"DECIMATE_OK src_tris={before} -> out_tris={after} target={TARGET} "
      f"degenerate={degen} node_scale={scale} material={mat} "
      f"tex_before={has_tex_before} tex_after={has_tex}")
