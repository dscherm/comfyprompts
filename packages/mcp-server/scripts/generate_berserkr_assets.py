"""Batch asset generator for Berserkr equipment and UI elements.

Reads equipment_prompts.json or ui_prompts.json and generates images
through the ComfyUI API using the portrait workflow as a base template.

Uses raw urllib for ComfyUI communication (no SDK dependency).

Usage:
    python generate_berserkr_assets.py --type equipment [--item ID] [--dry-run]
    python generate_berserkr_assets.py --type equipment --retry-failed
    python generate_berserkr_assets.py --type ui [--item ID] [--dry-run]

Examples:
    python generate_berserkr_assets.py --type equipment                    # All equipment
    python generate_berserkr_assets.py --type ui                           # All UI elements
    python generate_berserkr_assets.py --type equipment --item great_axe   # Single item
    python generate_berserkr_assets.py --type equipment --dry-run          # Preview prompts
    python generate_berserkr_assets.py --type equipment --retry-failed     # Retry only failures
"""

import argparse
import hashlib
import json
import logging
import os
import sys
import time
import urllib.error
import urllib.request
import uuid
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

COMFYUI_URL = "http://127.0.0.1:8188"
TOOLCHAIN_ROOT = Path(__file__).resolve().parent.parent.parent.parent
WORKFLOWS_DIR = TOOLCHAIN_ROOT / "workflows" / "mcp"
BERSERKR_DIR = TOOLCHAIN_ROOT / "workflows" / "berserkr"
GODOT_PROJECT = Path("D:/Projects/berserkr-godot")

MAX_RETRIES = 3
RETRY_BACKOFF_SECONDS = 5

ASSET_CONFIG = {
    "equipment": {
        "prompts_file": BERSERKR_DIR / "equipment_prompts.json",
        "list_key": "equipment",
        "output_base": GODOT_PROJECT / "games" / "berserkr" / "assets" / "sprites" / "equipment",
        "width": 512,
        "height": 512,
        "subdir_key": "item_category",
    },
    "ui": {
        "prompts_file": BERSERKR_DIR / "ui_prompts.json",
        "list_key": "elements",
        "output_base": GODOT_PROJECT / "games" / "berserkr" / "assets" / "sprites" / "ui",
        "width": 512,
        "height": 512,
        "subdir_key": "ui_category",
    },
}

# Workflow node IDs (from berserkr_chargen_portrait.json)
# "2" = EmptySD3LatentImage (width, height)
# "3" = CLIPTextEncode - Positive Prompt (text)
# "4" = CLIPTextEncode - Negative Prompt (text)
# "5" = KSampler (seed)
# "7" = SaveImage (filename_prefix)


def seed_for_name(name: str) -> int:
    """Deterministic seed from item name."""
    return int(hashlib.md5(name.encode()).hexdigest()[:8], 16)


def load_workflow_template() -> dict:
    """Load the berserkr_chargen_portrait workflow JSON."""
    path = WORKFLOWS_DIR / "berserkr_chargen_portrait.json"
    with open(path) as f:
        return json.load(f)


def build_workflow(item: dict, width: int, height: int, prefix: str) -> tuple:
    """Inject item-specific values into the workflow template.

    Returns (workflow_dict, seed).
    """
    workflow = load_workflow_template()
    seed = seed_for_name(item["name"])

    # Node 2: EmptySD3LatentImage - set dimensions
    workflow["2"]["inputs"]["width"] = width
    workflow["2"]["inputs"]["height"] = height

    # Node 3: Positive Prompt
    workflow["3"]["inputs"]["text"] = item["positive_prompt"]

    # Node 4: Negative Prompt
    workflow["4"]["inputs"]["text"] = item["negative_prompt"]

    # Node 5: KSampler - set seed
    workflow["5"]["inputs"]["seed"] = seed

    # Node 7: SaveImage - set filename prefix
    workflow["7"]["inputs"]["filename_prefix"] = f"Berserkr_{prefix}_{item['id']}"

    return workflow, seed


def get_output_path(item: dict, config: dict) -> Path:
    """Determine local output path for an item."""
    subdir = item.get(config["subdir_key"], "misc")
    if not subdir:
        subdir = "misc"
    return config["output_base"] / subdir / f"{item['id']}.png"


