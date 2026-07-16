"""Build a labeled eval set for testing whether a local VLM can spot 3D game-art
defects in renders.

Ground truth comes from two sources:
  - known-good: shipped kit GLBs under ``products/*/models_glb/*.glb``, rendered as-is
    (label ``none``)
  - known-bad: the same source GLBs re-rendered with a deterministic, programmatically
    injected defect (label = the defect type)

Source GLBs under ``products/`` are only ever opened for reading by the Blender
subprocess (imported into a fresh in-memory scene) and are never written to.

Usage:
    python scripts/vlm_eval/build_eval_set.py [--seed 42] [--n-assets 24] [--force]
"""

from __future__ import annotations

import argparse
import json
import random
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_DIR = Path(__file__).resolve().parent
RENDER_SCRIPT = SCRIPT_DIR / "blender_render_defect.py"
DEFAULT_BLENDER_EXE = r"C:\Program Files\Blender Foundation\Blender 5.0\blender.exe"
DEFAULT_OUT_DIR = SCRIPT_DIR / "renders"
DEFAULT_LABELS_PATH = SCRIPT_DIR / "labels.json"

DEFECT_TYPES: list[str] = [
    "flipped_normals",
    "unwelded_cracks",
    "missing_texture",
    "uv_smear",
    "scale_error",
    "wrong_orientation",
]

sys.path.insert(0, str(REPO_ROOT / "tools" / "security"))
from filename_guard import safe_filename  # noqa: E402


def _candidate_glbs() -> list[Path]:
    glbs = sorted((REPO_ROOT / "products").glob("*/models_glb/*.glb"))
    if not glbs:
        raise RuntimeError("no source GLBs found under products/*/models_glb/*.glb")
    return glbs


def _sample_assets(glbs: list[Path], seed: int, n_assets: int) -> list[Path]:
    rng = random.Random(seed)
    n = min(n_assets, len(glbs))
    return rng.sample(glbs, n)


def _image_name(glb: Path, defect_type: str) -> str:
    kit = glb.parent.parent.name
    stem = glb.stem
    name = f"{kit}__{stem}__{defect_type}.png"
    return safe_filename(name)


def _render(
    blender_exe: str,
    glb: Path,
    defect_type: str,
    seed: int,
    out_png: Path,
    force: bool,
) -> bool:
    if out_png.exists() and not force:
        return True
    out_png.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        blender_exe,
        "--background",
        "--factory-startup",
        "--python",
        str(RENDER_SCRIPT),
        "--",
        str(glb),
        defect_type,
        str(seed),
        str(out_png),
    ]
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=180, check=False
        )
    except subprocess.TimeoutExpired:
        print(f"TIMEOUT rendering {glb.name} ({defect_type})", file=sys.stderr)
        return False
    if result.returncode != 0 or not out_png.exists():
        print(f"FAILED rendering {glb.name} ({defect_type}):", file=sys.stderr)
        print(result.stdout[-2000:], file=sys.stderr)
        print(result.stderr[-2000:], file=sys.stderr)
        return False
    return True


def build(
    seed: int,
    n_assets: int,
    out_dir: Path,
    labels_path: Path,
    blender_exe: str,
    force: bool,
) -> list[dict]:
    glbs = _candidate_glbs()
    sampled = _sample_assets(glbs, seed, n_assets)

    entries: list[dict] = []
    for i, glb in enumerate(sampled):
        defect_type = DEFECT_TYPES[i % len(DEFECT_TYPES)]
        variant_seed = seed * 10_000 + i

        clean_name = _image_name(glb, "none")
        clean_png = out_dir / clean_name
        if _render(blender_exe, glb, "none", seed, clean_png, force):
            entries.append(
                {
                    "image": clean_png.relative_to(REPO_ROOT).as_posix(),
                    "asset": glb.relative_to(REPO_ROOT).as_posix(),
                    "defect_type": "none",
                    "seed": seed,
                }
            )

        defect_name = _image_name(glb, defect_type)
        defect_png = out_dir / defect_name
        if _render(blender_exe, glb, defect_type, variant_seed, defect_png, force):
            entries.append(
                {
                    "image": defect_png.relative_to(REPO_ROOT).as_posix(),
                    "asset": glb.relative_to(REPO_ROOT).as_posix(),
                    "defect_type": defect_type,
                    "seed": variant_seed,
                }
            )

    entries.sort(key=lambda e: e["image"])
    return entries


def _verify(entries: list[dict]) -> None:
    if len(entries) < 40:
        raise RuntimeError(f"expected >=40 labeled entries, got {len(entries)}")
    missing = [e["image"] for e in entries if not (REPO_ROOT / e["image"]).exists()]
    if missing:
        raise RuntimeError(f"labels.json references missing images: {missing}")
    defect_kinds = {e["defect_type"] for e in entries} - {"none"}
    if len(defect_kinds) < 5:
        raise RuntimeError(f"expected >=5 defect types, got {sorted(defect_kinds)}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--n-assets", type=int, default=24)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--labels", type=Path, default=DEFAULT_LABELS_PATH)
    parser.add_argument("--blender-exe", default=DEFAULT_BLENDER_EXE)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    entries = build(
        seed=args.seed,
        n_assets=args.n_assets,
        out_dir=args.out_dir,
        labels_path=args.labels,
        blender_exe=args.blender_exe,
        force=args.force,
    )
    _verify(entries)

    args.labels.parent.mkdir(parents=True, exist_ok=True)
    with open(args.labels, "w", encoding="utf-8") as f:
        json.dump(entries, f, indent=2)
        f.write("\n")

    counts: dict[str, int] = {}
    for e in entries:
        counts[e["defect_type"]] = counts.get(e["defect_type"], 0) + 1
    print(f"Wrote {len(entries)} entries to {args.labels}")
    for defect_type, count in sorted(counts.items()):
        print(f"  {defect_type}: {count}")


if __name__ == "__main__":
    main()
