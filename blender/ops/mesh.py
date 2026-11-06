"""Mesh ops: wrap the low-poly kit scripts in tools/asset_generators/lowpoly/."""

import json
import struct
from pathlib import Path

import bpy

from . import REPO_ROOT, default_out, register, require_file, run_script

LOWPOLY = REPO_ROOT / "tools" / "asset_generators" / "lowpoly"


def glb_tris(path: str) -> int:
    """Triangle count of a GLB, read from its JSON chunk (no Blender import)."""
    data = Path(path).read_bytes()
    if data[:4] != b"glTF":
        raise ValueError(f"not a GLB: {path}")
    (jlen,) = struct.unpack_from("<I", data, 12)
    doc = json.loads(data[20:20 + jlen])
    acc = doc.get("accessors", [])
    tris = 0
    for mesh in doc.get("meshes", []):
        for prim in mesh.get("primitives", []):
            if prim.get("mode", 4) != 4:
                continue
            idx = prim.get("indices")
            src = idx if idx is not None else prim["attributes"]["POSITION"]
            count = acc[src]["count"]
            tris += count // 3
    return tris


@register("decimate_to")
def decimate_to(path=None, tris=None, out=None):
    """decimate_lowpoly.py to a triangle budget. The script stops within 5% above
    its target, so the budget is enforced here: re-run with a lower target until
    the exported GLB is at or under `tris`."""
    src = require_file(path)
    if tris is None or int(tris) <= 0:
        raise ValueError("decimate_to needs a positive 'tris'")
    budget = int(tris)
    dst = out or default_out(src, "decimate_to")
    script = LOWPOLY / "decimate_lowpoly.py"
    logs, target, got = [], budget, -1
    for attempt in range(4):
        logs.append(run_script(script, [src, dst, target]))
        got = glb_tris(dst)
        logs.append(f"decimate_to: attempt {attempt + 1} target={target} "
                    f"-> {got} tris (budget {budget})")
        if got <= budget:
            return dst, "\n".join(logs)
        target = max(4, int(target * budget / got * 0.97))
    raise RuntimeError(f"could not reach {budget} tris (last {got})\n" + "\n".join(logs))


@register("bake_uv")
def bake_uv(path=None, textured=None, out=None, px=1024):
    """bake_lowpoly.py: smart-UV the low-poly and bake the textured source's colour."""
    low = require_file(path)
    tex = require_file(textured, "textured")
    dst = out or default_out(low, "bake_uv")
    log = run_script(LOWPOLY / "bake_lowpoly.py", [low, tex, dst, int(px)])
    if not Path(dst).is_file():
        raise RuntimeError(f"bake_lowpoly.py wrote no file at {dst}\n{log}")
    return dst, log


_IMPORTERS = {
    ".glb": lambda p: bpy.ops.import_scene.gltf(filepath=p),
    ".gltf": lambda p: bpy.ops.import_scene.gltf(filepath=p),
    ".fbx": lambda p: bpy.ops.import_scene.fbx(filepath=p),
    ".obj": lambda p: bpy.ops.wm.obj_import(filepath=p),
}


@register("export_glb")
def export_glb(path=None, out=None):
    """Load a GLB/glTF/FBX/OBJ (into an empty scene) or open a .blend, and export
    the whole scene, animations included, as one GLB."""
    src = require_file(path)
    if not out:
        raise ValueError("export_glb needs 'out'")
    ext = Path(src).suffix.lower()
    if ext == ".blend":
        bpy.ops.wm.open_mainfile(filepath=src)
    elif ext in _IMPORTERS:
        bpy.ops.wm.read_factory_settings(use_empty=True)
        _IMPORTERS[ext](src)
    else:
        raise ValueError(f"export_glb cannot read '{ext}' "
                         f"(supported: .blend, {', '.join(_IMPORTERS)})")
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.export_scene.gltf(filepath=str(out), export_format="GLB", export_animations=True)
    n = len([o for o in bpy.context.scene.objects if o.type == "MESH"])
    return str(out), f"export_glb: {src} -> {out} ({n} mesh object(s), {glb_tris(str(out))} tris)"