def check_comfyui():
    """Verify ComfyUI is running."""
    try:
        urllib.request.urlopen(f"{COMFYUI_URL}/system_stats", timeout=5)
        return True
    except Exception:
        return False


def queue_prompt(workflow: dict) -> list:
    """Queue a workflow in ComfyUI and poll until complete. Returns output image info list."""
    client_id = str(uuid.uuid4())
    payload = json.dumps({"prompt": workflow, "client_id": client_id}).encode()

    req = urllib.request.Request(
        f"{COMFYUI_URL}/prompt",
        data=payload,
        headers={"Content-Type": "application/json"},
    )
    resp = urllib.request.urlopen(req, timeout=30)
    result = json.loads(resp.read())
    prompt_id = result["prompt_id"]

    # Poll history until this prompt_id appears
    while True:
        time.sleep(1)
        history_url = f"{COMFYUI_URL}/history/{prompt_id}"
        hist_resp = urllib.request.urlopen(history_url, timeout=10)
        history = json.loads(hist_resp.read())
        if prompt_id in history:
            status_info = history[prompt_id].get("status", {})
            if status_info.get("status_str") == "error":
                msgs = status_info.get("messages", [])
                raise RuntimeError(f"ComfyUI execution error: {msgs}")
            outputs = history[prompt_id].get("outputs", {})
            for node_id, node_out in outputs.items():
                if "images" in node_out:
                    return node_out["images"], prompt_id
            return [], prompt_id

    return [], prompt_id


def download_image(image_info: dict, save_path: str):
    """Download a generated image from ComfyUI output to a local path."""
    filename = image_info["filename"]
    subfolder = image_info.get("subfolder", "")
    folder_type = image_info.get("type", "output")

    url = (
        f"{COMFYUI_URL}/view?"
        f"filename={urllib.request.quote(filename)}"
        f"&subfolder={urllib.request.quote(subfolder)}"
        f"&type={folder_type}"
    )
    data = urllib.request.urlopen(url, timeout=30).read()
    os.makedirs(os.path.dirname(save_path), exist_ok=True)
    with open(save_path, "wb") as f:
        f.write(data)


def load_existing_manifest(config: dict) -> dict:
    """Load existing manifest and return dict of id -> entry."""
    manifest_file = config["output_base"] / "generation_manifest.json"
    if not manifest_file.exists():
        return {}
    with open(manifest_file) as f:
        data = json.load(f)
    return {e["id"]: e for e in data.get("entries", [])}


def generate_single(item: dict, config: dict, prefix: str, dry_run: bool = False) -> dict:
    """Generate a single item sprite. Returns manifest entry dict."""
    output_path = get_output_path(item, config)

    if output_path.exists():
        logger.info("SKIP %s -- already exists at %s", item["name"], output_path)
        return {"id": item["id"], "path": str(output_path), "status": "skipped"}

    workflow, seed = build_workflow(item, config["width"], config["height"], prefix)

    if dry_run:
        logger.info("DRY RUN -- %s (seed=%d)", item["name"], seed)
        logger.info("  Prompt: %.100s...", item["positive_prompt"])
        logger.info("  Output: %s", output_path)
        return {"id": item["id"], "path": str(output_path), "status": "dry_run", "seed": seed}

    # Retry loop
    for attempt in range(1, MAX_RETRIES + 1):
        logger.info("GENERATE %s (seed=%d) [attempt %d/%d]", item["name"], seed, attempt, MAX_RETRIES)
        try:
            images, prompt_id = queue_prompt(workflow)
            if images:
                download_image(images[0], str(output_path))
                logger.info("  Saved to %s", output_path)
                return {
                    "id": item["id"],
                    "path": str(output_path),
                    "seed": seed,
                    "prompt_id": prompt_id,
                    "status": "generated",
                }
            else:
                logger.warning("  No output images returned for %s", item["name"])
        except Exception as e:
            logger.error("  Attempt %d failed for %s: %s", attempt, item["name"], e)

        if attempt < MAX_RETRIES:
            wait = RETRY_BACKOFF_SECONDS * attempt
            logger.info("  Retrying in %ds...", wait)
            time.sleep(wait)

    logger.error("  FAILED %s after %d attempts", item["name"], MAX_RETRIES)
    return {"id": item["id"], "path": str(output_path), "status": "failed"}


