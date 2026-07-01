"""Per-piece turntable renders for the DissonantCity catalog gallery.
For every exported GLB: dark dusk-neon studio, auto-frame, render a 360° turntable
(F frames, object rotates on Z). Frames go to scratchpad; bloom + GIF assembly is
done separately (turntable_assemble.py) since EEVEE Next has no legacy bloom.

    blender --background --python turntable_render.py -- [frames] [res] [only_names_csv]
"""
import bpy, sys, math, mathutils, os

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
FRAMES = int(argv[0]) if len(argv) > 0 else 20
RES = int(argv[1]) if len(argv) > 1 else 512
ONLY = set(argv[2].split(",")) if len(argv) > 2 and argv[2] else None

KIT = r"D:/Projects/comfyui-toolchain/products/dissonant_city_v1/models_glb"
OUTROOT = r"C:/Users/scher/AppData/Local/Temp/claude/D--Projects-comfyui-toolchain/0e5e1c40-e596-49a6-a43d-bfbe573d38ce/scratchpad/turntable"
os.makedirs(OUTROOT, exist_ok=True)

names = sorted(f[:-4] for f in os.listdir(KIT) if f.endswith(".glb"))
if ONLY:
    names = [n for n in names if n in ONLY]


def clear():
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()
    for coll in (bpy.data.meshes, bpy.data.materials, bpy.data.lights, bpy.data.cameras):
        for b in list(coll):
            coll.remove(b)


def sun(sc, e, rot, c, sh=True):
    L = bpy.data.objects.new("S", bpy.data.lights.new("S", 'SUN'))
    sc.collection.objects.link(L)
    L.data.energy = e
    L.data.angle = math.radians(8)
    L.data.color = c
    L.data.use_shadow = sh
    L.rotation_euler = tuple(math.radians(a) for a in rot)


def studio(sc):
    # dark dusk-neon studio — dark-navy bodies stay navy, neon emission dominates
    sc.world = bpy.data.worlds.new("W")
    sc.world.use_nodes = True
    bg = sc.world.node_tree.nodes["Background"]
    bg.inputs[0].default_value = (0.035, 0.035, 0.065, 1.0)
    bg.inputs[1].default_value = 0.35
    sc.view_settings.view_transform = 'Standard'
    sun(sc, 1.15, (55, 12, 25), (1.0, 0.92, 0.82))        # dim warm key
    sun(sc, 0.70, (60, 0, 210), (0.45, 0.78, 0.98), False)  # cool fill
    sun(sc, 0.55, (50, 0, 130), (1.0, 0.45, 0.72), False)   # pink rim


bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
for eng in ('BLENDER_EEVEE_NEXT', 'BLENDER_EEVEE'):
    try:
        sc.render.engine = eng
        break
    except Exception:
        continue
try:
    sc.eevee.taa_render_samples = 48
except Exception:
    pass
sc.render.resolution_x = RES
sc.render.resolution_y = RES
sc.render.film_transparent = False

for name in names:
    clear()
    studio(sc)
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=f"{KIT}/{name}.glb")
    roots = [o for o in bpy.data.objects if o not in before and not o.parent]

    # bounds
    mn = mathutils.Vector((1e9, 1e9, 1e9))
    mx = mathutils.Vector((-1e9, -1e9, -1e9))
    for r in roots:
        for o in [r] + list(r.children_recursive):
            if o.type != 'MESH':
                continue
            for c in o.bound_box:
                w = o.matrix_world @ mathutils.Vector(c)
                mn = mathutils.Vector((min(mn[i], w[i]) for i in range(3)))
                mx = mathutils.Vector((max(mx[i], w[i]) for i in range(3)))
    ctr = (mn + mx) / 2
    size = max((mx - mn).x, (mx - mn).y, (mx - mn).z) or 2.0

    # pivot at footprint center; parent roots so the object spins on Z
    piv = bpy.data.objects.new("piv", None)
    sc.collection.objects.link(piv)
    piv.location = (ctr.x, ctr.y, mn.z)
    for r in roots:
        r.parent = piv
        r.matrix_parent_inverse = piv.matrix_world.inverted()

    # ground disc
    bpy.ops.mesh.primitive_circle_add(radius=size * 1.5, fill_type='NGON',
                                      location=(ctr.x, ctr.y, mn.z - 0.01))
    gd = bpy.context.active_object
    gm = bpy.data.materials.new("g")
    gm.use_nodes = True
    gm.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.05, 0.05, 0.08, 1)
    gd.data.materials.append(gm)

    # camera: fixed 3/4, framing the piece; pivot spins under it
    cam = bpy.data.objects.new("C", bpy.data.cameras.new("C"))
    sc.collection.objects.link(cam)
    sc.camera = cam
    d = size * 1.9
    tgt = mathutils.Vector((ctr.x, ctr.y, ctr.z))
    cam.location = (ctr.x + d, ctr.y - d, ctr.z + d * 0.62)
    look = tgt - mathutils.Vector(cam.location)
    cam.rotation_euler = look.to_track_quat('-Z', 'Y').to_euler()
    cam.data.lens = 55

    outdir = os.path.join(OUTROOT, name)
    os.makedirs(outdir, exist_ok=True)
    for f in range(FRAMES):
        piv.rotation_euler.z = 2 * math.pi * f / FRAMES
        sc.render.filepath = os.path.join(outdir, f"frame_{f:03d}.png")
        bpy.ops.render.render(write_still=True)
    print(f"TURNTABLE {name} frames={FRAMES}")

print(f"TURNTABLE ALL DONE pieces={len(names)} frames={FRAMES} res={RES}")
