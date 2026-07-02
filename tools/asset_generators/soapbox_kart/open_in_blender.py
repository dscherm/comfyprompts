"""Open the Soapbox Kart Kit in the Blender GUI for a live visual pass.
Assembles a race diorama from the kit GLBs + mascot racers, sets Material-Preview
shading, frames the view, and LEAVES BLENDER OPEN (no render, no quit).
Launch (GUI, non-blocking):
    Start-Process "<blender.exe>" -ArgumentList '--python open_in_blender.py'
"""
import bpy, math, mathutils, os

ROOT = r"D:/Projects/comfyui-toolchain/products/soapbox_kart_kit_v1"
KIT = f"{ROOT}/models_glb"
MASC = f"{ROOT}/mascots"

bpy.ops.wm.read_factory_settings(use_empty=False)
# clear default scene
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete()
sc = bpy.context.scene


def imp(path, loc, rot=0):
    if not os.path.exists(path):
        print("MISSING", path); return
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=path)
    for r in [o for o in bpy.data.objects if o not in before and not o.parent]:
        r.location = loc; r.rotation_euler.z = math.radians(rot)


def kit(n, loc, rot=0): imp(f"{KIT}/{n}.glb", loc, rot)
def mascot(n, loc, rot=0): imp(f"{MASC}/{n}.glb", loc, rot)


# straightaway with a corner sweep
for gy in (-2, 0, 2, 4):
    kit("track_straight", (0, gy, 0))
kit("track_start", (0, -2, 0))
kit("track_corner", (0, 6, 0)); kit("track_corner", (-2, 6, 0), 90)
kit("finish_gate", (0, -1.9, 0)); kit("banner", (0, -3.4, 0)); kit("checkpoint_arch", (0, 4, 0))
# racers
mascot("robot", (-0.5, 0.4, 0), 8); mascot("frog", (0.55, 1.7, 0), -6)
mascot("wizard", (0.5, -0.8, 0), -4); kit("kart_rocket", (-0.55, 3.0, 0), 6)
# lining
for gy in (-2.4, -0.8, 0.8, 2.4, 4.0):
    kit("cone", (1.15, gy, 0)); kit("cone", (-1.15, gy, 0))
kit("tire_stack", (1.7, 1.6, 0)); kit("tire_stack", (-1.7, 0.0, 0))
kit("barrier", (1.7, -1.2, 0), 90); kit("haybale", (-1.7, 3.2, 0), 30)
kit("boost_pad", (0, 0.4, 0)); kit("pickup_boost", (0, 3.2, 0))
kit("flag_pole", (1.9, -2.6, 0)); kit("sign_arrow", (-1.9, -1.8, 0), 40)
kit("barrel", (1.9, 4.4, 0))

# ground + light
bpy.ops.mesh.primitive_plane_add(size=40, location=(0, 1, -0.02))
gd = bpy.context.active_object
gm = bpy.data.materials.new("g"); gm.use_nodes = True
gm.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.10, 0.13, 0.11, 1)
gd.data.materials.append(gm)
sc.world.use_nodes = True
sc.world.node_tree.nodes["Background"].inputs[0].default_value = (0.22, 0.26, 0.34, 1.0)

L = bpy.data.objects.new("S", bpy.data.lights.new("S", 'SUN')); sc.collection.objects.link(L)
L.data.energy = 3.0; L.rotation_euler = tuple(math.radians(a) for a in (58, 20, 20))
try:
    sc.render.engine = 'BLENDER_EEVEE_NEXT'
except Exception:
    pass

# Material-Preview shading in every 3D viewport + frame all
for w in bpy.context.window_manager.windows:
    for area in w.screen.areas:
        if area.type == 'VIEW_3D':
            for space in area.spaces:
                if space.type == 'VIEW_3D':
                    space.shading.type = 'MATERIAL'
                    space.clip_end = 1000
print("SCENE READY — explore in the viewport. (Material-Preview shading on.)")
