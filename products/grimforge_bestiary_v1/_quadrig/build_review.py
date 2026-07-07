"""Import the 4 UniRig-rigged quads into one scene, arranged in a row on a ground,
with lights + a framing camera, and save a .blend for interactive inspection.
Each keeps its armature+skin so you can pose/inspect the auto-rig.

    blender -b --python build_review.py -- <quadrig_dir> <out.blend>
"""
import bpy, sys, os
from mathutils import Vector

argv = sys.argv[sys.argv.index("--")+1:]
QDIR, OUTB = argv[0], argv[1]
NAMES = ["hell_hound", "bone_hound", "grave_boar", "dire_rat"]

bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
spacing = 1.4
placed = 0
for i, n in enumerate(NAMES):
    p = os.path.join(QDIR, f"{n}_rigged.glb")
    if not os.path.exists(p):
        print("MISSING", n); continue
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=p)
    new = [o for o in bpy.data.objects if o not in before]
    meshes = [o for o in new if o.type == "MESH"]
    # normalize each to ~1.0 tall-ish for a consistent row, base on ground, offset X
    mn = Vector((1e9,)*3); mx = -mn
    for m in meshes:
        for c in m.bound_box:
            w = m.matrix_world @ Vector(c)
            for k in range(3): mn[k] = min(mn[k], w[k]); mx[k] = max(mx[k], w[k])
    size = mx - mn; longest = max(size) or 1.0
    s = 1.0 / longest
    roots = [o for o in new if o.parent is None]
    for r in roots:
        r.scale = (r.scale[0]*s, r.scale[1]*s, r.scale[2]*s)
    bpy.context.view_layer.update()
    # recompute after scale, drop to floor + offset
    mn = Vector((1e9,)*3); mx = -mn
    for m in meshes:
        for c in m.bound_box:
            w = m.matrix_world @ Vector(c)
            for k in range(3): mn[k] = min(mn[k], w[k]); mx[k] = max(mx[k], w[k])
    ctr = (mn+mx)/2
    for r in roots:
        r.location.x += (i*spacing) - ctr.x
        r.location.y += -ctr.y
        r.location.z += -mn.z
    # rename armature for clarity
    for o in new:
        if o.type == "ARMATURE": o.name = f"{n}_rig"; o.show_in_front = True
    placed += 1

# ground
bpy.ops.mesh.primitive_plane_add(size=max(placed*spacing+3, 6))
gm = bpy.data.materials.new("ground"); gm.use_nodes = True
gm.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.18,0.18,0.2,1)
bpy.context.active_object.data.materials.append(gm)
# lights
sun = bpy.data.lights.new("sun","SUN"); so = bpy.data.objects.new("sun",sun); sc.collection.objects.link(so)
so.rotation_euler = (0.9, 0, 0.6); sun.energy = 3.5
# camera framing the row
cam = bpy.data.cameras.new("cam"); co = bpy.data.objects.new("cam",cam); sc.collection.objects.link(co)
midx = (placed-1)*spacing/2
co.location = (midx, -placed*1.6-2, 1.6); co.rotation_euler = (1.15, 0, 0)
sc.camera = co
# view settings
sc.render.engine = "BLENDER_EEVEE"
bpy.ops.wm.save_as_mainfile(filepath=OUTB)
print("REVIEW_BLEND_SAVED", OUTB, "placed", placed)
