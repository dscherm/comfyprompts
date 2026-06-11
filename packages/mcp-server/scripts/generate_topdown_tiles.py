"""Generate seamless top-down terrain tiles for Berserkr using ComfyUI SDXL.

Art direction: Frank Miller Sin City x Frank Frazetta 70s fantasy.
High contrast, dramatic shadows, stylized painted surfaces, desaturated
palette with selective warm amber highlights and cold blue-grey shadows.

Uses SDXL + SeamlessTile (circular convolution) + CircularVAEDecode for
guaranteed seamless tiling. DnD Art Style LoRA at low strength adds
subtle fantasy painterly quality without overpowering the Sin City aesthetic.

Usage:
    python generate_topdown_tiles.py [--dry-run] [--terrain TYPE] [--size 1024] [--force] [--deploy]
    python generate_topdown_tiles.py --terrain frost_forest_floor --force  # Test single terrain
    python generate_topdown_tiles.py --force --deploy  # Regenerate all + deploy to Godot
"""

import argparse
import hashlib
import json
import logging
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
TILESETS_DIR = GODOT_PROJECT / "games" / "berserkr" / "assets" / "tilesets"
TERRAIN_MAP_FILE = TILESETS_DIR / "location_terrain_map.json"
OUTPUT_BASE = TILESETS_DIR / "generated"

# --- Art Direction: Sin City x Frazetta ---
# Proper ground surface textures with dark, high-contrast, moody color palette.
# The "Sin City x Frazetta" aesthetic comes from the COLOR PALETTE and CONTRAST,
# not from making SDXL generate paintings/illustrations (which confuses it).
# Keep proven "material texture" language + push mood dark.

# LoRA optional — base SDXL + SeamlessTile produces correct textures
LORA_NAME = "style\\Dungeons_and_Dragons_Art_Style.safetensors"
LORA_STRENGTH = 0.25

