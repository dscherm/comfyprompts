"""Studio render of a single DissonantCity piece (import its GLB, neutral studio,
3/4 view). For the item-by-item review. Bloom applied separately.
    blender --background --python studio_render.py -- <piece_name>
"""
import bpy, sys, math, mathutils

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else ["tower_tall_cyan"]
NAME = argv[0]
KIT = r"D:/Projects/comfyui-toolchain/products/dissonant_city_v1/models_glb"
OUT = rf"C:/Users/scher/AppData/Local/Temp/claude/D--Projects-comfyui-toolchain/0e5e1c40-e596-49a6-a43d-bfbe573d38ce/scratchpad/piece_{NAME}.png"

bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene

# import the piece GLB
bpy.ops.import_scene.gltf(filepath=f"{KIT}/{NAME}.glb")
objs = [o for o in bpy.data.objects if o.type == 'MESH']

# bounds -> frame
mn = mathutils.Vector((1e9, 1e9, 1e9)); mx = mathutils.Vector((-1e9, -1e9, -1e9))
for o in objs:
    for c in o.bound_box:
        w = o.matrix_world @ mathutils.Vector(c)
        mn = mathutils.Vector((min(mn[i], w[i]) for i in range(3)))
        mx = mathutils.Vector((max(mx[i], w[i]) for i in range(3)))
ctr = (mn + mx) / 2
size = max((mx - mn).x, (mx - mn).y, (mx - mn).z)

# neutral dark studio (so flat colors + neon both read)
sc.world = bpy.data.worlds.new("W"); sc.world.use_nodes = True
bg = sc.world.node_tree.nodes["Background"]
bg.inputs[0].default_value = (0.10, 0.10, 0.13, 1.0); bg.inputs[1].default_value = 0.5
sc.view_settings.view_transform = 'Standard'

def sun(e, rot, c, sh=True):
    L = bpy.data.objects.new("S", bpy.data.lights.new("S", 'SUN')); sc.collection.objects.link(L)
    L.data.energy = e; L.data.angle = math.radians(8); L.data.color = c; L.data.use_shadow = sh
    L.rotation_euler = tuple(math.radians(a) for a in rot)
sun(3.0, (55, 12, 25), (1.0, 0.95, 0.88))     # key
sun(1.6, (60, 0, 210), (0.6, 0.8, 0.95), False)  # cool fill
sun(1.2, (50, 0, 130), (1.0, 0.6, 0.8), False)   # warm rim

# ground shadow-catcher disc
bpy.ops.mesh.primitive_circle_add(radius=size * 1.4, fill_type='NGON', location=(ctr.x, ctr.y, mn.z))
gd = bpy.context.active_object
gm = bpy.data.materials.new("g"); gm.use_nodes = True
gm.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.07, 0.07, 0.09, 1)
gd.data.materials.append(gm)

cam = bpy.data.objects.new("C", bpy.data.cameras.new("C")); sc.collection.objects.link(cam); sc.camera = cam
d = size * 2.0
cam.location = (ctr.x + d, ctr.y - d, ctr.z + d * 0.7)
look = ctr - mathutils.Vector(cam.location); cam.rotation_euler = look.to_track_quat('-Z', 'Y').to_euler()
cam.data.lens = 50

for eng in ('BLENDER_EEVEE_NEXT', 'BLENDER_EEVEE'):
    try:
        sc.render.engine = eng; break
    except Exception:
        continue
try:
    sc.eevee.taa_render_samples = 64
except Exception:
    pass
sc.render.resolution_x = 800; sc.render.resolution_y = 800
sc.render.filepath = OUT
bpy.ops.render.render(write_still=True)
print("PIECE RENDER DONE ->", OUT)
