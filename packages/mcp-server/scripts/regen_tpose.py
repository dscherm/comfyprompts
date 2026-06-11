"""Regenerate T-pose concept art for all 34 Mixamo-targetable models.

Covers all 24 characters (10 classes + 14 NPCs) and 10 humanoid creatures.
Uses raw urllib to talk to ComfyUI directly (no SDK dependency).
Prompts are read directly from character_prompts.json and creature_prompts.json.

Usage:
    python regen_tpose.py [--dry-run] [--character ID] [--type {characters,creatures,all}] [--force]
"""

import argparse
import hashlib
import json
import logging
import os
import shutil
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

COMFYUI_URL = "http://127.0.0.1:8188"
TOOLCHAIN_ROOT = Path(__file__).resolve().parent.parent.parent.parent
CHARACTER_PROMPTS_FILE = TOOLCHAIN_ROOT / "workflows" / "berserkr" / "character_prompts.json"
CREATURE_PROMPTS_FILE = TOOLCHAIN_ROOT / "workflows" / "berserkr" / "creature_prompts.json"
GODOT_PROJECT = Path("D:/Projects/berserkr-godot")
CHARACTER_OUTPUT_BASE = GODOT_PROJECT / "games" / "berserkr" / "assets" / "sprites" / "characters" / "concepts"
CREATURE_OUTPUT_BASE = GODOT_PROJECT / "games" / "berserkr" / "assets" / "sprites" / "creatures"

# Only these humanoid creatures get T-pose art (the ones targetable by Mixamo)
HUMANOID_CREATURE_IDS = {
    "trollkin", "draugr", "barrow_wight", "huldra", "frost_giant",
    "ice_troll", "hel_walker", "fire_giant", "dark_elf", "duergar",
}


def seed_for_name(name: str) -> int:
    return int(hashlib.md5(name.encode()).hexdigest()[:8], 16) + 5000


def build_workflow(positive_prompt: str, negative_prompt: str, seed: int, filename_prefix: str) -> dict:
    return {
        "1": {
            "inputs": {"ckpt_name": "flux1-dev-fp8.safetensors"},
            "class_type": "CheckpointLoaderSimple",
        },
        "2": {
            "inputs": {"width": 528, "height": 528, "batch_size": 1},
            "class_type": "EmptySD3LatentImage",
        },
        "3": {
            "inputs": {"text": positive_prompt, "clip": ["1", 1]},
            "class_type": "CLIPTextEncode",
        },
        "4": {
            "inputs": {"text": negative_prompt, "clip": ["1", 1]},
            "class_type": "CLIPTextEncode",
        },
        "5": {
            "inputs": {
                "seed": seed,
                "steps": 25,
                "cfg": 1.0,
                "sampler_name": "euler",
                "scheduler": "simple",
                "denoise": 1.0,
                "model": ["1", 0],
                "positive": ["3", 0],
                "negative": ["4", 0],
                "latent_image": ["2", 0],
            },
            "class_type": "KSampler",
        },
        "6": {
            "inputs": {"samples": ["5", 0], "vae": ["1", 2]},
            "class_type": "VAEDecode",
        },
        "7": {
            "inputs": {"filename_prefix": filename_prefix, "images": ["6", 0]},
            "class_type": "SaveImage",
        },
    }


def queue_prompt(workflow: dict) -> str:
    payload = json.dumps({"prompt": workflow}).encode()
    req = urllib.request.Request(
        f"{COMFYUI_URL}/prompt",
        data=payload,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read())
    return data["prompt_id"]


def poll_history(prompt_id: str, timeout: int = 300, interval: int = 5) -> dict | None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(f"{COMFYUI_URL}/history/{prompt_id}", timeout=10) as resp:
                data = json.loads(resp.read())
            if prompt_id in data:
                entry = data[prompt_id]
                status = entry.get("status", {})
                if status.get("status_str") == "success" or status.get("completed", False):
                    return entry
                if status.get("status_str") == "error":
                    logger.error("  Workflow error: %s", status)
                    return None
        except Exception:
            pass
        time.sleep(interval)
    logger.error("  Timed out waiting for workflow %s", prompt_id)
    return None


def download_image(history_entry: dict, output_path: Path) -> bool:
    outputs = history_entry.get("outputs", {})
    for node_id, node_out in outputs.items():
        images = node_out.get("images", [])
        for img in images:
            filename = img.get("filename", "")
            subfolder = img.get("subfolder", "")
            img_type = img.get("type", "output")
            url = f"{COMFYUI_URL}/view?filename={filename}&subfolder={subfolder}&type={img_type}"
            try:
                with urllib.request.urlopen(url, timeout=30) as resp:
                    output_path.parent.mkdir(parents=True, exist_ok=True)
                    with open(output_path, "wb") as f:
                        f.write(resp.read())
                    size_kb = output_path.stat().st_size // 1024
                    logger.info("  Saved: %s (%d KB)", output_path.name, size_kb)
                    return True
            except Exception as e:
                logger.error("  Download failed: %s", e)
    return False


