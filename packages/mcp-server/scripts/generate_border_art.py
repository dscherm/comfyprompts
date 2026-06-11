"""Generate border/backdrop art for Berserkr interior spaces.

Creates 5 different art direction variants for the border area outside
playable diamond tiles in interior locations. Each is a standalone
artistic backdrop rather than a seamless tile.

Styles:
1. Cosmic - deep space, nebula, stars
2. Eternal Winter - frozen tundra, ice, aurora
3. Celtic Art - knotwork, spirals, illuminated manuscript
4. Runes - Norse futhark, carved stone, ancient symbols
5. Psychedelic Fantasy - surreal, swirling, dreamlike

Usage:
    python generate_border_art.py [--dry-run] [--style NAME] [--size 1024]
"""

import argparse
import hashlib
import json
import logging
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

COMFYUI_URL = "http://127.0.0.1:8188"
GODOT_PROJECT = Path("D:/Projects/berserkr-godot")
OUTPUT_DIR = GODOT_PROJECT / "games" / "berserkr" / "assets" / "tilesets" / "generated" / "borders"

LORA_NAME = "style\\Dungeons_and_Dragons_Art_Style.safetensors"
LORA_STRENGTH = 0.3

BORDER_STYLES = {
    "cosmic": {
        "prompt": (
            "dark cosmic void with distant stars and galaxies, deep space nebula, "
            "swirling purple and blue gas clouds, scattered bright pinpoint stars, "
            "dark indigo and deep violet space, faint gold stardust trails, "
            "vast cosmic darkness with ethereal glow, Yggdrasil cosmic world tree silhouette, "
            "Norse mythology cosmic void Ginnungagap, dark fantasy space art"
        ),
        "negative": (
            "planets, earth, moon, sun, astronaut, spaceship, bright, cheerful, "
            "text, watermark, characters, people, buildings, ground, horizon"
        ),
    },
    "eternal_winter": {
        "prompt": (
            "frozen eternal winter landscape, towering ice formations and glacier walls, "
            "aurora borealis green and purple lights in dark sky, howling blizzard snow, "
            "massive icicle formations, frozen tundra wasteland, Niflheim realm of ice, "
            "Norse mythological frozen realm, deep blue ice cavern walls, "
            "swirling snowstorm vortex, dark fantasy winter atmosphere"
        ),
        "negative": (
            "summer, green, flowers, warm, sunny, characters, people, buildings, "
            "text, watermark, cheerful, bright"
        ),
    },
    "celtic_art": {
        "prompt": (
            "intricate Celtic knotwork border pattern on dark background, "
            "interlaced spirals and endless knot designs, gold and emerald illuminated manuscript style, "
            "ancient Celtic art ornamental patterns, triquetra and triskelion symbols, "
            "dark leather and aged parchment texture with gold leaf details, "
            "Book of Kells style ornate decoration, Norse-Celtic fusion art, "
            "dark green and gold color palette, detailed interlace patterns"
        ),
        "negative": (
            "modern, digital, neon, bright, characters, people, landscape, "
            "text, watermark, 3d render, realistic photo"
        ),
    },
    "runes": {
        "prompt": (
            "ancient Norse runic inscriptions carved into dark weathered stone, "
            "glowing Elder Futhark rune symbols with faint golden light emanating from carvings, "
            "aged dark granite surface covered in mystical runic text and bind runes, "
            "Nordic runestone texture with ancient carved symbols, "
            "dark stone with luminous runic magic, Odin's wisdom runes, "
            "Norse mythology magical inscription, dark and moody atmosphere"
        ),
        "negative": (
            "modern, digital, bright, cheerful, characters, people, landscape, "
            "text, watermark, English text, Latin alphabet"
        ),
    },
    "psychedelic_fantasy": {
        "prompt": (
            "surreal psychedelic dark fantasy art, swirling cosmic patterns, "
            "otherworldly dreamscape with impossible geometry, "
            "vibrant deep purple magenta and electric blue flowing energy, "
            "Bifrost rainbow bridge energy tendrils, fractal Norse mythology visions, "
            "dark psychedelic mushroom forest with glowing runes, "
            "mystical vortex of color and shadow, dark fantasy trip art, "
            "swirling dark energy patterns, nine realms merging"
        ),
        "negative": (
            "realistic, photo, mundane, boring, plain, characters, people, "
            "text, watermark, bright white, washed out"
        ),
    },
    "cosmic_ice": {
        "prompt": (
            "cosmic nebula merging with frozen ice realm, deep space void filled with "
            "crystalline ice formations and frost, swirling purple and blue nebula gas "
            "freezing into glacial ice structures, frozen stardust and icicle constellations, "
            "Niflheim meets Ginnungagap cosmic frozen void, aurora borealis shimmering "
            "through ice crystal nebula clouds, deep indigo space with frozen white and "
            "cyan ice shards floating among stars, Norse mythology primordial ice and cosmic "
            "darkness merging, dark fantasy frozen space art, ethereal frost nebula glow"
        ),
        "negative": (
            "warm, fire, lava, summer, green, characters, people, buildings, "
            "text, watermark, cheerful, bright, sunny, earth, planet"
        ),
    },
    "celtic_snow": {
        "prompt": (
            "intricate Celtic knotwork patterns formed from ice crystals and snowflakes, "
            "frozen Celtic spirals and endless knot designs made of frost and ice, "
            "delicate snow crystal lattice forming triquetra and triskelion symbols, "
            "ice blue and silver frozen Celtic ornamental patterns on dark winter background, "
            "frost-covered carved stone with Celtic interlace filled with frozen crystals, "
            "Norse-Celtic winter fusion, snowflake mandala with knotwork borders, "
            "frozen illuminated manuscript style, crystalline ice art with ancient Celtic motifs, "
            "dark moody winter atmosphere with glowing ice-blue Celtic patterns"
        ),
        "negative": (
            "warm, summer, green, fire, modern, digital, neon, characters, people, "
            "text, watermark, bright, cheerful, realistic photo"
        ),
    },
}


