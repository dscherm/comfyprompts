"""Per-piece turntable renders for the Soapbox Kart Kit gallery. Renders every kit
GLB (models_glb/) AND every Hunyuan3D mascot (mascots/*-raw.glb) on a 360° turntable
in a bright cartoon studio. Frames -> scratchpad; bloom + GIF assembly separate.
    blender --background --python turntable_render.py -- [frames] [res] [only_csv]
"""
import bpy, sys, math, mathutils, os

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
FRAMES = int(argv[0]) if len(argv) > 0 else 20
RES = int(argv[1]) if len(argv) > 1 else 512
ONLY = set(argv[2].split(",")) if len(argv) > 2 and argv[2] else None

ROOT = r"D:/Projects/comfyui-toolchain/products/soapbox_kart_kit_v1"
KIT = f"{ROOT}/models_glb"
MASC = f"{ROOT}/mascots"
OUTROOT = r"C:/Users/scher/AppData/Local/Temp/claude/D--Projects-comfyui-toolchain/0e5e1c40-e596-49a6-a43d-bfbe573d38ce/scratchpad/kart_turntable"
os.makedirs(OUTROOT, exist_ok=True)

# (display_name, glb_path)
kit_items = [(f[:-4], f"{KIT}/{f}") for f in sorted(os.listdir(KIT)) if f.endswith(".glb")]
# prefer cleaned mascots (<name>.glb) over raw (<name>-raw.glb) when present
masc_items = []
if os.path.isdir(MASC):
    globs = [f for f in sorted(os.listdir(MASC))
             if f.endswith(".glb") and ".orig." not in f]   # ignore _orig backups
    clean = {f[:-4] for f in globs if not f.endswith("-raw.glb")}
    for f in globs:
        if not f.endswith("-raw.glb"):
            masc_items.append(("mascot_" + f[:-4], f"{MASC}/{f}"))
        elif f[:-8] not in clean:
            masc_items.append(("mascot_" + f[:-8], f"{MASC}/{f}"))
items = kit_items + masc_items
if ONLY == {"kit"}:
    items = kit_items
elif ONLY == {"mascots"}:
    items = masc_items
elif ONLY:
    items = [(n, p) for n, p in items if n in ONLY]


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
    L.data.angle = math.radians(10)
    L.data.color = c
    L.data.use_shadow = sh
    L.rotation_euler = tuple(math.radians(a) for a in rot)


def studio(sc):
    sc.world = bpy.data.worlds.new("W")
    sc.world.use_nodes = True
    bg = sc.world.node_tree.nodes["Background"]
    bg.inputs[0].default_value = (0.16, 0.17, 0.20, 1.0)
    bg.inputs[1].default_value = 0.7
    sc.view_settings.view_transform = 'Standard'
    sun(sc, 3.0, (55, 12, 25), (1.0, 0.96, 0.9))
    sun(sc, 1.7, (60, 0, 210), (0.7, 0.82, 0.95), False)
    sun(sc, 1.2, (50, 0, 130), (1.0, 0.85, 0.7), False)


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

for name, path in items:
    clear()
    studio(sc)
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=path)
    roots = [o for o in bpy.data.objects if o not in before and not o.parent]

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

    piv = bpy.data.objects.new("piv", None)
    sc.collection.objects.link(piv)
    piv.location = (ctr.x, ctr.y, mn.z)
    for r in roots:
        r.parent = piv
        r.matrix_parent_inverse = piv.matrix_world.inverted()

    bpy.ops.mesh.primitive_circle_add(radius=size * 1.5, fill_type='NGON', location=(ctr.x, ctr.y, mn.z - 0.01))
    gd = bpy.context.active_object
    gm = bpy.data.materials.new("g")
    gm.use_nodes = True
    gm.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.12, 0.13, 0.15, 1)
    gd.data.materials.append(gm)

    cam = bpy.data.objects.new("C", bpy.data.cameras.new("C"))
    sc.collection.objects.link(cam)
    sc.camera = cam
    d = size * 1.9
    tgt = mathutils.Vector((ctr.x, ctr.y, ctr.z))
    cam.location = (ctr.x + d, ctr.y - d, ctr.z + d * 0.6)
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

print(f"TURNTABLE ALL DONE items={len(items)} frames={FRAMES} res={RES}")
