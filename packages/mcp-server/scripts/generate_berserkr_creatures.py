"""Batch creature art generator for the Berserkr game.

Reads creature_prompts.json and generates creature illustrations through
the ComfyUI API using the Berserkr chargen portrait workflow as a base.

Usage:
    python generate_berserkr_creatures.py [--creature ID] [--dry-run]
"""

import argparse
import hashlib
import json
import logging
import os
import sys
import time
from pathlib import Path

# Add SDK to path if running standalone
SDK_PATH = Path(__file__).resolve().parent.parent.parent / "sdk" / "src"
if SDK_PATH.exists():
    sys.path.insert(0, str(SDK_PATH))

from comfyui_agent_sdk.client.comfyui_client import ComfyUIClient
from comfyui_agent_sdk.config import ComfyUIConfig

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# Humanoid creatures that need Mixamo rigging — generate in T-pose
HUMANOID_CREATURE_IDS = {
    "trollkin", "draugr", "barrow_wight", "huldra", "frost_giant",
    "ice_troll", "dark_elf", "duergar", "hel_walker", "fire_giant",
}

# --- Paths ---
TOOLCHAIN_ROOT = Path(__file__).resolve().parent.parent.parent.parent
WORKFLOWS_DIR = TOOLCHAIN_ROOT / "workflows" / "mcp"
PROMPTS_FILE = TOOLCHAIN_ROOT / "workflows" / "berserkr" / "creature_prompts.json"
GODOT_PROJECT = Path("D:/Projects/berserkr-godot")
OUTPUT_BASE = GODOT_PROJECT / "games" / "berserkr" / "assets" / "sprites" / "creatures"
MANIFEST_FILE = OUTPUT_BASE / "generation_manifest.json"


def seed_for_name(name: str) -> int:
    """Deterministic seed from creature name for reproducibility."""
    return int(hashlib.md5(name.encode()).hexdigest()[:8], 16)


def load_workflow(workflow_name: str) -> dict:
    """Load a workflow JSON from the workflows/mcp directory."""
    path = WORKFLOWS_DIR / f"{workflow_name}.json"
    with open(path) as f:
        return json.load(f)


def _build_tpose_creature_prompt(creature: dict) -> str:
    """Build a T-pose prompt for humanoid creatures that need Mixamo rigging.

    Uses the creature's identity_features for visual description instead of
    the action-pose positive_prompt. Combined with the standard art style
    and T-pose instructions for clean auto-rigging.
    """
    # Filter out weapon/equipment references from identity features (T-pose = empty hands)
    weapon_keywords = {"staff", "shield", "axe", "seax", "bow", "spear", "sword", "weapon",
                        "dual-wield", "blade", "club", "pick", "war pick"}
    identity_features = [
        feat for feat in creature.get("identity_features", [])
        if not any(kw in feat.lower() for kw in weapon_keywords)
    ]
    identity = ", ".join(identity_features)
    palette = creature.get("color_palette", [])
    color = palette[1] if len(palette) > 1 else "ink black"

    subject = (
        f"full body character illustration of {creature['name']}, {identity}, "
        f"standing in T-pose arms extended straight out to sides at shoulder height palms facing down, "
        f"legs slightly apart, hands open and empty, no weapons no shields no staffs, "
        f"symmetrical front-facing view, full body visible from head to feet, "
        f"NOT cropped NOT cut off, plain white background, isolated character on white, "
        f"no background elements no scenery, character design reference sheet style"
    )

    return (
        f"Frank Miller Sin City meets Frank Frazetta 1970s fantasy art, "
        f"{subject}, "
        f"HEAVY BLACK INK illustration style, extreme high contrast black and white "
        f"with selective bold color accents of {color}, "
        f"stark dramatic noir shadows and silhouettes, thick aggressive ink brushstrokes "
        f"and splatter, deep chiaroscuro with pools of pure black shadow, "
        f"gritty noir atmosphere, raw expressive linework, graphic novel aesthetic, "
        f"visible ink texture and cross-hatching, "
        f"NOT photorealistic NOT smooth NOT digital NOT 3d render"
    )


def build_creature_workflow(creature: dict, seed: int) -> dict:
    """Build a creature illustration workflow.

    Uses the portrait workflow as base but at 528x528 for creature art.
    Humanoid creatures get a T-pose prompt override for Mixamo rigging;
    non-humanoid creatures use the original positive_prompt unchanged.
    """
    workflow = load_workflow("berserkr_chargen_portrait")

    # Humanoid creatures need T-pose for Mixamo auto-rigging
    if creature["id"] in HUMANOID_CREATURE_IDS:
        prompt = _build_tpose_creature_prompt(creature)
    else:
        prompt = creature["positive_prompt"]

    workflow["2"]["inputs"]["width"] = 528
    workflow["2"]["inputs"]["height"] = 528
    workflow["3"]["inputs"]["text"] = prompt
    workflow["4"]["inputs"]["text"] = creature["negative_prompt"]
    workflow["5"]["inputs"]["seed"] = seed
    workflow["7"]["inputs"]["filename_prefix"] = f"Berserkr_Creature_{creature['id']}"
    return workflow


def get_output_path(creature: dict) -> Path:
    """Determine the output path for a generated creature image."""
    realm = creature.get("realm", "midgard")
    filename = f"{creature['id']}.png"
    return OUTPUT_BASE / realm / filename


