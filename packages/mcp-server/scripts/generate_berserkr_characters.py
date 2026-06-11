"""Batch character art generator for the Berserkr game.

Reads character_prompts.json and game data, then generates portraits, full-body
concepts, and class cards through the ComfyUI API using the Berserkr chargen
workflows.

Usage:
    python generate_berserkr_characters.py [--phase PHASE] [--character ID] [--dry-run]

Phases:
    1 - NPC dialogue portraits (512x512)
    2 - Class selection cards (528x528)
    3 - Full-body concepts (528x528)
    all - Run all phases (default)

Examples:
    python generate_berserkr_characters.py                         # Generate everything
    python generate_berserkr_characters.py --phase 1               # NPC portraits only
    python generate_berserkr_characters.py --character grimr       # Single character
    python generate_berserkr_characters.py --dry-run               # Print prompts, don't generate
"""

import argparse
import copy
import hashlib
import json
import logging
import os
import shutil
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

# --- Paths ---
TOOLCHAIN_ROOT = Path(__file__).resolve().parent.parent.parent.parent
WORKFLOWS_DIR = TOOLCHAIN_ROOT / "workflows" / "mcp"
PROMPTS_FILE = TOOLCHAIN_ROOT / "workflows" / "berserkr" / "character_prompts.json"
GODOT_PROJECT = Path("D:/Projects/berserkr-godot")
OUTPUT_BASE = GODOT_PROJECT / "games" / "berserkr" / "assets" / "sprites" / "characters"
MANIFEST_FILE = OUTPUT_BASE / "generation_manifest.json"

