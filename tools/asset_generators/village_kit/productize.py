"""productize — assemble a sellable GrimForge product from a kit spec.

Builds every piece once and exports it in all marketplace formats
(GLB / glTF / OBJ+MTL / FBX / DAE), renders a catalog under the spec's aesthetic
profile, and writes README.md + LISTING.md. With ``--atlas`` the pieces are built
in KayKit color-atlas mode and the shared atlas PNGs are shipped alongside. The
Godot showcase (hero.png) and per-piece gallery are rendered separately via
godot_verify (see README).

    blender -b --python productize.py -- <spec.py> <product_dir> [product_name] [--atlas]
"""

import json
import os
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from kit_pipeline import PROFILES, TRI_HI, TRI_LO, _load_spec, _render_catalog  # noqa: E402
from kitlib import EMISSION, PALETTE, Kit  # noqa: E402

# Interchange coverage matching KayKit (FBX/OBJ/DAE/GLTF) plus USD. DAE is
# best-effort: Blender 5.0 dropped the Collada exporter, so it's pruned at runtime
# on builds that can't produce it (USD fills the same interchange role natively).
FORMATS = ("glb", "gltf", "obj", "fbx", "usd", "dae")
ATLAS_MASTER = 512  # shipped atlas master size (QUALITY_RUBRIC §4); +128² thumb


_FMT_DOC = {
    "glb": "`models_glb/` — glTF binary (Godot, Unity, Unreal, Blender)",
    "gltf": "`models_gltf/` — glTF separate (`.gltf` + `.bin` + textures)",
    "obj": "`models_obj/` — Wavefront OBJ + MTL",
    "fbx": "`models_fbx/` — Autodesk FBX (textures embedded)",
    "usd": "`models_usd/` — Universal Scene Description (`.usdc`)",
    "dae": "`models_dae/` — COLLADA DAE",
}


def _write_docs(
    product_dir: str, title: str, aesthetic: str, names: list,
    atlas: bool = False, avail: list | None = None,
) -> None:
    avail = avail if avail is not None else ["glb", "obj", "fbx"]
    pretty = ", ".join(n.replace("_", " ") for n in names)
    shading = (
        "shaded with a shared KayKit-style color atlas (wood/stone/thatch/stained-glass "
        "patterns baked in; `atlas_color.png` + `atlas_emit.png` shipped in the root)"
        if atlas
        else "flat-shaded in the GrimForge palette"
    )
    formats_md = "".join(f"- {_FMT_DOC[f]}\n" for f in avail if f in _FMT_DOC)
    fmt_label = {"glb": "GLB", "gltf": "glTF", "obj": "OBJ", "fbx": "FBX",
                 "usd": "USD", "dae": "DAE"}
    fmt_list = " + ".join(fmt_label[f] for f in avail if f in fmt_label)
    with open(os.path.join(product_dir, "README.md"), "w", encoding="utf-8") as f:
        f.write(
            f"# {title}\n\n"
            f"{len(names)} modular low-poly 3D pieces, {shading}, in the GrimForge "
            f"{aesthetic} palette. Procedurally generated; original work.\n\n"
            f"## Formats\n"
            + formats_md
            + f"\n## Pieces ({len(names)})\n"
            + "".join(f"- {n.replace('_', ' ')}\n" for n in names)
            + "\n## License\nRoyalty-free for commercial and personal use. "
            "Outputs are procedurally generated; disclose AI assistance where required.\n"
        )
    with open(os.path.join(product_dir, "LISTING.md"), "w", encoding="utf-8") as f:
        f.write(
            f"## Title\n`{title}`\n\n"
            f"## Short description\n> {len(names)} modular low-poly dark-fantasy pieces — "
            f"{pretty}. {fmt_list}. Grid-modular for Godot, Unity, Unreal.\n\n"
            f"## Tags\n`low-poly`, `dark-fantasy`, `occult`, `horror`, `medieval`, `modular`, "
            f"`3D`, `kit`, `game-ready`, `GLB`, `glTF`, `FBX`, `USD`, `Godot`, `Unity`\n\n"
            f"## Gallery (upload order)\n1. `hero.png`\n2. `catalog.png`\n"
            f"3. close-ups in `gallery/`\n\n"
            f"## Pre-publish checklist\n- [ ] Zip models_glb/ (+obj/fbx), README, hero, catalog.\n"
            f"- [ ] Note 'procedurally generated low-poly'.\n"
            f"- [ ] Royalty-free commercial license.\n"
        )


