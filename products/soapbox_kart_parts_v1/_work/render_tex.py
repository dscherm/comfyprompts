"""render_tex.py — headless textured render of a GLB (keeps materials), 3 orbit views.
Usage: blender --background --python render_tex.py -- <glb> <name> <out_dir> [px]
"""
import bpy, math, sys, os, mathutils
argv = sys.argv[sys.argv.index("--") + 1:]
glb, name, out_dir = argv[0], argv[1], argv[2]
px = int(argv[3]) if len(argv) > 3 else 640

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=glb)
meshes = [o for o in bpy.context.scene.objects if o.type == "MESH"]
mn = mathutils.Vector((1e9,)*3); mx = mathutils.Vector((-1e9,)*3)
for o in meshes:
    for c in o.bound_box:
        w = o.matrix_world @ mathutils.Vector(c)
        mn = mathutils.Vector(map(min, mn, w)); mx = mathutils.Vector(map(max, mx, w))
center = (mn + mx) / 2; size = max((mx - mn).x, (mx - mn).y, (mx - mn).z) or 1.0

world = bpy.data.worlds.new("w"); bpy.context.scene.world = world; world.use_nodes = True
world.node_tree.nodes["Background"].inputs[0].default_value = (0.92, 0.92, 0.94, 1)
world.node_tree.nodes["Background"].inputs[1].default_value = 0.9
for rot, e in [((0.6, 0, 0.8), 3.0), ((0.7, 0, -2.2), 1.5)]:
    l = bpy.data.lights.new("s", "SUN"); l.energy = e
    ob = bpy.data.objects.new("s", l); bpy.context.scene.collection.objects.link(ob); ob.rotation_euler = rot

cam_d = bpy.data.cameras.new("c"); cam = bpy.data.objects.new("c", cam_d)
bpy.context.scene.collection.objects.link(cam); bpy.context.scene.camera = cam
sc = bpy.context.scene
engines = [e.identifier for e in bpy.types.RenderSettings.bl_rna.properties["engine"].enum_items]
sc.render.engine = "BLENDER_EEVEE_NEXT" if "BLENDER_EEVEE_NEXT" in engines else "BLENDER_EEVEE"
sc.render.resolution_x = px; sc.render.resolution_y = px
os.makedirs(out_dir, exist_ok=True)
dist = size * 2.1
for label, deg in [("front", 0), ("tq", 45), ("side", 90)]:
    a = math.radians(deg)
    cam.location = (center.x + dist*math.sin(a), center.y - dist*math.cos(a), center.z + size*0.4)
    d = center - cam.location; cam.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()
    sc.render.filepath = f"{out_dir}/{name}_{label}.png"
    bpy.ops.render.render(write_still=True)
print("TEX_RENDER_DONE", flush=True)
