"""Clean Hunyuan3D mascot meshes: remove the floating ground-disc/shadow artifact
(a flat slab below the model, separated by a vertical gap), then recenter so the
model sits at origin with its base on z=0. Preserves textures/UVs. Overwrites the
textured GLB in place (keeps a .orig backup once).
    blender --background --python mascot_cleanup.py -- [name_csv]
"""
import bpy, sys, math, mathutils, os, shutil

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
NAMES = argv[0].split(",") if argv and argv[0] else ["robot", "frog", "wizard", "shark", "skeleton"]
MASC = r"D:/Projects/comfyui-toolchain/products/soapbox_kart_kit_v1/mascots"


def clean_one(name):
    src = f"{MASC}/{name}.glb"
    if not os.path.exists(src):
        print("SKIP (no textured glb)", name)
        return
    os.makedirs(f"{MASC}/_orig", exist_ok=True)
    backup = f"{MASC}/_orig/{name}.orig.glb"
    if not os.path.exists(backup):
        shutil.copy2(src, backup)

    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=src)
    meshes = [o for o in bpy.data.objects if o.type == 'MESH']
    if not meshes:
        print("SKIP (no mesh)", name)
        return
    bpy.ops.object.select_all(action='SELECT')
    bpy.context.view_layer.objects.active = meshes[0]
    if len(meshes) > 1:
        bpy.ops.object.join()
    obj = bpy.context.active_object

    mw = obj.matrix_world
    zs = sorted((mw @ v.co).z for v in obj.data.vertices)
    n = len(zs)
    zmin, zmax = zs[0], zs[-1]
    H = zmax - zmin or 1.0
    nb = 120
    bins = [0] * nb
    for z in zs:
        bins[min(nb - 1, int((z - zmin) / H * nb))] += 1

    # scan upward: first empty band with a disc below (>2% verts) and the mascot
    # above (>50% verts) => cut there and drop the disc.
    cut = None
    below = 0
    for i in range(nb):
        below += bins[i]
        if bins[i] == 0 and below > 0.02 * n and (n - below) > 0.5 * n:
            cut = zmin + (i + 0.5) / nb * H
            break

    if cut is not None:
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_all(action='DESELECT')
        bpy.ops.object.mode_set(mode='OBJECT')
        for v in obj.data.vertices:
            if (mw @ v.co).z < cut:
                v.select = True
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.delete(type='VERT')
        bpy.ops.object.mode_set(mode='OBJECT')
        print(f"  {name}: cut disc below z={cut:.2f} (dropped bottom slab)")
    else:
        print(f"  {name}: no clear disc gap found — left as-is")

    # recenter: base to z=0, xy centered on the mesh bounds
    bpy.context.view_layer.update()
    cs = [obj.matrix_world @ mathutils.Vector(c) for c in obj.bound_box]
    xmin = min(p.x for p in cs); xmax = max(p.x for p in cs)
    ymin = min(p.y for p in cs); ymax = max(p.y for p in cs)
    zmn = min(p.z for p in cs)
    obj.location.x -= (xmin + xmax) / 2
    obj.location.y -= (ymin + ymax) / 2
    obj.location.z -= zmn
    bpy.context.view_layer.update()

    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.export_scene.gltf(filepath=src, use_selection=True, export_format='GLB')
    print(f"  {name}: recentered + re-exported -> {src}")


for nm in NAMES:
    clean_one(nm)
print("MASCOT CLEANUP DONE")
