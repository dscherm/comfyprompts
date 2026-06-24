"""render_multiview — Blender orthographic multi-view renderer (blender-mcp).

Dataset-gen stage for the multiview-consistency LoRA (see `.ralph/spec.md`).
Renders clean, orthographic, Hunyuan3D-friendly views of 3D meshes we already
own, to build a training set for the `mv_ortho` LoRA. Output of this stage feeds
caption.py -> launch_train.py, exactly like any other train_lora dataset.

It drives **blender-mcp** (the project's primary Blender interface) over its
socket on localhost:9876 — the same `execute_code` protocol the MCP server uses.
Per mesh it ships one parameterized Blender Python program that: wipes the scene,
imports the mesh, recenters it, sets a neutral world + even lighting and an
ORTHOGRAPHIC camera, then renders each requested angle to
`<out>/<mesh>__<view>.png`. The view is encoded in the filename so caption.py
can derive a per-view tag downstream.

Headless `blender --background` is the documented *fallback*; this script targets
the live blender-mcp socket first (CLAUDE.md: "always try blender-mcp first").

Stdlib only. Dataset-agnostic: nothing mesh-specific is hardcoded.

Usage:
    # Blender must be open with the blender-mcp addon serving on port 9876.
    python scripts/train_lora/render_multiview.py \\
        --src "D:/Projects/ComfyUI/output/3D" \\
        --out "E:/ai-training/datasets/mv_ortho" \\
        --angles front,back,left,right,front_left,front_right
"""

from __future__ import annotations

import argparse
import json
import os
import socket
import sys
from pathlib import Path

BLENDER_HOST = os.environ.get("BLENDER_HOST", "localhost")
BLENDER_PORT = int(os.environ.get("BLENDER_PORT", "9876"))

MESH_EXTS = (".glb", ".gltf", ".obj", ".fbx", ".ply", ".stl")

# name -> (azimuth_deg, elevation_deg). Azimuth 0 = camera in front of the
# subject (-Y), increasing toward the subject's right (+X). Elevation is degrees
# above the horizon. Front view is the primary target for single-image Hunyuan3D;
# the others add silhouette/volume coverage.
ANGLES: dict[str, tuple[float, float]] = {
    "front": (0.0, 0.0),
    "back": (180.0, 0.0),
    "left": (-90.0, 0.0),
    "right": (90.0, 0.0),
    "front_left": (-40.0, 10.0),
    "front_right": (40.0, 10.0),
}


def _rpc(command: dict, timeout: float = 300.0) -> dict:
    """Send one command to the blender-mcp socket and return the parsed response.

    The addon frames neither requests nor responses with a length prefix: it
    accumulates bytes until the JSON parses. We mirror that — send the whole
    command, then recv until the response JSON is complete (or timeout).
    A fresh connection per command keeps each call self-contained.
    """
    with socket.create_connection((BLENDER_HOST, BLENDER_PORT), timeout=timeout) as sock:
        sock.settimeout(timeout)
        sock.sendall(json.dumps(command).encode("utf-8"))
        buf = b""
        while True:
            try:
                chunk = sock.recv(8192)
            except socket.timeout:
                raise RuntimeError(f"blender-mcp timed out after {timeout}s")
            if not chunk:
                break
            buf += chunk
            try:
                return json.loads(buf.decode("utf-8"))
            except json.JSONDecodeError:
                continue  # partial response, keep reading
    raise RuntimeError("blender-mcp closed the connection before a full response")


def preflight() -> None:
    """Confirm blender-mcp is reachable before touching any files."""
    try:
        resp = _rpc({"type": "get_scene_info"}, timeout=15.0)
    except (OSError, RuntimeError) as e:
        raise SystemExit(
            f"blender-mcp is not reachable at {BLENDER_HOST}:{BLENDER_PORT} ({e}). "
            f"Open Blender and start the MCP addon (socket server on 9876), then "
            f"retry. Nothing was written."
        )
    if resp.get("status") != "success":
        raise SystemExit(f"blender-mcp preflight failed: {resp.get('message', resp)}")


def _blender_code(mesh_path: str, out_dir: str, angles: list[str], res: int,
                  margin: float, transparent: bool) -> str:
    """Build the Blender Python program rendered for one mesh.

    Runs inside Blender via execute_code; prints a one-line JSON summary that
    run_mesh() parses out of captured stdout.
    """
    angle_map = {a: ANGLES[a] for a in angles}
    cfg = {
        "mesh_path": mesh_path,
        "out_dir": out_dir,
        "angles": angle_map,
        "res": res,
        "margin": margin,
        "transparent": transparent,
    }
    # The config is injected as a literal dict so the Blender side needs no args.
    return "import bpy, json, math, os\n" \
           "from mathutils import Vector\n" \
           f"CFG = json.loads({json.dumps(json.dumps(cfg))})\n" + _BLENDER_BODY


