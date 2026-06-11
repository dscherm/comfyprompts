"""Generate UI icons for Berserkr RPG using ComfyUI Flux pipeline.

Generates 64x64 dark fantasy icons with Norse aesthetic via Flux 1 Dev FP8.
Icons are generated at 512x512 internally (Flux minimum) then downscaled to 64x64.

Categories:
    abilities  - 5 core ability stat icons
    conditions - 10 status effect icons
    actions    - 8 combat action icons
    menus      - 6 menu/HUD icons

Usage:
    python generate_ui_icons.py [--dry-run] [--category abilities] [--icon swift]
    python generate_ui_icons.py --category conditions --dry-run
    python generate_ui_icons.py --no-downscale
"""

import argparse
import hashlib
import json
import logging
import struct
import sys
import time
import urllib.error
import urllib.request
import zlib
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

COMFYUI_URL = "http://127.0.0.1:8188"
GODOT_PROJECT = Path("D:/Projects/berserkr-godot")
OUTPUT_BASE = GODOT_PROJECT / "games" / "berserkr" / "assets" / "sprites" / "ui" / "icons"

# Generation size (Flux needs at least 512 to produce coherent results)
GENERATION_SIZE = 512
# Final icon size after downscale
ICON_SIZE = 64

# ── Icon definitions: category -> { icon_id: subject_description } ──────────

ICON_DEFINITIONS = {
    "abilities": {
        "swift": "a single winged boot with small feathered wings, Norse leather boot with wing motif",
        "guile": "a cunning fox mask with narrow eyes, stylized animal face mask, trickster symbol",
        "might": "a clenched armored fist, gauntlet with spiked knuckles, raw power symbol",
        "fortitude": "a round Viking shield with iron boss, sturdy defensive shield, endurance symbol",
        "wits": "a single all-seeing eye with a raven silhouette above it, wisdom and perception symbol",
    },
    "conditions": {
        "poisoned": "a dripping potion vial with skull on label, toxic green drops falling, poison symbol",
        "stunned": "circling stars and spiral lines above, dazed dizzy symbol, impact effect",
        "bleeding": "a single large blood drop with smaller drops, wound bleeding symbol",
        "frightened": "a menacing skull with hollow eyes, terror fear symbol, dark omen",
        "exhausted": "a broken chain link snapped in half, fatigue weakness symbol, shattered metal",
        "prone": "a fallen figure silhouette face down, knocked down symbol, collapsed body",
        "grappled": "two hands gripping each other tightly, wrestling hold symbol, locked grip",
        "invisible": "a faded translucent ghostly outline of a figure, vanishing disappearing symbol",
        "enraged": "a burning flame in shape of angry face, fury berserker rage symbol, fire",
        "charmed": "a heart shape with carved Norse rune inside, enchantment charm magic symbol",
    },
    "actions": {
        "attack": "a single Viking sword blade pointing upward, sharp steel weapon, strike symbol",
        "defend": "a raised kite shield with iron bands, blocking defensive stance symbol",
        "parry": "two crossed swords forming an X shape, blade deflection counter symbol",
        "flee": "a pair of running boots with motion lines behind, escape retreat symbol",
        "use_item": "a round potion bottle with cork stopper, consumable item use symbol",
        "special": "a star burst explosion with radiating lines, powerful special move symbol",
        "cast_rune": "a single glowing Norse rune stone with magical aura, runic magic casting symbol",
        "move": "a bold directional arrow pointing right with motion lines, movement travel symbol",
    },
    "menus": {
        "inventory": "a wooden treasure chest with iron bands slightly open, storage container symbol",
        "quest_log": "a rolled parchment scroll with wax seal, written record document symbol",
        "party": "three figure silhouettes standing together in group, companions team symbol",
        "map": "a compass rose with cardinal directions, navigation wayfinding symbol",
        "settings": "a mechanical gear cog wheel with teeth, configuration options symbol",
        "grimoire": "a thick leather-bound book with rune on cover, spellbook tome symbol",
    },
}

# ── Style prompt ─────────────────────────────────────────────────────────────

ICON_STYLE = (
    "dark fantasy RPG icon, single centered symbol on solid dark background, "
    "{subject}, "
    "gold (#c8a030) and bronze metallic color palette on near-black (#1a1a1a) background, "
    "Norse Viking aesthetic, thick bold ink outlines, high contrast, "
    "clean simple icon design, no text, no letters, "
    "square icon composition, symbol fills frame, "
    "hand-drawn ink illustration style, visible brushstroke texture"
)

