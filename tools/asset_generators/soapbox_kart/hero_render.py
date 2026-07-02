"""Soapbox Kart Kit hero — assemble a race diorama from the kit GLBs + mascot
racers, render a 3/4 cover shot. Bright cartoon studio; light bloom separate.
    blender --background --python hero_render.py
"""
import bpy, math, mathutils, os

ROOT = r"D:/Projects/comfyui-toolchain/products/soapbox_kart_kit_v1"
KIT = f"{ROOT}/models_glb"
MASC = f"{ROOT}/mascots"
OUT = r"C:/Users/scher/AppData/Local/Temp/claude/D--Projects-comfyui-toolchain/0e5e1c40-e596-49a6-a43d-bfbe573d38ce/scratchpad/soapbox_kart_hero.png"

bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene


def imp(path, loc, rot=0, scale=1.0):
    if not os.path.exists(path):
        print("MISSING", path); return
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=path)
    for r in [o for o in bpy.data.objects if o not in before and not o.parent]:
        r.location = loc; r.rotation_euler.z = math.radians(rot); r.scale = (scale, scale, scale)


def kit(name, loc, rot=0, scale=1.0):
    imp(f"{KIT}/{name}.glb", loc, rot, scale)


def mascot(name, loc, rot=0, scale=1.0):
    imp(f"{MASC}/{name}.glb", loc, rot, scale)


# --- track: a straightaway (3 tiles) flanked by grass, curving off at the back ---
for gy in (-2, 0, 2, 4):
    kit("track_straight", (0, gy, 0))
kit("track_start", (0, -2, 0))
kit("track_corner", (0, 6, 0), rot=0)
kit("track_corner", (-2, 6, 0), rot=90)

# start gate over the line + banner behind
kit("finish_gate", (0, -1.9, 0))
kit("banner", (0, -3.4, 0))
kit("checkpoint_arch", (0, 4, 0))

# racers on the grid (karts + mascots), staggered
mascot("robot", (-0.5, 0.4, 0), rot=8)
mascot("frog", (0.55, 1.6, 0), rot=-6)
kit("kart_rocket", (-0.55, 2.8, 0), rot=6)
mascot("wizard", (0.5, -0.8, 0), rot=-4)

# cones + tire walls + hazards lining the track edges
for gy in (-2.4, -0.8, 0.8, 2.4, 4.0):
    kit("cone", (1.15, gy, 0)); kit("cone", (-1.15, gy, 0))
kit("tire_stack", (1.7, 1.6, 0)); kit("tire_stack", (-1.7, 0.0, 0))
kit("barrier", (1.7, -1.2, 0), rot=90); kit("haybale", (-1.7, 3.2, 0), rot=30)
kit("boost_pad", (0, 0.0, 0))
kit("pickup_boost", (0, 3.2, 0)); kit("flag_pole", (1.9, -2.6, 0)); kit("sign_arrow", (-1.9, -1.8, 0), rot=40)
kit("barrel", (1.9, 4.4, 0)); kit("oil_slick", (0.4, -1.0, 0))

# ground
bpy.ops.mesh.primitive_plane_add(size=40, location=(0, 1, -0.02))
gd = bpy.context.active_object
gm = bpy.data.materials.new("g"); gm.use_nodes = True
gm.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.10, 0.13, 0.11, 1)
gd.data.materials.append(gm)

# bright cartoon dusk studio
sc.world = bpy.data.worlds.new("W"); sc.world.use_nodes = True
bg = sc.world.node_tree.nodes["Background"]
bg.inputs[0].default_value = (0.22, 0.26, 0.34, 1.0); bg.inputs[1].default_value = 0.7
sc.view_settings.view_transform = 'Standard'


def sun(e, rot, c, sh=True):
    L = bpy.data.objects.new("S", bpy.data.lights.new("S", 'SUN')); sc.collection.objects.link(L)
    L.data.energy = e; L.data.angle = math.radians(9); L.data.color = c; L.data.use_shadow = sh
    L.rotation_euler = tuple(math.radians(a) for a in rot)


sun(3.2, (58, 20, 20), (1.0, 0.94, 0.85))
sun(1.6, (55, 0, 210), (0.7, 0.82, 0.98), False)
sun(1.1, (48, 0, 120), (1.0, 0.7, 0.55), False)

cam = bpy.data.objects.new("C", bpy.data.cameras.new("C")); sc.collection.objects.link(cam); sc.camera = cam
cam.data.type = 'ORTHO'; cam.data.ortho_scale = 11.0
cam.location = (7.5, -8.5, 6.5)
look = mathutils.Vector((0, 1.0, 0.6)) - mathutils.Vector(cam.location)
cam.rotation_euler = look.to_track_quat('-Z', 'Y').to_euler()

for eng in ('BLENDER_EEVEE_NEXT', 'BLENDER_EEVEE'):
    try:
        sc.render.engine = eng; break
    except Exception:
        continue
try:
    sc.eevee.taa_render_samples = 96
except Exception:
    pass
sc.render.resolution_x = 1600; sc.render.resolution_y = 1150
sc.render.filepath = OUT
bpy.ops.render.render(write_still=True)
print("KART HERO DONE ->", OUT)
