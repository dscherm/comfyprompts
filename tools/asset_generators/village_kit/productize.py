"""productize — assemble a sellable GrimForge product from a kit spec.

Builds every piece once and exports it in all three marketplace formats
(GLB / OBJ+MTL / FBX), renders a catalog under the spec's aesthetic profile,
and writes README.md + LISTING.md. The Godot showcase (hero.png) and per-piece
gallery are rendered separately via godot_verify (see README).

    blender -b --python productize.py -- <spec.py> <product_dir> [product_name]
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from kit_pipeline import PROFILES, _load_spec, _render_catalog  # noqa: E402
from kitlib import EMISSION, PALETTE, Kit  # noqa: E402

FORMATS = ("glb", "obj", "fbx")


def _write_docs(product_dir: str, title: str, aesthetic: str, names: list) -> None:
    pretty = ", ".join(n.replace("_", " ") for n in names)
    with open(os.path.join(product_dir, "README.md"), "w", encoding="utf-8") as f:
        f.write(
            f"# {title}\n\n"
            f"{len(names)} modular low-poly 3D pieces, flat-shaded in the GrimForge "
            f"{aesthetic} palette. Procedurally generated; original work.\n\n"
            f"## Formats\n"
            f"- `models_glb/` — glTF binary (Godot, Unity, Unreal, Blender)\n"
            f"- `models_obj/` — Wavefront OBJ + MTL\n"
            f"- `models_fbx/` — Autodesk FBX\n\n"
            f"## Pieces ({len(names)})\n"
            + "".join(f"- {n.replace('_', ' ')}\n" for n in names)
            + "\n## License\nRoyalty-free for commercial and personal use. "
            "Outputs are procedurally generated; disclose AI assistance where required.\n"
        )
    with open(os.path.join(product_dir, "LISTING.md"), "w", encoding="utf-8") as f:
        f.write(
            f"## Title\n`{title}`\n\n"
            f"## Short description\n> {len(names)} modular low-poly dark-fantasy pieces — "
            f"{pretty}. GLB + OBJ + FBX. Grid-modular for Godot, Unity, Unreal.\n\n"
            f"## Tags\n`low-poly`, `dark-fantasy`, `occult`, `horror`, `medieval`, `modular`, "
            f"`3D`, `kit`, `game-ready`, `GLB`, `FBX`, `Godot`, `Unity`\n\n"
            f"## Gallery (upload order)\n1. `hero.png`\n2. `catalog.png`\n"
            f"3. close-ups in `gallery/`\n\n"
            f"## Pre-publish checklist\n- [ ] Zip models_glb/ (+obj/fbx), README, hero, catalog.\n"
            f"- [ ] Note 'procedurally generated low-poly'.\n"
            f"- [ ] Royalty-free commercial license.\n"
        )


def main() -> int:
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    if len(argv) < 2:
        print("PRODUCT result=FAIL reason=usage: -- <spec.py> <product_dir> [name]")
        return 2
    spec_path, product_dir = argv[0], argv[1]
    name = argv[2] if len(argv) > 2 else os.path.basename(spec_path)[:-3]
    spec = _load_spec(spec_path)

    for fmt in FORMATS:
        os.makedirs(os.path.join(product_dir, f"models_{fmt}"), exist_ok=True)

    palette = {**PALETTE, **getattr(spec, "PALETTE_OVERRIDE", {})}
    emission = {**EMISSION, **getattr(spec, "EMISSION_OVERRIDE", {})}
    k = Kit(palette=palette, emission=emission, reset_scene=True)
    aesthetic = getattr(spec, "AESTHETIC", "medieval")
    profile = PROFILES.get(aesthetic, PROFILES["medieval"])

    pieces = spec.PIECES
    cols = 3 if len(pieces) <= 9 else 5
    names = []
    for i, (pname, fn) in enumerate(pieces):
        obj = fn(k)                                            # built at origin
        for fmt in FORMATS:                                   # export all formats first
            method, ext = k.exporters[fmt]
            method(obj, os.path.join(product_dir, f"models_{fmt}", pname + ext))
        col, row = i % cols, i // cols                        # then lay out for the catalog
        obj.location = (col * 2.6 - (cols - 1) * 1.3, -row * 2.6 + 3.0, 0)
        names.append(pname)

    k.box([], 60, 60, 0.1, (0, 0, -0.06), profile["ground"])
    catalog = os.path.join(product_dir, "catalog.png")
    _render_catalog(k.scene, catalog, max(12.0, cols * 2.6 + 4), profile)
    _write_docs(product_dir, getattr(spec, "TITLE", name), aesthetic, names)

    counts = {fmt: len(os.listdir(os.path.join(product_dir, f"models_{fmt}"))) for fmt in FORMATS}
    print(f"PRODUCT result=OK name={name} pieces={len(names)} formats={counts} dir={product_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
