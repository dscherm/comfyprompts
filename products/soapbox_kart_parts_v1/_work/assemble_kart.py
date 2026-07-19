"""assemble_kart.py — snap a full kart from kit parts to prove the modular system.

Places each part on the hot-rod chassis (front = +Y, per lp_chassis_rail's cowl). This is
a demo assembly: positions/scales are a hand-tuned loadout (the low-poly parts are centered
on their own bbox, not on a mount pivot, so exact socket-snapping needs per-part pivots — a
later refinement). Renders clay views of the assembled kart.

    blender --background --python assemble_kart.py -- [out_dir]
"""
import bpy, math, sys, os, mathutils

ROOT = "D:/Projects/comfyui-toolchain/products/soapbox_kart_parts_v1"
LP = ROOT + "/lowpoly"
ML = ROOT + "/models_lowpoly"
OUT = sys.argv[sys.argv.index("--") + 1] if "--" in sys.argv and len(sys.argv) > sys.argv.index("--") + 1 else ROOT + "/_work/assembly"

# name, glb, position, rotation(deg XYZ), uniform scale
LOADOUT = [
    ("chassis",  f"{LP}/lp_chassis_rail.glb", (0, 0, 0.0), (0, 0, 0), 1.0),
    ("wheelFL",  f"{LP}/lp_wheel.glb", (-0.42,  0.66, 0.22), (0, 0, 0), 0.52),
    ("wheelFR",  f"{LP}/lp_wheel.glb", ( 0.42,  0.66, 0.22), (0, 0, 0), 0.52),
    ("wheelRL",  f"{LP}/lp_wheel.glb", (-0.42, -0.66, 0.22), (0, 0, 0), 0.52),
    ("wheelRR",  f"{LP}/lp_wheel.glb", ( 0.42, -0.66, 0.22), (0, 0, 0), 0.52),
    ("engine",   f"{ML}/engine_steam.glb", (0, -0.55, 0.34), (0, 0, 0), 0.42),
    ("seat",     f"{ML}/seat_bucket.glb", (0, -0.06, 0.34), (0, 0, 180), 0.44),
    ("steering", f"{LP}/lp_steering_wheel.glb", (0, 0.20, 0.36), (25, 0, 0), 0.55),
    ("roof",     f"{LP}/lp_rollcage.glb", (0, -0.02, 0.40), (0, 0, 0), 0.80),
    ("nose",     f"{LP}/lp_grille.glb", (0, 0.66, 0.30), (0, 0, 180), 0.85),
    ("tail",     f"{LP}/lp_tail_stacks.glb", (0, -0.66, 0.28), (0, 0, 0), 0.85),
    ("sideL",    f"{LP}/lp_number_plate.glb", (-0.34, 0.05, 0.34), (0, 0, 90), 0.7),
    ("sideR",    f"{LP}/lp_number_plate.glb", ( 0.34, 0.05, 0.34), (0, 0, -90), 0.7),
]


def place(name, glb, pos, rot_deg, scale):
    before = set(bpy.context.scene.objects)
    bpy.ops.import_scene.gltf(filepath=glb)
    new = [o for o in bpy.context.scene.objects if o not in before and o.type == "MESH"]
    bpy.ops.object.select_all(action="DESELECT")
    for o in new:
        o.select_set(True)
    bpy.context.view_layer.objects.active = new[0]
    if len(new) > 1:
        bpy.ops.object.join()
    o = bpy.context.view_layer.objects.active
    o.name = name
    o.scale = (scale, scale, scale)
    o.rotation_euler = tuple(math.radians(a) for a in rot_deg)
    o.location = pos
    return o


def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    objs = [place(*spec) for spec in LOADOUT]

    # ground the kart: drop so the lowest wheel point sits at z=0
    bpy.context.view_layer.update()
    minz = min((o.matrix_world @ mathutils.Vector(c)).z
               for o in objs for c in o.bound_box)
    for o in objs:
        o.location.z -= minz

    # clay render
    os.makedirs(OUT, exist_ok=True)
    sc = bpy.context.scene
    sc.render.engine = "BLENDER_WORKBENCH"
    sc.display.shading.light = "STUDIO"; sc.display.shading.color_type = "SINGLE"
    sc.display.shading.single_color = (0.62, 0.62, 0.64); sc.display.shading.show_cavity = True
    sc.render.resolution_x = 900; sc.render.resolution_y = 700
    cam_d = bpy.data.cameras.new("Cam"); cam = bpy.data.objects.new("Cam", cam_d)
    bpy.context.collection.objects.link(cam); sc.camera = cam
    target = mathutils.Vector((0, 0, 0.45)); r = 3.4
    for nm, (az, el) in {"hero": (35, 22), "side": (90, 12), "front": (0, 14), "rear": (180, 16)}.items():
        aa, ee = math.radians(az), math.radians(el)
        cam.location = (r * math.sin(aa) * math.cos(ee), -r * math.cos(aa) * math.cos(ee), 0.45 + r * math.sin(ee))
        d = target - cam.location
        cam.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
        sc.render.filepath = os.path.join(OUT, f"kart_{nm}.png")
        bpy.ops.render.render(write_still=True)
        print("RENDERED", nm, flush=True)
    print("ASSEMBLY_DONE", flush=True)


if __name__ == "__main__":
    main()
