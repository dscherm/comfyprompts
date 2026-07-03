"""Orbit turntable of the assembled grand castle.
blender -b --python turntable_castle.py -- <frames_dir> <N>
"""
import math
import sys

D = r"D:/Projects/comfyui-toolchain/tools/asset_generators/village_kit"
sys.path.insert(0, D)
import bpy  # noqa: E402
import mathutils  # noqa: E402
import kit_castle as C  # noqa: E402
from kitlib import EMISSION, PALETTE, Kit  # noqa: E402

FR = sys.argv[sys.argv.index("--") + 1]
N = int(sys.argv[sys.argv.index("--") + 2])


def place(o, x, y, z=0.0, rz=0.0):
    o.location = (x, y, z)
    o.rotation_euler = (0, 0, math.radians(rz))


k = Kit(palette=dict(PALETTE), emission=EMISSION, reset_scene=True, atlas=True)
scene = k.scene
place(C.tower_spire(k), -2, -2)
place(C.tower_spire(k), 2, -2)
place(C.tower_spire_tall(k), -2, 2)
place(C.tower_spire_tall(k), 2, 2)
place(C.gatehouse(k), 0, -2)
place(C.wall_arrow(k), -1, -2)
place(C.wall_arrow(k), 1, -2)
for x in (-1, 0, 1):
    place(C.wall(k), x, 2, 0, 180)
for y in (-1, 0, 1):
    place(C.wall(k), -2, y, 0, 90)
    place(C.wall(k), 2, y, 0, 90)
place(C.keep(k), 0, 0.85)
place(C.great_hall(k), -1.15, -0.85, 0, 90)
place(C.chapel(k), 1.25, -0.7)
place(C.well(k), 0.0, -1.2)
place(C.brazier(k), -0.55, -1.55)
place(C.brazier(k), 0.55, -1.55)
place(C.banner_pole(k), -1.4, 1.15)
place(C.pennant_pole(k), 1.4, 1.15)
for img in k._atlas_imgs:
    if not img.packed_file:
        img.pack()

gk = Kit(palette=dict(PALETTE), emission=EMISSION, atlas=False)
gk.box([], 60, 60, 0.1, (0, 0, -0.06), "grass")
sun = bpy.data.objects.new("S", bpy.data.lights.new("S", "SUN"))
scene.collection.objects.link(sun)
sun.data.energy = 3.1
sun.data.color = (1.0, 0.95, 0.83)
sun.rotation_euler = (math.radians(52), math.radians(10), math.radians(40))
fill = bpy.data.objects.new("F", bpy.data.lights.new("F", "SUN"))
scene.collection.objects.link(fill)
fill.data.energy = 0.7
fill.data.color = (0.6, 0.72, 0.95)
fill.data.use_shadow = False
fill.rotation_euler = (math.radians(66), 0, math.radians(210))
scene.world = bpy.data.worlds.new("W")
scene.world.use_nodes = True
bg = scene.world.node_tree.nodes["Background"]
bg.inputs[1].default_value = 0.6
bg.inputs[0].default_value = (0.62, 0.72, 0.6, 1)
scene.view_settings.view_transform = "Standard"
cam = bpy.data.objects.new("C", bpy.data.cameras.new("C"))
scene.collection.objects.link(cam)
scene.camera = cam
cam.data.type = "ORTHO"
cam.data.ortho_scale = 8.6
for eng in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE"):
    try:
        scene.render.engine = eng
        break
    except (TypeError, AttributeError):
        continue
try:
    scene.eevee.taa_render_samples = 48
except Exception:
    pass
scene.render.resolution_x = 900
scene.render.resolution_y = 720
tgt = mathutils.Vector((0, 0, 1.0))
rad = 8.5
for i in range(N):
    a = math.radians(i * 360.0 / N)
    cam.location = (math.cos(a) * rad, math.sin(a) * rad, 5.2)
    cam.rotation_euler = (tgt - mathutils.Vector(cam.location)).to_track_quat("-Z", "Y").to_euler()
    scene.render.filepath = "%s/f%03d.png" % (FR, i)
    bpy.ops.render.render(write_still=True)
print("CASTLE TURNTABLE OK", N)
