"""Regenerate non-full-body character concept art with explicit full-body framing.

Targets 16 characters (5 classes + 11 NPCs) that were originally generated with
bust/upper-body/3-4 framing. Uses raw urllib to talk to ComfyUI directly.

Usage:
    python regen_fullbody.py [--dry-run] [--character ID]
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
PROMPTS_FILE = TOOLCHAIN_ROOT / "workflows" / "berserkr" / "character_prompts.json"
GODOT_PROJECT = Path("D:/Projects/berserkr-godot")
OUTPUT_BASE = GODOT_PROJECT / "games" / "berserkr" / "assets" / "sprites" / "characters" / "concepts"

# Characters that need full-body regeneration
REGEN_CLASSES = ["skald", "valkyrie", "shield_thane", "raider", "vanir_warden"]
REGEN_NPCS = [
    "mysterious_stranger", "drunk_warrior", "merchant", "skald_npc",
    "smithy_apprentice", "farm_survivor", "gate_guard", "hirdman_guard",
    "innkeeper_helga", "jarl_erik", "temple_acolyte",
]
REGEN_IDS = set(REGEN_CLASSES + REGEN_NPCS)

# Color accent mapping
COLOR_ACCENTS = {
    "berserkr": "deep crimson red and burning amber orange",
    "valkyrie": "cold blue-white and pale silver",
    "vanir_warden": "deep forest black and amber",
    "skald": "warm amber and honey gold",
    "runecaster": "cold blue and pale silver",
    "shield_thane": "deep crimson red and burning amber orange",
    "raider": "deep violet and rust orange",
    "hunter": "deep violet and rust orange",
    "seer": "cold blue and pale silver",
    "thrall_risen": "deep violet and rust orange",
    "innkeeper_helga": "warm amber and honey gold",
    "mysterious_stranger": "single icy blue-white",
    "drunk_warrior": "deep crimson red and burning amber orange",
    "gate_guard": "warm amber and honey gold",
    "merchant": "deep violet and rust orange",
    "jarl_erik": "deep crimson red and burning amber orange",
    "thorvald_smith": "deep crimson red and burning amber orange",
    "volva_sigrid": "cold blue and pale silver",
    "skald_npc": "warm amber and honey gold",
    "hirdman_guard": "deep crimson red and burning amber orange",
    "astrid_missing": "warm amber and honey gold",
    "smithy_apprentice": "warm amber and honey gold",
    "temple_acolyte": "forest green and gold",
    "farm_survivor": "warm amber and honey gold",
}

STYLE_PREFIX = (
    "Frank Miller Sin City meets Frank Frazetta 1970s fantasy art, "
    "{subject}, "
    "HEAVY BLACK INK illustration style, extreme high contrast black and white "
    "with selective bold color accents of {color_accent}, "
    "stark dramatic noir shadows and silhouettes, thick aggressive ink brushstrokes "
    "and splatter, Frank Miller comic panel composition, pulp magazine cover art, "
    "deep chiaroscuro with pools of pure black shadow, gritty noir atmosphere, "
    "psychedelic lurid color bleeding through the black ink darkness, "
    "raw expressive linework, graphic novel aesthetic, visible ink texture and "
    "cross-hatching, romanticism meets noir, epic swords-and-sorcery mood, "
    "NOT photorealistic NOT smooth NOT digital NOT 3d render"
)

NEGATIVE_PROMPT = (
    "photorealistic, digital art, 3d render, smooth, airbrushed, modern, clean, "
    "minimalist, flat, anime, cartoon, chibi, watermark, text, signature, blurry, "
    "low quality, deformed hands, extra fingers, soft lighting, pastel colors, cute, "
    "gentle, cropped, partial body, bust only, portrait crop, cut off at waist, "
    "cut off at knees, missing feet, missing legs, headshot only, upper body only"
)


def seed_for_name(name: str) -> int:
    return int(hashlib.md5(name.encode()).hexdigest()[:8], 16)


def build_fullbody_prompt(character: dict) -> str:
    color_accent = COLOR_ACCENTS.get(character["id"], "deep crimson red and burning amber orange")
    # Filter out weapon/equipment references (T-pose = empty hands)
    weapon_keywords = {"staff", "shield", "axe", "seax", "bow", "spear", "sword", "weapon", "dual-wield"}
    identity_features = [
        feat for feat in character.get("identity_features", [])
        if not any(kw in feat.lower() for kw in weapon_keywords)
    ]
    identity = ", ".join(identity_features)
    subject = (
        f"FULL BODY character illustration of {character['name']}, {identity}, "
        f"standing in T-pose arms extended straight out to sides at shoulder height palms facing down, "
        f"legs slightly apart, hands open and empty, no weapons no shields no staffs, "
        f"symmetrical front-facing view, full body visible from head to feet including boots, "
        f"NOT cropped NOT cut off, plain white background, isolated character on white, "
        f"no background elements no scenery, character design reference sheet style"
    )
    return STYLE_PREFIX.format(subject=subject, color_accent=color_accent)


def build_workflow(prompt: str, seed: int, filename_prefix: str) -> dict:
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
            "inputs": {"text": prompt, "clip": ["1", 1]},
            "class_type": "CLIPTextEncode",
        },
        "4": {
            "inputs": {"text": NEGATIVE_PROMPT, "clip": ["1", 1]},
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


def main():
    parser = argparse.ArgumentParser(description="Regenerate non-full-body character concepts")
    parser.add_argument("--dry-run", action="store_true", help="Print prompts, don't generate")
    parser.add_argument("--character", type=str, default=None, help="Regenerate only this character ID")
    args = parser.parse_args()

    if not args.dry_run and not check_comfyui():
        logger.error("ComfyUI is not running at %s", COMFYUI_URL)
        sys.exit(1)

    # Load character data
    with open(PROMPTS_FILE) as f:
        prompts_data = json.load(f)

    characters = prompts_data.get("characters", [])

    # Filter to only characters needing regen
    if args.character:
        targets = [c for c in characters if c["id"] == args.character]
    else:
        targets = [c for c in characters if c["id"] in REGEN_IDS]

    logger.info("Regenerating %d characters with full-body framing", len(targets))

    # Back up existing images
    backup_dir = OUTPUT_BASE / "_backup_pre_fullbody"
    backup_dir.mkdir(parents=True, exist_ok=True)

    converted = 0
    failed = 0
    skipped = 0
    start_time = time.time()

    for i, char in enumerate(targets, 1):
        char_type = "classes" if char["type"] == "class" else "npcs"
        output_path = OUTPUT_BASE / char_type / f"{char['id']}.png"

        logger.info("[%d/%d] %s (%s)", i, len(targets), char["name"], char["id"])

        # Back up existing
        if output_path.exists():
            backup_path = backup_dir / char_type / f"{char['id']}.png"
            backup_path.parent.mkdir(parents=True, exist_ok=True)
            if not backup_path.exists():
                shutil.copy2(output_path, backup_path)
                logger.info("  Backed up existing to %s", backup_path)

        prompt = build_fullbody_prompt(char)
        seed = seed_for_name(char["name"]) + 5000  # Seed offset for T-pose full-body regen

        if args.dry_run:
            logger.info("  DRY RUN — prompt: %s...", prompt[:150])
            logger.info("  Seed: %d, Output: %s", seed, output_path)
            skipped += 1
            continue

        workflow = build_workflow(prompt, seed, f"Berserkr_Fullbody_{char['id']}")

        try:
            prompt_id = queue_prompt(workflow)
            logger.info("  Queued: %s", prompt_id[:11])

            history = poll_history(prompt_id)
            if history and download_image(history, output_path):
                converted += 1
            else:
                logger.error("  FAILED: %s", char["id"])
                failed += 1
        except Exception as e:
            logger.error("  FAILED: %s — %s", char["id"], e)
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
        logger.info("Backups saved to: %s", backup_dir)


if __name__ == "__main__":
    main()
