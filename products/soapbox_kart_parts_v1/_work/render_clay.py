"""render_clay.py — headless Blender clay render of a GLB from 4 orbit angles.

TRELLIS output is geometry-only (grey), so a uniform clay material + even lighting is the
honest way to judge topology/shape. Renders <name>_v0..v3.png (front, 3/4, side, back) into
an output dir for montage review.

Usage (headless):
    blender --background --python render_clay.py -- <glb_path> <name> <out_dir> [px]
"""
import sys
import math
import bpy

argv = sys.argv[sys.argv.index("--") + 1:]
glb, name, out_dir = argv[0], argv[1], argv[2]
px = int(argv[3]) if len(argv) > 3 else 640

# --- clean scene ---
bpy.ops.wm.read_factory_settings(use_empty=True)

# --- import ---
bpy.ops.import_scene.gltf(filepath=glb)
meshes = [o for o in bpy.context.scene.objects if o.type == "MESH"]
if not meshes:
    print("NO MESH IMPORTED", flush=True); sys.exit(1)

# --- center + measure bbox over all meshes (world space) ---
import mathutils
mn = mathutils.Vector((1e9, 1e9, 1e9)); mx = mathutils.Vector((-1e9, -1e9, -1e9))
for o in meshes:
    for c in o.bound_box:
        w = o.matrix_world @ mathutils.Vector(c)
        mn = mathutils.Vector(map(min, mn, w)); mx = mathutils.Vector(map(max, mx, w))
center = (mn + mx) / 2
size = max((mx - mn).x, (mx - mn).y, (mx - mn).z) or 1.0

# --- clay material on everything ---
clay = bpy.data.materials.new("clay"); clay.use_nodes = True
bsdf = clay.node_tree.nodes.get("Principled BSDF")
bsdf.inputs["Base Color"].default_value = (0.62, 0.62, 0.64, 1)
bsdf.inputs["Roughness"].default_value = 0.65
for o in meshes:
    o.data.materials.clear(); o.data.materials.append(clay)

# --- world (soft grey studio) ---
world = bpy.data.worlds.new("w"); bpy.context.scene.world = world
world.use_nodes = True
world.node_tree.nodes["Background"].inputs[0].default_value = (0.9, 0.9, 0.92, 1)
world.node_tree.nodes["Background"].inputs[1].default_value = 0.6

# --- key + fill lights ---
for i, (rot, e) in enumerate([((0.6, 0, 0.8), 4.0), ((0.7, 0, -2.2), 2.0)]):
    l = bpy.data.lights.new(f"sun{i}", "SUN"); l.energy = e
    ob = bpy.data.objects.new(f"sun{i}", l); bpy.context.scene.collection.objects.link(ob)
    ob.rotation_euler = rot

# --- camera ---
cam_data = bpy.data.cameras.new("cam"); cam = bpy.data.objects.new("cam", cam_data)
bpy.context.scene.collection.objects.link(cam); bpy.context.scene.camera = cam
dist = size * 2.1

# --- render settings ---
sc = bpy.context.scene
sc.render.engine = "BLENDER_EEVEE_NEXT" if "BLENDER_EEVEE_NEXT" in \
    [e.identifier for e in bpy.types.RenderSettings.bl_rna.properties["engine"].enum_items] else "BLENDER_EEVEE"
sc.render.resolution_x = px; sc.render.resolution_y = px
sc.render.film_transparent = False

angles = [("front", 0), ("threequarter", 45), ("side", 90), ("back", 180)]
for label, deg in angles:
    a = math.radians(deg)
    cam.location = (center.x + dist * math.sin(a), center.y - dist * math.cos(a), center.z + size * 0.5)
    # aim camera at center
    d = center - cam.location
    cam.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()
    sc.render.filepath = f"{out_dir}/{name}_{label}.png"
    bpy.ops.render.render(write_still=True)
    print(f"rendered {label}", flush=True)
print("CLAY_RENDER_DONE", flush=True)
