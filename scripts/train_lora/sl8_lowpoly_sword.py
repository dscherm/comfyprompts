"""sl8_lowpoly_sword — weld + decimate a TRELLIS.2 sword mesh to low-poly (Task SL8).

TRELLIS.2 outputs a dense (~1M face) and UNWELDED mesh (coincident-vertex fragments
— see memory trellis-unwelded-mesh-weld-before-smooth). This: imports the GLB, joins
+ WELDS (merge by distance) FIRST, then decimates to a low-poly target, shade-flats,
recenters, and exports a clean low-poly GLB for flat-shaded rendering into lowpoly_flat.

Headless Blender (import/decimate/export — CPU, no GPU):
  blender --background --factory-startup --python sl8_lowpoly_sword.py -- <in.glb> <out.glb> [target_faces]
"""
import sys
import bpy
import bmesh

argv = sys.argv[sys.argv.index("--") + 1:]
IN, OUT = argv[0], argv[1]
TARGET = int(argv[2]) if len(argv) > 2 else 1200

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=IN)

meshes = [o for o in bpy.data.objects if o.type == "MESH"]
if not meshes:
    raise SystemExit("no mesh in " + IN)

# Join all mesh fragments into one object.
bpy.ops.object.select_all(action="DESELECT")
for o in meshes:
    o.select_set(True)
bpy.context.view_layer.objects.active = meshes[0]
if len(meshes) > 1:
    bpy.ops.object.join()
obj = bpy.context.view_layer.objects.active

# WELD FIRST (merge coincident TRELLIS fragments) — before any decimation.
me = obj.data
bm = bmesh.new(); bm.from_mesh(me)
bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-4)
bm.to_mesh(me); bm.free()
me.update()
welded_faces = len(me.polygons)

# Decimate to the low-poly target.
if welded_faces > TARGET:
    dec = obj.modifiers.new("dec", "DECIMATE")
    dec.decimate_type = "COLLAPSE"
    dec.ratio = max(0.01, TARGET / welded_faces)
    bpy.ops.object.modifier_apply(modifier=dec.name)

# Faceted low-poly look + recenter to origin, feet/base at Z=0-ish (center bbox).
for p in obj.data.polygons:
    p.use_smooth = False
bpy.ops.object.origin_set(type="ORIGIN_GEOMETRY", center="BOUNDS")
obj.location = (0.0, 0.0, 0.0)

final_faces = len(obj.data.polygons)
bpy.ops.object.select_all(action="DESELECT")
obj.select_set(True)
bpy.context.view_layer.objects.active = obj
bpy.ops.export_scene.gltf(filepath=OUT, export_format="GLB", use_selection=True,
                          export_animations=False)
print("LOWPOLY %s  welded_faces=%d -> final_faces=%d" % (OUT, welded_faces, final_faces))
