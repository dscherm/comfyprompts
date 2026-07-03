"""Assemble complete castles from kit_castle parts (proves the grid snaps).
blender -b --python assemble_castles.py -- <grand|dark> <out.png>
"""
import math
import sys

D = r"D:/Projects/comfyui-toolchain/tools/asset_generators/village_kit"
sys.path.insert(0, D)
import bpy  # noqa: E402
import mathutils  # noqa: E402
import kit_castle as C  # noqa: E402
from kitlib import EMISSION, PALETTE, Kit  # noqa: E402

NAME = sys.argv[sys.argv.index("--") + 1]
OUT = sys.argv[sys.argv.index("--") + 2]
DARK = NAME == "dark"


def place(o, x, y, z=0, rz=0):
    o.location = (x, y, z)
    o.rotation_euler = (0, 0, math.radians(rz))
    return o


def spired_tower(k, x, y, cap, storeys=2):
    for s in range(storeys):
        m = C._recolor(k, C.tower_round_mid, "mid", C._DARK) if DARK else C.tower_round_mid(k)
        place(m, x, y, s * 1.0)
    place(cap(k), x, y, storeys * 1.0)


def build(k):
    wall = C.wall_dark if DARK else C.wall
    wall_arrow = C.wall_arrow_dark if DARK else C.wall_arrow
    gate = C.gatehouse_dark if DARK else C.gatehouse
    keep = C.keep_dark if DARK else C.keep
    hall = C.great_hall_dark if DARK else C.great_hall
    chapel = C.chapel_dark if DARK else C.chapel
    cap = C.cap_cone_dark if DARK else C.cap_cone_slate
    cap2 = C.cap_cone_tall_red if DARK else C.cap_cone_red

    # four corner spired towers (enclosure corners at (+-2, +-2))
    spired_tower(k, -2, -2, cap, 2)
    spired_tower(k, 2, -2, cap, 2)
    spired_tower(k, -2, 2, cap2, 3)      # taller rear towers
    spired_tower(k, 2, 2, cap2, 3)

    # front curtain wall + central gatehouse
    place(gate(k), 0, -2, 0)
    for x in (-1, 1):
        place(wall_arrow(k), x, -2, 0)
    # back curtain wall
    for x in (-1, 0, 1):
        place(wall(k), x, 2, 0, 180)
    # side curtain walls (rotated to run along Y)
    for y in (-1, 0, 1):
        place(wall(k), -2, y, 0, 90)
        place(wall(k), 2, y, 0, 90)

    # central keep + inner ward buildings
    place(keep(k), 0, 0.7, 0)
    place(hall(k), -1.0, -0.5, 0, 90)
    place(chapel(k), 1.05, -0.3, 0, -90)

    # courtyard dressing
    if DARK:
        place(C.brazier_witch(k), -0.7, -1.1, 0)
        place(C.brazier_witch(k), 0.7, -1.1, 0)
        place(C.banner_pole(k), 0.8, 0.9, 0)
    else:
        place(C.well(k), 0.7, -1.0, 0)
        place(C.market_stall(k), -0.9, 1.0, 0)
        place(C.banner_pole(k), 0.85, 1.0, 0)
        place(C.tree(k), -1.1, 1.2, 0)


k = Kit(palette=dict(PALETTE), emission=EMISSION, reset_scene=True, atlas=True)
scene = k.scene
build(k)
for img in k._atlas_imgs:
    if not img.packed_file:
        img.pack()

gk = Kit(palette=dict(PALETTE), emission=EMISSION, atlas=False)
gk.box([], 60, 60, 0.1, (0, 0, -0.06), "dirt" if DARK else "grass")

sun = bpy.data.objects.new("S", bpy.data.lights.new("S", "SUN"))
scene.collection.objects.link(sun)
fill = bpy.data.objects.new("F", bpy.data.lights.new("F", "SUN"))
scene.collection.objects.link(fill)
fill.data.use_shadow = False
scene.world = bpy.data.worlds.new("W")
scene.world.use_nodes = True
bg = scene.world.node_tree.nodes["Background"]
scene.view_settings.view_transform = "Standard"
if DARK:
    sun.data.energy = 1.1
    sun.data.color = (0.55, 0.62, 0.85)
    sun.rotation_euler = (math.radians(58), math.radians(8), math.radians(35))
    fill.data.energy = 0.4
    fill.data.color = (0.7, 0.4, 0.25)
    fill.rotation_euler = (math.radians(70), 0, math.radians(200))
    bg.inputs[1].default_value = 0.16
    bg.inputs[0].default_value = (0.05, 0.06, 0.09, 1)
else:
    sun.data.energy = 3.2
    sun.data.color = (1.0, 0.95, 0.82)
    sun.rotation_euler = (math.radians(52), math.radians(10), math.radians(38))
    fill.data.energy = 0.8
    fill.data.color = (0.6, 0.72, 0.95)
    fill.rotation_euler = (math.radians(66), 0, math.radians(210))
    bg.inputs[1].default_value = 0.6
    bg.inputs[0].default_value = (0.66, 0.76, 0.86, 1)

cam = bpy.data.objects.new("C", bpy.data.cameras.new("C"))
scene.collection.objects.link(cam)
scene.camera = cam
cam.data.type = "ORTHO"
cam.data.ortho_scale = 8.4
cam.location = (5.2, -6.4, 4.8)
look = mathutils.Vector((0, 0, 0.8)) - mathutils.Vector(cam.location)
cam.rotation_euler = look.to_track_quat("-Z", "Y").to_euler()
for eng in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE"):
    try:
        scene.render.engine = eng
        break
    except (TypeError, AttributeError):
        continue
try:
    scene.eevee.taa_render_samples = 96
except Exception:
    pass
scene.render.resolution_x = 1800
scene.render.resolution_y = 1350
scene.render.filepath = OUT
bpy.ops.render.render(write_still=True)
print("CASTLE ASSEMBLED OK", NAME, OUT)
