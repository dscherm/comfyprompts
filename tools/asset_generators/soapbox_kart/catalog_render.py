"""Catalog grid render of the Soapbox Kart Kit — import every GLB, lay out on a
grid, one 3/4 camera, bright neutral cartoon studio (light bloom only for the
glowing pickups/boost pads). Bloom applied separately (../dissonant_city/bloom.py).
    blender --background --python catalog_render.py
"""
import bpy, math, mathutils, os

KIT = r"D:/Projects/comfyui-toolchain/products/soapbox_kart_kit_v1/models_glb"
OUT = r"C:/Users/scher/AppData/Local/Temp/claude/D--Projects-comfyui-toolchain/0e5e1c40-e596-49a6-a43d-bfbe573d38ce/scratchpad/soapbox_kart_catalog.png"

ORDER = [
    "kart_racer", "kart_rocket", "kart_tub", "kart_crate",
    "track_straight", "track_corner", "track_start", "ramp_up", "jump_ramp",
    "finish_gate", "checkpoint_arch", "banner", "sign_arrow", "flag_pole",
    "cone", "tire_stack", "crate", "barrier", "barrel", "haybale",
    "oil_slick", "puddle", "boost_pad", "pickup_boost", "pickup_shield", "pickup_wrench",
]
COLS = 6
SPACING = 2.7

bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene


def imp(name, loc):
    path = f"{KIT}/{name}.glb"
    if not os.path.exists(path):
        print("MISSING", path)
        return None
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=path)
    roots = [o for o in bpy.data.objects if o not in before and not o.parent]
    for r in roots:
        r.location = loc
    return roots


present = {f[:-4] for f in os.listdir(KIT) if f.endswith(".glb")}
names = [n for n in ORDER if n in present] + sorted(present - set(ORDER))

mn = mathutils.Vector((1e9, 1e9, 1e9))
mx = mathutils.Vector((-1e9, -1e9, -1e9))
for i, name in enumerate(names):
    col, row = i % COLS, i // COLS
    gx = col * SPACING - (COLS - 1) * SPACING / 2
    gy = -row * SPACING
    roots = imp(name, (gx, gy, 0))
    if not roots:
        continue
    bpy.context.view_layer.update()
    for r in roots:
        for o in [r] + list(r.children_recursive):
            if o.type != 'MESH':
                continue
            for c in o.bound_box:
                w = o.matrix_world @ mathutils.Vector(c)
                mn = mathutils.Vector((min(mn[j], w[j]) for j in range(3)))
                mx = mathutils.Vector((max(mx[j], w[j]) for j in range(3)))

ctr = (mn + mx) / 2
span = max((mx - mn).x, (mx - mn).y)

# bright neutral cartoon studio — solid flat colors read best under even light
sc.world = bpy.data.worlds.new("W")
sc.world.use_nodes = True
bg = sc.world.node_tree.nodes["Background"]
bg.inputs[0].default_value = (0.16, 0.17, 0.20, 1.0)
bg.inputs[1].default_value = 0.7
sc.view_settings.view_transform = 'Standard'


def sun(e, rot, c, sh=True):
    L = bpy.data.objects.new("S", bpy.data.lights.new("S", 'SUN'))
    sc.collection.objects.link(L)
    L.data.energy = e
    L.data.angle = math.radians(10)
    L.data.color = c
    L.data.use_shadow = sh
    L.rotation_euler = tuple(math.radians(a) for a in rot)


sun(3.0, (55, 12, 25), (1.0, 0.96, 0.9))
sun(1.7, (60, 0, 210), (0.7, 0.82, 0.95), False)
sun(1.2, (50, 0, 130), (1.0, 0.85, 0.7), False)

bpy.ops.mesh.primitive_plane_add(size=span * 2.4, location=(ctr.x, ctr.y, mn.z - 0.02))
gd = bpy.context.active_object
gm = bpy.data.materials.new("g")
gm.use_nodes = True
gm.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.13, 0.14, 0.16, 1)
gd.data.materials.append(gm)

cam = bpy.data.objects.new("C", bpy.data.cameras.new("C"))
sc.collection.objects.link(cam)
sc.camera = cam
cam.data.type = 'ORTHO'
cam.data.ortho_scale = span * 1.16
d = span
cam.location = (ctr.x + d * 0.5, ctr.y - d * 0.95, ctr.z + d * 0.8)
look = mathutils.Vector((ctr.x, ctr.y, ctr.z + 0.3)) - mathutils.Vector(cam.location)
cam.rotation_euler = look.to_track_quat('-Z', 'Y').to_euler()

for eng in ('BLENDER_EEVEE_NEXT', 'BLENDER_EEVEE'):
    try:
        sc.render.engine = eng
        break
    except Exception:
        continue
try:
    sc.eevee.taa_render_samples = 96
except Exception:
    pass
sc.render.resolution_x = 1600
sc.render.resolution_y = 1200
sc.render.filepath = OUT
bpy.ops.render.render(write_still=True)
print(f"KART CATALOG DONE n={len(names)} ->", OUT)
