"""Headless Blender: render an animated GLB's clip as a PNG frame sequence.

Renders the action once through at 24fps, camera framed like protocol C1.
Assemble with:  ffmpeg -framerate 24 -i <out_dir>/f%04d.png -c:v libx264 \\
                -pix_fmt yuv420p -crf 24 out.mp4

Usage:
    blender --background --factory-startup --python blender_render_clip_video.py \\
        -- <animated.glb> <action_substring> <out_frames_dir> [max_seconds]
"""
import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector

argv = sys.argv[sys.argv.index("--") + 1 :]
src, substring, out_path = argv[0], argv[1], argv[2]
max_seconds = float(argv[3]) if len(argv) > 3 else 5.0

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=src)

arm = next(o for o in bpy.data.objects if o.type == "ARMATURE")
meshes = [
    o for o in bpy.data.objects
    if o.type == "MESH"
    and any(m.type == "ARMATURE" and m.object == arm for m in o.modifiers)
]
for o in bpy.data.objects:
    if o.type == "MESH" and o not in meshes:
        o.hide_render = True
    if o.type == "ARMATURE":
        o.hide_render = True

action = next(a for a in bpy.data.actions if substring.lower() in a.name.lower())
if arm.animation_data is None:
    arm.animation_data_create()
arm.animation_data.action = action

scene = bpy.context.scene
scene.render.engine = "BLENDER_EEVEE"
scene.render.resolution_x = 640
scene.render.resolution_y = 640
scene.render.fps = 24
start, end = int(action.frame_range[0]), int(action.frame_range[1])
end = min(end, start + int(max_seconds * scene.render.fps))
scene.frame_start, scene.frame_end = start, end

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

# frame on the mid-animation bounds, padded so the gait never exits frame
scene.frame_set((start + end) // 2)
depsgraph = bpy.context.evaluated_depsgraph_get()
mins = Vector((1e18,) * 3)
maxs = Vector((-1e18,) * 3)
for mesh in meshes:
    eo = mesh.evaluated_get(depsgraph)
    em = eo.to_mesh()
    for v in em.vertices:
        w = mesh.matrix_world @ v.co
        for i in range(3):
            mins[i] = min(mins[i], w[i])
            maxs[i] = max(maxs[i], w[i])
    eo.to_mesh_clear()
size = max(maxs - mins)
focus = (mins + maxs) / 2

cam_data = bpy.data.cameras.new("c")
cam_data.type = "ORTHO"
cam_data.ortho_scale = size * 1.5
cam = bpy.data.objects.new("c", cam_data)
scene.collection.objects.link(cam)
scene.camera = cam
az, el = math.radians(35), math.radians(12)
dist = size * 4
cam.location = (
    focus.x + dist * math.cos(el) * math.sin(az),
    focus.y - dist * math.cos(el) * math.cos(az),
    focus.z + dist * math.sin(el),
)
cam.rotation_euler = (focus - cam.location).to_track_quat("-Z", "Y").to_euler()

# This Blender build has no FFmpeg encoder compiled in — render PNG frames;
# the caller assembles the MP4 with system ffmpeg.
frames_dir = Path(out_path)
frames_dir.mkdir(parents=True, exist_ok=True)
scene.render.image_settings.file_format = "PNG"
scene.render.filepath = str(frames_dir / "f")
bpy.ops.render.render(animation=True)
print("FRAMES", frames_dir, f"range {start}-{end}")