# Terrain prompts: proven material texture descriptions.
# Each describes what the surface looks like from directly above.
TERRAIN_PROMPTS = {
    "frost_forest_floor": {
        "default": (
            "deep snow blanketing forest floor with dark pine needles poking through, "
            "thick white snow with ice crystals on frozen earth, scattered frost-covered twigs, "
            "heavy winter snowfall covering ground, blue-white shadows in snow"
        ),
        "dense": (
            "thick undisturbed snow covering dense forest floor, only traces of dark bark "
            "and frozen pine needles visible beneath heavy snowpack, deep blue shadows in snow, "
            "frozen white winter wilderness ground"
        ),
        "path": (
            "trampled snow trail through frozen forest, compressed white snow path "
            "with boot prints and animal tracks, fresh powder on edges, "
            "icy packed snow trail surface with scattered frost-covered pine needles"
        ),
    },
    "sacred_clearing": {
        "default": (
            "pristine white snow surface with faint glowing blue-tinted frost patterns, "
            "mystical ice crystal formations on frozen sacred ground, ethereal shimmer "
            "in undisturbed snow, delicate crystalline frost mandalas on white snow"
        ),
    },
    "dirt_road": {
        "default": (
            "snow-covered road with packed ice and frozen ruts, heavy snow over cobblestones "
            "and frozen earth, cart wheel tracks filled with fresh snow, white snow surface "
            "with hints of dark stone beneath, frozen winter road"
        ),
        "cobble": (
            "cobblestones barely visible beneath thick layer of packed snow and ice, "
            "rounded grey stones poking through white snowpack in places, "
            "frozen mortar gaps filled with ice, winter road surface"
        ),
    },
    "snow_field": {
        "default": (
            "fresh white snow surface with subtle wind-sculpted ripples, fine powder texture, "
            "gentle undulating snow drifts, clean cold white with blue-grey shadows in depressions"
        ),
        "icy": (
            "crystalline ice sheet surface over hard-packed snow, reflective glassy patches, "
            "sharp frost crystal formations, cracked ice with white fracture lines on blue-grey surface"
        ),
        "muddy": (
            "dirty snow mixed with frozen dark mud near village paths, trampled grey-brown slush, "
            "ice-crusted puddles of meltwater, churned frozen ground with snow patches"
        ),
    },
    "village_ground": {
        "default": (
            "village ground covered in trampled snow with patches of frozen gravel showing through, "
            "dirty white snow surface with scattered straw and ash, "
            "well-trodden winter village paths, frozen footprints in packed snow"
        ),
        "planks": (
            "rough hewn timber plank surface dusted with snow and frost, dark wood grain visible "
            "between white frost patches, ice crystals in gaps between frozen boards, aged grey timber"
        ),
    },
    "wood_floor_interior": {
        "default": (
            "aged oak wood plank surface with dark grain patterns, warm amber-brown tone, "
            "subtle dust in plank gaps, wear-polished smooth wood texture with visible annual rings"
        ),
        "hearth": (
            "darkened charred wood plank surface near heat source, soot-stained timber grain, "
            "scattered fine ash on blackened boards, orange-amber heat discoloration on wood"
        ),
    },
    "stone_floor_interior": {
        "default": (
            "smooth grey flagstone floor surface, large flat rectangular stone slabs, "
            "thin dark mortar joints between stones, uniform grey stone texture, "
            "polished worn ancient stone pavement"
        ),
        "bloodstained": (
            "worn grey flagstone floor surface with dark brown-red dried stains, "
            "large flat stone slabs with scratch marks, dark mortar joints, "
            "grey stone pavement with old discoloration"
        ),
    },
    "forge_floor": {
        "default": (
            "soot-darkened stone and packed earth surface, scattered metallic filings and "
            "tiny spark burn marks, coal dust ground into grey-black stone, orange heat-stained patches"
        ),
    },
    "cave_floor": {
        "default": (
            "rough uneven grey stone surface with mineral deposit streaks, damp patches with "
            "slight sheen, scattered fine pebbles and grit on natural rock floor"
        ),
        "bones": (
            "dark stained rough stone surface, deep scratches and gouges in rock, rust-brown "
            "discoloration patches on grey cave floor, scattered fine debris and grit"
        ),
    },
    "barrow_ground": {
        "default": (
            "ancient burial mound ground buried under deep snow, frozen dark earth with "
            "thick white snowpack, occasional dead brown grass poking through ice, "
            "heavy frost on compacted frozen soil, bleak winter tundra"
        ),
        "stone": (
            "ancient megalithic stone surface half-buried in snow, ice-filled runic carvings "
            "on weathered grey rock, thick frost and snow accumulation on old stone, "
            "frozen lichen under ice layer on carved burial stones"
        ),
    },
    "graveyard": {
        "default": (
            "deep snow covering graveyard ground, frozen earth beneath thick snowpack, "
            "dead brown grass stems poking through white snow, ice crystals on cold soil, "
            "bleak winter graveyard with heavy frost and snow covering"
        ),
        "overgrown": (
            "snow-covered dead brambles and frozen vines over dark earth, tangled brown "
            "dead vegetation encased in ice and frost, thick snow on decayed organic matter, "
            "frozen winter graveyard overgrowth"
        ),
    },
}

# Style prefix: ground texture with dark, contrasty mood.
# Uses proven "material texture" language, pushes palette darker.
STYLE_PREFIX = (
    "top-down overhead view looking straight down, seamless tileable ground texture, "
    "{subject}, "
    "dark fantasy game texture, 8K detail, high contrast, "
    "deep shadows, heavily desaturated, "
    "cold blue-grey shadows, warm amber highlights, "
    "dark moody atmosphere, gritty raw surface, "
    "uniform surface distribution, no vignette, no border, no framing, "
    "surface material only, no vertical objects, no depth perspective"
)

# Negative: standard cleanup + block bright/cheerful
NEGATIVE_PROMPT = (
    "3d render, digital painting, illustration, ink drawing, sketch, cartoon, anime, "
    "bright, cheerful, clean, smooth, polished, soft lighting, pastel colors, "
    "cracked earth, dried mud, desert, arid, drought, cracking, "
    "large leaves, fallen leaves, pinecones, centered object, single object, "
    "vignette, dark edges, bright center, dark border, gradient border, spotlight, "
    "frame, framing, composition, centered subject, "
    "perspective, vanishing point, horizon, sky, clouds, "
    "trees, trunks, branches, leaves, bushes, plants growing upward, "
    "flowers, pumpkins, sunflowers, mushrooms, ferns, "
    "buildings, walls, roofs, fences, gates, doors, windows, pillars, "
    "gravestones, tombstones, standing stones, monuments, statues, crosses, "
    "furniture, tables, chairs, barrels, crates, pots, "
    "characters, people, animals, creatures, skulls, bones, skeletons, "
    "text, watermark, signature, blurry, low quality"
)