# --- Color accent mapping by character archetype ---
COLOR_ACCENTS = {
    # Classes
    "berserkr": "deep crimson red and burning amber orange",
    "valkyrie": "forest green and gold",
    "vanir_warden": "forest green and gold",
    "skald": "warm amber and honey gold",
    "runecaster": "cold blue and pale silver",
    "shield_thane": "deep crimson red and burning amber orange",
    "raider": "deep violet and rust orange",
    "hunter": "deep violet and rust orange",
    "seer": "cold blue and pale silver",
    "thrall_risen": "deep violet and rust orange",
    # NPCs
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

# --- Berserkr style prompt ---
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


def seed_for_name(name: str) -> int:
    """Deterministic seed from character name for reproducibility."""
    return int(hashlib.md5(name.encode()).hexdigest()[:8], 16)


def load_prompts() -> dict:
    """Load character_prompts.json created by the prompt-engineer."""
    with open(PROMPTS_FILE) as f:
        return json.load(f)


def load_workflow(workflow_name: str) -> dict:
    """Load a workflow JSON from the workflows/mcp directory."""
    path = WORKFLOWS_DIR / f"{workflow_name}.json"
    with open(path) as f:
        return json.load(f)


def build_portrait_workflow(character: dict, seed: int) -> dict:
    """Build a portrait workflow with substituted parameters."""
    workflow = load_workflow("berserkr_chargen_portrait")
    color_accent = COLOR_ACCENTS.get(character["id"], "deep crimson red and burning amber orange")

    # Build subject from the character's positive_prompt identity features
    identity = ", ".join(character.get("identity_features", []))
    subject = f"portrait of {character['name']}, {identity}, bust portrait facing viewer, Norse fantasy setting"

    prompt = STYLE_PREFIX.format(subject=subject, color_accent=color_accent)

    # Substitute parameters into workflow
    workflow["2"]["inputs"]["width"] = 512
    workflow["2"]["inputs"]["height"] = 512
    workflow["3"]["inputs"]["text"] = prompt
    workflow["5"]["inputs"]["seed"] = seed
    workflow["7"]["inputs"]["filename_prefix"] = f"Berserkr_Portrait_{character['id']}"
    return workflow


def build_fullbody_workflow(character: dict, seed: int) -> dict:
    """Build a full-body concept workflow with substituted parameters."""
    workflow = load_workflow("berserkr_chargen_fullbody")
    color_accent = COLOR_ACCENTS.get(character["id"], "deep crimson red and burning amber orange")

    # Filter out weapon/equipment references from identity features (T-pose = empty hands)
    weapon_keywords = {"staff", "shield", "axe", "seax", "bow", "spear", "sword", "weapon", "dual-wield"}
    identity_features = [
        feat for feat in character.get("identity_features", [])
        if not any(kw in feat.lower() for kw in weapon_keywords)
    ]
    identity = ", ".join(identity_features)
    subject = (
        f"full body character illustration of {character['name']}, {identity}, "
        f"standing in T-pose arms extended straight out to sides at shoulder height palms facing down, "
        f"legs slightly apart, hands open and empty, no weapons no shields no staffs, "
        f"symmetrical front-facing view, full body visible from head to feet including boots, "
        f"NOT cropped NOT cut off, plain white background, isolated character on white, "
        f"no background elements no scenery, character design reference sheet style"
    )

    prompt = STYLE_PREFIX.format(subject=subject, color_accent=color_accent)

    workflow["2"]["inputs"]["width"] = 528
    workflow["2"]["inputs"]["height"] = 528
    workflow["3"]["inputs"]["text"] = prompt
    workflow["5"]["inputs"]["seed"] = seed + 1000  # Offset seed for different result
    workflow["7"]["inputs"]["filename_prefix"] = f"Berserkr_Fullbody_{character['id']}"
    return workflow


def build_card_workflow(character: dict, seed: int) -> dict:
    """Build a class card workflow with substituted parameters."""
    workflow = load_workflow("berserkr_chargen_card")
    color_accent = COLOR_ACCENTS.get(character["id"], "deep crimson red and burning amber orange")

    equipment_str = ", ".join(character.get("equipment", [])[:3])
    subject = (
        f"character card illustration of a {character['name']}, "
        f"{character.get('positive_prompt', '').split(', detailed face, ')[-1].split(', background')[0] if ', detailed face, ' in character.get('positive_prompt', '') else character['name']}, "
        f"wielding {equipment_str}, "
        f"ornate Norse knotwork border frame, rune inscriptions along the edges, "
        f"tarot card composition, three-quarter body view heroic pose, Norse fantasy setting"
    )

    prompt = STYLE_PREFIX.format(subject=subject, color_accent=color_accent)

    workflow["2"]["inputs"]["width"] = 528
    workflow["2"]["inputs"]["height"] = 528
    workflow["3"]["inputs"]["text"] = prompt
    workflow["5"]["inputs"]["seed"] = seed + 2000
    workflow["7"]["inputs"]["filename_prefix"] = f"Berserkr_Card_{character['id']}"
    return workflow


def ensure_output_dirs():
    """Create the output directory structure in the Godot project."""
    dirs = [
        OUTPUT_BASE / "portraits" / "classes",
        OUTPUT_BASE / "portraits" / "npcs",
        OUTPUT_BASE / "busts",
        OUTPUT_BASE / "cards",
        OUTPUT_BASE / "concepts" / "classes",
        OUTPUT_BASE / "concepts" / "npcs",
    ]
    for d in dirs:
        d.mkdir(parents=True, exist_ok=True)


def get_output_path(character: dict, phase: str) -> Path:
    """Determine the output path for a generated image."""
    char_type = "classes" if character["type"] == "class" else "npcs"
    filename = f"{character['id']}.png"

    if phase == "portrait":
        return OUTPUT_BASE / "portraits" / char_type / filename
    elif phase == "card":
        return OUTPUT_BASE / "cards" / filename
    elif phase == "fullbody":
        return OUTPUT_BASE / "concepts" / char_type / filename
    return OUTPUT_BASE / filename


def generate_single(
    client: ComfyUIClient,
    character: dict,
    phase: str,
    dry_run: bool = False,
) -> dict | None:
    """Generate a single character image.

    Returns a manifest entry dict on success, None on skip/failure.
    """
    output_path = get_output_path(character, phase)

    # Skip if already generated (resume support)
    if output_path.exists():
        logger.info("SKIP %s %s — already exists at %s", phase, character["name"], output_path)
        return {"character": character["id"], "phase": phase, "path": str(output_path), "status": "skipped"}

    seed = seed_for_name(character["name"])

    if phase == "portrait":
        workflow = build_portrait_workflow(character, seed)
    elif phase == "card":
        workflow = build_card_workflow(character, seed)
    elif phase == "fullbody":
        workflow = build_fullbody_workflow(character, seed)
    else:
        logger.error("Unknown phase: %s", phase)
        return None

    prompt_text = workflow["3"]["inputs"]["text"]

    if dry_run:
        logger.info("DRY RUN — %s %s", phase, character["name"])
        logger.info("  Prompt: %s", prompt_text[:200] + "...")
        logger.info("  Seed: %s", workflow["5"]["inputs"]["seed"])
        logger.info("  Output: %s", output_path)
        return {"character": character["id"], "phase": phase, "path": str(output_path), "status": "dry_run"}

    logger.info("GENERATE %s %s (seed=%d)", phase, character["name"], workflow["5"]["inputs"]["seed"])

    try:
        result = client.run_custom_workflow(workflow, max_attempts=120)
        asset_url = result.get("asset_url", "")
        filename = result.get("filename", "")

        if asset_url:
            # Download the generated image from ComfyUI
            import requests
            img_response = requests.get(asset_url, timeout=30)
            if img_response.status_code == 200:
                output_path.parent.mkdir(parents=True, exist_ok=True)
                with open(output_path, "wb") as f:
                    f.write(img_response.content)
                logger.info("  Saved to %s", output_path)
                return {
                    "character": character["id"],
                    "phase": phase,
                    "path": str(output_path),
                    "seed": workflow["5"]["inputs"]["seed"],
                    "prompt_id": result.get("prompt_id"),
                    "status": "generated",
                }
            else:
                logger.error("  Failed to download image: HTTP %d", img_response.status_code)
        else:
            logger.error("  No asset_url in result: %s", result)

    except Exception as e:
        logger.error("  Generation failed for %s %s: %s", phase, character["name"], e)

    return {"character": character["id"], "phase": phase, "path": str(output_path), "status": "failed"}


def run_phase(
    client: ComfyUIClient | None,
    characters: list[dict],
    phase: str,
    filter_type: str | None,
    filter_id: str | None,
    dry_run: bool,
) -> list[dict]:
    """Run a generation phase for a set of characters."""
    manifest_entries = []

    for char in characters:
        # Filter by type (class vs npc)
        if filter_type and char["type"] != filter_type:
            continue
        # Filter by specific character ID
        if filter_id and char["id"] != filter_id:
            continue

        entry = generate_single(client, char, phase, dry_run=dry_run)
        if entry:
            manifest_entries.append(entry)

        # Small delay between generations to avoid overwhelming ComfyUI
        if not dry_run and entry and entry.get("status") == "generated":
            time.sleep(2)

    return manifest_entries


def main():
    parser = argparse.ArgumentParser(description="Batch generate Berserkr character art")
    parser.add_argument("--phase", choices=["1", "2", "3", "all"], default="all",
                        help="Phase to run: 1=portraits, 2=cards, 3=fullbody, all=everything")
    parser.add_argument("--character", type=str, default=None,
                        help="Generate only this character ID (e.g., 'grimr', 'berserkr')")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print prompts without generating")
    parser.add_argument("--comfyui-url", type=str, default=None,
                        help="ComfyUI server URL (default: http://localhost:8188)")
    args = parser.parse_args()

    # Load character prompts
    if not PROMPTS_FILE.exists():
        logger.error("character_prompts.json not found at %s", PROMPTS_FILE)
        sys.exit(1)

    prompts_data = load_prompts()
    characters = prompts_data.get("characters", [])
    logger.info("Loaded %d characters from %s", len(characters), PROMPTS_FILE)

    # Verify workflow files exist
    for wf in ["berserkr_chargen_portrait", "berserkr_chargen_fullbody", "berserkr_chargen_card"]:
        wf_path = WORKFLOWS_DIR / f"{wf}.json"
        if not wf_path.exists():
            logger.error("Workflow not found: %s", wf_path)
            sys.exit(1)

    # Create output directories
    ensure_output_dirs()

    # Connect to ComfyUI (unless dry run)
    client = None
    if not args.dry_run:
        config = ComfyUIConfig()
        if args.comfyui_url:
            client = ComfyUIClient(config, base_url=args.comfyui_url)
        else:
            client = ComfyUIClient(config)

        if not client.is_available():
            logger.error("ComfyUI is not available at %s", client.base_url)
            logger.error("Start ComfyUI first, or use --dry-run to preview prompts")
            sys.exit(1)

        conn = client.check_connection()
        vram_total = conn.get("vram_total", 0)
        vram_free = conn.get("vram_free", 0)
        logger.info("Connected to ComfyUI — VRAM: %.1f GB total, %.1f GB free",
                     vram_total / (1024**3) if vram_total else 0,
                     vram_free / (1024**3) if vram_free else 0)

    # Determine which phases to run
    phases = []
    if args.phase in ("1", "all"):
        phases.append(("portrait", "npc", "Phase 1: NPC Dialogue Portraits"))
    if args.phase in ("2", "all"):
        phases.append(("card", "class", "Phase 2: Class Selection Cards"))
    if args.phase in ("3", "all"):
        phases.append(("fullbody", None, "Phase 3: Full-body Concepts"))

    # Run phases
    all_entries = []
    total_start = time.time()

    for phase, filter_type, description in phases:
        logger.info("=" * 60)
        logger.info(description)
        logger.info("=" * 60)

        entries = run_phase(client, characters, phase, filter_type, args.character, args.dry_run)
        all_entries.extend(entries)

        generated = sum(1 for e in entries if e.get("status") == "generated")
        skipped = sum(1 for e in entries if e.get("status") == "skipped")
        failed = sum(1 for e in entries if e.get("status") == "failed")
        logger.info("  %s complete: %d generated, %d skipped, %d failed",
                     description, generated, skipped, failed)

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

    # Summary
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
