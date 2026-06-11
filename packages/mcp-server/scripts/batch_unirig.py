"""Batch auto-rigging via UniRig for Berserkr game models.

Runs the full UniRig pipeline (skeleton prediction + skinning + merge) on
character and creature GLBs. Produces rigged GLBs ready for animation.

Usage:
    python batch_unirig.py [--asset-type characters|creatures|all] [--model ID] [--dry-run]

Requires:
    - UniRig installed at C:/UniRig with model checkpoints
    - UniRig venv at C:/UniRig/.venv (Python 3.11 + CUDA deps)

Pipeline per model:
    1. Extract mesh → NPZ (bpy-based mesh extraction)
    2. Predict skeleton (AI autoregressive model, ~1-3s)
    3. Predict skin weights (AI cross-attention model, ~1-3s)
    4. Merge skeleton + skin with original textured mesh → rigged GLB
"""

import argparse
import logging
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# --- Paths ---
UNIRIG_DIR = Path("C:/UniRig")
UNIRIG_PYTHON = UNIRIG_DIR / ".venv" / "Scripts" / "python.exe"
GODOT_PROJECT = Path("D:/Projects/berserkr-godot")
GAME_ASSETS = GODOT_PROJECT / "games" / "berserkr" / "assets"
MODELS_DIR = GAME_ASSETS / "models"

# Humanoid creatures that need rigging (same list as generate_berserkr_creatures.py)
HUMANOID_CREATURE_IDS = {
    "trollkin", "draugr", "barrow_wight", "huldra", "frost_giant",
    "ice_troll", "dark_elf", "duergar", "hel_walker", "fire_giant",
    "bandit", "bandit_chief", "nisse",
}


def find_glbs(asset_type: str) -> list[tuple[str, Path]]:
    """Find GLB files to rig based on asset type.

    Returns list of (model_id, glb_path) tuples.
    """
    glbs = []

    if asset_type in ("characters", "all"):
        # Character classes
        classes_dir = MODELS_DIR / "characters" / "classes"
        if classes_dir.exists():
            for f in sorted(classes_dir.glob("*.glb")):
                if f.stem.endswith("_rigged"):
                    continue
                glbs.append((f.stem, f))

        # Character NPCs
        npcs_dir = MODELS_DIR / "characters" / "npcs"
        if npcs_dir.exists():
            for f in sorted(npcs_dir.glob("*.glb")):
                if f.stem.endswith("_rigged"):
                    continue
                glbs.append((f.stem, f))

    if asset_type in ("creatures", "all"):
        # Creature models (humanoid only)
        creatures_dir = MODELS_DIR / "creatures"
        if creatures_dir.exists():
            for realm_dir in sorted(creatures_dir.iterdir()):
                if realm_dir.is_dir() and not realm_dir.name.startswith("_"):
                    for f in sorted(realm_dir.glob("*.glb")):
                        if f.stem.endswith("_rigged"):
                            continue
                        if f.stem in HUMANOID_CREATURE_IDS:
                            glbs.append((f.stem, f))

    return glbs


def run_unirig_step(
    args: list[str], step_name: str, timeout: int = 300,
    allow_crash: bool = False, success_file: Path | None = None,
) -> bool:
    """Run a UniRig Python module step using the UniRig venv.

    Args:
        allow_crash: If True, treat non-zero exit as success if success_file exists.
            Used for the extract step where bpy segfaults on cleanup but data is saved.
        success_file: File that must exist for allow_crash to consider it a success.

    Returns True on success.
    """
    cmd = [str(UNIRIG_PYTHON)] + args
    logger.info("  [%s] Running: %s", step_name, " ".join(cmd[-4:]))

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=str(UNIRIG_DIR),
            env={**os.environ, "PYTHONPATH": str(UNIRIG_DIR)},
        )

        if result.returncode != 0:
            if allow_crash and success_file and success_file.exists():
                logger.info("  [%s] Process crashed (exit %d) but output exists — continuing",
                            step_name, result.returncode)
                return True
            logger.error("  [%s] FAILED (exit %d)", step_name, result.returncode)
            if result.stderr:
                for line in result.stderr.strip().split("\n")[-5:]:
                    logger.error("    %s", line)
            return False

        return True

    except subprocess.TimeoutExpired:
        logger.error("  [%s] TIMEOUT after %ds", step_name, timeout)
        return False
    except Exception as e:
        logger.error("  [%s] ERROR: %s", step_name, e)
        return False


