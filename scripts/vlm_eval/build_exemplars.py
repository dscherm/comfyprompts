"""Build the canonical Tier-2 (perceptual) rig-deformation exemplar corpus.

Produces version-controlled ground truth for "skin weights melt" — the finding in
lessons/unirig-skin-weights-melt-use-accurig.md: a rig with naive automatic/
envelope skin weights deforms badly at bent joints (knees lose definition, limbs
pinch or fail to bend) while production-quality weights deform cleanly on the
exact same mesh + skeleton + pose. Two source assets cover both rig families:
the AccuRIG humanoid (berserkr) and a UniRig quadruped (bestiary hell hound).

The GOOD/BAD pair differs in exactly one variable — skin weights — everything else
(mesh, skeleton, pose, camera, lighting) is held identical. See
blender_render_rig_exemplar.py for how the pair is constructed.

Source FBX under products/ is only ever opened for reading (imported into a fresh
in-memory Blender scene) and is never written to.

Usage:
    python scripts/vlm_eval/build_exemplars.py [--seed 42] [--force]
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_DIR = Path(__file__).resolve().parent
RENDER_SCRIPT = SCRIPT_DIR / "blender_render_rig_exemplar.py"
DEFAULT_BLENDER_EXE = r"C:\Program Files\Blender Foundation\Blender 5.0\blender.exe"
DEFAULT_OUT_DIR = REPO_ROOT / "eval" / "exemplars" / "rig_deformation"
DEFAULT_MANIFEST_PATH = REPO_ROOT / "eval" / "exemplars" / "manifest.json"

# fist_clench (a diagnostic pose named in the original brief) was dropped: the
# berserkr_accurig.fbx CC_Base skeleton has no individual finger bones (only a
# single terminal Hand bone per side), so a "clenched fist" pose cannot be
# posed via bone rotation on this asset. wrist_curl was tried as a substitute
# but rotating the Hand bone swings the whole forearm through an
# anatomically-implausible arc on this rig rather than a contained curl, so it
# was dropped too rather than shipped as a weak/misleading exemplar.
DROPPED_POSES_NOTE = (
    "fist_clench/wrist_curl dropped: berserkr_accurig.fbx has no finger bones "
    "(CC_Base skeleton, Hand is terminal), and rotating the Hand bone alone "
    "produces an implausible whole-arm swing rather than a contained wrist "
    "motion on this asset. knee_bend, elbow_bend, and hip_flex all produce "
    "clear, convincing good/bad deltas."
)

# One entry per source asset. Pose names must match the rig_kind's table in
# blender_render_rig_exemplar.py. The quadruped's good weights are UniRig
# (the validated quadruped rigging path — AccuRIG/Mixamo are humanoid-only);
# the bad twin is naive envelope weights, same mechanism as the humanoid pair.
ASSETS: list[dict] = [
    {
        "rig_kind": "humanoid",
        "project_type": "humanoid",
        "model": REPO_ROOT / "products" / "berserkr_v2_chars_v1" / "rigged"
        / "berserkr_accurig.fbx",
        "good_weights": "AccuRIG",
        "poses": ["knee_bend", "elbow_bend", "hip_flex"],
    },
    {
        "rig_kind": "quadruped",
        "project_type": "quadruped",
        "model": REPO_ROOT / "products" / "grimforge_bestiary_v1" / "_quadrig"
        / "hell_hound_rigged.glb",
        "good_weights": "UniRig",
        "poses": ["front_knee_bend", "hind_knee_bend", "neck_bend"],
    },
]


def _run_blender(blender_exe: str, asset: dict, seed: int, out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    cmd = [
        blender_exe,
        "--background",
        "--factory-startup",
        "--python",
        str(RENDER_SCRIPT),
        "--",
        str(asset["model"]),
        asset["rig_kind"],
        str(seed),
        str(out_dir),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=300, check=False)
    if result.returncode != 0:
        print(result.stdout[-4000:], file=sys.stderr)
        print(result.stderr[-4000:], file=sys.stderr)
        raise RuntimeError(f"blender render failed (exit {result.returncode})")
    if "ERROR" in result.stdout:
        print(result.stdout[-4000:], file=sys.stderr)
        raise RuntimeError("blender render reported a validation ERROR — see output above")


def _build_manifest(out_dir: Path) -> dict:
    pairs = []
    for asset in ASSETS:
        for pose in asset["poses"]:
            good = out_dir / f"good__{pose}.png"
            bad = out_dir / f"bad__{pose}.png"
            pairs.append(
                {
                    "pose": pose,
                    "project_type": asset["project_type"],
                    "source_asset": asset["model"].relative_to(REPO_ROOT).as_posix(),
                    "good": good.relative_to(REPO_ROOT).as_posix(),
                    "bad": bad.relative_to(REPO_ROOT).as_posix(),
                    "differing_variable": (
                        f"skin weights ({asset['good_weights']} vs naive envelope)"
                    ),
                }
            )
    return {
        "criteria": [
            {
                "id": "rig_deformation_melt",
                "project_types": sorted({a["project_type"] for a in ASSETS}),
                "description": (
                    "Skin weights that deform badly at bent joints: knees lose "
                    "definition, limbs pinch/tear/fail-to-bend, versus clean "
                    "production-quality deformation (AccuRIG humanoid, UniRig "
                    "quadruped) on the identical mesh, skeleton, and pose."
                ),
                "tier": 2,
                "decider": "model+human",
                "source_lesson": "lessons/unirig-skin-weights-melt-use-accurig.md",
                "notes": DROPPED_POSES_NOTE,
                "pairs": pairs,
            }
        ]
    }


def _verify(manifest: dict) -> None:
    for criterion in manifest["criteria"]:
        pairs = criterion["pairs"]
        if not pairs:
            raise RuntimeError(f"criterion {criterion['id']} has no pairs")
        for pair in pairs:
            for key in ("good", "bad"):
                path = REPO_ROOT / pair[key]
                if not path.exists():
                    raise RuntimeError(f"manifest references missing file: {pair[key]}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST_PATH)
    parser.add_argument("--blender-exe", default=DEFAULT_BLENDER_EXE)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    for asset in ASSETS:
        if not asset["model"].exists():
            raise RuntimeError(f"source model not found: {asset['model']}")

    for asset in ASSETS:
        expected = [
            args.out_dir / f"{twin}__{pose}.png"
            for pose in asset["poses"]
            for twin in ("good", "bad")
        ]
        if args.force or not all(p.exists() for p in expected):
            _run_blender(args.blender_exe, asset, args.seed, args.out_dir)

    manifest = _build_manifest(args.out_dir)
    _verify(manifest)

    args.manifest.parent.mkdir(parents=True, exist_ok=True)
    with open(args.manifest, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)
        f.write("\n")

    n_pairs = sum(len(c["pairs"]) for c in manifest["criteria"])
    print(f"Wrote manifest with {n_pairs} pair(s) to {args.manifest}")
    for criterion in manifest["criteria"]:
        for pair in criterion["pairs"]:
            print(f"  {pair['pose']}: {pair['good']} / {pair['bad']}")


if __name__ == "__main__":
    main()
