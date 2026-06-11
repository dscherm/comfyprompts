"""Batch-apply procedural animations to all UniRig-rigged GLB models.

Runs Blender headless with animate_unirig.py on each *_rigged.glb to produce
*_animated.glb with 6 NLA tracks (idle, walk, run, attack_1, hit_reaction, death).

Usage:
    python batch_animate_unirig.py [--asset-type characters|creatures|all] [--model ID] [--dry-run]

Replaces the _rigged.glb in-place (backs up to _rigged_preanim.glb first).
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
BLENDER = Path(r"C:\Program Files\Blender Foundation\Blender 5.0\blender.exe")
SCRIPT_DIR = Path(__file__).parent
ANIMATE_SCRIPT = SCRIPT_DIR / "animate_unirig.py"
GODOT_PROJECT = Path("D:/Projects/berserkr-godot")
GAME_ASSETS = GODOT_PROJECT / "games" / "berserkr" / "assets"
MODELS_DIR = GAME_ASSETS / "models"

# Humanoid creatures (same list as batch_unirig.py)
HUMANOID_CREATURE_IDS = {
    "trollkin", "draugr", "barrow_wight", "huldra", "frost_giant",
    "ice_troll", "dark_elf", "duergar", "hel_walker", "fire_giant",
    "bandit", "bandit_chief", "nisse",
}


def find_rigged_glbs(asset_type: str) -> list[tuple[str, Path]]:
    """Find *_rigged.glb files to animate."""
    glbs = []

    if asset_type in ("characters", "all"):
        for subdir in ["classes", "npcs"]:
            d = MODELS_DIR / "characters" / subdir
            if d.exists():
                for f in sorted(d.glob("*_rigged.glb")):
                    model_id = f.stem.replace("_rigged", "")
                    glbs.append((model_id, f))

    if asset_type in ("creatures", "all"):
        creatures_dir = MODELS_DIR / "creatures"
        if creatures_dir.exists():
            for realm_dir in sorted(creatures_dir.iterdir()):
                if realm_dir.is_dir() and not realm_dir.name.startswith("_"):
                    for f in sorted(realm_dir.glob("*_rigged.glb")):
                        model_id = f.stem.replace("_rigged", "")
                        if model_id in HUMANOID_CREATURE_IDS:
                            glbs.append((model_id, f))

    return glbs


def animate_single(model_id: str, rigged_glb: Path, dry_run: bool = False) -> dict:
    """Run Blender headless to apply animations to a single rigged GLB.

    The animated GLB replaces the rigged GLB in-place. A backup is made first.
    """
    # Output goes to a temp file, then replaces the original
    animated_tmp = rigged_glb.parent / f"{model_id}_animated_tmp.glb"

    if dry_run:
        logger.info("DRY RUN — %s (%s)", model_id, rigged_glb)
        return {"model": model_id, "status": "dry_run"}

    logger.info("ANIMATE %s", model_id)

    # Restore from preanim backup if it exists (ensures clean skeleton, no stale anims)
    backup = rigged_glb.parent / f"{model_id}_rigged_preanim.glb"
    if backup.exists():
        shutil.copy2(backup, rigged_glb)
        logger.info("  Restored from preanim backup")

    logger.info("  Input: %s (%.1f MB)", rigged_glb, rigged_glb.stat().st_size / 1e6)
    start = time.time()

    cmd = [
        str(BLENDER),
        "--background",
        "--python", str(ANIMATE_SCRIPT),
        "--",
        str(rigged_glb),
        str(animated_tmp),
    ]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=120,
        )

        if result.returncode != 0:
            logger.error("  FAILED (exit %d)", result.returncode)
            # Show last few lines of stderr
            if result.stderr:
                for line in result.stderr.strip().split("\n")[-5:]:
                    logger.error("    %s", line)
            # Also check stdout for Python errors
            if result.stdout:
                for line in result.stdout.strip().split("\n")[-5:]:
                    if "ERROR" in line or "Traceback" in line:
                        logger.error("    %s", line)
            return {"model": model_id, "status": "failed", "error": "blender_exit"}

        if not animated_tmp.exists():
            logger.error("  Blender produced no output at %s", animated_tmp)
            return {"model": model_id, "status": "failed", "error": "no_output"}

        # Back up the rigged GLB and replace with animated version
        backup = rigged_glb.parent / f"{model_id}_rigged_preanim.glb"
        if not backup.exists():
            shutil.copy2(rigged_glb, backup)

        shutil.move(str(animated_tmp), str(rigged_glb))


        elapsed = time.time() - start
        size_mb = rigged_glb.stat().st_size / 1e6
        logger.info("  DONE in %.1fs — %s (%.1f MB)", elapsed, rigged_glb, size_mb)

        return {
            "model": model_id,
            "status": "animated",
            "path": str(rigged_glb),
            "elapsed": round(elapsed, 1),
            "size_mb": round(size_mb, 1),
        }

    except subprocess.TimeoutExpired:
        logger.error("  TIMEOUT after 120s")
        return {"model": model_id, "status": "failed", "error": "timeout"}
    except Exception as e:
        logger.error("  EXCEPTION: %s", e)
        return {"model": model_id, "status": "failed", "error": str(e)}
    finally:
        # Clean up temp file if it still exists
        if animated_tmp.exists():
            try:
                animated_tmp.unlink()
            except Exception:
                pass


def main():
    parser = argparse.ArgumentParser(description="Batch-animate UniRig-rigged models")
    parser.add_argument("--asset-type", choices=["characters", "creatures", "all"],
                        default="all", help="Which models to animate")
    parser.add_argument("--model", type=str, default=None,
                        help="Animate only this model ID")
    parser.add_argument("--dry-run", action="store_true",
                        help="Show what would be animated without running")
    args = parser.parse_args()

    # Verify dependencies
    if not BLENDER.exists():
        logger.error("Blender not found at %s", BLENDER)
        sys.exit(1)
    if not ANIMATE_SCRIPT.exists():
        logger.error("animate_unirig.py not found at %s", ANIMATE_SCRIPT)
        sys.exit(1)

    # Find rigged GLBs
    glbs = find_rigged_glbs(args.asset_type)
    if args.model:
        glbs = [(mid, path) for mid, path in glbs if mid == args.model]

    if not glbs:
        logger.error("No rigged GLBs found for asset-type=%s model=%s", args.asset_type, args.model)
        sys.exit(1)

    logger.info("=" * 60)
    logger.info("Batch Animate UniRig Models (6 procedural animations)")
    logger.info("Models to animate: %d", len(glbs))
    logger.info("Asset type: %s", args.asset_type)
    logger.info("=" * 60)

    results = []
    total_start = time.time()

    for i, (model_id, glb_path) in enumerate(glbs, 1):
        logger.info("")
        logger.info("[%d/%d] %s", i, len(glbs), model_id)
        result = animate_single(model_id, glb_path, dry_run=args.dry_run)
        results.append(result)

    elapsed = time.time() - total_start
    animated = sum(1 for r in results if r["status"] == "animated")
    failed = sum(1 for r in results if r["status"] == "failed")

    logger.info("")
    logger.info("=" * 60)
    logger.info("COMPLETE — %d animated, %d failed in %.1fs", animated, failed, elapsed)
    logger.info("=" * 60)

    if failed > 0:
        logger.info("Failed models:")
        for r in results:
            if r["status"] == "failed":
                logger.info("  %s (%s)", r["model"], r.get("error", "?"))


if __name__ == "__main__":
    main()
