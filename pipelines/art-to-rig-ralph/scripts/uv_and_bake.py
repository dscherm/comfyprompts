"""UV-unwrap a character's prepared mesh and bake the TRELLIS texture onto it.

Inputs:  prepared GLB (untextured, the rig's source geometry)
         textured GLB (TRELLIS MeshTexturing output, same shape at TRELLIS scale)
Outputs: player_char_v1_for_accurig.obj  (cm scale, WITH UVs -> AccuRIG preserves them)
         rookie_albedo.png               (2048 albedo baked to the new UV layout)
         preview render for the visual checkpoint

Usage: blender --background --python uv_and_bake.py --            <prepared.glb> <textured.glb> <out_dir> <name> <accurig_obj_out>
"""
import bpy
import bmesh
import sys
from mathutils import Vector

a = sys.argv[sys.argv.index("--") + 1:]
PREPARED, TEXTURED, OUTDIR, NAME, OBJ_OUT = a[0], a[1], a[2], a[3], a[4]

bpy.ops.wm.read_factory_settings(use_empty=True)

# ---- target: prepared mesh, welded, smart-UV ------------------------------
bpy.ops.import_scene.gltf(filepath=PREPARED)
meshes = [o for o in bpy.data.objects if o.type == "MESH"]
tgt = max(meshes, key=lambda o: len(o.data.vertices))
for o in meshes:
    if o is not tgt:
        bpy.data.objects.remove(o, do_unlink=True)
tgt.name = "rookie_target"

bm = bmesh.new(); bm.from_mesh(tgt.data)
bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=1e-5)
bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
bm.to_mesh(tgt.data); bm.free(); tgt.data.update()

bpy.context.view_layer.objects.active = tgt
bpy.ops.object.select_all(action="DESELECT")
tgt.select_set(True)
bpy.ops.object.mode_set(mode="EDIT")
bpy.ops.mesh.select_all(action="SELECT")
bpy.ops.uv.smart_project(angle_limit=1.15192, island_margin=0.003)  # 66 deg
bpy.ops.object.mode_set(mode="OBJECT")
print("UV_DONE islands margin ok, uvs:", len(tgt.data.uv_layers))

# ---- source: textured TRELLIS mesh, normalized onto the target ------------
before = set(bpy.data.objects)
bpy.ops.import_scene.gltf(filepath=TEXTURED)
src_meshes = [o for o in set(bpy.data.objects) - before if o.type == "MESH"]
src = max(src_meshes, key=lambda o: len(o.data.vertices))
src.name = "rookie_source"

# normalize source exactly like mesh-prep did: height 1.8, centered, grounded
h = src.dimensions.z
s = 1.8 / h
src.scale = (s, s, s)
bpy.context.view_layer.objects.active = src
bpy.ops.object.select_all(action="DESELECT")
src.select_set(True)
bpy.ops.object.transform_apply(scale=True)
bpy.ops.object.origin_set(type="ORIGIN_GEOMETRY", center="BOUNDS")
src.location = (0.0, 0.0, 0.0)
bpy.ops.object.transform_apply(location=True)
mw = src.matrix_world
lowest = min((mw @ v.co).z for v in src.data.vertices)
src.location.z -= lowest
bpy.ops.object.transform_apply(location=True)
print("SRC_ALIGNED dims", tuple(round(d, 3) for d in src.dimensions))

# ---- bake: source diffuse color -> target UV layout ------------------------
img = bpy.data.images.new(f"{NAME}_albedo", 2048, 2048, alpha=False)
mat = bpy.data.materials.new("bake_target")
mat.use_nodes = True
node = mat.node_tree.nodes.new("ShaderNodeTexImage")
node.image = img
mat.node_tree.nodes.active = node
tgt.data.materials.clear()
tgt.data.materials.append(mat)

# Zero the METALLIC influence before a DIFFUSE-color bake: TRELLIS texturing
# ships a metallic/roughness map, and metals have no diffuse — they bake BLACK
# (pip came out charcoal). Unlinking Metallic makes every surface bake its base
# color. (An EMIT bake was tried instead and writes LINEAR radiance — saved
# PNGs come out dark; the DIFFUSE COLOR pass handles the transform correctly.)
for smat in src.data.materials:            # NB: do not shadow `mat` (bake target)
    if not smat or not smat.use_nodes:
        continue
    nt = smat.node_tree
    bsdf = next((n for n in nt.nodes if n.type == "BSDF_PRINCIPLED"), None)
    if bsdf is None:
        continue
    met = bsdf.inputs["Metallic"]
    for lk in list(met.links):
        nt.links.remove(lk)
    met.default_value = 0.0
    print(f"METALLIC_ZEROED {smat.name}")

scene = bpy.context.scene
scene.render.engine = "CYCLES"
scene.cycles.device = "CPU"          # GPU is busy with ComfyUI
scene.cycles.samples = 16
scene.render.bake.use_selected_to_active = True
scene.render.bake.cage_extrusion = 0.03
scene.render.bake.use_pass_direct = False
scene.render.bake.use_pass_indirect = False

bpy.ops.object.select_all(action="DESELECT")
src.select_set(True)
tgt.select_set(True)
bpy.context.view_layer.objects.active = tgt
bpy.ops.object.bake(type="DIFFUSE", pass_filter={"COLOR"})
img.filepath_raw = f"{OUTDIR}/{NAME}_albedo.png"
img.file_format = "PNG"
img.save()
print("BAKE_DONE", img.filepath_raw)

# ---- export: cm OBJ WITH UVs for AccuRIG -----------------------------------
bpy.ops.object.select_all(action="DESELECT")
tgt.select_set(True)
bpy.context.view_layer.objects.active = tgt
tgt.scale = (100, 100, 100)
bpy.ops.object.transform_apply(scale=True)
obj_out = OBJ_OUT
bpy.ops.wm.obj_export(filepath=obj_out, export_selected_objects=True,
                      export_materials=False, export_uv=True)
print("OBJ_DONE", obj_out)

# ---- preview render of the textured target ---------------------------------
tgt.scale = (0.01, 0.01, 0.01)
bpy.ops.object.transform_apply(scale=True)
bsdf = mat.node_tree.nodes.get("Principled BSDF")
mat.node_tree.links.new(node.outputs["Color"], bsdf.inputs["Base Color"])
src.hide_render = True

scene.render.engine = "BLENDER_EEVEE"
scene.render.resolution_x = 720
scene.render.resolution_y = 900
cam_data = bpy.data.cameras.new("C")
cam = bpy.data.objects.new("C", cam_data)
scene.collection.objects.link(cam)
scene.camera = cam
cam.data.type = "ORTHO"
cam.data.ortho_scale = 2.1
sun_data = bpy.data.lights.new("S", type="SUN")
sun = bpy.data.objects.new("S", sun_data)
scene.collection.objects.link(sun)
sun.data.energy = 4.0
sun.rotation_euler = (0.7, 0.1, 0.2)
if scene.world is None:
    scene.world = bpy.data.worlds.new("W")
scene.world.use_nodes = True
scene.world.node_tree.nodes["Background"].inputs[0].default_value = (0.85, 0.85, 0.85, 1)
for label, loc, rot in (("front", (0, -3, 0.9), (1.5708, 0, 0)),
                        ("back", (0, 3, 0.9), (1.5708, 0, 3.1416))):
    cam.location = loc
    cam.rotation_euler = rot
    scene.render.filepath = f"{OUTDIR}/{NAME}_textured_{label}.png"
    bpy.ops.render.render(write_still=True)
print("PREVIEWS_DONE")
