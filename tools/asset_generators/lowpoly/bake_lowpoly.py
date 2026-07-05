"""Bake a TRELLIS-textured mesh's colour onto a decimated low-poly mesh and export
a textured low-poly GLB (+ albedo PNG). Smart-UV unwrap the low-poly, normalise
both meshes to the same unit box so they overlap, bake DIFFUSE COLOR from the
textured source to the low-poly's new UVs, apply it, export. Headless.

Reuses the proven bits from the character pipeline's uv_and_bake.py:
  - smart_project angle 66deg, island margin 0.003
  - **unlink Metallic on the source** before a DIFFUSE-COLOR bake — TRELLIS
    texturing ships a metallic map, and metals bake BLACK on a diffuse pass.
  - selected_to_active DIFFUSE {COLOR}, CPU Cycles.

    blender -b --python bake_lowpoly.py -- <lowpoly.glb> <textured.glb> <out.glb> [albedo_px]
"""
import os
import sys

import bpy
import mathutils

a = sys.argv[sys.argv.index("--") + 1:]
LOW, TEX, OUT = a[0], a[1], a[2]
PX = int(a[3]) if len(a) > 3 else 2048


def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def imp(p):
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=p)
    return [o for o in bpy.data.objects if o not in before and o.type == "MESH"]


def sel(o):
    bpy.ops.object.select_all(action="DESELECT")
    o.select_set(True)
    bpy.context.view_layer.objects.active = o


def join(ms):
    if len(ms) == 1:
        return ms[0]
    sel(ms[0])
    for o in ms:
        o.select_set(True)
    bpy.ops.object.join()
    return bpy.context.active_object


def normalise(o):
    """Centre at origin and scale so the max dimension = 1 — both meshes share the
    same shape, so this makes them overlap for the selected-to-active bake."""
    sel(o)
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    bb = [o.matrix_world @ mathutils.Vector(c) for c in o.bound_box]
    mn = mathutils.Vector((min(v.x for v in bb), min(v.y for v in bb), min(v.z for v in bb)))
    mx = mathutils.Vector((max(v.x for v in bb), max(v.y for v in bb), max(v.z for v in bb)))
    size = max(mx - mn) or 1.0
    o.location -= (mn + mx) / 2
    sel(o)
    bpy.ops.object.transform_apply(location=True)
    o.scale = (1.0 / size,) * 3
    sel(o)
    bpy.ops.object.transform_apply(scale=True)


reset()

# target = low-poly, smart-UV unwrapped
tgt = join(imp(LOW))
normalise(tgt)
sel(tgt)
bpy.ops.object.mode_set(mode="EDIT")
bpy.ops.mesh.select_all(action="SELECT")
bpy.ops.uv.smart_project(angle_limit=1.15192, island_margin=0.003)
bpy.ops.object.mode_set(mode="OBJECT")

# source = textured full-res, normalised to overlap the target
src = join(imp(TEX))
normalise(src)

# bake image assigned to the target
img = bpy.data.images.new("albedo", PX, PX, alpha=False)
bmat = bpy.data.materials.new("bake_target")
bmat.use_nodes = True
node = bmat.node_tree.nodes.new("ShaderNodeTexImage")
node.image = img
bmat.node_tree.nodes.active = node
tgt.data.materials.clear()
tgt.data.materials.append(bmat)

# unlink Metallic on the source so metals don't bake black
for sm in src.data.materials:
    if sm and sm.use_nodes:
        bsdf = sm.node_tree.nodes.get("Principled BSDF")
        if bsdf:
            met = bsdf.inputs["Metallic"]
            for link in list(met.links):
                sm.node_tree.links.remove(link)
            met.default_value = 0.0

sc = bpy.context.scene
sc.render.engine = "CYCLES"
sc.cycles.device = "CPU"
sc.cycles.samples = 4
sc.render.bake.use_selected_to_active = True
sc.render.bake.cage_extrusion = 0.05
sc.render.bake.use_pass_direct = False
sc.render.bake.use_pass_indirect = False
bpy.ops.object.select_all(action="DESELECT")
src.select_set(True)
tgt.select_set(True)
bpy.context.view_layer.objects.active = tgt
bpy.ops.object.bake(type="DIFFUSE", pass_filter={"COLOR"})

albedo_name = os.path.splitext(os.path.basename(OUT))[0] + "_albedo.png"
albedo_path = os.path.join(os.path.dirname(OUT) or ".", albedo_name)
img.filepath_raw = albedo_path
img.file_format = "PNG"
img.save()

# apply the baked albedo as the target's base colour for export
appmat = bpy.data.materials.new("lowpoly_tex")
appmat.use_nodes = True
bsdf = appmat.node_tree.nodes["Principled BSDF"]
bsdf.inputs["Roughness"].default_value = 0.9
tex = appmat.node_tree.nodes.new("ShaderNodeTexImage")
tex.image = img
appmat.node_tree.links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
tgt.data.materials.clear()
tgt.data.materials.append(appmat)

for p in tgt.data.polygons:
    p.use_smooth = False
sel(tgt)
bpy.ops.export_scene.gltf(filepath=OUT, export_format="GLB", use_selection=True)
tris = sum(len(p.vertices) - 2 for p in tgt.data.polygons)
print(f"BAKE_OK lowpoly_tris={tris} albedo={albedo_path}")
