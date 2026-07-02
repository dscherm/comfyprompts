"""kit_pipeline — turn a GrimForge *spec* module into kit assets + a catalog.

A spec is any Python module that defines::

    PIECES: list[tuple[str, callable]]   # (name, fn(kit) -> joined object)

and may optionally define ``PALETTE_OVERRIDE`` / ``EMISSION_OVERRIDE`` dicts
and a ``TITLE`` string. Builders receive a :class:`kitlib.Kit` and call its
primitive methods (``k.box`` / ``k.cyl`` / ...), so the GrimForge style is
enforced by construction.

This is the "build + export + catalog" stage of the village-kit pipeline.
Run headless::

    blender -b --python kit_pipeline.py -- <spec.py> <out_dir>

Outputs ``<out_dir>/glb/<name>.glb`` for every piece and ``<out_dir>/
catalog.png``. The Godot import-verify stage is separate (see the
examples/godot_village builders).
"""

import importlib.util
import json
import math
import os
import sys

import bpy
import mathutils

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from kitlib import EMISSION, PALETTE, Kit, hex_to_rgba  # noqa: E402

# KayKit tri-count band (QUALITY_RUBRIC.md §1) — reported per piece; the gate
# (kit_quality_check.py) reads the tris.json this writes and flags out-of-band.
TRI_LO, TRI_HI = 20, 5659

# Named aesthetic profiles — the catalog-render half of the GrimForge "look".
# A spec selects one via ``AESTHETIC = "occult"`` (default "medieval"). The
# Godot import-verify stage carries matching lighting in godot_verify/build.gd.
PROFILES: dict[str, dict] = {
    "medieval": {
        "sun_energy": 3.0, "sun_color": "fff4e0",
        "fill_energy": 1.1, "fill_color": "cfe0ff",
        "world_color": "8a96a2", "world_strength": 0.55,
        "ground": "dirt",
    },
    "occult": {
        "sun_energy": 2.3, "sun_color": "ffd2a0",   # warm key
        "fill_energy": 0.5, "fill_color": "5a7ad8",  # cold fill
        "world_color": "0c1018", "world_strength": 0.22,  # deep dark
        "ground": "stone_dk",
    },
}


def _load_spec(path: str):
    spec = importlib.util.spec_from_file_location("kit_spec", path)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    if not getattr(mod, "PIECES", None):
        raise ValueError(f"{path} defines no PIECES list")
    return mod


def _render_catalog(scene, out_png: str, ortho: float, profile: dict, view: str = "top") -> None:
    sun = bpy.data.objects.new("Sun", bpy.data.lights.new("Sun", "SUN"))
    scene.collection.objects.link(sun)
    sun.data.energy = profile["sun_energy"]
    sun.data.color = hex_to_rgba(profile["sun_color"])[:3]
    sun.data.angle = math.radians(5)
    sun.rotation_euler = (math.radians(52), math.radians(10), math.radians(35))
    fill = bpy.data.objects.new("Fill", bpy.data.lights.new("Fill", "SUN"))
    scene.collection.objects.link(fill)
    fill.data.energy = profile["fill_energy"]
    fill.data.color = hex_to_rgba(profile["fill_color"])[:3]
    fill.data.use_shadow = False
    fill.rotation_euler = (math.radians(62), 0, math.radians(215))
    scene.world = bpy.data.worlds.new("W")
    scene.world.use_nodes = True
    bg = scene.world.node_tree.nodes["Background"]
    bg.inputs[1].default_value = profile["world_strength"]
    bg.inputs[0].default_value = hex_to_rgba(profile["world_color"])
    scene.view_settings.view_transform = "Standard"
    cam = bpy.data.objects.new("Cam", bpy.data.cameras.new("Cam"))
    scene.collection.objects.link(cam)
    scene.camera = cam
    cam.data.type = "ORTHO"
    cam.data.ortho_scale = ortho
    if view == "3q":
        # corner 3/4 view — for kits whose pieces are vertical (walls/parts) and
        # would read as thin edges from the default top-down camera.
        cam.location = (ortho * 0.42, -ortho * 0.66, ortho * 0.5)
        target = mathutils.Vector((0, 0, ortho * 0.06))
    else:
        cam.location = (0, -12, 16)
        target = mathutils.Vector((0, 0, 0))
    look = target - mathutils.Vector(cam.location)
    cam.rotation_euler = look.to_track_quat("-Z", "Y").to_euler()
    for engine in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE"):
        try:
            scene.render.engine = engine
            break
        except (TypeError, AttributeError):
            continue
    try:
        scene.eevee.taa_render_samples = 48
    except Exception:
        pass
    scene.render.resolution_x = 1500
    scene.render.resolution_y = 1100
    scene.render.filepath = out_png
    bpy.ops.render.render(write_still=True)


def main() -> int:
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    atlas = "--atlas" in argv
    pos = [a for a in argv if not a.startswith("--")]
    if len(pos) < 2:
        print("PIPELINE result=FAIL reason=usage: -- <spec.py> <out_dir> [--atlas]")
        return 2
    spec_path, out_dir = pos[0], pos[1]
    spec = _load_spec(spec_path)

    glb_dir = os.path.join(out_dir, "glb")
    os.makedirs(glb_dir, exist_ok=True)

    palette = {**PALETTE, **getattr(spec, "PALETTE_OVERRIDE", {})}
    emission = {**EMISSION, **getattr(spec, "EMISSION_OVERRIDE", {})}
    k = Kit(palette=palette, emission=emission, reset_scene=True, atlas=atlas)

    aesthetic = getattr(spec, "AESTHETIC", "medieval")
    profile = PROFILES.get(aesthetic, PROFILES["medieval"])

    pieces = spec.PIECES
    cols = 3 if len(pieces) <= 9 else 6
    tris: dict[str, int] = {}
    for i, (name, fn) in enumerate(pieces):
        obj = fn(k)
        if atlas:
            k.pack_atlas()                    # embed the shared atlas in each GLB
        tris[name] = k.tri_count(obj)
        k.export_glb(obj, os.path.join(glb_dir, f"{name}.glb"))
        col, row = i % cols, i // cols
        obj.location = (col * 2.4 - (cols - 1) * 1.2, -row * 2.4 + 2.4, 0)

    with open(os.path.join(out_dir, "tris.json"), "w", encoding="utf-8") as f:
        json.dump(tris, f, indent=2, sort_keys=True)
    lo, hi = min(tris.values()), max(tris.values())
    out_of_band = sorted(n for n, t in tris.items() if not (TRI_LO <= t <= TRI_HI))

    # ground slab under the catalog, tinted by the aesthetic profile
    k.box([], 40, 40, 0.1, (0, 0, -0.06), profile["ground"])
    catalog = os.path.join(out_dir, "catalog.png")
    _render_catalog(k.scene, catalog, max(10.0, cols * 2.4 + 4), profile)

    ok = all(
        os.path.getsize(os.path.join(glb_dir, f"{n}.glb")) > 0 for n, _ in pieces
    ) and os.path.isfile(catalog)
    print(
        f"PIPELINE result={'OK' if ok else 'FAIL'} title={getattr(spec, 'TITLE', '?')!r} "
        f"aesthetic={aesthetic} atlas={atlas} pieces={len(pieces)} "
        f"tris={lo}..{hi} out_of_band={out_of_band or 'none'} "
        f"glb_dir={glb_dir} catalog={catalog}"
    )
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