# Blender-side body. Kept as a module constant (not an f-string) so braces and
# bpy calls stay readable; it reads its inputs from the CFG dict prepended above.
_BLENDER_BODY = r'''
def _wipe():
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for block in (bpy.data.meshes, bpy.data.materials, bpy.data.images):
        for b in list(block):
            if b.users == 0:
                block.remove(b)

def _import(path):
    ext = os.path.splitext(path)[1].lower()
    if ext in (".glb", ".gltf"):
        bpy.ops.import_scene.gltf(filepath=path)
    elif ext == ".fbx":
        bpy.ops.import_scene.fbx(filepath=path)
    elif ext == ".obj":
        bpy.ops.wm.obj_import(filepath=path)
    elif ext == ".ply":
        bpy.ops.wm.ply_import(filepath=path)
    elif ext == ".stl":
        bpy.ops.wm.stl_import(filepath=path)
    else:
        raise RuntimeError("unsupported mesh extension: " + ext)

def _mesh_objects():
    return [o for o in bpy.context.scene.objects if o.type == "MESH"]

def _combined_bbox(objs):
    mins = Vector((1e18, 1e18, 1e18))
    maxs = Vector((-1e18, -1e18, -1e18))
    for o in objs:
        for corner in o.bound_box:
            wc = o.matrix_world @ Vector(corner)
            for i in range(3):
                mins[i] = min(mins[i], wc[i])
                maxs[i] = max(maxs[i], wc[i])
    return mins, maxs

def _setup_world(transparent):
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE"  # EEVEE-Next under the legacy enum id (4.2+/5.0)
    world = bpy.data.worlds.get("World") or bpy.data.worlds.new("World")
    scene.world = world
    world.use_nodes = True
    bg = world.node_tree.nodes.get("Background")
    if bg:
        bg.inputs[0].default_value = (0.8, 0.8, 0.8, 1.0)  # neutral light grey
        bg.inputs[1].default_value = 1.0
    scene.render.film_transparent = bool(transparent)

def _add_lights(radius):
    # Even, mostly flat key+fill+rim so the silhouette reads cleanly for 3D.
    specs = [((1, -1, 1), 4.0), ((-1, -1, 0.5), 2.5), ((0, 1, 1), 2.0)]
    for i, (d, energy) in enumerate(specs):
        light = bpy.data.lights.new("mvkey%d" % i, type="SUN")
        light.energy = energy
        obj = bpy.data.objects.new("mvkey%d" % i, light)
        bpy.context.collection.objects.link(obj)
        direction = Vector(d)
        obj.rotation_euler = (-direction).to_track_quat("Z", "Y").to_euler()

def _make_camera(max_dim, margin):
    cam_data = bpy.data.cameras.new("mvcam")
    cam_data.type = "ORTHO"
    cam_data.ortho_scale = max_dim * margin
    cam_data.clip_start = 0.001
    cam_data.clip_end = max_dim * 20.0
    cam = bpy.data.objects.new("mvcam", cam_data)
    bpy.context.collection.objects.link(cam)
    bpy.context.scene.camera = cam
    return cam

def _place(cam, az_deg, el_deg, radius, target):
    # Orbit the camera around the subject's world-space bbox center and aim at it.
    # We never move the geometry — armature-parented meshes (FBX) don't recenter
    # correctly by editing object.location, so framing is done purely by the camera.
    az = math.radians(az_deg)
    el = math.radians(el_deg)
    horiz = radius * math.cos(el)
    offset = Vector((horiz * math.sin(az), -horiz * math.cos(az), radius * math.sin(el)))
    cam.location = target + offset
    cam.rotation_euler = (-offset).to_track_quat("-Z", "Y").to_euler()

def run():
    _wipe()
    _import(CFG["mesh_path"])
    objs = _mesh_objects()
    if not objs:
        print("MVRESULT " + json.dumps({"mesh": CFG["mesh_path"], "rendered": [],
              "error": "no mesh objects after import"}))
        return
    mins, maxs = _combined_bbox(objs)
    center = (mins + maxs) * 0.5
    dims = maxs - mins
    max_dim = max(dims.x, dims.y, dims.z) or 1.0
    radius = max_dim * 3.0

    _setup_world(CFG["transparent"])
    _add_lights(radius)
    cam = _make_camera(max_dim, CFG["margin"])

    scene = bpy.context.scene
    scene.render.resolution_x = CFG["res"]
    scene.render.resolution_y = CFG["res"]
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA" if CFG["transparent"] else "RGB"

    os.makedirs(CFG["out_dir"], exist_ok=True)
    stem = os.path.splitext(os.path.basename(CFG["mesh_path"]))[0]
    rendered = []
    for view, (az, el) in CFG["angles"].items():
        _place(cam, az, el, radius, center)
        out_path = os.path.join(CFG["out_dir"], "%s__%s.png" % (stem, view))
        scene.render.filepath = out_path
        bpy.ops.render.render(write_still=True)
        rendered.append(os.path.basename(out_path))
    print("MVRESULT " + json.dumps({"mesh": CFG["mesh_path"], "rendered": rendered}))

run()
'''