ICON_NEGATIVE = (
    "photorealistic, 3d render, smooth, airbrushed, blurry, low quality, deformed, "
    "watermark, text, signature, words, letters, numbers, "
    "anime, cartoon, cute, chibi, pastel colors, "
    "white background, light background, gradient background, "
    "multiple objects, busy scene, landscape, environment, "
    "photograph, digital painting, concept art scene"
)


# ── PNG downscale (nearest-neighbor, no PIL dependency) ──────────────────────

def _read_png_chunks(data: bytes) -> list[tuple[str, bytes]]:
    """Parse PNG file into chunks."""
    assert data[:8] == b'\x89PNG\r\n\x1a\n', "Not a PNG file"
    chunks = []
    pos = 8
    while pos < len(data):
        length = struct.unpack(">I", data[pos:pos + 4])[0]
        chunk_type = data[pos + 4:pos + 8].decode("ascii")
        chunk_data = data[pos + 8:pos + 8 + length]
        chunks.append((chunk_type, chunk_data))
        pos += 12 + length  # 4 len + 4 type + data + 4 crc
        if chunk_type == "IEND":
            break
    return chunks


def _decode_png_pixels(data: bytes) -> tuple[int, int, int, bytes]:
    """Decode a simple 8-bit RGBA PNG into raw pixel data.

    Returns (width, height, channels, pixel_bytes).
    Only handles 8-bit depth, color type 2 (RGB) or 6 (RGBA), no interlacing.
    """
    chunks = _read_png_chunks(data)
    ihdr_data = None
    idat_parts = []
    for ctype, cdata in chunks:
        if ctype == "IHDR":
            ihdr_data = cdata
        elif ctype == "IDAT":
            idat_parts.append(cdata)

    width, height, bit_depth, color_type = struct.unpack(">IIBB", ihdr_data[:10])
    compression, filter_method, interlace = struct.unpack("BBB", ihdr_data[10:13])
    assert bit_depth == 8, f"Unsupported bit depth: {bit_depth}"
    assert interlace == 0, "Interlaced PNGs not supported"

    if color_type == 2:
        channels = 3
    elif color_type == 6:
        channels = 4
    else:
        raise ValueError(f"Unsupported color type: {color_type}")

    raw = zlib.decompress(b"".join(idat_parts))
    stride = width * channels
    pixels = bytearray(width * height * channels)

    prev_row = bytearray(stride)
    pos = 0
    for y in range(height):
        filter_byte = raw[pos]
        pos += 1
        row = bytearray(raw[pos:pos + stride])
        pos += stride

        if filter_byte == 0:  # None
            pass
        elif filter_byte == 1:  # Sub
            for i in range(stride):
                a = row[i - channels] if i >= channels else 0
                row[i] = (row[i] + a) & 0xFF
        elif filter_byte == 2:  # Up
            for i in range(stride):
                row[i] = (row[i] + prev_row[i]) & 0xFF
        elif filter_byte == 3:  # Average
            for i in range(stride):
                a = row[i - channels] if i >= channels else 0
                row[i] = (row[i] + (a + prev_row[i]) // 2) & 0xFF
        elif filter_byte == 4:  # Paeth
            for i in range(stride):
                a = row[i - channels] if i >= channels else 0
                b = prev_row[i]
                c = prev_row[i - channels] if i >= channels else 0
                p = a + b - c
                pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
                if pa <= pb and pa <= pc:
                    pr = a
                elif pb <= pc:
                    pr = b
                else:
                    pr = c
                row[i] = (row[i] + pr) & 0xFF

        offset = y * stride
        pixels[offset:offset + stride] = row
        prev_row = row

    return width, height, channels, bytes(pixels)


def _encode_png(width: int, height: int, channels: int, pixels: bytes) -> bytes:
    """Encode raw RGBA pixels as a PNG file."""
    color_type = 6 if channels == 4 else 2

    # Build filtered scanlines (filter=0 for simplicity)
    stride = width * channels
    scanlines = bytearray()
    for y in range(height):
        scanlines.append(0)  # filter byte: None
        offset = y * stride
        scanlines.extend(pixels[offset:offset + stride])

    compressed = zlib.compress(bytes(scanlines), 9)

    def _chunk(ctype: str, data: bytes) -> bytes:
        raw = ctype.encode("ascii") + data
        crc = struct.pack(">I", zlib.crc32(raw) & 0xFFFFFFFF)
        return struct.pack(">I", len(data)) + raw + crc

    ihdr = struct.pack(">IIBBBBB", width, height, 8, color_type, 0, 0, 0)
    png = b'\x89PNG\r\n\x1a\n'
    png += _chunk("IHDR", ihdr)
    png += _chunk("IDAT", compressed)
    png += _chunk("IEND", b"")
    return png


def downscale_png(input_path: Path, output_path: Path, target_size: int) -> bool:
    """Downscale a PNG to target_size x target_size using area averaging.

    No external dependencies required. Converts RGB to RGBA (opaque) if needed.
    """
    try:
        with open(input_path, "rb") as f:
            data = f.read()

        src_w, src_h, channels, pixels = _decode_png_pixels(data)

        if src_w == target_size and src_h == target_size:
            return True  # Already correct size

        # Area-average downscale
        scale_x = src_w / target_size
        scale_y = src_h / target_size
        out_channels = 4  # Always output RGBA
        out_pixels = bytearray(target_size * target_size * out_channels)

        for dy in range(target_size):
            for dx in range(target_size):
                # Source region
                sx0 = int(dx * scale_x)
                sy0 = int(dy * scale_y)
                sx1 = min(int((dx + 1) * scale_x), src_w)
                sy1 = min(int((dy + 1) * scale_y), src_h)

                r_sum = g_sum = b_sum = a_sum = 0
                count = 0
                for sy in range(sy0, sy1):
                    for sx in range(sx0, sx1):
                        offset = (sy * src_w + sx) * channels
                        r_sum += pixels[offset]
                        g_sum += pixels[offset + 1]
                        b_sum += pixels[offset + 2]
                        a_sum += pixels[offset + 3] if channels == 4 else 255
                        count += 1

                if count > 0:
                    out_offset = (dy * target_size + dx) * out_channels
                    out_pixels[out_offset] = r_sum // count
                    out_pixels[out_offset + 1] = g_sum // count
                    out_pixels[out_offset + 2] = b_sum // count
                    out_pixels[out_offset + 3] = a_sum // count

        result = _encode_png(target_size, target_size, out_channels, bytes(out_pixels))
        with open(output_path, "wb") as f:
            f.write(result)
        return True

    except Exception as e:
        logger.error("  Downscale failed: %s", e)
        return False


# ── ComfyUI API helpers ──────────────────────────────────────────────────────

def seed_for_name(name: str) -> int:
    """Deterministic seed from icon name for reproducibility."""
    return int(hashlib.md5(name.encode()).hexdigest()[:8], 16)


def build_workflow(prompt: str, seed: int, filename_prefix: str, size: int = 512) -> dict:
    """Build a Flux 1 Dev FP8 workflow for icon generation."""
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
            "inputs": {"text": ICON_NEGATIVE, "clip": ["1", 1]},
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
    """Submit a workflow to ComfyUI and return the prompt_id."""
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
    """Poll ComfyUI history until the prompt completes or times out."""
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
    """Download the generated image from ComfyUI output."""
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
    """Check if ComfyUI is running and reachable."""
    try:
        with urllib.request.urlopen(f"{COMFYUI_URL}/system_stats", timeout=5) as resp:
            return resp.status == 200
    except Exception:
        return False


# ── Main generation logic ────────────────────────────────────────────────────

def get_icons_to_generate(args) -> list[dict]:
    """Build filtered list of icons based on CLI arguments."""
    result = []
    for category, icons in ICON_DEFINITIONS.items():
        if args.category and category != args.category:
            continue
        for icon_id, subject in icons.items():
            if args.icon and icon_id != args.icon:
                continue
            result.append({
                "category": category,
                "icon_id": icon_id,
                "subject": subject,
            })
    return result


def main():
    parser = argparse.ArgumentParser(
        description="Generate UI icons for Berserkr RPG via ComfyUI Flux pipeline"
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Print what would be generated without calling ComfyUI",
    )
    parser.add_argument(
        "--category", type=str, default=None,
        choices=["abilities", "conditions", "actions", "menus"],
        help="Generate only icons in this category",
    )
    parser.add_argument(
        "--icon", type=str, default=None,
        help="Generate only this specific icon (e.g. swift, poisoned, attack)",
    )
    parser.add_argument(
        "--no-downscale", action="store_true",
        help="Keep images at generation size (512x512) instead of downscaling to 64x64",
    )
    parser.add_argument(
        "--size", type=int, default=GENERATION_SIZE,
        help=f"Generation size in pixels (default {GENERATION_SIZE})",
    )
    args = parser.parse_args()

    icons = get_icons_to_generate(args)
    if not icons:
        logger.error("No icons matched the given filters")
        sys.exit(1)

    target_size = args.size if args.no_downscale else ICON_SIZE

    logger.info(
        "Generating %d UI icons (render %dx%d -> final %dx%d)",
        len(icons), args.size, args.size, target_size, target_size,
    )
    logger.info("Output: %s", OUTPUT_BASE)

    if not args.dry_run and not check_comfyui():
        logger.error("ComfyUI is not running at %s", COMFYUI_URL)
        sys.exit(1)

    OUTPUT_BASE.mkdir(parents=True, exist_ok=True)

    generated = 0
    failed = 0
    skipped = 0
    start_time = time.time()

    for i, icon in enumerate(icons, 1):
        category = icon["category"]
        icon_id = icon["icon_id"]
        label = f"{category}/{icon_id}"

        # Output goes into category subdirectory
        category_dir = OUTPUT_BASE / category
        output_path = category_dir / f"{icon_id}.png"

        logger.info("[%d/%d] %s", i, len(icons), label)

        full_prompt = ICON_STYLE.format(subject=icon["subject"])
        seed = seed_for_name(f"berserkr_icon_{icon_id}") + 3000

        if args.dry_run:
            logger.info("  DRY RUN -- prompt: %s...", full_prompt[:140])
            logger.info("  Seed: %d, Output: %s", seed, output_path)
            skipped += 1
            continue

        # Skip existing
        if output_path.exists():
            logger.info("  Already exists, skipping")
            skipped += 1
            continue

        workflow = build_workflow(
            full_prompt, seed,
            f"Berserkr_Icon_{category}_{icon_id}",
            args.size,
        )

        try:
            prompt_id = queue_prompt(workflow)
            logger.info("  Queued: %s", prompt_id[:11])

            history = poll_history(prompt_id)
            if not history:
                logger.error("  FAILED: %s", label)
                failed += 1
                continue

            if args.no_downscale:
                # Save full-size directly
                if download_image(history, output_path):
                    generated += 1
                else:
                    logger.error("  FAILED: %s", label)
                    failed += 1
            else:
                # Download to temp path, then downscale
                temp_path = category_dir / f"_{icon_id}_full.png"
                category_dir.mkdir(parents=True, exist_ok=True)
                if download_image(history, temp_path):
                    if downscale_png(temp_path, output_path, ICON_SIZE):
                        logger.info("  Downscaled: %dx%d -> %dx%d",
                                    args.size, args.size, ICON_SIZE, ICON_SIZE)
                        generated += 1
                    else:
                        logger.error("  Downscale failed, keeping full-size: %s", label)
                        temp_path.rename(output_path)
                        generated += 1
                    # Clean up temp file
                    if temp_path.exists():
                        temp_path.unlink()
                else:
                    logger.error("  FAILED: %s", label)
                    failed += 1

        except Exception as e:
            logger.error("  FAILED: %s -- %s", label, e)
            failed += 1

        if i < len(icons):
            time.sleep(2)

    elapsed = time.time() - start_time
    logger.info("")
    logger.info("=" * 60)
    logger.info(
        "COMPLETE -- %d generated, %d failed, %d skipped in %.1fs",
        generated, failed, skipped, elapsed,
    )
    logger.info("Output directory: %s", OUTPUT_BASE)
    logger.info("=" * 60)

    # Print summary table
    if not args.dry_run:
        logger.info("")
        logger.info("Icons by category:")
        for cat in ICON_DEFINITIONS:
            cat_dir = OUTPUT_BASE / cat
            if cat_dir.exists():
                count = len(list(cat_dir.glob("*.png")))
                logger.info("  %-12s %d icons", cat, count)


if __name__ == "__main__":
    main()
