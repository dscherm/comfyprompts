"""Batch submit Hunyuan3D v2.0 geometry-only jobs for 8 characters.

Uploads each character's fullbody image to ComfyUI, substitutes parameters
into the geometry-only workflow, queues the prompt, polls for completion,
and copies the output GLB to each character's 3d/ folder.

Usage:
    python batch_hunyuan3d.py
    python batch_hunyuan3d.py --dry-run
    python batch_hunyuan3d.py --characters bones,crank
"""

import argparse
import copy
import json
import logging
import os
import random
import shutil
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

COMFYUI_URL = "http://localhost:8188"
COMFYUI_OUTPUT = Path("D:/Projects/ComfyUI/output")

PIPELINE_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_ROOT = PIPELINE_ROOT / "output"
WORKFLOW_DIR = Path(__file__).resolve().parent.parent.parent.parent / "workflows" / "mcp"

CHARACTERS = ["bones", "crank", "grit", "pip", "punk_king", "rust", "smog", "sparks"]

# Defaults matching the meta.json
GUIDANCE_SCALE = 5.5
STEPS = 50
OCTREE_RESOLUTION = 256
MAX_FACES = 50000


# ---------------------------------------------------------------------------
# ComfyUI helpers
# ---------------------------------------------------------------------------

def check_comfyui() -> bool:
    try:
        with urllib.request.urlopen(f"{COMFYUI_URL}/system_stats", timeout=5) as resp:
            return resp.status == 200
    except Exception:
        return False


def upload_image(image_path: Path) -> str:
    """Upload an image to ComfyUI and return the server-side filename."""
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
            with urllib.request.urlopen(
                f"{COMFYUI_URL}/history/{prompt_id}", timeout=10
            ) as resp:
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
                            logger.error(
                                "  Error: %s",
                                m[1].get("exception_message", "")[:300],
                            )
                    return None
        except Exception:
            pass
        time.sleep(interval)
    logger.error("  Timed out after %ds", timeout)
    return None


# ---------------------------------------------------------------------------
# Workflow builder
# ---------------------------------------------------------------------------

def load_workflow() -> dict:
    path = WORKFLOW_DIR / "hunyuan3d_v20_geometry_only.json"
    if not path.exists():
        raise FileNotFoundError(f"Workflow not found: {path}")
    with open(path) as f:
        return json.load(f)


def build_workflow(
    image_name: str,
    filename_prefix: str,
    seed: int = 42,
) -> dict:
    """Build geometry-only workflow with parameter substitution."""
    wf = copy.deepcopy(load_workflow())

    params = {
        "PARAM_STR_IMAGE_PATH": image_name,
        "PARAM_FLOAT_GUIDANCE_SCALE": GUIDANCE_SCALE,
        "PARAM_INT_STEPS": STEPS,
        "PARAM_INT_SEED": seed,
        "PARAM_INT_OCTREE_RESOLUTION": OCTREE_RESOLUTION,
        "PARAM_INT_MAX_FACES": MAX_FACES,
    }

    for node_id, node in wf.items():
        inputs = node.get("inputs", {})
        for key, value in list(inputs.items()):
            if isinstance(value, str) and value.startswith("PARAM_"):
                if value in params:
                    inputs[key] = params[value]

    # Set unique output filename prefix
    wf["11"]["inputs"]["filename_prefix"] = filename_prefix

    return wf


# ---------------------------------------------------------------------------
# GLB retrieval
# ---------------------------------------------------------------------------

