"""render_anim_poses — render one representative frame per animation clip.

Drives blender-mcp (live Blender, EEVEE on the display GPU — NOT the 3090 Ti) to
import a multi-clip GLB and render a mid-action pose for each requested clip, so
the clips can be eyeballed for correct deformation (no scramble/melt).

Usage:
  python render_anim_poses.py <glb> <out_dir> clip:frac clip:frac ...
  e.g. python render_anim_poses.py berserkr_anims.glb poses sword_slash_r:0.5 death:0.85
"""
from __future__ import annotations
import json, os, socket, sys
from pathlib import Path

HOST = os.environ.get("BLENDER_HOST", "localhost")
PORT = int(os.environ.get("BLENDER_PORT", "9876"))


def rpc(cmd: dict, timeout: float = 300.0) -> dict:
    with socket.create_connection((HOST, PORT), timeout=timeout) as s:
        s.settimeout(timeout)
        s.sendall(json.dumps(cmd).encode())
        buf = b""
        while True:
            chunk = s.recv(8192)
            if not chunk:
                break
            buf += chunk
            try:
                return json.loads(buf.decode())
            except json.JSONDecodeError:
                continue
    raise RuntimeError("blender-mcp closed early")


BODY = r'''
import bpy, json, math, os
from mathutils import Vector
CFG = json.loads(__CFG__)

for o in list(bpy.data.objects):
    bpy.data.objects.remove(o, do_unlink=True)
for coll in (bpy.data.meshes, bpy.data.materials, bpy.data.images, bpy.data.actions):
    for b in list(coll):
        if getattr(b, "users", 0) == 0:
            coll.remove(b)

bpy.ops.import_scene.gltf(filepath=CFG["glb"])
arm = next(o for o in bpy.data.objects if o.type == "ARMATURE")
meshes = [o for o in bpy.data.objects if o.type == "MESH"]
actions = {a.name: a for a in bpy.data.actions}

# even world + lights + a front-3/4 elevated camera framing the rest bbox
scene = bpy.context.scene
scene.render.engine = "BLENDER_EEVEE"
world = bpy.data.worlds.get("World") or bpy.data.worlds.new("World")
scene.world = world; world.use_nodes = True
bg = world.node_tree.nodes.get("Background")
if bg: bg.inputs[0].default_value = (0.82, 0.82, 0.82, 1.0)
for d, e in [((1,-1,1),4.0), ((-1,-1,0.5),2.5), ((0,1,1),2.0)]:
    ld = bpy.data.lights.new("k", type="SUN"); ld.energy = e
    lo = bpy.data.objects.new("k", ld); bpy.context.collection.objects.link(lo)
    lo.rotation_euler = (-Vector(d)).to_track_quat("Z","Y").to_euler()

def bbox():
    mn = Vector((1e18,)*3); mx = Vector((-1e18,)*3)
    for o in meshes:
        for c in o.bound_box:
            w = o.matrix_world @ Vector(c)
            for i in range(3):
                mn[i] = min(mn[i], w[i]); mx[i] = max(mx[i], w[i])
    return mn, mx
mn, mx = bbox()
center = (mn+mx)*0.5
maxd = max((mx-mn).x, (mx-mn).y, (mx-mn).z) or 1.0
cam_data = bpy.data.cameras.new("c"); cam_data.type = "ORTHO"
cam_data.ortho_scale = maxd*1.7; cam_data.clip_end = maxd*20
cam = bpy.data.objects.new("c", cam_data); bpy.context.collection.objects.link(cam)
scene.camera = cam
az, el = math.radians(35), math.radians(12); r = maxd*3
off = Vector((r*math.cos(el)*math.sin(az), -r*math.cos(el)*math.cos(az), r*math.sin(el)))
cam.location = center + off
cam.rotation_euler = (-off).to_track_quat("-Z","Y").to_euler()

scene.render.resolution_x = CFG["res"]; scene.render.resolution_y = CFG["res"]
scene.render.image_settings.file_format = "PNG"
os.makedirs(CFG["out_dir"], exist_ok=True)
if not arm.animation_data:
    arm.animation_data_create()
rendered = []
for clip, frac in CFG["clips"]:
    act = actions.get(clip)
    if not act:
        continue
    arm.animation_data.action = act
    fs, fe = act.frame_range
    scene.frame_set(int(fs + frac*(fe-fs)))
    p = os.path.join(CFG["out_dir"], clip + ".png")
    scene.render.filepath = p
    bpy.ops.render.render(write_still=True)
    rendered.append(clip)
print("POSES " + json.dumps(rendered))
'''


def main():
    glb = str(Path(sys.argv[1]).resolve())
    out_dir = str(Path(sys.argv[2]).resolve())
    clips = []
    for spec in sys.argv[3:]:
        name, _, frac = spec.partition(":")
        clips.append([name, float(frac) if frac else 0.5])
    cfg = {"glb": glb.replace("\\", "/"), "out_dir": out_dir.replace("\\", "/"),
           "clips": clips, "res": 640}
    code = BODY.replace("__CFG__", json.dumps(json.dumps(cfg)))
    resp = rpc({"type": "execute_code", "params": {"code": code}})
    out = (resp.get("result") or {}).get("result", "") if resp.get("status") == "success" else resp
    print(out)


if __name__ == "__main__":
    main()
