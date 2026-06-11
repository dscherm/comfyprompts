"""Generate isometric terrain tiles for Berserkr scenes using ComfyUI Flux.

Reads terrain types from location_terrain_map.json and generates isometric
tile images for each terrain type and variant.

Usage:
    python generate_isometric_tiles.py [--dry-run] [--terrain TYPE] [--size 512]
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
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

COMFYUI_URL = "http://127.0.0.1:8188"
GODOT_PROJECT = Path("D:/Projects/berserkr-godot")
TERRAIN_MAP_FILE = GODOT_PROJECT / "games" / "berserkr" / "assets" / "tilesets" / "location_terrain_map.json"
OUTPUT_BASE = GODOT_PROJECT / "games" / "berserkr" / "assets" / "tilesets" / "generated"

# Tile prompts per terrain type — FLAT GROUND TEXTURE ONLY
# Each prompt describes ONLY the material/surface you'd see looking straight down at the ground.
TERRAIN_PROMPTS = {
    "frost_forest_floor": {
        "default": "dark frozen soil with scattered pine needles, frost crystals, tiny twigs, dead leaf litter on dirt",
        "dense": "dark wet humus soil, thick decaying pine needle layer, moss patches, mud between flat root ridges",
        "path": "packed dirt trail with boot prints in thin snow, pine needles on earth, small pebbles, frost at edges",
    },
    "sacred_clearing": {
        "default": "moss-covered flat stone pavement, wildflower petals, clover in flagstone cracks, faint runic etching, lichen",
    },
    "dirt_road": {
        "default": "packed hard dirt with cart wheel ruts, small pebbles, gravel, frost on edges, dried mud cracks",
        "cobble": "worn rounded cobblestones set in mortar, frost in cracks, moss in gaps between stones",
    },
    "snow_field": {
        "default": "smooth white snow surface, wind-swept ridge patterns, frozen grass tips poking through",
        "icy": "cracked ice sheet over hard-packed snow, frost crystal formations, frozen puddle surface",
        "muddy": "brown mud and half-melted slush, trampled churned earth, dirty snow patches, frozen boot prints",
    },
    "village_ground": {
        "default": "packed muddy dirt with cobblestone patches, trampled straw, cart wheel ruts, gravel",
        "planks": "rough timber plank surface over dark earth, gaps between boards, nail heads, mud splatters",
    },
    "wood_floor_interior": {
        "default": "aged oak plank floor, dark wood grain, gaps between planks, scattered straw, warm amber tone",
        "hearth": "wooden planks with charred edges, ash and soot on wood, scorch marks, ember glow warmth",
    },
    "stone_floor_interior": {
        "default": "large cut flagstone floor, worn smooth grey stone, mortar lines, carved knotwork border pattern",
        "bloodstained": "dark stone block floor, dried rust-brown stains in stone, scratch marks, dark patches",
    },
    "forge_floor": {
        "default": "scorched dark stone floor, metal filing glints, soot and coal dust, heat-cracked stone, ash",
    },
    "cave_floor": {
        "default": "rough natural rock surface, damp patches, loose gravel, mineral deposit streaks, grey-brown stone",
        "bones": "rock floor with scattered bone fragments, dark stains in stone, scratch marks, dried blood",
    },
    "barrow_ground": {
        "default": "frost-covered dead grass on compacted earth, flat stone slabs flush with ground, moss, frozen soil",
        "stone": "ancient fitted megalithic stone surface, weathered runic carvings in flat stone, moss in cracks",
    },
    "graveyard": {
        "default": "frost-covered churned earth, dead grass, cracked flat stone fragments, frozen mud, dead petals",
        "overgrown": "dead bramble vines flat across earth, decaying leaves on soil, cracked old stone, wild grass",
    },
}

STYLE_PREFIX = (
    "seamless tileable ground texture, top-down overhead view looking straight down, "
    "flat surface material texture, {subject}, "
    "high contrast ink illustration style, black and white with cold blue-white "
    "and warm amber color accents, bold ink brushstroke texture, "
    "game tile seamless edges, square tile, "
    "gritty dark atmosphere, visible ink grain texture, "
    "NO depth NO perspective NO objects NO vertical elements NO horizon NO sky"
)

NEGATIVE_PROMPT = (
    "photorealistic, 3d render, smooth, airbrushed, blurry, low quality, deformed, "
    "watermark, text, signature, anime, cartoon, "
    "perspective, vanishing point, depth, 3d scene, isometric scene, "
    "trees, trunks, branches, leaves, canopy, bushes, plants growing upward, "
    "buildings, houses, walls, roofs, fences, gates, doors, windows, pillars, columns, "
    "gravestones, tombstones, standing stones, monuments, statues, "
    "furniture, tables, chairs, barrels, crates, "
    "characters, people, animals, creatures, "
    "sky, horizon, clouds, sun, moon, stars, "
    "shadows of tall objects, silhouettes of objects"
)


def seed_for_name(name: str) -> int:
    return int(hashlib.md5(name.encode()).hexdigest()[:8], 16)


def build_tile_prompt(terrain_type: str, variant: str) -> str:
    subject = TERRAIN_PROMPTS.get(terrain_type, {}).get(variant, "")
    if not subject:
        subject = f"isometric tile of {terrain_type} {variant} terrain, Norse fantasy setting"
    return STYLE_PREFIX.format(subject=subject)


def build_workflow(prompt: str, seed: int, filename_prefix: str, size: int = 512) -> dict:
    return {
        "1": {
            "inputs": {"ckpt_name": "flux1-dev-fp8.safetensors"},
            "class_type": "CheckpointLoaderSimple",
        },
        "2": {
            "inputs": {"width": size, "height": size, "batch_size": 1},
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
    parser = argparse.ArgumentParser(description="Generate isometric terrain tiles")
    parser.add_argument("--dry-run", action="store_true", help="Print prompts, don't generate")
    parser.add_argument("--terrain", type=str, default=None, help="Generate only this terrain type")
    parser.add_argument("--size", type=int, default=512, help="Tile size in pixels (default 512)")
    args = parser.parse_args()

    if not args.dry_run and not check_comfyui():
        logger.error("ComfyUI is not running at %s", COMFYUI_URL)
        sys.exit(1)

    # Load terrain map
    with open(TERRAIN_MAP_FILE) as f:
        terrain_data = json.load(f)

    terrain_types = terrain_data.get("terrain_types", {})

    # Build generation list
    tiles_to_generate = []
    for terrain_type, info in terrain_types.items():
        if args.terrain and terrain_type != args.terrain:
            continue
        for variant in info.get("variants", ["default"]):
            filename = f"{terrain_type}.png" if variant == "default" else f"{terrain_type}_{variant}.png"
            tiles_to_generate.append({
                "terrain_type": terrain_type,
                "variant": variant,
                "filename": filename,
            })

    logger.info("Generating %d isometric tiles at %dx%d", len(tiles_to_generate), args.size, args.size)

    OUTPUT_BASE.mkdir(parents=True, exist_ok=True)

    generated = 0
    failed = 0
    skipped = 0
    start_time = time.time()

    for i, tile in enumerate(tiles_to_generate, 1):
        output_path = OUTPUT_BASE / tile["filename"]
        label = f"{tile['terrain_type']}/{tile['variant']}"

        logger.info("[%d/%d] %s", i, len(tiles_to_generate), label)

        prompt = build_tile_prompt(tile["terrain_type"], tile["variant"])
        seed = seed_for_name(f"berserkr_tile_{tile['terrain_type']}_{tile['variant']}") + 5000

        if args.dry_run:
            logger.info("  DRY RUN — prompt: %s...", prompt[:120])
            logger.info("  Seed: %d, Output: %s", seed, output_path)
            skipped += 1
            continue

        # Skip existing
        if output_path.exists():
            logger.info("  Already exists, skipping")
            skipped += 1
            continue

        workflow = build_workflow(prompt, seed, f"Berserkr_Tile_{tile['terrain_type']}_{tile['variant']}", args.size)

        try:
            prompt_id = queue_prompt(workflow)
            logger.info("  Queued: %s", prompt_id[:11])

            history = poll_history(prompt_id)
            if history and download_image(history, output_path):
                generated += 1
            else:
                logger.error("  FAILED: %s", label)
                failed += 1
        except Exception as e:
            logger.error("  FAILED: %s — %s", label, e)
            failed += 1

        if i < len(tiles_to_generate):
            time.sleep(2)

    elapsed = time.time() - start_time
    logger.info("")
    logger.info("=" * 60)
    logger.info("COMPLETE — %d generated, %d failed, %d skipped in %.1fs",
                generated, failed, skipped, elapsed)
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