def ensure_output_dirs(creatures: list[dict]):
    """Create the output directory structure organized by realm."""
    realms = set(c.get("realm", "midgard") for c in creatures)
    for realm in realms:
        (OUTPUT_BASE / realm).mkdir(parents=True, exist_ok=True)


def generate_single(
    client: ComfyUIClient,
    creature: dict,
    dry_run: bool = False,
) -> dict | None:
    """Generate a single creature image."""
    output_path = get_output_path(creature)

    if output_path.exists():
        logger.info("SKIP %s — already exists at %s", creature["name"], output_path)
        return {"creature": creature["id"], "path": str(output_path), "status": "skipped"}

    seed = seed_for_name(creature["name"])
    workflow = build_creature_workflow(creature, seed)

    if dry_run:
        prompt_text = workflow["3"]["inputs"]["text"]
        logger.info("DRY RUN — %s%s", creature["name"],
                     " [T-POSE OVERRIDE]" if creature["id"] in HUMANOID_CREATURE_IDS else "")
        logger.info("  Prompt: %s", prompt_text[:200] + "...")
        logger.info("  Seed: %s", seed)
        logger.info("  Output: %s", output_path)
        return {"creature": creature["id"], "path": str(output_path), "status": "dry_run"}

    logger.info("GENERATE %s [%s/%s] (seed=%d)",
                creature["name"], creature.get("realm", "?"),
                creature.get("creature_type", "?"), seed)

    try:
        result = client.run_custom_workflow(workflow, max_attempts=120)
        asset_url = result.get("asset_url", "")

        if asset_url:
            import requests
            img_response = requests.get(asset_url, timeout=30)
            if img_response.status_code == 200:
                output_path.parent.mkdir(parents=True, exist_ok=True)
                with open(output_path, "wb") as f:
                    f.write(img_response.content)
                logger.info("  Saved to %s", output_path)
                return {
                    "creature": creature["id"],
                    "path": str(output_path),
                    "seed": seed,
                    "prompt_id": result.get("prompt_id"),
                    "status": "generated",
                }
            else:
                logger.error("  Failed to download image: HTTP %d", img_response.status_code)
        else:
            logger.error("  No asset_url in result: %s", result)

    except Exception as e:
        logger.error("  Generation failed for %s: %s", creature["name"], e)

    return {"creature": creature["id"], "path": str(output_path), "status": "failed"}


def main():
    parser = argparse.ArgumentParser(description="Batch generate Berserkr creature art")
    parser.add_argument("--creature", type=str, default=None,
                        help="Generate only this creature ID (e.g., 'draugr', 'frost_giant')")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print prompts without generating")
    parser.add_argument("--comfyui-url", type=str, default=None,
                        help="ComfyUI server URL (default: http://localhost:8188)")
    args = parser.parse_args()

    if not PROMPTS_FILE.exists():
        logger.error("creature_prompts.json not found at %s", PROMPTS_FILE)
        sys.exit(1)

    with open(PROMPTS_FILE) as f:
        prompts_data = json.load(f)

    creatures = prompts_data.get("creatures", [])
    logger.info("Loaded %d creatures from %s", len(creatures), PROMPTS_FILE)

    # Verify workflow exists
    wf_path = WORKFLOWS_DIR / "berserkr_chargen_portrait.json"
    if not wf_path.exists():
        logger.error("Workflow not found: %s", wf_path)
        sys.exit(1)

    ensure_output_dirs(creatures)

    # Connect to ComfyUI
    client = None
    if not args.dry_run:
        config = ComfyUIConfig()
        if args.comfyui_url:
            client = ComfyUIClient(config, base_url=args.comfyui_url)
        else:
            client = ComfyUIClient(config)

        if not client.is_available():
            logger.error("ComfyUI is not available at %s", client.base_url)
            sys.exit(1)

        conn = client.check_connection()
        vram_total = conn.get("vram_total", 0)
        vram_free = conn.get("vram_free", 0)
        logger.info("Connected to ComfyUI — VRAM: %.1f GB total, %.1f GB free",
                     vram_total / (1024**3) if vram_total else 0,
                     vram_free / (1024**3) if vram_free else 0)

    # Generate
    all_entries = []
    total_start = time.time()

    logger.info("=" * 60)
    logger.info("Generating %d creature illustrations", len(creatures))
    logger.info("=" * 60)

    for creature in creatures:
        if args.creature and creature["id"] != args.creature:
            continue

        entry = generate_single(client, creature, dry_run=args.dry_run)
        if entry:
            all_entries.append(entry)

        if not args.dry_run and entry and entry.get("status") == "generated":
            time.sleep(2)

    elapsed = time.time() - total_start

    # Write manifest
    if not args.dry_run and all_entries:
        manifest = {
            "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "total_elapsed_seconds": round(elapsed, 1),
            "entries": all_entries,
        }
        with open(MANIFEST_FILE, "w") as f:
            json.dump(manifest, f, indent=2)
        logger.info("Manifest written to %s", MANIFEST_FILE)

    total_generated = sum(1 for e in all_entries if e.get("status") == "generated")
    total_skipped = sum(1 for e in all_entries if e.get("status") == "skipped")
    total_failed = sum(1 for e in all_entries if e.get("status") == "failed")
    logger.info("")
    logger.info("=" * 60)
    logger.info("COMPLETE — %d generated, %d skipped, %d failed in %.1fs",
                 total_generated, total_skipped, total_failed, elapsed)
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