def main() -> int:
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    atlas = "--atlas" in argv
    pos = [a for a in argv if not a.startswith("--")]
    if len(pos) < 2:
        print("PRODUCT result=FAIL reason=usage: -- <spec.py> <product_dir> [name] [--atlas]")
        return 2
    spec_path, product_dir = pos[0], pos[1]
    name = pos[2] if len(pos) > 2 else os.path.basename(spec_path)[:-3]
    spec = _load_spec(spec_path)

    for fmt in FORMATS:
        os.makedirs(os.path.join(product_dir, f"models_{fmt}"), exist_ok=True)

    palette = {**PALETTE, **getattr(spec, "PALETTE_OVERRIDE", {})}
    emission = {**EMISSION, **getattr(spec, "EMISSION_OVERRIDE", {})}
    k = Kit(palette=palette, emission=emission, reset_scene=True,
            atlas=atlas, atlas_size=ATLAS_MASTER)
    aesthetic = getattr(spec, "AESTHETIC", "medieval")
    profile = PROFILES.get(aesthetic, PROFILES["medieval"])

    pieces = spec.PIECES
    cols = 3 if len(pieces) <= 9 else 5
    # Phase 1: build every piece (populates the scene + the shared atlas).
    built = [(pname, fn(k)) for pname, fn in pieces]
    # Phase 2: ship the atlas PNGs *before* export so OBJ/FBX/DAE reference a real
    # file and GLB/glTF embed the packed image.
    if atlas:
        k.save_atlas(product_dir)
    # Phase 3: export every piece in every format + record tri counts. A format
    # that fails on the first piece (e.g. DAE on Blender 5.0) is pruned for the run.
    names, tris, avail, dropped = [], {}, list(FORMATS), {}
    for idx, (pname, obj) in enumerate(built):
        tris[pname] = k.tri_count(obj)
        for fmt in list(avail):
            method, ext = k.exporters[fmt]
            try:
                method(obj, os.path.join(product_dir, f"models_{fmt}", pname + ext))
            except Exception as exc:  # noqa: BLE001
                if idx == 0:
                    avail.remove(fmt)
                    dropped[fmt] = str(exc).splitlines()[0][:70]
                else:
                    raise
        names.append(pname)
    for fmt in FORMATS:  # drop empty dirs for pruned formats
        if fmt not in avail:
            fd = os.path.join(product_dir, f"models_{fmt}")
            if os.path.isdir(fd) and not os.listdir(fd):
                os.rmdir(fd)
    # OBJ .mtl references the atlas by bare name; copy it beside the .obj so the
    # models_obj/ folder is self-contained (glTF/USD already carry their textures).
    if atlas and "obj" in avail:
        src = os.path.join(product_dir, "atlas_color.png")
        if os.path.exists(src):
            shutil.copy2(src, os.path.join(product_dir, "models_obj", "atlas_color.png"))
    # Phase 4: lay the pieces out for the catalog render.
    for i, (_pname, obj) in enumerate(built):
        col, row = i % cols, i // cols
        obj.location = (col * 2.6 - (cols - 1) * 1.3, -row * 2.6 + 3.0, 0)

    with open(os.path.join(product_dir, "tris.json"), "w", encoding="utf-8") as f:
        json.dump(tris, f, indent=2, sort_keys=True)
    lo, hi = min(tris.values()), max(tris.values())
    out_of_band = sorted(n for n, t in tris.items() if not (TRI_LO <= t <= TRI_HI))

    k.box([], 60, 60, 0.1, (0, 0, -0.06), profile["ground"])
    catalog = os.path.join(product_dir, "catalog.png")
    view = getattr(spec, "HERO_VIEW", "top")   # "3q" for vertical parts kits
    _render_catalog(k.scene, catalog, max(12.0, cols * 2.6 + 4), profile, view)
    _write_docs(product_dir, getattr(spec, "TITLE", name), aesthetic, names, atlas, avail)

    counts = {fmt: len(os.listdir(os.path.join(product_dir, f"models_{fmt}"))) for fmt in avail}
    print(
        f"PRODUCT result=OK name={name} atlas={atlas} pieces={len(names)} "
        f"tris={lo}..{hi} out_of_band={out_of_band or 'none'} "
        f"formats={counts} dropped={dropped or 'none'} dir={product_dir}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