def check_comfyui() -> bool:
    try:
        with urllib.request.urlopen(f"{COMFYUI_URL}/system_stats", timeout=5) as resp:
            return resp.status == 200
    except Exception:
        return False


def load_character_targets(filter_id: str | None) -> list[dict]:
    """Load all 24 characters from character_prompts.json."""
    with open(CHARACTER_PROMPTS_FILE) as f:
        data = json.load(f)

    characters = data.get("characters", [])
    targets = []
    for char in characters:
        char_type = "classes" if char["type"] == "class" else "npcs"
        output_path = CHARACTER_OUTPUT_BASE / char_type / f"{char['id']}.png"
        backup_dir = CHARACTER_OUTPUT_BASE / char_type / "_backup_pre_tpose"
        targets.append({
            "id": char["id"],
            "name": char["name"],
            "kind": "Character",
            "positive_prompt": char["positive_prompt"],
            "negative_prompt": char["negative_prompt"],
            "output_path": output_path,
            "backup_dir": backup_dir,
        })

    if filter_id:
        targets = [t for t in targets if t["id"] == filter_id]

    return targets


def load_creature_targets(filter_id: str | None) -> list[dict]:
    """Load 10 humanoid creatures from creature_prompts.json."""
    with open(CREATURE_PROMPTS_FILE) as f:
        data = json.load(f)

    creatures = data.get("creatures", [])
    targets = []
    for creature in creatures:
        if creature["id"] not in HUMANOID_CREATURE_IDS:
            continue
        realm = creature.get("realm", "midgard")
        output_path = CREATURE_OUTPUT_BASE / realm / f"{creature['id']}.png"
        backup_dir = CREATURE_OUTPUT_BASE / realm / "_backup_pre_tpose"
        targets.append({
            "id": creature["id"],
            "name": creature["name"],
            "kind": "Creature",
            "positive_prompt": creature["positive_prompt"],
            "negative_prompt": creature["negative_prompt"],
            "output_path": output_path,
            "backup_dir": backup_dir,
        })

    if filter_id:
        targets = [t for t in targets if t["id"] == filter_id]

    return targets


def main():
    parser = argparse.ArgumentParser(description="Regenerate T-pose concept art for Mixamo-targetable models")
    parser.add_argument("--dry-run", action="store_true", help="Print prompts, don't generate")
    parser.add_argument("--character", type=str, default=None, help="Generate only this character/creature ID")
    parser.add_argument("--type", type=str, choices=["characters", "creatures", "all"], default="all",
                        help="Filter by type (default: all)")
    parser.add_argument("--force", action="store_true", help="Overwrite existing (default behavior for this script)")
    args = parser.parse_args()

    if not args.dry_run and not check_comfyui():
        logger.error("ComfyUI is not running at %s", COMFYUI_URL)
        sys.exit(1)

    # Build target list based on --type filter
    targets = []
    if args.type in ("characters", "all"):
        targets.extend(load_character_targets(args.character))
    if args.type in ("creatures", "all"):
        targets.extend(load_creature_targets(args.character))

    if not targets:
        logger.error("No targets found (filter: --character=%s --type=%s)", args.character, args.type)
        sys.exit(1)

    logger.info("Regenerating T-pose art for %d models", len(targets))

    converted = 0
    failed = 0
    skipped = 0
    start_time = time.time()

    for i, target in enumerate(targets, 1):
        logger.info("[%d/%d] %s: %s (%s)", i, len(targets), target["kind"], target["name"], target["id"])

        # Back up existing image
        output_path = target["output_path"]
        if output_path.exists():
            backup_dir = target["backup_dir"]
            backup_dir.mkdir(parents=True, exist_ok=True)
            backup_path = backup_dir / f"{target['id']}.png"
            if not backup_path.exists():
                shutil.copy2(output_path, backup_path)
                logger.info("  Backed up existing to %s", backup_path)

        seed = seed_for_name(target["name"])

        if args.dry_run:
            logger.info("  DRY RUN — prompt: %s...", target["positive_prompt"][:150])
            logger.info("  Seed: %d, Output: %s", seed, output_path)
            skipped += 1
            continue

        workflow = build_workflow(
            target["positive_prompt"],
            target["negative_prompt"],
            seed,
            f"Berserkr_TPose_{target['id']}",
        )

        try:
            prompt_id = queue_prompt(workflow)
            logger.info("  Queued: %s", prompt_id[:11])

            history = poll_history(prompt_id)
            if history and download_image(history, output_path):
                converted += 1
            else:
                logger.error("  FAILED: %s", target["id"])
                failed += 1
        except Exception as e:
            logger.error("  FAILED: %s — %s", target["id"], e)
            failed += 1

        # Brief delay between generations
        if i < len(targets):
            time.sleep(2)

    elapsed = time.time() - start_time
    logger.info("")
    logger.info("=" * 60)
    logger.info("COMPLETE — %d regenerated, %d failed, %d skipped in %.1fs",
                converted, failed, skipped, elapsed)
    logger.info("=" * 60)

    if not args.dry_run and converted > 0:
        logger.info("Backups saved to _backup_pre_tpose/ subdirectories")


if __name__ == "__main__":
    main()