def seed_for_name(name: str) -> int:
    return int(hashlib.md5(name.encode()).hexdigest()[:8], 16)


def build_workflow(prompt: str, negative: str, seed: int,
                   filename_prefix: str, size: int = 1024) -> dict:
    """SDXL workflow for border art (no seamless tiling needed)."""
    return {
        "1": {
            "inputs": {"ckpt_name": "sd_xl_base_1.0.safetensors"},
            "class_type": "CheckpointLoaderSimple",
        },
        "2": {
            "inputs": {
                "lora_name": LORA_NAME,
                "strength_model": LORA_STRENGTH,
                "strength_clip": LORA_STRENGTH,
                "model": ["1", 0],
                "clip": ["1", 1],
            },
            "class_type": "LoraLoader",
        },
        "3": {
            "inputs": {"width": size, "height": size, "batch_size": 1},
            "class_type": "EmptyLatentImage",
        },
        "4": {
            "inputs": {"text": prompt, "clip": ["2", 1]},
            "class_type": "CLIPTextEncode",
        },
        "5": {
            "inputs": {"text": negative, "clip": ["2", 1]},
            "class_type": "CLIPTextEncode",
        },
        "6": {
            "inputs": {
                "seed": seed,
                "steps": 35,
                "cfg": 7.5,
                "sampler_name": "dpmpp_2m_sde",
                "scheduler": "karras",
                "denoise": 1.0,
                "model": ["2", 0],
                "positive": ["4", 0],
                "negative": ["5", 0],
                "latent_image": ["3", 0],
            },
            "class_type": "KSampler",
        },
        "7": {
            "inputs": {"samples": ["6", 0], "vae": ["1", 2]},
            "class_type": "VAEDecode",
        },
        "8": {
            "inputs": {"filename_prefix": filename_prefix, "images": ["7", 0]},
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


def poll_history(prompt_id: str, timeout: int = 600, interval: int = 5):
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(
                f"{COMFYUI_URL}/history/{prompt_id}", timeout=10
            ) as resp:
                data = json.loads(resp.read())
            if prompt_id in data:
                entry = data[prompt_id]
                status = entry.get("status", {})
                if status.get("status_str") == "success" or status.get("completed"):
                    return entry
                if status.get("status_str") == "error":
                    logger.error("  Workflow error: %s", status)
                    return None
        except Exception:
            pass
        time.sleep(interval)
    return None


def download_image(history_entry: dict, output_path: Path) -> bool:
    outputs = history_entry.get("outputs", {})
    node_out = outputs.get("8", {})
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
                logger.info("  Saved: %s (%d KB)", output_path.name,
                            output_path.stat().st_size // 1024)
                return True
        except Exception as e:
            logger.error("  Download failed: %s", e)
    return False


def main():
    parser = argparse.ArgumentParser(description="Generate border art for Berserkr")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--force", action="store_true", help="Regenerate even if file exists")
    parser.add_argument("--style", help="Generate only this style")
    parser.add_argument("--size", type=int, default=1024)
    args = parser.parse_args()

    styles = BORDER_STYLES
    if args.style:
        if args.style not in styles:
            logger.error("Unknown style: %s (available: %s)",
                         args.style, ", ".join(styles.keys()))
            sys.exit(1)
        styles = {args.style: styles[args.style]}

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    logger.info("Generating %d border art styles at %dx%d", len(styles), args.size, args.size)

    for style_name, style_data in styles.items():
        output_path = OUTPUT_DIR / f"border_{style_name}.png"

        if not args.force and output_path.exists():
            logger.info("Skipping %s (already exists, use --force to regenerate)", style_name)
            continue

        logger.info("Generating: %s", style_name)

        seed = seed_for_name(f"border_{style_name}")
        workflow = build_workflow(
            style_data["prompt"], style_data["negative"],
            seed, f"border_{style_name}", args.size
        )

        if args.dry_run:
            logger.info("  [DRY RUN] Would generate %s", output_path.name)
            continue

        prompt_id = queue_prompt(workflow)
        logger.info("  Queued: %s", prompt_id)

        result = poll_history(prompt_id)
        if result is None:
            logger.error("  FAILED: %s (timeout after 600s)", style_name)
            continue

        download_image(result, output_path)

    logger.info("Border art generation complete!")


if __name__ == "__main__":
    main()