def _parse_result(resp: dict) -> dict:
    """Pull the MVRESULT JSON line out of blender-mcp's captured stdout."""
    if resp.get("status") != "success":
        raise RuntimeError(resp.get("message", f"blender error: {resp}"))
    stdout = (resp.get("result") or {}).get("result", "")
    for line in stdout.splitlines():
        if line.startswith("MVRESULT "):
            return json.loads(line[len("MVRESULT "):])
    raise RuntimeError(f"no MVRESULT in Blender output: {stdout[:200]!r}")


def render_mesh(mesh_path: Path, out_dir: Path, angles: list[str], res: int,
                margin: float, transparent: bool) -> dict:
    code = _blender_code(str(mesh_path).replace("\\", "/"), str(out_dir).replace("\\", "/"),
                         angles, res, margin, transparent)
    resp = _rpc({"type": "execute_code", "params": {"code": code}})
    return _parse_result(resp)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Blender orthographic multi-view renderer (blender-mcp).")
    ap.add_argument("--src", required=True, help="Mesh dir (recursed) or a single mesh file.")
    ap.add_argument("--out", required=True, help="Output dir for rendered views.")
    ap.add_argument("--angles", default="front,back,left,right,front_left,front_right",
                    help="Comma list of view names: " + ",".join(ANGLES))
    ap.add_argument("--res", type=int, default=768, help="Square render resolution.")
    ap.add_argument("--margin", type=float, default=1.15,
                    help="Ortho framing margin (1.0 = tight bbox).")
    ap.add_argument("--transparent", action="store_true",
                    help="Transparent background (RGBA) instead of neutral grey.")
    ap.add_argument("--include", default="",
                    help="Comma substrings; keep only mesh paths matching any (case-insensitive).")
    ap.add_argument("--exclude", default="",
                    help="Comma substrings; drop mesh paths matching any (case-insensitive).")
    ap.add_argument("--limit", type=int, default=0, help="Only the first N meshes (trial).")
    args = ap.parse_args(argv)

    angles = [a.strip() for a in args.angles.split(",") if a.strip()]
    bad = [a for a in angles if a not in ANGLES]
    if bad:
        raise SystemExit(f"unknown angle(s): {bad}. Choose from: {', '.join(ANGLES)}")

    src = Path(args.src)
    if src.is_file():
        meshes = [src]
    elif src.is_dir():
        meshes = sorted(p for p in src.rglob("*") if p.suffix.lower() in MESH_EXTS)
    else:
        raise SystemExit(f"--src not found: {src}")
    inc = [s.strip().lower() for s in args.include.split(",") if s.strip()]
    exc = [s.strip().lower() for s in args.exclude.split(",") if s.strip()]
    if inc:
        meshes = [m for m in meshes if any(s in str(m).lower() for s in inc)]
    if exc:
        meshes = [m for m in meshes if not any(s in str(m).lower() for s in exc)]
    if args.limit:
        meshes = meshes[: args.limit]
    if not meshes:
        raise SystemExit(f"no meshes ({', '.join(MESH_EXTS)}) under {src} after include/exclude")

    out_dir = Path(args.out)
    preflight()
    print(f"rendering {len(meshes)} mesh(es) x {len(angles)} view(s) -> {out_dir}", flush=True)

    stats = {"meshes": len(meshes), "rendered": 0, "failed": 0}
    for i, mesh in enumerate(meshes, 1):
        try:
            result = render_mesh(mesh, out_dir, angles, args.res, args.margin, args.transparent)
            if result.get("error"):
                stats["failed"] += 1
                print(f"  ! [{i}/{len(meshes)}] {mesh.name}: {result['error']}", file=sys.stderr)
                continue
            n = len(result.get("rendered", []))
            stats["rendered"] += n
            print(f"  + [{i}/{len(meshes)}] {mesh.name}: {n} view(s)", flush=True)
        except (OSError, RuntimeError) as e:
            stats["failed"] += 1
            print(f"  ! [{i}/{len(meshes)}] {mesh.name}: {e}", file=sys.stderr)

    print(json.dumps(stats, indent=2))
    return 1 if stats["rendered"] == 0 else 0


if __name__ == "__main__":
    sys.exit(main())
