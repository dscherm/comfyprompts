"""ink_to_3d — one-shot orchestrator: a 2D drawing -> game-ready 3D mesh.

Chains the three committed ink-to-clay-ralph / toolchain tools:
  1. infer_kontext.py   ink drawing  -> clean faithful clay render (trained Kontext LoRA)
  2. trellis_recon.py   clay image   -> dense 3D GLB (TRELLIS.2, ~10 min, blocks ComfyUI)
  3. mesh_product_check clay GLB     -> validated + fixed game-ready GLB + FBX

ComfyUI must be UP on the 3090 Ti for stages 1-2 (generation only). Stage 3 is
headless Blender. Each stage writes into --out-dir and is skipped if its output
already exists (resumable).

  python ink_to_3d.py <ink.png> [--out-dir <dir>] [--name <slug>] [--max-tris 8000]
  python ink_to_3d.py <ink.png> --skip-trellis     # stages 1 only (fast plumbing check)
  python ink_to_3d.py <ink.png> --base             # use the base-model clay baseline
"""
from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path("D:/Projects/comfyui-toolchain")
PYEXE = "D:/Projects/ComfyUI/venv/Scripts/python.exe"
BLENDER = r"C:/Program Files/Blender Foundation/Blender 5.0/blender.exe"
COMFY_INPUT = Path("D:/Projects/ComfyUI/input")
COMFY_OUTPUT = Path("D:/Projects/ComfyUI/output")
INFER = ROOT / "pipelines/ink-to-clay-ralph/scripts/infer_kontext.py"
TRELLIS = ROOT / "scripts/train_lora/eval/trellis_recon.py"
MESH_TO_SOLID = ROOT / "pipelines/photo-to-3d/scripts/mesh_to_solid.py"
MESHCHECK = ROOT / "scripts/mesh_product_check.py"


def sh(cmd: list, stage: str) -> None:
    print(f"\n=== [{stage}] {' '.join(str(c) for c in cmd[:4])} ...", flush=True)
    r = subprocess.run([str(c) for c in cmd], cwd=str(ROOT))
    if r.returncode != 0:
        sys.exit(f"[{stage}] FAILED (exit {r.returncode})")


def sh_soft(cmd: list, stage: str) -> int:
    """Run a stage that may 'fail' a quality gate — report, do NOT abort the chain."""
    print(f"\n=== [{stage}] {' '.join(str(c) for c in cmd[:4])} ...", flush=True)
    return subprocess.run([str(c) for c in cmd], cwd=str(ROOT)).returncode


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("ink")
    ap.add_argument("--out-dir", default=None, help="default <ROOT>/output/ink_to_3d/<name>")
    ap.add_argument("--name", default=None, help="slug (default from the ink filename)")
    ap.add_argument("--max-tris", type=int, default=8000)
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--base", action="store_true", help="base-model clay (skip the trained LoRA)")
    ap.add_argument("--skip-trellis", action="store_true", help="stop after clay (plumbing check)")
    a = ap.parse_args()

    ink = Path(a.ink)
    if not ink.exists():
        sys.exit(f"missing ink: {ink}")
    name = a.name or re.sub(r"[^a-z0-9]+", "_", ink.stem.lower()).strip("_")
    out = Path(a.out_dir) if a.out_dir else ROOT / "output" / "ink_to_3d" / name
    out.mkdir(parents=True, exist_ok=True)

    # Stage 1: ink -> clay
    clay = out / f"{name}_clay.png"
    if clay.exists():
        print(f"[1/3] clay exists, skipping -> {clay}")
    else:
        cmd = [PYEXE, INFER, str(ink), str(clay), "--seed", a.seed]
        if a.base:
            cmd.append("--base")
        sh(cmd, "1/3 ink->clay")
        if not clay.exists():
            sys.exit("[1/3] no clay produced")
    if a.skip_trellis:
        print(f"\nDONE (clay only): {clay}")
        return

    # Stage 2: clay -> GLB (via TRELLIS; stage the clay into ComfyUI/input)
    prefix = f"3D/ink3d_{name}"
    glb = COMFY_OUTPUT / "3D" / f"ink3d_{name}_00001_.glb"
    if glb.exists():
        print(f"[2/3] GLB exists, skipping -> {glb}")
    else:
        staged = COMFY_INPUT / f"ink3d_{name}.png"
        shutil.copyfile(clay, staged)
        sh([PYEXE, TRELLIS, "--image", staged.name, "--prefix", prefix, "--seed", a.seed],
           "2/3 clay->GLB (TRELLIS ~10min)")
        if not glb.exists():
            sys.exit(f"[2/3] no GLB at {glb}")
    raw = out / f"{name}.glb"
    shutil.copyfile(glb, raw)

    # Stage 2.5: heal the raw TRELLIS mesh — weld unwelded fragments + voxel remesh
    # toward watertight, so the reducer isn't blocked by non-manifold soup.
    healed = out / f"{name}_solid.glb"
    if not healed.exists():
        sh([BLENDER, "--background", "--python", MESH_TO_SOLID, "--",
            "--input", str(raw), "--output-dir", str(out), "--name", f"{name}_solid",
            "--watertight", "--formats", "glb"], "2.5/3 heal -> solid")
    src = healed if healed.exists() else raw

    # Stage 3: game-ready validate + fix + export. NON-FATAL — raw TRELLIS meshes are
    # organic/non-manifold and may not clear the strict MESH-PRODUCT gate; report the
    # verdict and still deliver the clay + raw GLB + healed solid.
    report = out / f"{name}_meshcheck.json"
    rc = sh_soft([BLENDER, "--background", "--factory-startup", "--python", MESHCHECK, "--",
                  "--src", str(src), "--max-tris", a.max_tris, "--fix", "--quad-remesh",
                  "--export-dir", str(out), "--report", str(report)],
                 "3/3 mesh-product check + export")
    gate = "PASS (game-ready GLB+FBX exported)" if rc == 0 else \
        "FAIL — strict gate not met on the raw TRELLIS mesh; clay + GLB + healed solid delivered"

    print(f"\n=== INK->3D COMPLETE — mesh-gate: {gate} ===")
    for f in sorted(out.iterdir()):
        if f.is_file():
            print(f"  {f.name}")


if __name__ == "__main__":
    main()