def seed_for_name(name: str) -> int:
    return int(hashlib.md5(name.encode()).hexdigest()[:8], 16)


def build_tile_prompt(terrain_type: str, variant: str) -> str:
    subject = TERRAIN_PROMPTS.get(terrain_type, {}).get(variant, "")
    if not subject:
        subject = f"{terrain_type} {variant} ground surface texture, dark Norse fantasy"
    return STYLE_PREFIX.format(subject=subject)


def build_workflow(prompt: str, seed: int, filename_prefix: str, size: int = 1024,
                   use_lora: bool = True) -> dict:
    """SDXL workflow with seamless tiling + optional DnD Art Style LoRA.

    Pipeline:
      Checkpoint → LoRA (optional) → SeamlessTile → KSampler → CircularVAEDecode → Save
    """
    workflow = {
        # Load SDXL checkpoint
        "1": {
            "inputs": {"ckpt_name": "sd_xl_base_1.0.safetensors"},
            "class_type": "CheckpointLoaderSimple",
        },
        # Empty latent at SDXL native resolution
        "3": {
            "inputs": {"width": size, "height": size, "batch_size": 1},
            "class_type": "EmptyLatentImage",
        },
        # Negative prompt (CLIP from checkpoint or LoRA)
        "5": {
            "inputs": {"text": NEGATIVE_PROMPT, "clip": ["1", 1]},
            "class_type": "CLIPTextEncode",
        },
    }

    # Optional LoRA for fantasy painterly style
    if use_lora:
        workflow["2"] = {
            "inputs": {
                "lora_name": LORA_NAME,
                "strength_model": LORA_STRENGTH,
                "strength_clip": LORA_STRENGTH,
                "model": ["1", 0],
                "clip": ["1", 1],
            },
            "class_type": "LoraLoader",
        }
        model_source = ["2", 0]
        clip_source = ["2", 1]
    else:
        model_source = ["1", 0]
        clip_source = ["1", 1]

    # Enable seamless tiling on model (circular convolution padding)
    workflow["10"] = {
        "inputs": {
            "model": model_source,
            "tiling": "enable",
            "copy_model": "Make a copy",
        },
        "class_type": "SeamlessTile",
    }

    # Positive prompt (CLIP from LoRA if used, else checkpoint)
    workflow["4"] = {
        "inputs": {"text": prompt, "clip": clip_source},
        "class_type": "CLIPTextEncode",
    }

    # Update negative prompt CLIP source
    workflow["5"]["inputs"]["clip"] = clip_source

    # KSampler with seamless model — dpmpp_2m_sde for sharper detail
    workflow["6"] = {
        "inputs": {
            "seed": seed,
            "steps": 35,
            "cfg": 7.5,
            "sampler_name": "dpmpp_2m_sde",
            "scheduler": "karras",
            "denoise": 1.0,
            "model": ["10", 0],  # From SeamlessTile
            "positive": ["4", 0],
            "negative": ["5", 0],
            "latent_image": ["3", 0],
        },
        "class_type": "KSampler",
    }

    # Circular VAE decode for seamless output
    workflow["7"] = {
        "inputs": {
            "samples": ["6", 0],
            "vae": ["1", 2],
            "tiling": "enable",
        },
        "class_type": "CircularVAEDecode",
    }

    # Save the tile
    workflow["8"] = {
        "inputs": {"filename_prefix": filename_prefix, "images": ["7", 0]},
        "class_type": "SaveImage",
    }

    # Also save an offset version for seam QA (shifted 50%/50%)
    workflow["9"] = {
        "inputs": {
            "pixels": ["7", 0],
            "x_percent": 50.0,
            "y_percent": 50.0,
        },
        "class_type": "OffsetImage",
    }
    workflow["11"] = {
        "inputs": {
            "filename_prefix": f"{filename_prefix}_seamcheck",
            "images": ["9", 0],
        },
        "class_type": "SaveImage",
    }

    return workflow


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


def download_image(history_entry: dict, output_path: Path, node_id: str = "8") -> bool:
    """Download the main tile image (node 8), skip the seamcheck (node 11)."""
    outputs = history_entry.get("outputs", {})
    node_out = outputs.get(node_id, {})
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
    # Fallback: try any node with images
    if not images:
        for nid, nout in outputs.items():
            imgs = nout.get("images", [])
            if imgs and "seamcheck" not in imgs[0].get("filename", ""):
                return download_image(history_entry, output_path, node_id=nid)
    return False


