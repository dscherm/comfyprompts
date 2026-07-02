#!/usr/bin/env python
"""kit_quality_check — the machine-checkable subset of QUALITY_RUBRIC.md, as a
build/CI gate.

    python kit_quality_check.py <product_or_build_dir>

Checks the automatable rubric rows: export formats present (GLB/OBJ+MTL/FBX;
DAE aspirational), snake_case naming (§7), catalog + README + LISTING presence
(§8), and palette validity (§5). MUST failures exit non-zero. Aspirational KayKit
targets (200+ pieces §1, DAE/glTF §8, gallery/hero §8) are WARN only. Tri-count
bands (§1, 20..~5659) require Blender and are reported by the pipeline, not here.
"""

import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

DENSITY_TARGET = 200  # KayKit flagship density (aspirational WARN, see research)
NAME_RE = re.compile(r"^[a-z][a-z0-9_]*$")


def _names(d, sub, ext):
    p = os.path.join(d, sub)
    if not os.path.isdir(p):
        return set()
    return {f[: -len(ext)] for f in os.listdir(p) if f.endswith(ext)}


def check(d):
    musts, warns = [], []
    glb = _names(d, "models_glb", ".glb")
    obj = _names(d, "models_obj", ".obj")
    fbx = _names(d, "models_fbx", ".fbx")

    if not glb:
        musts.append("no models_glb/*.glb found")
    for n in sorted(glb):
        if n not in obj:
            musts.append(f"{n}: missing OBJ export")
        elif not os.path.exists(os.path.join(d, "models_obj", n + ".mtl")):
            musts.append(f"{n}: missing OBJ .mtl")
        if n not in fbx:
            musts.append(f"{n}: missing FBX export")
        if not NAME_RE.match(n):
            musts.append(f"{n}: name not snake_case (§7)")

    for doc in ("catalog.png", "README.md", "LISTING.md"):
        if not os.path.exists(os.path.join(d, doc)):
            musts.append(f"missing {doc} (§8)")

    if not _names(d, "models_dae", ".dae"):
        warns.append("no DAE export — KayKit ships FBX/OBJ/DAE/GLTF (§8)")
    if not os.path.isdir(os.path.join(d, "gallery")):
        warns.append("no gallery/ per-piece close-ups (§8)")
    if not os.path.exists(os.path.join(d, "hero.png")):
        warns.append("no hero.png (§8)")
    if len(glb) < DENSITY_TARGET:
        warns.append(f"density {len(glb)}/{DENSITY_TARGET}+ pieces — KayKit bar (§1)")

    try:
        from kitlib import validate_palette

        validate_palette()
    except Exception as exc:  # noqa: BLE001
        musts.append(f"palette invalid (§5): {exc}")

    print(f"KIT QUALITY CHECK  dir={d}  pieces={len(glb)}")
    for m in musts:
        print(f"  FAIL  {m}")
    for w in warns:
        print(f"  WARN  {w}")
    print("  NOTE  tri-count band (20..~5659, §1) not checked here — see the "
          "pipeline tri report / QUALITY_RUBRIC.md.")
    print(f"RESULT {'FAIL' if musts else 'PASS'} ({len(musts)} must, {len(warns)} warn)")
    return 1 if musts else 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("usage: kit_quality_check.py <product_or_build_dir>")
        raise SystemExit(2)
    raise SystemExit(check(sys.argv[1]))
