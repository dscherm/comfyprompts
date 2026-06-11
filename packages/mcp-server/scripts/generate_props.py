"""Generate 3D prop assets for Berserkr using ComfyUI.

Phase 1: Concept art (SDXL Flux, ~36s each) — Sin City ink style single object on white bg
Phase 2: GLB conversion (Hunyuan3D v2.0 textured, ~125s each) — concept art → textured 3D model

Usage:
    python generate_props.py --phase 1 [--category trees] [--prop pine_large]
    python generate_props.py --phase 2 [--category trees] [--prop pine_large]
    python generate_props.py --dry-run --phase 1
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
import urllib.error
import urllib.request
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

COMFYUI_URL = "http://127.0.0.1:8188"
GODOT_PROJECT = Path("D:/Projects/berserkr-godot")
CONCEPT_OUTPUT = GODOT_PROJECT / "games" / "berserkr" / "assets" / "sprites" / "props"
GLB_OUTPUT = GODOT_PROJECT / "games" / "berserkr" / "assets" / "models" / "props"
WORKFLOW_DIR = Path(__file__).resolve().parent.parent.parent.parent / "workflows" / "mcp"
COMFYUI_OUTPUT = Path("D:/Projects/ComfyUI/output")

# Prop definitions: category -> { prop_id: concept_prompt }
PROP_DEFINITIONS = {
    "trees": {
        "pine_large": "tall ancient pine tree with frost-covered branches, thick gnarled trunk, heavy snow on boughs, isolated single tree",
        "pine_medium": "medium pine tree with sparse frost-dusted branches, straight trunk, winter conifer",
        "dead_tree": "dead leafless tree with twisted bare branches, broken trunk top, dark bark peeling, skeletal winter tree",
        "birch": "slender birch tree with white bark and black knot marks, few remaining yellow leaves, thin graceful trunk",
    },
    "rocks": {
        "rock_large": "large rough boulder with moss patches, grey weathered stone, cracks and lichen, natural rock formation",
        "rock_medium": "medium rounded rock with frost on top, grey stone, partially buried in earth",
        "rock_small": "small rough stone, pebble cluster, grey-brown natural rock on ground",
        "boulder_snow": "massive boulder covered in thick snow, ice formations on sides, frozen stone",
        "rock_cluster": "cluster of rough stones grouped together, varied sizes, natural rock grouping on ground",
    },
    "structures": {
        "fence_section": "wooden fence section with two posts and horizontal planks, rough-hewn timber, weathered grey wood, frost on top",
        "wooden_post": "single wooden post driven into ground, weathered grey timber, slightly leaning, rope remnant",
        "barrel": "wooden barrel with iron bands, aged oak staves, slightly worn, medieval storage barrel",
        "crate": "rough wooden storage crate with iron nails, planks nailed together, medieval cargo box",
        "well": "stone well with low circular wall, wooden crossbeam and bucket rope, moss on stones, medieval village well",
        "signpost": "wooden signpost with directional arrow signs, carved text, tall timber post at crossroads",
        "wooden_fence": "long wooden fence with vertical planks and horizontal rails, rough timber, weathered grey wood",
    },
    "furniture": {
        "table_large": "large wooden trestle table, heavy oak planks on sturdy legs, medieval longhouse table, worn surface",
        "bench": "long wooden bench, simple plank seat on thick legs, medieval hall seating",
        "chair": "simple wooden chair with straight back, medieval rustic furniture, worn seat",
        "shelf": "tall wooden shelf unit with multiple levels, rough timber construction, medieval storage",
        "weapon_rack": "wall-mounted weapon rack holding swords and axes, wooden frame with iron pegs, medieval armory",
    },
    "sacred": {
        "runestone": "tall carved runestone with glowing Norse runes, ancient grey stone slab, moss at base, mystical standing stone",
        "standing_stone": "tall rough standing stone, ancient megalith, weathered grey surface, monolith",
        "altar_stone": "flat stone altar on rough stone base, offerings on top surface, sacred stone platform",
        "offering_bowl": "small stone bowl on ground with silver coins and dried flowers, ritual offering vessel",
    },
    "graveyard": {
        "gravestone_tall": "tall thin gravestone, carved Norse text, weathered grey stone, slightly tilted, frost patches",
        "gravestone_wide": "wide low gravestone, rounded top, weathered carved surface, moss growing on edges",
        "iron_cross": "iron cross grave marker, rusted metal, simple cross shape, driven into earth at slight angle",
        "cairn": "stone cairn burial marker, stacked rounded stones in pyramid shape, moss between stones",
        "gravestone_simple": "simple low gravestone, plain rectangular stone slab, weathered surface, modest burial marker",
    },
    "cave": {
        "stalagmite_large": "large stalagmite rising from cave floor, mineral deposits, dripping wet surface, natural cave formation",
        "stalagmite_small": "small stalagmite cluster on cave floor, pointed mineral deposits, wet stone",
        "bone_pile": "pile of scattered bones on ground, animal and human bones mixed, cracked for marrow, cave floor debris",
        "skull_totem": "crude totem made of stacked skulls on a stick, primitive tribal marker, bone decoration, troll lair",
        "moss_patch": "patch of thick green moss on cave floor, soft damp ground cover, dark green cave moss",
        "stream_crossing": "narrow underground stream with wet stones, dark water flowing through cave, shallow cave creek",
    },
    "forge": {
        "anvil": "blacksmith anvil on wooden stump base, heavy dark iron, worn striking surface, soot-covered",
        "quench_barrel": "half barrel filled with dark water, wooden staves with iron bands, steam rising, blacksmith tool",
        "bellows": "large forge bellows, leather and wood construction, iron nozzle, blacksmith workshop tool",
        "tool_rack": "wall-mounted tool rack with hammers tongs and files, wooden frame with iron hooks, blacksmith tools",
    },
    "debris": {
        "dead_leaves": "pile of dead brown leaves on ground, scattered autumn debris, frost-edged leaf litter",
        "mushroom_cluster": "cluster of small mushrooms growing on ground, brown caps, forest floor fungi",
        "frost_patch": "patch of ice crystals and frost on ground surface, white crystalline formation, frozen dew",
        "hay_pile": "small pile of loose hay and straw on ground, dried golden grass, scattered medieval farm debris",
    },
    "village": {
        "market_stall": "medieval market stall with wooden frame and canvas awning, display counter, rough timber construction",
        "cart": "two-wheeled wooden cart with open back, medieval farm cart, wooden wheels with iron rims",
        "torch_post": "tall wooden post with iron torch bracket at top, burning torch, medieval street light",
        "banner_post": "tall wooden pole with hanging fabric banner, raven emblem, medieval village banner",
        "log_pile": "stacked chopped firewood logs, neatly piled timber rounds, medieval village woodpile",
        "hay_bale": "rectangular hay bale bound with twine, golden straw, medieval farm supply",
    },
    "vegetation": {
        "bush_small": "small scraggly bush with frost-tipped leaves, sparse winter shrub, low ground cover plant",
        "bush_medium": "medium dense bush with dark green leaves and frost, rounded winter shrub, thick foliage",
    },
    "dungeon": {
        "sarcophagus": "heavy stone sarcophagus with carved lid, Norse knotwork relief, ancient burial coffin, dark stone",
        "brazier": "tall iron brazier on tripod legs, burning coals inside bowl, embers glowing, dungeon fire pit",
        "bone_throne": "massive throne constructed from bones and skulls, dark lord seat, skeletal armrests, macabre furniture",
        "treasure_pile": "pile of gold coins and jewels on ground, scattered treasure hoard, glinting precious metals and gems",
        "broken_pillar": "broken stone column, cracked marble pillar base with rubble, collapsed ancient architecture",
        "campfire_remains": "extinguished campfire with charred logs and ash ring, cold fire pit, scattered embers on ground",
        "candelabra": "tall iron candelabra with multiple candle holders, melted wax dripping, standing floor candle holder",
        "debris": "scattered stone rubble and broken masonry, dungeon floor debris, crumbled wall fragments",
        "rock_pile": "heap of rough stones and broken rocks, collapsed rubble pile, dungeon debris mound",
        "war_banner": "tattered war banner on tall pole, torn dark fabric with faded skull emblem, battle-worn flag",
        "iron_cage": "rusty iron cage with vertical bars, hanging chain, medieval dungeon prisoner cage, dark metal",
        "stone_bench": "simple stone bench carved from single block, smooth seat surface, dungeon seating, grey stone",
    },
    "dwarven": {
        "dwarven_machinery": "complex dwarven clockwork machinery with gears and pipes, brass and iron mechanical device, steampunk",
        "dwarven_door": "massive ornate stone door with dwarven rune carvings, heavy iron hinges, geometric patterns",
        "dwarven_statue": "carved stone dwarf warrior statue, full armor and hammer, stoic bearded face, monument",
        "workbench": "heavy dwarven workbench with tools scattered on top, thick stone slab on iron legs, crafting station",
        "crystal_cluster": "cluster of luminous blue crystals growing from stone, glowing mineral formation, magical gems",
        "mining_cart": "iron mining cart on small wheels, ore-filled hopper, dwarven mine equipment, rust and dirt",
        "enchanted_anvil": "ornate dwarven anvil with glowing rune inscriptions, magical forge tool, enchanted dark iron",
        "great_forge": "massive dwarven forge with stone chimney, iron doors, bellows system, grand smithing furnace",
        "fountain": "ornate stone fountain with basin and central column, water flowing, dwarven geometric carved stone",
    },
    "ice": {
        "ice_pillar": "tall crystalline ice pillar, frozen column with cracks and refractions, clear blue ice formation",
        "frozen_corpse": "frozen warrior corpse encased in ice, ancient dead figure in armor, frost-covered body",
        "frost_rune": "glowing frost rune inscribed on ground, circular magical symbol in ice, blue arcane markings",
        "frozen_bookshelf": "tall bookshelf covered in thick ice and frost, frozen books with icicles, ice-encrusted wood",
        "ice_desk": "desk made of solid ice, smooth frozen surface, translucent blue ice furniture with frost edges",
        "hot_spring": "steaming hot spring pool in ice cave, warm water vapor rising, melted ice rim, thermal pool",
        "rune_circle": "large magical rune circle on frozen ground, intricate glowing blue pattern, arcane ritual circle",
        "ice_throne": "majestic throne carved from solid ice, crystalline armrests and high back, frozen royal seat",
        "orb_pedestal": "stone pedestal with floating magical orb, glowing sphere hovering above column, enchanted artifact stand",
        "frozen_pillars": "pair of tall ice-covered stone pillars, frozen columns with icicles, frost-encrusted architecture",
        "ice_heart_crystal": "massive heart-shaped crystal of pure ice, pulsing blue glow, legendary frozen artifact, radiant gem",
    },
}

CONCEPT_STYLE = (
    "Frank Miller Sin City HEAVY BLACK INK illustration, "
    "single isolated object on clean white background, "
    "{subject}, "
    "extreme high contrast black and white, bold silhouette, "
    "thick aggressive ink brushstrokes, graphic novel aesthetic, "
    "centered composition, full object visible, "
    "NOT photorealistic NOT smooth NOT digital NOT 3d render"
)

CONCEPT_NEGATIVE = (
    "photorealistic, digital art, 3d render, smooth, airbrushed, blurry, "
    "low quality, deformed, background scene, landscape, multiple objects, "
    "characters, people, text, watermark, color, pastel"
)


def seed_for_name(name: str) -> int:
    return int(hashlib.md5(name.encode()).hexdigest()[:8], 16)


def build_concept_workflow(prompt: str, seed: int, filename_prefix: str, size: int = 512) -> dict:
    """Build a Flux workflow for concept art generation."""
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
            "inputs": {"text": CONCEPT_NEGATIVE, "clip": ["1", 1]},
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


def _load_workflow(name: str) -> dict:
    """Load a workflow JSON from the workflows/mcp directory."""
    path = WORKFLOW_DIR / name
    with open(path, "r") as f:
        return json.load(f)


def _substitute_params(wf: dict, params: dict) -> dict:
    """Replace PARAM_* placeholders in workflow with actual values."""
    raw = json.dumps(wf)
    for key, value in params.items():
        placeholder = f'"PARAM_{key}"'
        if isinstance(value, str):
            raw = raw.replace(placeholder, json.dumps(value))
        else:
            raw = raw.replace(placeholder, str(value))
    return json.loads(raw)


def build_textured_workflow(
    image_name: str,
    filename_prefix: str,
    seed: int = 42,
    guidance_scale: float = 5.5,
    steps: int = 50,
    octree_resolution: int = 256,
    max_faces: int = 30000,
    geometry_only: bool = False,
) -> dict:
    """Build a Hunyuan3D v2.0 pipeline workflow.

    Uses lower octree_resolution (256) and max_faces (30k) than characters
    since props are simpler objects that don't need as much detail.

    If geometry_only=True, strips texture pipeline nodes (faster, no custom_rasterizer needed).
    """
    wf = _load_workflow("hunyuan3d_v20_image_to_3d.json")
    wf = _substitute_params(wf, {
        "STR_IMAGE_PATH": image_name,
        "FLOAT_GUIDANCE_SCALE": guidance_scale,
        "INT_STEPS": steps,
        "INT_SEED": seed,
        "INT_OCTREE_RESOLUTION": octree_resolution,
        "INT_MAX_FACES": max_faces,
    })
    # Set output filename prefixes
    wf["11"]["inputs"]["filename_prefix"] = f"3D/{filename_prefix}_geometry"
    if geometry_only:
        # Remove texture pipeline nodes (4,5,12-24) to avoid custom_rasterizer DLL error
        texture_nodes = ["4", "5", "12", "13", "14", "15", "16", "17", "18", "19", "20", "21", "22", "23", "24"]
        for node_id in texture_nodes:
            wf.pop(node_id, None)
    else:
        wf["24"]["inputs"]["filename_prefix"] = f"3D/{filename_prefix}_textured"
    return wf


def download_glb_by_prefix(output_path: Path, filename_prefix: str) -> bool:
    """Download GLB by scanning ComfyUI output directory for matching files.

    Hy3DExportMesh returns STRING, not tracked in history outputs.
    We scan the output directory for files matching the prefix.
    """
    prefix_path = COMFYUI_OUTPUT / filename_prefix
    search_dir = prefix_path.parent
    search_stem = prefix_path.name

    if not search_dir.exists():
        return False

    candidates = sorted(
        [f for f in search_dir.iterdir()
         if f.name.startswith(search_stem) and f.suffix == ".glb"],
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )

    if candidates:
        src = candidates[0]
        output_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, output_path)
        size_mb = output_path.stat().st_size / (1024 * 1024)
        logger.info("  Saved: %s (%.1f MB) [from %s]", output_path.name, size_mb, src.name)
        return True

    return False


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


def poll_history(prompt_id: str, timeout: int = 600, interval: int = 5) -> dict | None:
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


def download_output(history_entry: dict, output_path: Path, output_key: str = "images") -> bool:
    """Download output from ComfyUI history. output_key is 'images' for PNGs or '3d' for GLBs."""
    outputs = history_entry.get("outputs", {})
    for node_id, node_out in outputs.items():
        items = node_out.get(output_key, [])
        for item in items:
            filename = item.get("filename", "")
            subfolder = item.get("subfolder", "")
            item_type = item.get("type", "output")
            url = f"{COMFYUI_URL}/view?filename={filename}&subfolder={subfolder}&type={item_type}"
            try:
                with urllib.request.urlopen(url, timeout=60) as resp:
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


def get_props_to_generate(args) -> list[dict]:
    """Build list of props to generate based on filters."""
    result = []
    for category, props in PROP_DEFINITIONS.items():
        if args.category and category != args.category:
            continue
        for prop_id, prompt in props.items():
            if args.prop and prop_id != args.prop:
                continue
            result.append({
                "category": category,
                "prop_id": prop_id,
                "prompt": prompt,
            })
    return result


def run_phase1(args):
    """Generate concept art images."""
    props = get_props_to_generate(args)
    logger.info("Phase 1: Generating %d concept art images", len(props))

    generated = 0
    failed = 0
    skipped = 0

    for i, prop in enumerate(props, 1):
        output_path = CONCEPT_OUTPUT / prop["category"] / f"{prop['prop_id']}.png"
        label = f"{prop['category']}/{prop['prop_id']}"
        logger.info("[%d/%d] %s", i, len(props), label)

        full_prompt = CONCEPT_STYLE.format(subject=prop["prompt"])
        seed = seed_for_name(f"berserkr_prop_{prop['prop_id']}") + 7000

        if args.dry_run:
            logger.info("  DRY RUN — prompt: %s...", full_prompt[:120])
            skipped += 1
            continue

        if output_path.exists():
            logger.info("  Already exists, skipping")
            skipped += 1
            continue

        workflow = build_concept_workflow(
            full_prompt, seed,
            f"Berserkr_Prop_{prop['category']}_{prop['prop_id']}",
            args.size,
        )

        try:
            prompt_id = queue_prompt(workflow)
            logger.info("  Queued: %s", prompt_id[:11])
            history = poll_history(prompt_id)
            if history and download_output(history, output_path, "images"):
                generated += 1
            else:
                logger.error("  FAILED: %s", label)
                failed += 1
        except Exception as e:
            logger.error("  FAILED: %s — %s", label, e)
            failed += 1

        if i < len(props):
            time.sleep(2)

    logger.info("Phase 1 COMPLETE — %d generated, %d failed, %d skipped", generated, failed, skipped)


def run_phase2(args):
    """Convert concept art to textured GLB models via Hunyuan3D v2.0."""
    props = get_props_to_generate(args)
    logger.info("Phase 2: Converting %d concept images to textured GLB", len(props))

    generated = 0
    failed = 0
    skipped = 0

    for i, prop in enumerate(props, 1):
        concept_path = CONCEPT_OUTPUT / prop["category"] / f"{prop['prop_id']}.png"
        glb_path = GLB_OUTPUT / prop["category"] / f"{prop['prop_id']}.glb"
        label = f"{prop['category']}/{prop['prop_id']}"
        prefix = f"Hy3D_props_{prop['category']}_{prop['prop_id']}"
        logger.info("[%d/%d] %s", i, len(props), label)

        if args.dry_run:
            logger.info("  DRY RUN — concept: %s → GLB: %s", concept_path, glb_path)
            skipped += 1
            continue

        if glb_path.exists():
            logger.info("  GLB already exists, skipping")
            skipped += 1
            continue

        if not concept_path.exists():
            logger.error("  Concept art not found: %s — run phase 1 first", concept_path)
            failed += 1
            continue

        # Upload concept image to ComfyUI input dir
        try:
            with open(concept_path, "rb") as f:
                img_data = f.read()
            upload_filename = f"berserkr_prop_{prop['prop_id']}.png"
            boundary = "----FormBoundary7MA4YWxkTrZu0gW"
            body = (
                f"--{boundary}\r\n"
                f'Content-Disposition: form-data; name="image"; filename="{upload_filename}"\r\n'
                f"Content-Type: image/png\r\n\r\n"
            ).encode() + img_data + f"\r\n--{boundary}--\r\n".encode()
            req = urllib.request.Request(
                f"{COMFYUI_URL}/upload/image",
                data=body,
                headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
            )
            with urllib.request.urlopen(req, timeout=30) as resp:
                upload_result = json.loads(resp.read())
                uploaded_name = upload_result.get("name", upload_filename)
        except Exception as e:
            logger.error("  Upload failed: %s", e)
            failed += 1
            continue

        seed = seed_for_name(f"berserkr_prop_{prop['prop_id']}") + 9000
        glb_prefix = f"3D/{prefix}_geometry"

        try:
            workflow = build_textured_workflow(
                uploaded_name, prefix, seed,
                octree_resolution=256,
                max_faces=30000,
                geometry_only=True,
            )
            prompt_id = queue_prompt(workflow)
            logger.info("  Queued: %s", prompt_id[:11])
            history = poll_history(prompt_id, timeout=900, interval=15)
            if history and download_glb_by_prefix(glb_path, glb_prefix):
                generated += 1
            else:
                logger.error("  FAILED: %s", label)
                failed += 1
        except Exception as e:
            logger.error("  FAILED: %s — %s", label, e)
            failed += 1

        if i < len(props):
            time.sleep(3)

    logger.info("Phase 2 COMPLETE — %d generated, %d failed, %d skipped", generated, failed, skipped)


def main():
    parser = argparse.ArgumentParser(description="Generate 3D prop assets for Berserkr")
    parser.add_argument("--phase", type=int, required=True, choices=[1, 2],
                        help="1 = concept art, 2 = GLB conversion")
    parser.add_argument("--dry-run", action="store_true", help="Print prompts, don't generate")
    parser.add_argument("--category", type=str, default=None,
                        help="Generate only this category (trees, rocks, etc.)")
    parser.add_argument("--prop", type=str, default=None,
                        help="Generate only this specific prop (pine_large, etc.)")
    parser.add_argument("--size", type=int, default=512,
                        help="Concept art size in pixels (default 512)")
    args = parser.parse_args()

    if not args.dry_run and not check_comfyui():
        logger.error("ComfyUI is not running at %s", COMFYUI_URL)
        sys.exit(1)

    if args.phase == 1:
        run_phase1(args)
    else:
        run_phase2(args)


if __name__ == "__main__":
    main()