def check_comfyui() -> bool:
    try:
        with urllib.request.urlopen(f"{COMFYUI_URL}/system_stats", timeout=5) as resp:
            return resp.status == 200
    except Exception:
        return False


def deploy_tiles():
    """Copy generated tiles to the active tilesets directory, backup originals, clear .import files."""
    backup_dir = TILESETS_DIR / "old_sdxl_backup"
    backup_dir.mkdir(parents=True, exist_ok=True)

    generated_files = list(OUTPUT_BASE.glob("*.png"))
    if not generated_files:
        logger.warning("No generated tiles found in %s", OUTPUT_BASE)
        return

    deployed = 0
    for src in generated_files:
        dest = TILESETS_DIR / src.name
        import_file = TILESETS_DIR / f"{src.name}.import"

        # Backup existing tile
        if dest.exists():
            backup_path = backup_dir / src.name
            if not backup_path.exists():
                shutil.copy2(dest, backup_path)
                logger.info("  Backed up: %s", src.name)

        # Copy new tile
        shutil.copy2(src, dest)
        deployed += 1

        # Remove .import so Godot reimports
        if import_file.exists():
            import_file.unlink()

    logger.info("Deployed %d tiles to %s", deployed, TILESETS_DIR)
    logger.info("Originals backed up to %s", backup_dir)
    logger.info("Cleared .import files — Godot will reimport on next launch")


def main():
    parser = argparse.ArgumentParser(
        description="Generate seamless top-down terrain tiles (SDXL + Sin City/Frazetta style)")
    parser.add_argument("--dry-run", action="store_true", help="Print prompts, don't generate")
    parser.add_argument("--terrain", type=str, default=None, help="Generate only this terrain type")
    parser.add_argument("--variant", type=str, default=None,
                        help="Generate only this variant (requires --terrain)")
    parser.add_argument("--size", type=int, default=1024, help="Tile size in pixels (default 1024)")
    parser.add_argument("--force", action="store_true", help="Regenerate even if file exists")
    parser.add_argument("--no-lora", action="store_true", help="Skip DnD Art Style LoRA")
    parser.add_argument("--seed-offset", type=int, default=0,
                        help="Seed offset for generating variants (e.g., 1000 for v2, 2000 for v3)")
    parser.add_argument("--suffix", type=str, default="",
                        help="Filename suffix for variants (e.g., '_v2' generates frost_forest_floor_v2.png)")
    parser.add_argument("--deploy", action="store_true",
                        help="Copy generated tiles to active tilesets dir, backup originals")
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
            if args.variant and variant != args.variant:
                continue
            base = terrain_type if variant == "default" else f"{terrain_type}_{variant}"
            filename = f"{base}{args.suffix}.png"
            tiles_to_generate.append({
                "terrain_type": terrain_type,
                "variant": variant,
                "filename": filename,
            })

    use_lora = not args.no_lora
    lora_label = f" + DnD LoRA @{LORA_STRENGTH}" if use_lora else ""
    logger.info("Generating %d tiles at %dx%d (SDXL + SeamlessTile%s)",
                len(tiles_to_generate), args.size, args.size, lora_label)
    logger.info("Art direction: Frank Miller Sin City x Frank Frazetta 70s fantasy")

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
        # New seed series (8000+) to avoid old cached results. seed-offset for variants.
        seed = seed_for_name(f"berserkr_sincity_{tile['terrain_type']}_{tile['variant']}") + 8000 + args.seed_offset

        if args.dry_run:
            logger.info("  DRY RUN — prompt: %s...", prompt[:160])
            logger.info("  Seed: %d, Output: %s", seed, output_path)
            skipped += 1
            continue

        # Skip existing unless --force
        if output_path.exists() and not args.force:
            logger.info("  Already exists, skipping (use --force to regenerate)")
            skipped += 1
            continue

        workflow = build_workflow(
            prompt, seed,
            f"Berserkr_Tile_{tile['terrain_type']}_{tile['variant']}",
            args.size,
            use_lora=use_lora,
        )

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
    logger.info("Output: %s", OUTPUT_BASE)
    logger.info("=" * 60)

    if args.deploy and generated > 0:
        logger.info("")
        logger.info("Deploying tiles...")
        deploy_tiles()


if __name__ == "__main__":
    main()