def main():
    parser = argparse.ArgumentParser(description="Batch generate Berserkr equipment/UI art via ComfyUI")
    parser.add_argument("--type", choices=["equipment", "ui"], required=True,
                        help="Asset type to generate")
    parser.add_argument("--item", type=str, default=None,
                        help="Generate only this item ID")
    parser.add_argument("--retry-failed", action="store_true",
                        help="Only regenerate items with 'failed' status in existing manifest")
    parser.add_argument("--dry-run", action="store_true",
                        help="Preview what would be generated without running ComfyUI")
    parser.add_argument("--comfyui-url", type=str, default=None,
                        help="ComfyUI server URL (default: http://127.0.0.1:8188)")
    args = parser.parse_args()

    global COMFYUI_URL
    if args.comfyui_url:
        COMFYUI_URL = args.comfyui_url

    config = ASSET_CONFIG[args.type]
    prefix = "Equipment" if args.type == "equipment" else "UI"

    if not config["prompts_file"].exists():
        logger.error("Prompts file not found: %s", config["prompts_file"])
        sys.exit(1)

    with open(config["prompts_file"]) as f:
        data = json.load(f)

    items = data.get(config["list_key"], [])
    logger.info("Loaded %d %s items from %s", len(items), args.type, config["prompts_file"])

    # Filter to single item if requested
    if args.item:
        items = [i for i in items if i["id"] == args.item]
        if not items:
            logger.error("Item '%s' not found in prompts file", args.item)
            sys.exit(1)

    # Filter to failed-only if --retry-failed
    if args.retry_failed:
        existing = load_existing_manifest(config)
        failed_ids = {eid for eid, entry in existing.items() if entry.get("status") == "failed"}
        items = [i for i in items if i["id"] in failed_ids]
        logger.info("Retrying %d failed items", len(items))
        if not items:
            logger.info("No failed items to retry.")
            return
        # Delete existing PNGs for failed items so skip logic doesn't trigger
        for item in items:
            out = get_output_path(item, config)
            if out.exists():
                out.unlink()
                logger.info("  Removed stale %s", out)

    # Check ComfyUI availability
    if not args.dry_run:
        if not check_comfyui():
            logger.error("ComfyUI is not running at %s", COMFYUI_URL)
            sys.exit(1)
        logger.info("Connected to ComfyUI at %s", COMFYUI_URL)

    all_entries = []
    total_start = time.time()

    logger.info("=" * 60)
    logger.info("Generating %d %s assets", len(items), args.type)
    logger.info("=" * 60)

    for i, item in enumerate(items, 1):
        logger.info("[%d/%d] %s", i, len(items), item["name"])
        entry = generate_single(item, config, prefix, dry_run=args.dry_run)
        all_entries.append(entry)
        # Small delay between successful generations to let ComfyUI breathe
        if not args.dry_run and entry.get("status") == "generated":
            time.sleep(2)

    elapsed = time.time() - total_start

    # Update manifest
    if not args.dry_run and all_entries:
        manifest_file = config["output_base"] / "generation_manifest.json"

        # Merge with existing manifest if retrying
        if args.retry_failed and manifest_file.exists():
            with open(manifest_file) as f:
                old_manifest = json.load(f)
            old_entries = {e["id"]: e for e in old_manifest.get("entries", [])}
            # Update old entries with new results
            for entry in all_entries:
                old_entries[entry["id"]] = entry
            merged_entries = list(old_entries.values())
        else:
            merged_entries = all_entries

        manifest = {
            "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "total_elapsed_seconds": round(elapsed, 1),
            "entries": merged_entries,
        }
        manifest_file.parent.mkdir(parents=True, exist_ok=True)
        with open(manifest_file, "w") as f:
            json.dump(manifest, f, indent=2)
        logger.info("Manifest saved: %s", manifest_file)

    generated = sum(1 for e in all_entries if e.get("status") == "generated")
    skipped = sum(1 for e in all_entries if e.get("status") == "skipped")
    failed = sum(1 for e in all_entries if e.get("status") == "failed")
    logger.info("")
    logger.info("=" * 60)
    logger.info("COMPLETE -- %d generated, %d skipped, %d failed in %.1fs",
                generated, skipped, failed, elapsed)
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
