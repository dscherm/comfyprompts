"""Regenerate Valkyrie and Vanir Warden full-body concept art.

Targeted regen with corrected color accents for Frank Miller Sin City noir style.
Uses raw urllib to talk to ComfyUI directly (no SDK needed).

Usage:
    python regen_valkyrie_vanir.py [--dry-run]
"""

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
GODOT_PROJECT = Path("D:/Projects/berserkr-godot")
OUTPUT_DIR = GODOT_PROJECT / "games" / "berserkr" / "assets" / "sprites" / "characters" / "concepts" / "classes"
BACKUP_DIR = OUTPUT_DIR / "_backup_pre_regen_v2"

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
    "cut off at knees, missing feet, missing legs, headshot only, upper body only, "
    "green tint, oversaturated colors, too colorful, World of Warcraft style"
)

# Two characters to regenerate with corrected noir-appropriate color accents
CHARACTERS = [
    {
        "id": "valkyrie",
        "name": "Valkyrie",
        "identity_features": [
            "golden blonde braided hair with silver clasps",
            "ice-blue eyes",
            "polished chainmail armor",
            "swan-feather cloak",
            "gold circlet on brow",
            "noble regal bearing",
        ],
        # Changed from "forest green and gold" to noir-appropriate palette
        "color_accent": "cold icy blue-white and pale silver",
    },
    {
        "id": "vanir_warden",
        "name": "Vanir Warden",
        "identity_features": [
            "long auburn hair woven with ivy",
            "gentle green eyes",
            "leather armor with leaf and bark motifs",
            "mistletoe crown",
            "moss-stained hands",
        ],
        # Changed from "forest green and gold" to noir-appropriate palette
        "color_accent": "deep forest black-green and warm amber",
    },
]


def seed_for_name(name: str) -> int:
    return int(hashlib.md5(name.encode()).hexdigest()[:8], 16)


def build_fullbody_prompt(character: dict) -> str:
    identity = ", ".join(character["identity_features"])
    subject = (
        f"FULL BODY character illustration of {character['name']}, {identity}, "
        f"standing in a T-pose arms extended straight out to sides at shoulder height "
        f"palms facing down, legs slightly apart, hands open and empty, "
        f"no weapons no shields no staffs, "
        f"FULL BODY FROM HEAD TO FEET visible, feet touching ground, "
        f"complete figure shown from top of head to bottom of boots, "
        f"full-length character design reference sheet style, "
        f"plain white background, isolated character on white, "
        f"no background elements no scenery, Norse fantasy setting"
    )
    return STYLE_PREFIX.format(subject=subject, color_accent=character["color_accent"])


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
    import argparse
    parser = argparse.ArgumentParser(description="Regenerate Valkyrie and Vanir Warden concept art")
    parser.add_argument("--dry-run", action="store_true", help="Print prompts, don't generate")
    args = parser.parse_args()

    if not args.dry_run and not check_comfyui():
        logger.error("ComfyUI is not running at %s", COMFYUI_URL)
        sys.exit(1)

    # Create backup directory
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)

    converted = 0
    failed = 0
    start_time = time.time()

    for i, char in enumerate(CHARACTERS, 1):
        output_path = OUTPUT_DIR / f"{char['id']}.png"
        logger.info("[%d/%d] %s (%s)", i, len(CHARACTERS), char["name"], char["id"])

        prompt = build_fullbody_prompt(char)
        # Use a new seed offset (4000) distinct from previous regen attempts
        seed = seed_for_name(char["name"]) + 4000

        if args.dry_run:
            logger.info("  DRY RUN")
            logger.info("  Prompt: %s", prompt[:300])
            logger.info("  Seed: %d", seed)
            logger.info("  Output: %s", output_path)
            logger.info("  Color accent: %s", char["color_accent"])
            continue

        # Back up existing before generating
        if output_path.exists():
            backup_path = BACKUP_DIR / f"{char['id']}.png"
            if not backup_path.exists():
                shutil.copy2(output_path, backup_path)
                logger.info("  Backed up existing to %s", backup_path)
            # Remove existing so we generate fresh
            output_path.unlink()
            logger.info("  Removed existing %s", output_path.name)

        workflow = build_workflow(prompt, seed, f"Berserkr_Fullbody_v2_{char['id']}")

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
            logger.error("  FAILED: %s -- %s", char["id"], e)
            failed += 1

        # Brief delay between generations
        if i < len(CHARACTERS):
            time.sleep(2)

    elapsed = time.time() - start_time
    logger.info("")
    logger.info("=" * 60)
    logger.info("COMPLETE -- %d regenerated, %d failed in %.1fs", converted, failed, elapsed)
    logger.info("=" * 60)

    if not args.dry_run and converted > 0:
        logger.info("Backups saved to: %s", BACKUP_DIR)
        logger.info("New concept art at: %s", OUTPUT_DIR)


if __name__ == "__main__":
    main()
