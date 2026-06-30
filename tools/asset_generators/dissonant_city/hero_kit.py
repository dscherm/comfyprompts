"""DissonantCity kit hero — import the exported GLB pieces, lay out a city, render.
Headless Blender. Bloom applied separately (bloom.py)."""
import bpy, math, mathutils, os

KIT = r"D:/Projects/comfyui-toolchain/products/dissonant_city_v1/models_glb"
OUT = r"C:/Users/scher/AppData/Local/Temp/claude/D--Projects-comfyui-toolchain/0e5e1c40-e596-49a6-a43d-bfbe573d38ce/scratchpad/dissonant_city_kit_hero.png"


def Hx(h):
    return tuple(int(h[i:i+2], 16) / 255 for i in (0, 2, 4)) + (1.0,)


def imp(name, loc, rot=0):
    path = f"{KIT}/{name}.glb"
    if not os.path.exists(path):
        return
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=path)
    for r in [o for o in bpy.data.objects if o not in before and not o.parent]:
        r.location = loc; r.rotation_euler.z = math.radians(rot)


bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene

# ground: road grid + plaza
for x in range(-3, 4):
    for y in range(-3, 4):
        gx, gy = x * 2, y * 2
        if x == 0 or y == 0:
            imp("road_junction" if x == 0 and y == 0 else "road_straight", (gx, gy, 0), 0 if x == 0 else 90)
        else:
            imp("plaza_tile", (gx, gy, 0))

# building ring on the grid
imp("tower_tall_cyan", (-4, 4, 0)); imp("tower_tall_purple", (4, 4, 0))
imp("tower_cyl", (-4, -4, 0)); imp("arcology", (4, -4, 0))
imp("dome_building", (0, 5, 0)); imp("ziggurat", (-5, 0, 0))
imp("slab_shop_pink", (5, 0.5, 0), 90); imp("slab_shop_cyan", (0, -5, 0))
imp("tower_short_pink", (5, 5, 0))
# skybridge between the two tall towers
imp("bridge_support", (-1.4, 4, 0)); imp("bridge_support", (1.4, 4, 0))
imp("skybridge", (0, 4, 0), 90)
# props / detail
imp("billboard", (-2, 2, 0), 30); imp("billboard", (2, -2, 0), -30)
imp("neon_arch", (0, 2, 0))
imp("hover_car", (-1.2, 0.6, 0.0), 20); imp("hover_car2", (1.4, -0.8, 0.0), -40)
imp("hover_car", (0.4, 2.6, 0.0), 70)
imp("antenna", (-5, 5, 0)); imp("holo_pylon", (3, 2, 0)); imp("holo_pylon", (-3, -2, 0))
imp("fountain_pad", (0, 0, 0))
for p in [(-2, -3), (2, 3), (-3, 2), (3, -3)]:
    imp("streetlight", (p[0], p[1], 0))
for p in [(-5, -3), (5, -2), (-2, 5)]:
    imp("crystals", (p[0], p[1], 0))
imp("palm_retro", (-3, 3, 0)); imp("palm_retro", (3, -2, 0))
imp("barrier", (1, 4, 0), 0)

# dusk neon mood
sc.world = bpy.data.worlds.new("W"); sc.world.use_nodes = True
bg = sc.world.node_tree.nodes["Background"]; bg.inputs[0].default_value = Hx("231033"); bg.inputs[1].default_value = 0.42
# big cream sun
bpy.ops.mesh.primitive_circle_add(radius=8, fill_type='NGON', location=(0, 24, 8), rotation=(math.radians(90), 0, 0))
s = bpy.context.active_object
sm = bpy.data.materials.new("sun"); sm.use_nodes = True
sb = sm.node_tree.nodes["Principled BSDF"]; sb.inputs["Emission Color"].default_value = Hx("FFD27A"); sb.inputs["Emission Strength"].default_value = 11
s.data.materials.append(sm)
sc.view_settings.view_transform = 'Standard'

def sun(e, rot, c, sh=True):
    L = bpy.data.objects.new("S", bpy.data.lights.new("S", 'SUN')); sc.collection.objects.link(L)
    L.data.energy = e; L.data.angle = math.radians(6); L.data.color = c; L.data.use_shadow = sh
    L.rotation_euler = tuple(math.radians(a) for a in rot)
sun(2.6, (62, 8, 8), (1.0, 0.80, 0.66)); sun(1.9, (58, 0, 210), (0.45, 0.85, 0.95), False)
sun(1.5, (50, 0, 30), (1.0, 0.35, 0.7), False)

cam = bpy.data.objects.new("C", bpy.data.cameras.new("C")); sc.collection.objects.link(cam); sc.camera = cam
cam.data.type = 'ORTHO'; cam.data.ortho_scale = 24; cam.location = (20, -20, 15)
look = mathutils.Vector((0, 0, 2.0)) - mathutils.Vector(cam.location)
cam.rotation_euler = look.to_track_quat('-Z', 'Y').to_euler()
for eng in ('BLENDER_EEVEE_NEXT', 'BLENDER_EEVEE'):
    try:
        sc.render.engine = eng; break
    except Exception:
        continue
try:
    sc.eevee.taa_render_samples = 64
except Exception:
    pass
sc.render.resolution_x = 1600; sc.render.resolution_y = 1150
sc.render.filepath = OUT
bpy.ops.render.render(write_still=True)
print("KIT HERO DONE ->", OUT)
