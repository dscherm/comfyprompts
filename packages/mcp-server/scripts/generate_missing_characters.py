"""Generate concept art + 3D GLBs for missing Berserkr characters.

Creates full-body T-pose concept art PNGs via Flux, then converts to textured
GLBs via Hunyuan3D v2.0. Handles both NPCs and creatures.

Missing characters:
  NPCs: heimdall_watcher, grimhild_runecaster, bjorn_shieldbreaker
  Creatures (midgard): bandit, bandit_chief, nisse

Usage:
    python generate_missing_characters.py [--dry-run] [--character ID] [--step concept|glb|all]
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
COMFYUI_OUTPUT = Path("D:/Projects/ComfyUI/output")
GODOT_PROJECT = Path("D:/Projects/berserkr-godot")
GAME_ASSETS = GODOT_PROJECT / "games" / "berserkr" / "assets"
TOOLCHAIN_ROOT = Path(__file__).resolve().parent.parent.parent.parent
WORKFLOW_DIR = TOOLCHAIN_ROOT / "workflows" / "mcp"

# Art style for concept generation (Sin City / Frazetta style)
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

# Character definitions for the 6 missing characters
MISSING_CHARACTERS = [
    {
        "id": "heimdall_watcher",
        "name": "Heimdall the Watcher",
        "type": "npc",
        "color_accent": "cold blue-white and pale silver",
        "identity_features": [
            "tall imposing figure",
            "piercing golden amber eyes that see all",
            "long silver-white hair flowing in wind",
            "ornate gilded chainmail armor",
            "large curved horn (Gjallarhorn) at belt",
            "great two-handed sword across back",
            "stoic watchful expression",
        ],
        "concept_dir": GAME_ASSETS / "sprites" / "characters" / "concepts" / "npcs",
        "model_dir": GAME_ASSETS / "models" / "characters" / "npcs",
    },
    {
        "id": "grimhild_runecaster",
        "name": "Grimhild the Runecaster",
        "type": "npc",
        "color_accent": "cold blue and pale silver",
        "identity_features": [
            "elderly hunched female",
            "wild grey hair with rune-inscribed bone ornaments",
            "deep-set knowing eyes one blue one milky white",
            "heavily wrinkled weathered face",
            "dark layered robes with glowing rune embroidery",
            "gnarled staff covered in carved runes",
            "fingers stained with woad blue dye",
        ],
        "concept_dir": GAME_ASSETS / "sprites" / "characters" / "concepts" / "npcs",
        "model_dir": GAME_ASSETS / "models" / "characters" / "npcs",
    },
    {
        "id": "bjorn_shieldbreaker",
        "name": "Bjorn Shieldbreaker",
        "type": "npc",
        "color_accent": "deep crimson red and burning amber orange",
        "identity_features": [
            "massive towering muscular build",
            "bald head with thick dark beard braided with iron rings",
            "broad scarred face with broken nose",
            "heavy fur-lined leather armor",
            "enormous two-handed warhammer",
            "trophy necklace of broken shield fragments",
            "fierce intimidating scowl",
        ],
        "concept_dir": GAME_ASSETS / "sprites" / "characters" / "concepts" / "npcs",
        "model_dir": GAME_ASSETS / "models" / "characters" / "npcs",
    },
    {
        "id": "bandit",
        "name": "Norse Bandit",
        "type": "creature",
        "color_accent": "deep violet and rust orange",
        "identity_features": [
            "lean wiry male outlaw",
            "hooded worn leather armor patched and dirty",
            "face half-covered by ragged cloth mask",
            "short sword and buckler",
            "dark eyes darting and suspicious",
            "tattered fur-trimmed cloak",
            "crude boots and wrapped leggings",
        ],
        "concept_dir": GAME_ASSETS / "sprites" / "creatures" / "midgard",
        "model_dir": GAME_ASSETS / "models" / "creatures" / "midgard",
    },
    {
        "id": "bandit_chief",
        "name": "Norse Bandit Chief",
        "type": "creature",
        "color_accent": "deep crimson red and burning amber orange",
        "identity_features": [
            "large imposing male outlaw leader",
            "heavy studded leather armor with stolen chainmail",
            "thick dark beard with gold rings woven in",
            "prominent scar across left eye",
            "battle axe in one hand round shield in other",
            "wolf pelt draped over shoulders",
            "arrogant confident sneer",
        ],
        "concept_dir": GAME_ASSETS / "sprites" / "creatures" / "midgard",
        "model_dir": GAME_ASSETS / "models" / "creatures" / "midgard",
    },
    {
        "id": "nisse",
        "name": "Nisse",
        "type": "creature",
        "color_accent": "warm amber and honey gold",
        "identity_features": [
            "very small gnome-like creature two feet tall",
            "oversized pointed red felt hat drooping over",
            "long white beard reaching to knees",
            "round ruddy nose and bright twinkling eyes",
            "simple grey wool tunic and tiny leather boots",
            "carrying a small wooden bowl of porridge",
            "mischievous impish grin",
        ],
        "concept_dir": GAME_ASSETS / "sprites" / "creatures" / "midgard",
        "model_dir": GAME_ASSETS / "models" / "creatures" / "midgard",
    },
]


def seed_for_name(name: str) -> int:
    return int(hashlib.md5(name.encode()).hexdigest()[:8], 16)


def check_comfyui() -> bool:
    try:
        with urllib.request.urlopen(f"{COMFYUI_URL}/system_stats", timeout=5) as resp:
            return resp.status == 200
    except Exception:
        return False


def queue_prompt(workflow: dict) -> str:
    payload = json.dumps({"prompt": workflow}).encode()
    req = urllib.request.Request(
        f"{COMFYUI_URL}/prompt",
        data=payload,
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read())
        return data["prompt_id"]
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")[:2000]
        logger.error("  ComfyUI rejected prompt (HTTP %d): %s", e.code, body)
        raise


def poll_history(prompt_id: str, timeout: int = 600, interval: int = 10) -> dict | None:
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
                    msgs = status.get("messages", [])
                    for m in msgs:
                        if m[0] == "execution_error":
                            logger.error("  Error: %s", m[1].get("exception_message", "")[:200])
                    return None
        except Exception:
            pass
        time.sleep(interval)
    logger.error("  Timed out after %ds", timeout)
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


def upload_image(image_path: Path) -> str:
    """Upload an image to ComfyUI and return the filename."""
    with open(image_path, "rb") as f:
        img_data = f.read()

    boundary = "----FormBoundary7MA4YWxkTrZu0gW"
    filename = image_path.name
    body = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="image"; filename="{filename}"\r\n'
        f"Content-Type: image/png\r\n\r\n"
    ).encode() + img_data + f"\r\n--{boundary}--\r\n".encode()

    req = urllib.request.Request(
        f"{COMFYUI_URL}/upload/image",
        data=body,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        result = json.loads(resp.read())
    return result["name"]


def download_glb(history_entry: dict, output_path: Path,
                 target_node: str | None = None,
                 filename_prefix: str | None = None) -> bool:
    """Download GLB from ComfyUI output."""
    outputs = history_entry.get("outputs", {})
    nodes_to_check = [target_node] if target_node else list(outputs.keys())

    for node_id in nodes_to_check:
        node_out = outputs.get(node_id, {})
        gltf_list = node_out.get("3d", node_out.get("gltf", node_out.get("mesh", [])))
        for glb_info in gltf_list:
            filename = glb_info.get("filename", "")
            subfolder = glb_info.get("subfolder", "")
            glb_type = glb_info.get("type", "output")
            url = f"{COMFYUI_URL}/view?filename={filename}&subfolder={subfolder}&type={glb_type}"
            try:
                with urllib.request.urlopen(url, timeout=60) as resp:
                    output_path.parent.mkdir(parents=True, exist_ok=True)
                    with open(output_path, "wb") as f:
                        f.write(resp.read())
                    size_mb = output_path.stat().st_size / (1024 * 1024)
                    logger.info("  Saved: %s (%.1f MB)", output_path.name, size_mb)
                    return True
            except Exception as e:
                logger.error("  Download via API failed: %s", e)

    # Fallback: scan ComfyUI output directory
    if filename_prefix:
        prefix_path = COMFYUI_OUTPUT / filename_prefix
        search_dir = prefix_path.parent
        base_name = prefix_path.name
        if search_dir.exists():
            matches = sorted(
                search_dir.glob(f"{base_name}_*.glb"),
                key=lambda p: p.stat().st_mtime,
                reverse=True,
            )
            if matches:
                src = matches[0]
                output_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, output_path)
                size_mb = output_path.stat().st_size / (1024 * 1024)
                logger.info("  Saved: %s (%.1f MB) [from %s]", output_path.name, size_mb, src.name)
                return True

    logger.error("  No GLB output found")
    return False


# ---- Concept Art Generation (Flux) ----

def build_concept_prompt(char: dict) -> str:
    """Build a full-body T-pose concept art prompt."""
    # Filter out weapon/equipment references for T-pose
    weapon_keywords = {"staff", "shield", "axe", "seax", "bow", "spear", "sword",
                       "weapon", "dual-wield", "hammer", "warhammer", "buckler",
                       "bowl", "horn"}
    identity = ", ".join(
        feat for feat in char["identity_features"]
        if not any(kw in feat.lower() for kw in weapon_keywords)
    )
    subject = (
        f"FULL BODY character illustration of {char['name']}, {identity}, "
        f"standing in T-pose arms extended straight out to sides at shoulder height palms facing down, "
        f"legs slightly apart, hands open and empty, no weapons no shields no staffs, "
        f"symmetrical front-facing view, full body visible from head to feet including boots, "
        f"NOT cropped NOT cut off, plain white background, isolated character on white, "
        f"no background elements no scenery, character design reference sheet style"
    )
    return STYLE_PREFIX.format(subject=subject, color_accent=char["color_accent"])


def build_flux_workflow(prompt: str, seed: int, filename_prefix: str) -> dict:
    """Build a Flux image generation workflow."""
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


# ---- GLB Generation (Hunyuan3D v2.0 textured pipeline) ----

def _load_workflow(name: str) -> dict:
    path = WORKFLOW_DIR / f"{name}.json"
    if not path.exists():
        raise FileNotFoundError(f"Workflow not found: {path}")
    with open(path) as f:
        return json.load(f)


def _substitute_params(workflow: dict, params: dict) -> dict:
    import copy
    wf = copy.deepcopy(workflow)
    for node_id, node in wf.items():
        inputs = node.get("inputs", {})
        for key, value in list(inputs.items()):
            if isinstance(value, str) and value.startswith("PARAM_"):
                if value in params:
                    inputs[key] = params[value]
    return wf


def build_textured_workflow(image_name: str, filename_prefix: str, seed: int = 42) -> dict:
    """Build Hunyuan3D v2.0 textured pipeline workflow."""
    wf = _load_workflow("hunyuan3d_v20_image_to_3d")
    params = {
        "PARAM_STR_IMAGE_PATH": image_name,
        "PARAM_FLOAT_GUIDANCE_SCALE": 5.5,
        "PARAM_INT_STEPS": 50,
        "PARAM_INT_SEED": seed,
        "PARAM_INT_OCTREE_RESOLUTION": 384,
        "PARAM_INT_MAX_FACES": 50000,
    }
    wf = _substitute_params(wf, params)
    wf["11"]["inputs"]["filename_prefix"] = f"3D/{filename_prefix}_geometry"
    wf["24"]["inputs"]["filename_prefix"] = f"3D/{filename_prefix}_textured"
    return wf


# ---- Main Pipeline ----

def generate_concept_art(char: dict, dry_run: bool = False) -> Path | None:
    """Generate concept art PNG for a character. Returns path on success."""
    output_path = char["concept_dir"] / f"{char['id']}.png"
    if output_path.exists():
        logger.info("  Concept art already exists: %s", output_path)
        return output_path

    prompt = build_concept_prompt(char)
    seed = seed_for_name(char["name"]) + 7000  # Unique seed offset for missing chars

    if dry_run:
        logger.info("  DRY RUN — prompt: %s...", prompt[:120])
        return None

    workflow = build_flux_workflow(prompt, seed, f"Berserkr_Missing_{char['id']}")

    try:
        prompt_id = queue_prompt(workflow)
        logger.info("  Queued concept: %s", prompt_id[:11])
        history = poll_history(prompt_id, timeout=900, interval=10)
        if history and download_image(history, output_path):
            return output_path
        else:
            logger.error("  FAILED concept art for %s", char["id"])
            return None
    except Exception as e:
        logger.error("  FAILED concept art for %s: %s", char["id"], e)
        return None


def generate_glb(char: dict, concept_path: Path, dry_run: bool = False) -> Path | None:
    """Generate textured GLB from concept art. Returns path on success."""
    output_path = char["model_dir"] / f"{char['id']}.glb"
    if output_path.exists():
        logger.info("  GLB already exists: %s", output_path)
        return output_path

    if dry_run:
        logger.info("  DRY RUN — would convert %s to GLB", concept_path.name)
        return None

    # Check for textured workflow
    wf_path = WORKFLOW_DIR / "hunyuan3d_v20_image_to_3d.json"
    if not wf_path.exists():
        logger.error("  Textured workflow not found at %s", wf_path)
        return None

    try:
        uploaded_name = upload_image(concept_path)
        logger.info("  Uploaded: %s", uploaded_name)

        prefix = f"Hy3D_missing_{char['id']}"
        seed = hash(char["id"]) % (2**32)
        workflow = build_textured_workflow(uploaded_name, prefix, seed)

        prompt_id = queue_prompt(workflow)
        logger.info("  Queued GLB: %s", prompt_id[:11])

        history = poll_history(prompt_id, timeout=900, interval=15)
        if history and download_glb(history, output_path,
                                    target_node="24",
                                    filename_prefix=f"3D/{prefix}_textured"):
            return output_path
        else:
            logger.error("  FAILED GLB for %s", char["id"])
            return None
    except Exception as e:
        logger.error("  FAILED GLB for %s: %s", char["id"], e)
        return None


def main():
    parser = argparse.ArgumentParser(description="Generate missing Berserkr character assets")
    parser.add_argument("--dry-run", action="store_true", help="Print what would be done")
    parser.add_argument("--character", type=str, default=None,
                        help="Generate only this character ID")
    parser.add_argument("--step", type=str, default="all",
                        choices=["concept", "glb", "all"],
                        help="Which step to run (default: all)")
    args = parser.parse_args()

    if not args.dry_run and not check_comfyui():
        logger.error("ComfyUI is not running at %s", COMFYUI_URL)
        sys.exit(1)

    targets = MISSING_CHARACTERS
    if args.character:
        targets = [c for c in targets if c["id"] == args.character]
        if not targets:
            logger.error("Unknown character: %s", args.character)
            logger.info("Available: %s", ", ".join(c["id"] for c in MISSING_CHARACTERS))
            sys.exit(1)

    logger.info("=" * 60)
    logger.info("Generating %d missing characters [step=%s]", len(targets), args.step)
    logger.info("=" * 60)

    results = {"concept_ok": 0, "concept_fail": 0, "glb_ok": 0, "glb_fail": 0}
    start_time = time.time()

    for i, char in enumerate(targets, 1):
        logger.info("")
        logger.info("[%d/%d] %s (%s) — %s", i, len(targets), char["name"], char["id"], char["type"])

        concept_path = char["concept_dir"] / f"{char['id']}.png"

        # Step 1: Concept art
        if args.step in ("concept", "all"):
            result = generate_concept_art(char, dry_run=args.dry_run)
            if result:
                concept_path = result
                results["concept_ok"] += 1
            elif not args.dry_run and not concept_path.exists():
                results["concept_fail"] += 1
                logger.error("  Skipping GLB — no concept art")
                continue

        # Step 2: GLB
        if args.step in ("glb", "all"):
            if not concept_path.exists():
                logger.error("  No concept art at %s — run with --step concept first", concept_path)
                results["glb_fail"] += 1
                continue
            result = generate_glb(char, concept_path, dry_run=args.dry_run)
            if result:
                results["glb_ok"] += 1
            elif not args.dry_run:
                results["glb_fail"] += 1

        # Brief delay between generations
        if i < len(targets) and not args.dry_run:
            time.sleep(3)

    elapsed = time.time() - start_time
    logger.info("")
    logger.info("=" * 60)
    logger.info("COMPLETE in %.1fs", elapsed)
    if args.step in ("concept", "all"):
        logger.info("  Concept art: %d ok, %d failed", results["concept_ok"], results["concept_fail"])
    if args.step in ("glb", "all"):
        logger.info("  GLBs: %d ok, %d failed", results["glb_ok"], results["glb_fail"])
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