def rig_single(model_id: str, glb_path: Path, output_dir: Path, dry_run: bool = False) -> dict:
    """Rig a single GLB model through the full UniRig pipeline.

    UniRig's path resolution breaks with absolute Windows paths (os.path.join
    discards prior components when it sees a drive letter). We work around this
    by copying the GLB into the UniRig CWD and using relative paths throughout.

    Steps:
        1. Extract mesh → NPZ (bpy-based, segfaults on cleanup but data is saved)
        2. Predict skeleton — NO --output so user_mode=False and predict_skeleton.npz is saved
        3. Predict skin weights — reads predict_skeleton.npz, outputs skin FBX
        4. Merge skeleton + skin with original textured mesh → rigged GLB

    Returns dict with status info.
    """
    rigged_path = output_dir / f"{model_id}_rigged.glb"

    if rigged_path.exists():
        logger.info("SKIP %s — rigged GLB already exists at %s", model_id, rigged_path)
        return {"model": model_id, "status": "skipped", "path": str(rigged_path)}

    if dry_run:
        logger.info("DRY RUN — %s", model_id)
        logger.info("  Input:  %s", glb_path)
        logger.info("  Output: %s", rigged_path)
        return {"model": model_id, "status": "dry_run", "path": str(rigged_path)}

    logger.info("RIG %s", model_id)
    logger.info("  Input: %s (%s)", glb_path, f"{glb_path.stat().st_size / 1e6:.1f} MB")
    start = time.time()

    # Copy GLB into UniRig CWD so all paths are relative (avoids Windows
    # absolute path issues with os.path.join inside UniRig).
    local_glb = UNIRIG_DIR / f"{model_id}.glb"
    shutil.copy2(glb_path, local_glb)

    # Relative paths from CWD (C:/UniRig)
    input_rel = f"{model_id}.glb"
    npz_dir_rel = "tmp"
    # After get_files: npz subdir = tmp/{model_id}/
    npz_subdir = UNIRIG_DIR / "tmp" / model_id
    results_dir = UNIRIG_DIR / "results" / model_id
    results_dir.mkdir(parents=True, exist_ok=True)

    try:
        # Step 1: Extract mesh to NPZ
        # bpy segfaults on cleanup but writes the NPZ successfully.
        npz_file = npz_subdir / "raw_data.npz"
        ok = run_unirig_step([
            "-m", "src.data.extract",
            "--config=configs/data/quick_inference.yaml",
            "--require_suffix=glb",
            "--force_override=true",
            "--num_runs=1",
            "--id=0",
            f"--time={model_id}",
            "--faces_target_count=50000",
            f"--input={input_rel}",
            f"--output_dir={npz_dir_rel}",
        ], "extract", timeout=120, allow_crash=True, success_file=npz_file)

        if not ok:
            return {"model": model_id, "status": "failed", "step": "extract"}
        if not npz_file.exists():
            logger.error("  Extract produced no NPZ at %s", npz_file)
            return {"model": model_id, "status": "failed", "step": "extract_no_npz"}

        # Step 2: Predict skeleton
        # We pass --output to place the FBX at a known location.
        # ar.py was patched to always save predict_skeleton.npz regardless
        # of user_mode, so the skin step can find it.
        skeleton_fbx = results_dir / "skeleton.fbx"
        ok = run_unirig_step([
            "run.py",
            "--task=configs/task/quick_inference_skeleton_articulationxl_ar_256.yaml",
            "--seed=12345",
            f"--input={input_rel}",
            f"--npz_dir={npz_dir_rel}",
            f"--output={skeleton_fbx}",
        ], "skeleton", timeout=600)

        if not ok:
            return {"model": model_id, "status": "failed", "step": "skeleton"}

        skeleton_npz = npz_subdir / "predict_skeleton.npz"
        if not skeleton_npz.exists():
            logger.error("  Skeleton step did not produce %s", skeleton_npz)
            return {"model": model_id, "status": "failed", "step": "skeleton_no_npz"}

        # Step 3: Predict skin weights
        # --output is OK here (we need FBX at a known path; NPZ save in skin
        # writer is not gated on user_mode).
        skin_fbx = results_dir / "skin.fbx"
        ok = run_unirig_step([
            "run.py",
            "--task=configs/task/quick_inference_unirig_skin.yaml",
            "--seed=12345",
            f"--input={input_rel}",
            f"--npz_dir={npz_dir_rel}",
            f"--output={skin_fbx}",
            "--data_name=predict_skeleton.npz",
        ], "skinning", timeout=600)

        if not ok:
            return {"model": model_id, "status": "failed", "step": "skinning"}

        if not skin_fbx.exists():
            # Try alternate output locations
            for candidate in results_dir.rglob("*.fbx"):
                if "skin" in candidate.name.lower() or "result" in candidate.name.lower():
                    skin_fbx = candidate
                    logger.info("  Found skin FBX at alternate location: %s", skin_fbx)
                    break

        if not skin_fbx.exists():
            logger.error("  Skin step produced no FBX")
            return {"model": model_id, "status": "failed", "step": "skinning_no_fbx"}

        # Step 4: Merge with original mesh (preserves textures)
        # Merge also uses bpy which segfaults on cleanup, but the GLB is
        # written before the crash (log shows "Finished glTF 2.0 export").
        ok = run_unirig_step([
            "-m", "src.inference.merge",
            "--require_suffix=glb",
            "--num_runs=1",
            "--id=0",
            f"--source={skin_fbx}",
            f"--target={glb_path}",
            f"--output={rigged_path}",
        ], "merge", timeout=120, allow_crash=True, success_file=rigged_path)

        if not ok:
            return {"model": model_id, "status": "failed", "step": "merge"}

        if not rigged_path.exists():
            logger.error("  Output file not created at %s", rigged_path)
            return {"model": model_id, "status": "failed", "step": "output_missing"}

        elapsed = time.time() - start
        size_mb = rigged_path.stat().st_size / 1e6
        logger.info("  DONE in %.1fs — %s (%.1f MB)", elapsed, rigged_path, size_mb)

        return {
            "model": model_id,
            "status": "rigged",
            "path": str(rigged_path),
            "elapsed": round(elapsed, 1),
            "size_mb": round(size_mb, 1),
        }

    except Exception as e:
        logger.error("  EXCEPTION: %s", e)
        return {"model": model_id, "status": "failed", "error": str(e)}

    finally:
        # Clean up temp files
        for cleanup_path in [local_glb, npz_subdir, results_dir]:
            if isinstance(cleanup_path, Path) and cleanup_path.exists():
                try:
                    if cleanup_path.is_dir():
                        shutil.rmtree(cleanup_path)
                    else:
                        cleanup_path.unlink()
                except Exception:
                    pass