def find_and_copy_glb(
    history_entry: dict, filename_prefix: str, dest: Path
) -> bool:
    """Find the generated GLB and copy it to dest.

    Tries two methods:
    1. History outputs API (node 11 outputs)
    2. Filesystem scan of ComfyUI output directory
    """
    # Method 1: History outputs API
    outputs = history_entry.get("outputs", {})
    node_out = outputs.get("11", {})
    # Hy3DExportMesh may output via 'text' (filepath string) or '3d'/'gltf' keys
    for key in ("3d", "gltf", "mesh"):
        items = node_out.get(key, [])
        for item in items:
            filename = item.get("filename", "")
            subfolder = item.get("subfolder", "")
            glb_type = item.get("type", "output")
            url = f"{COMFYUI_URL}/view?filename={filename}&subfolder={subfolder}&type={glb_type}"
            try:
                with urllib.request.urlopen(url, timeout=60) as resp:
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    with open(dest, "wb") as f:
                        f.write(resp.read())
                    size_mb = dest.stat().st_size / (1024 * 1024)
                    logger.info("  Saved via API: %s (%.1f MB)", dest, size_mb)
                    return True
            except Exception as e:
                logger.debug("  API download failed: %s", e)

    # Method 2: Hy3DExportMesh outputs a text string with the file path
    text_list = node_out.get("text", [])
    for text_item in text_list:
        # text_item is a string containing the full path to the exported file
        src = Path(text_item) if isinstance(text_item, str) else None
        if src and src.exists():
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dest)
            size_mb = dest.stat().st_size / (1024 * 1024)
            logger.info("  Copied from text output: %s (%.1f MB)", dest, size_mb)
            return True

    # Method 3: Scan ComfyUI output directory for matching prefix
    # filename_prefix is e.g. "3D/chargen_bones" -> look in output/3D/ for chargen_bones*.glb
    parts = filename_prefix.split("/")
    if len(parts) == 2:
        scan_dir = COMFYUI_OUTPUT / parts[0]
        prefix = parts[1]
    else:
        scan_dir = COMFYUI_OUTPUT
        prefix = filename_prefix

    if scan_dir.exists():
        # Find the most recently modified GLB matching the prefix
        candidates = sorted(
            scan_dir.glob(f"{prefix}*.glb"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        if candidates:
            src = candidates[0]
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dest)
            size_mb = dest.stat().st_size / (1024 * 1024)
            logger.info("  Copied from filesystem: %s -> %s (%.1f MB)", src.name, dest, size_mb)
            return True

    logger.error("  Could not find output GLB for prefix=%s", filename_prefix)
    return False


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def process_character(char_id: str, dry_run: bool = False) -> bool:
    """Process a single character through the Hunyuan3D geometry-only pipeline."""
    image_path = OUTPUT_ROOT / char_id / "fullbody" / "fullbody.png"
    dest_glb = OUTPUT_ROOT / char_id / "3d" / "character-raw.glb"

    if not image_path.exists():
        logger.error("  Image not found: %s", image_path)
        return False

    if dest_glb.exists():
        logger.info("  Output already exists: %s (skipping, use --force to regenerate)", dest_glb)
        return True

    logger.info("  Input: %s", image_path)
    logger.info("  Output: %s", dest_glb)

    if dry_run:
        logger.info("  [DRY RUN] Would submit job")
        return True

    # Step 1: Upload image
    logger.info("  Uploading image...")
    try:
        uploaded_name = upload_image(image_path)
    except Exception as e:
        logger.error("  Upload failed: %s", e)
        return False
    logger.info("  Uploaded as: %s", uploaded_name)

    # Step 2: Build workflow
    seed = random.randint(1, 2**31 - 1)
    filename_prefix = f"3D/chargen_{char_id}"
    wf = build_workflow(uploaded_name, filename_prefix, seed=seed)
    logger.info("  Seed: %d, prefix: %s", seed, filename_prefix)

    # Step 3: Queue prompt
    try:
        prompt_id = queue_prompt(wf)
    except Exception as e:
        logger.error("  Queue failed: %s", e)
        return False
    logger.info("  Queued prompt: %s", prompt_id)

    # Step 4: Poll for completion
    logger.info("  Waiting for completion (timeout 600s)...")
    t0 = time.time()
    entry = poll_history(prompt_id, timeout=600, interval=10)
    elapsed = time.time() - t0

    if entry is None:
        logger.error("  Generation failed or timed out after %.0fs", elapsed)
        return False
    logger.info("  Completed in %.0fs", elapsed)

    # Step 5: Download/copy GLB
    return find_and_copy_glb(entry, filename_prefix, dest_glb)


def main():
    parser = argparse.ArgumentParser(description="Batch Hunyuan3D geometry-only for characters")
    parser.add_argument("--dry-run", action="store_true", help="Don't actually submit jobs")
    parser.add_argument("--force", action="store_true", help="Regenerate even if output exists")
    parser.add_argument(
        "--characters",
        type=str,
        default=None,
        help="Comma-separated list of character IDs (default: all 8)",
    )
    args = parser.parse_args()

    chars = args.characters.split(",") if args.characters else CHARACTERS

    if not check_comfyui():
        logger.error("ComfyUI is not reachable at %s", COMFYUI_URL)
        sys.exit(1)

    logger.info("ComfyUI is running at %s", COMFYUI_URL)
    logger.info("Processing %d characters: %s", len(chars), ", ".join(chars))

    if args.force:
        logger.info("Force mode: will regenerate existing outputs")

    results = {}
    for i, char_id in enumerate(chars, 1):
        logger.info("[%d/%d] Processing: %s", i, len(chars), char_id)

        # If force mode, remove existing output
        dest_glb = OUTPUT_ROOT / char_id / "3d" / "character-raw.glb"
        if args.force and dest_glb.exists():
            dest_glb.unlink()
            logger.info("  Removed existing output")

        success = process_character(char_id, dry_run=args.dry_run)
        results[char_id] = success
        if success:
            logger.info("[%d/%d] SUCCESS: %s", i, len(chars), char_id)
        else:
            logger.info("[%d/%d] FAILED: %s", i, len(chars), char_id)

    # Summary
    logger.info("=" * 60)
    logger.info("BATCH COMPLETE")
    succeeded = sum(1 for v in results.values() if v)
    failed = sum(1 for v in results.values() if not v)
    logger.info("  Succeeded: %d / %d", succeeded, len(results))
    if failed:
        logger.info("  Failed: %s", ", ".join(k for k, v in results.items() if not v))
    logger.info("=" * 60)

    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    main()
