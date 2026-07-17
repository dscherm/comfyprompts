"""Render the melt diagnostic prescribed by lessons/unirig-skin-weights-melt-use-accurig.md:

    "Diagnose deformation by rendering mid-motion frames from front AND side at
     bent joints — static poses hide weight problems."

Renders an animated GLB at chosen frames from FRONT and SIDE, full-body plus a
knee-region crop, so weight melt (joint collapse, candy-wrapper limbs, stretched
points) is visible if present.

Usage:
    blender --background --factory-startup --python render_melt_diagnostic.py \\
        -- <animated.glb> <out_dir> <frame,frame,...>
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector

argv = sys.argv[sys.argv.index("--") + 1 :]
SRC, OUT = argv[0], Path(argv[1])
FRAMES = [int(f) for f in argv[2].split(",")]
OUT.mkdir(parents=True, exist_ok=True)

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=SRC)

arm = next(o for o in bpy.data.objects if o.type == "ARMATURE")
meshes = [o for o in bpy.data.objects
          if o.type == "MESH"
          and any(m.type == "ARMATURE" and m.object == arm for m in o.modifiers)]
for o in bpy.data.objects:
    if o.type == "MESH" and o not in meshes:
        o.hide_render = True
    if o.type == "ARMATURE":
        o.hide_render = True
for mesh in meshes:
    if mesh.animation_data:
        mesh.animation_data_clear()
    if mesh.data.shape_keys and mesh.data.shape_keys.animation_data:
        mesh.data.shape_keys.animation_data_clear()

# GLB NLA strips import as tracks; push the first one onto the active action
if arm.animation_data and arm.animation_data.nla_tracks:
    strip = arm.animation_data.nla_tracks[0].strips[0]
    arm.animation_data.action = strip.action
    print("ACTION", strip.action.name)

scene = bpy.context.scene
scene.render.engine = "BLENDER_EEVEE"
scene.render.resolution_x = 900
scene.render.resolution_y = 900

world = bpy.data.worlds.new("w")
world.use_nodes = True
bg = world.node_tree.nodes.get("Background")
if bg:
    bg.inputs["Color"].default_value = (0.82, 0.83, 0.86, 1.0)
scene.world = world
key = bpy.data.lights.new("k", type="SUN")
key.energy = 3.0
ko = bpy.data.objects.new("k", key)
ko.rotation_euler = (math.radians(55), 0, math.radians(30))
scene.collection.objects.link(ko)
fill = bpy.data.lights.new("f", type="SUN")
fill.energy = 1.0
fo = bpy.data.objects.new("f", fill)
fo.rotation_euler = (math.radians(-40), 0, math.radians(-140))
scene.collection.objects.link(fo)

cam_data = bpy.data.cameras.new("c")
cam_data.type = "ORTHO"
cam = bpy.data.objects.new("c", cam_data)
scene.collection.objects.link(cam)
scene.camera = cam


def bounds():
    dg = bpy.context.evaluated_depsgraph_get()
    mins = Vector((1e18,) * 3)
    maxs = Vector((-1e18,) * 3)
    for mesh in meshes:
        eo = mesh.evaluated_get(dg)
        em = eo.to_mesh()
        for v in em.vertices:
            w = mesh.matrix_world @ v.co
            for i in range(3):
                mins[i] = min(mins[i], w[i])
                maxs[i] = max(maxs[i], w[i])
        eo.to_mesh_clear()
    return mins, maxs


def aim(focus, view, az_deg, el_deg):
    cam.data.ortho_scale = view
    az, el = math.radians(az_deg), math.radians(el_deg)
    dist = view * 4
    cam.location = (focus.x + dist * math.cos(el) * math.sin(az),
                    focus.y - dist * math.cos(el) * math.cos(az),
                    focus.z + dist * math.sin(el))
    cam.rotation_euler = (focus - cam.location).to_track_quat("-Z", "Y").to_euler()


# character faces -Y: front = look from -Y (az 0); side = look from +X (az 90)
VIEWS = [("front", 0.0, 6.0), ("side", 90.0, 6.0)]

for f in FRAMES:
    scene.frame_set(f)
    bpy.context.view_layer.update()
    mins, maxs = bounds()
    size = max(maxs - mins)
    body = (mins + maxs) / 2
    # knee region: lower third, where the melt lesson says to look
    knees = Vector((body.x, body.y, mins.z + (maxs.z - mins.z) * 0.30))
    for name, az, el in VIEWS:
        aim(body, size * 1.15, az, el)
        scene.render.filepath = str(OUT / f"f{f:02d}_{name}_body.png")
        bpy.ops.render.render(write_still=True)
        aim(knees, size * 0.45, az, el)
        scene.render.filepath = str(OUT / f"f{f:02d}_{name}_knees.png")
        bpy.ops.render.render(write_still=True)
        print("RENDERED", f, name)
print("DONE")