def main():
    parser = argparse.ArgumentParser(description="Batch auto-rig Berserkr models via UniRig")
    parser.add_argument("--asset-type", choices=["characters", "creatures", "all"],
                        default="all", help="Which models to rig")
    parser.add_argument("--model", type=str, default=None,
                        help="Rig only this model ID (e.g., 'berserkr', 'draugr')")
    parser.add_argument("--dry-run", action="store_true",
                        help="Show what would be rigged without running")
    parser.add_argument("--output-dir", type=str, default=None,
                        help="Output directory for rigged GLBs (default: alongside originals)")
    args = parser.parse_args()

    # Verify UniRig setup
    if not UNIRIG_DIR.exists():
        logger.error("UniRig not found at %s", UNIRIG_DIR)
        sys.exit(1)
    if not UNIRIG_PYTHON.exists():
        logger.error("UniRig Python venv not found at %s", UNIRIG_PYTHON)
        sys.exit(1)

    skeleton_ckpt = UNIRIG_DIR / "experiments" / "skeleton" / "articulation-xl_quantization_256" / "model.ckpt"
    skin_ckpt = UNIRIG_DIR / "experiments" / "skin" / "articulation-xl" / "model.ckpt"
    if not skeleton_ckpt.exists() or not skin_ckpt.exists():
        logger.error("UniRig checkpoints not found. Expected:")
        logger.error("  %s", skeleton_ckpt)
        logger.error("  %s", skin_ckpt)
        sys.exit(1)

    # Find models
    glbs = find_glbs(args.asset_type)
    if args.model:
        glbs = [(mid, path) for mid, path in glbs if mid == args.model]

    if not glbs:
        logger.error("No GLBs found for asset-type=%s model=%s", args.asset_type, args.model)
        sys.exit(1)

    logger.info("=" * 60)
    logger.info("UniRig Batch Auto-Rigging")
    logger.info("Models to rig: %d", len(glbs))
    logger.info("Asset type: %s", args.asset_type)
    logger.info("=" * 60)

    results = []
    total_start = time.time()

    for i, (model_id, glb_path) in enumerate(glbs, 1):
        logger.info("")
        logger.info("[%d/%d] %s", i, len(glbs), model_id)

        # Output rigged GLBs alongside originals
        if args.output_dir:
            out_dir = Path(args.output_dir)
        else:
            out_dir = glb_path.parent

        out_dir.mkdir(parents=True, exist_ok=True)
        result = rig_single(model_id, glb_path, out_dir, dry_run=args.dry_run)
        results.append(result)

    elapsed = time.time() - total_start
    rigged = sum(1 for r in results if r["status"] == "rigged")
    skipped = sum(1 for r in results if r["status"] == "skipped")
    failed = sum(1 for r in results if r["status"] == "failed")

    logger.info("")
    logger.info("=" * 60)
    logger.info("COMPLETE — %d rigged, %d skipped, %d failed in %.1fs",
                rigged, skipped, failed, elapsed)
    logger.info("=" * 60)

    if failed > 0:
        logger.info("Failed models:")
        for r in results:
            if r["status"] == "failed":
                logger.info("  %s (step: %s)", r["model"], r.get("step", r.get("error", "?")))


if __name__ == "__main__":
    main()
