"""Batch convert 2D sprite images to 3D GLB models using Hunyuan3D v2.0.

Supports two modes:
  - textured (default): Full pipeline with background removal, mesh generation,
    delighting, multi-view texture sampling, baking, and inpainting.
    Uses the Hy3DWrapper nodes from ComfyUI-Hunyuan3DWrapper.
    ~5 min per model on RTX 3070.

  - geometry-only (--geometry-only): Fast mesh generation without textures.
    Uses the ImageOnlyCheckpointLoader repackaged workflow.
    ~1 min per model but produces white/untextured GLBs.

Usage:
    python hunyuan3d_batch_convert.py [--dry-run] [--asset-type TYPE] [--character ID]
    python hunyuan3d_batch_convert.py --asset-type characters --force
    python hunyuan3d_batch_convert.py --geometry-only --asset-type creatures

    TYPE: characters, creatures, equipment, all (default: all)
"""

import argparse
import copy
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
GAME_ASSETS = GODOT_PROJECT / "games" / "berserkr" / "assets"
WORKFLOW_DIR = Path(__file__).resolve().parent.parent.parent.parent / "workflows" / "mcp"

# Repackaged checkpoint (geometry-only mode)
CHECKPOINT_REPACKAGED = "hunyuan3d-dit-v2_fp16.safetensors"


def check_comfyui() -> bool:
    try:
        with urllib.request.urlopen(f"{COMFYUI_URL}/system_stats", timeout=5) as resp:
            return resp.status == 200
    except Exception:
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


# ---------------------------------------------------------------------------
# Workflow builders
# ---------------------------------------------------------------------------

def _load_workflow(name: str) -> dict:
    """Load a workflow JSON from the workflows/mcp directory."""
    path = WORKFLOW_DIR / f"{name}.json"
    if not path.exists():
        raise FileNotFoundError(f"Workflow not found: {path}")
    with open(path) as f:
        return json.load(f)


def _substitute_params(workflow: dict, params: dict) -> dict:
    """Deep-substitute PARAM_* placeholder strings in a workflow dict."""
    wf = copy.deepcopy(workflow)
    for node_id, node in wf.items():
        inputs = node.get("inputs", {})
        for key, value in list(inputs.items()):
            if isinstance(value, str) and value.startswith("PARAM_"):
                if value in params:
                    inputs[key] = params[value]
    return wf


def build_textured_workflow(
    image_name: str,
    filename_prefix: str,
    seed: int = 42,
    guidance_scale: float = 5.5,
    steps: int = 50,
    octree_resolution: int = 384,
    max_faces: int = 50000,
) -> dict:
    """Build the full Hunyuan3D v2.0 textured pipeline workflow.

    Loads the workflow JSON from workflows/mcp/hunyuan3d_v20_image_to_3d.json
    and substitutes parameters. Produces both geometry-only (node 11) and
    textured (node 24) GLB outputs.
    """
    wf = _load_workflow("hunyuan3d_v20_image_to_3d")

    params = {
        "PARAM_STR_IMAGE_PATH": image_name,
        "PARAM_FLOAT_GUIDANCE_SCALE": guidance_scale,
        "PARAM_INT_STEPS": steps,
        "PARAM_INT_SEED": seed,
        "PARAM_INT_OCTREE_RESOLUTION": octree_resolution,
        "PARAM_INT_MAX_FACES": max_faces,
    }

    wf = _substitute_params(wf, params)

    # Update output filename prefixes
    wf["11"]["inputs"]["filename_prefix"] = f"3D/{filename_prefix}_geometry"
    wf["24"]["inputs"]["filename_prefix"] = f"3D/{filename_prefix}_textured"

    return wf


def build_geometry_workflow(image_name: str, filename_prefix: str, seed: int = 42) -> dict:
    """Build the fast geometry-only workflow using ImageOnlyCheckpointLoader.

    This is the legacy pipeline — produces untextured white GLBs.
    """
    return {
        "54": {
            "inputs": {"ckpt_name": CHECKPOINT_REPACKAGED},
            "class_type": "ImageOnlyCheckpointLoader",
        },
        "56": {
            "inputs": {"image": image_name, "upload": "image"},
            "class_type": "LoadImage",
        },
        "70": {
            "inputs": {"model": ["54", 0], "shift": 1.0},
            "class_type": "ModelSamplingAuraFlow",
        },
        "51": {
            "inputs": {"clip_vision": ["54", 1], "image": ["56", 0], "crop": "none"},
            "class_type": "CLIPVisionEncode",
        },
        "66": {
            "inputs": {"resolution": 3072, "batch_size": 1},
            "class_type": "EmptyLatentHunyuan3Dv2",
        },
        "80": {
            "inputs": {"clip_vision_output": ["51", 0]},
            "class_type": "Hunyuan3Dv2Conditioning",
        },
        "3": {
            "inputs": {
                "seed": seed,
                "steps": 20,
                "cfg": 7.0,
                "sampler_name": "euler",
                "scheduler": "normal",
                "denoise": 1.0,
                "model": ["70", 0],
                "positive": ["80", 0],
                "negative": ["80", 1],
                "latent_image": ["66", 0],
            },
            "class_type": "KSampler",
        },
        "61": {
            "inputs": {
                "samples": ["3", 0],
                "vae": ["54", 2],
                "num_chunks": 8000,
                "octree_resolution": 256,
            },
            "class_type": "VAEDecodeHunyuan3D",
        },
        "81": {
            "inputs": {
                "voxel": ["61", 0],
                "algorithm": "surface net",
                "threshold": 0.6,
            },
            "class_type": "VoxelToMesh",
        },
        "82": {
            "inputs": {
                "filename_prefix": filename_prefix,
                "mesh": ["81", 0],
            },
            "class_type": "SaveGLB",
        },
    }


# ---------------------------------------------------------------------------
# ComfyUI interaction
# ---------------------------------------------------------------------------

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


def cancel_prompt(prompt_id: str) -> None:
    """Interrupt running job and clear pending queue to avoid backlog."""
    try:
        urllib.request.urlopen(
            urllib.request.Request(f"{COMFYUI_URL}/interrupt", method="POST"),
            timeout=5,
        )
    except Exception:
        pass
    try:
        req = urllib.request.Request(
            f"{COMFYUI_URL}/queue",
            data=json.dumps({"clear": True}).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        urllib.request.urlopen(req, timeout=5)
    except Exception:
        pass
    # Give ComfyUI a moment to settle
    time.sleep(3)


COMFYUI_OUTPUT = Path("D:/Projects/ComfyUI/output")


def download_glb(history_entry: dict, output_path: Path, target_node: str | None = None,
                 filename_prefix: str | None = None) -> bool:
    """Download GLB from ComfyUI output directory.

    First tries the history outputs API (works for SaveGLB).
    Falls back to scanning the ComfyUI output directory for files matching
    the filename_prefix (needed for Hy3DExportMesh which returns STRING).

    Args:
        history_entry: The completed prompt history entry.
        output_path: Where to save the GLB file.
        target_node: If set, only look at this node's output via history API.
        filename_prefix: Prefix used by Hy3DExportMesh (e.g. "3D/Hy3D_foo_textured").
    """
    # Method 1: Try history outputs API (SaveGLB uses '3d' key)
    outputs = history_entry.get("outputs", {})
    nodes_to_check = [target_node] if target_node else list(outputs.keys())

    for node_id in nodes_to_check:
        node_out = outputs.get(node_id, {})
        # SaveGLB and Hy3DExportMesh may use '3d', 'gltf', or 'mesh' keys
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

    # Method 2: Scan ComfyUI output directory for Hy3DExportMesh files
    if filename_prefix:
        # Hy3DExportMesh writes to output/<prefix>_NNNNN_.glb
        prefix_path = COMFYUI_OUTPUT / filename_prefix
        search_dir = prefix_path.parent
        base_name = prefix_path.name
        if search_dir.exists():
            # Find the most recent matching GLB
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


# ---------------------------------------------------------------------------
# Asset collection
# ---------------------------------------------------------------------------

def collect_assets(asset_type: str, character_filter: str = None) -> list[dict]:
    """Collect all assets that need 3D conversion."""
    assets = []

    if asset_type in ("characters", "all"):
        # Character classes
        classes_dir = GAME_ASSETS / "sprites" / "characters" / "concepts" / "classes"
        if classes_dir.exists():
            for png in sorted(classes_dir.glob("*.png")):
                char_id = png.stem
                if character_filter and char_id != character_filter:
                    continue
                assets.append({
                    "id": char_id,
                    "type": "characters",
                    "subcategory": "classes",
                    "source": png,
                    "output": GAME_ASSETS / "models" / "characters" / "classes" / f"{char_id}.glb",
                })

        # Character NPCs
        npcs_dir = GAME_ASSETS / "sprites" / "characters" / "concepts" / "npcs"
        if npcs_dir.exists():
            for png in sorted(npcs_dir.glob("*.png")):
                char_id = png.stem
                if character_filter and char_id != character_filter:
                    continue
                assets.append({
                    "id": char_id,
                    "type": "characters",
                    "subcategory": "npcs",
                    "source": png,
                    "output": GAME_ASSETS / "models" / "characters" / "npcs" / f"{char_id}.glb",
                })

    if asset_type in ("creatures", "all"):
        creatures_base = GAME_ASSETS / "sprites" / "creatures"
        if creatures_base.exists():
            for realm_dir in sorted(creatures_base.iterdir()):
                if not realm_dir.is_dir() or realm_dir.name.startswith("_"):
                    continue
                for png in sorted(realm_dir.glob("*.png")):
                    creature_id = png.stem
                    if character_filter and creature_id != character_filter:
                        continue
                    assets.append({
                        "id": creature_id,
                        "type": "creatures",
                        "subcategory": realm_dir.name,
                        "source": png,
                        "output": GAME_ASSETS / "models" / "creatures" / realm_dir.name / f"{creature_id}.glb",
                    })

    if asset_type in ("equipment", "all"):
        equipment_base = GAME_ASSETS / "sprites" / "equipment"
        if equipment_base.exists():
            for cat_dir in sorted(equipment_base.iterdir()):
                if not cat_dir.is_dir() or cat_dir.name.startswith("_"):
                    continue
                for png in sorted(cat_dir.glob("*.png")):
                    item_id = png.stem
                    if character_filter and item_id != character_filter:
                        continue
                    assets.append({
                        "id": item_id,
                        "type": "equipment",
                        "subcategory": cat_dir.name,
                        "source": png,
                        "output": GAME_ASSETS / "models" / "equipment" / cat_dir.name / f"{item_id}.glb",
                    })

    return assets


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Batch convert sprites to 3D GLB via Hunyuan3D v2")
    parser.add_argument("--dry-run", action="store_true", help="List assets only, don't convert")
    parser.add_argument("--asset-type", type=str, default="all",
                        choices=["characters", "creatures", "equipment", "all"],
                        help="Asset type to convert (default: all)")
    parser.add_argument("--character", type=str, default=None, help="Convert only this ID")
    parser.add_argument("--force", action="store_true", help="Overwrite existing GLBs")
    parser.add_argument("--geometry-only", action="store_true",
                        help="Use fast geometry-only pipeline (no textures, produces white GLBs)")
    parser.add_argument("--guidance-scale", type=float, default=5.5,
                        help="Guidance scale for mesh generation (default: 5.5)")
    parser.add_argument("--steps", type=int, default=50,
                        help="Diffusion steps for mesh generation (default: 50)")
    parser.add_argument("--octree-resolution", type=int, default=384,
                        help="Octree resolution for VAE decode (default: 384, range 128-512)")
    parser.add_argument("--skip-newer-than", type=str, default=None,
                        help="Skip GLBs modified after this date (YYYY-MM-DD)")
    parser.add_argument("--max-faces", type=int, default=50000,
                        help="Maximum face count after decimation (default: 50000)")
    args = parser.parse_args()

    mode = "geometry-only" if args.geometry_only else "textured"
    logger.info("Mode: %s", mode)

    if not args.geometry_only:
        wf_path = WORKFLOW_DIR / "hunyuan3d_v20_image_to_3d.json"
        if not wf_path.exists():
            logger.error("Textured workflow not found: %s", wf_path)
            logger.error("Falling back to geometry-only mode.")
            args.geometry_only = True
            mode = "geometry-only (fallback)"

    if not args.dry_run and not check_comfyui():
        logger.error("ComfyUI is not running at %s", COMFYUI_URL)
        sys.exit(1)

    assets = collect_assets(args.asset_type, args.character)
    if not assets:
        logger.error("No assets found for type=%s", args.asset_type)
        sys.exit(1)

    # Backup existing GLBs before overwriting
    if args.force:
        backup_dir = GAME_ASSETS / "models" / "_backup_pre_textured"
        for asset in assets:
            if asset["output"].exists():
                dest = backup_dir / asset["output"].relative_to(GAME_ASSETS / "models")
                dest.parent.mkdir(parents=True, exist_ok=True)
                if not dest.exists():
                    shutil.copy2(asset["output"], dest)
                    logger.info("  Backed up: %s", dest.name)

    # Filter out existing unless --force
    if not args.force:
        before = len(assets)
        assets = [a for a in assets if not a["output"].exists()]
        skipped = before - len(assets)
        if skipped:
            logger.info("Skipping %d existing GLBs (use --force to overwrite)", skipped)

    # Skip GLBs that were recently regenerated (modified after cutoff date)
    if args.skip_newer_than:
        from datetime import datetime
        cutoff = datetime.strptime(args.skip_newer_than, "%Y-%m-%d").timestamp()
        before = len(assets)
        assets = [a for a in assets if not a["output"].exists()
                  or a["output"].stat().st_mtime < cutoff]
        skipped = before - len(assets)
        if skipped:
            logger.info("Skipping %d GLBs newer than %s", skipped, args.skip_newer_than)

    logger.info("Processing %d assets [type=%s, mode=%s]", len(assets), args.asset_type, mode)

    if args.dry_run:
        for i, asset in enumerate(assets, 1):
            logger.info("[%d/%d] %s (%s/%s) -> %s",
                        i, len(assets), asset["id"], asset["type"], asset["subcategory"],
                        asset["output"].name)
        est_time = len(assets) * (60 if args.geometry_only else 300)
        logger.info("DRY RUN -- %d assets would be converted (~%dm estimated)", len(assets), est_time // 60)
        return

    converted = 0
    failed = 0
    start_time = time.time()
    manifest = []

    # Textured pipeline is slower: longer poll interval and timeout
    poll_interval = 10 if args.geometry_only else 15
    poll_timeout = 600 if args.geometry_only else 900

    for i, asset in enumerate(assets, 1):
        logger.info("[%d/%d] Processing %s (%s/%s) [%s]",
                    i, len(assets), asset["id"], asset["type"], asset["subcategory"], mode)
        asset_start = time.time()

        try:
            # Upload source image
            uploaded_name = upload_image(asset["source"])
            logger.info("  Uploaded: %s", uploaded_name)

            # Build and queue workflow
            prefix = f"Hy3D_{asset['type']}_{asset['id']}"
            seed = hash(asset["id"]) % (2**32)

            if args.geometry_only:
                workflow = build_geometry_workflow(uploaded_name, f"mesh/{prefix}", seed)
                target_node = None  # SaveGLB is the only output
                glb_prefix = None
            else:
                workflow = build_textured_workflow(
                    uploaded_name, prefix, seed,
                    guidance_scale=args.guidance_scale,
                    steps=args.steps,
                    octree_resolution=args.octree_resolution,
                    max_faces=args.max_faces,
                )
                target_node = "24"  # Textured GLB output node
                glb_prefix = f"3D/{prefix}_textured"

            prompt_id = queue_prompt(workflow)
            logger.info("  Queued: %s", prompt_id[:11])

            # Wait for completion
            history = poll_history(prompt_id, timeout=poll_timeout, interval=poll_interval)
            if history and download_glb(history, asset["output"],
                                        target_node=target_node,
                                        filename_prefix=glb_prefix):
                asset_elapsed = time.time() - asset_start
                converted += 1
                manifest.append({
                    "id": asset["id"],
                    "type": asset["type"],
                    "subcategory": asset["subcategory"],
                    "source": str(asset["source"]),
                    "glb_path": str(asset["output"]),
                    "mode": mode,
                    "elapsed_seconds": round(asset_elapsed, 1),
                    "status": "converted",
                })
                logger.info("  Done in %.0fs", asset_elapsed)
            else:
                logger.error("  FAILED: %s", asset["id"])
                cancel_prompt(prompt_id)
                failed += 1
                manifest.append({
                    "id": asset["id"],
                    "type": asset["type"],
                    "subcategory": asset["subcategory"],
                    "source": str(asset["source"]),
                    "status": "failed",
                })
        except Exception as e:
            logger.error("  FAILED: %s -- %s", asset["id"], e)
            failed += 1
            manifest.append({
                "id": asset["id"],
                "type": asset["type"],
                "subcategory": asset["subcategory"],
                "source": str(asset["source"]),
                "status": f"error: {e}",
            })

        # Brief pause between conversions
        if i < len(assets):
            time.sleep(3)

    elapsed = time.time() - start_time
    logger.info("")
    logger.info("=" * 60)
    logger.info("COMPLETE -- %d converted, %d failed in %.1fs (%.1fs/model avg)",
                converted, failed, elapsed,
                elapsed / max(converted, 1))
    logger.info("Mode: %s", mode)
    logger.info("=" * 60)

    # Save manifest
    manifest_path = GAME_ASSETS / "models" / f"hunyuan3d_manifest_{args.asset_type}.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    with open(manifest_path, "w") as f:
        json.dump({
            "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "mode": mode,
            "total_elapsed_seconds": round(elapsed, 1),
            "converted": converted,
            "failed": failed,
            "parameters": {
                "guidance_scale": args.guidance_scale,
                "steps": args.steps,
                "octree_resolution": args.octree_resolution,
                "max_faces": args.max_faces,
            } if not args.geometry_only else {},
            "entries": manifest,
        }, f, indent=2)
    logger.info("Manifest: %s", manifest_path)


if __name__ == "__main__":
    main()
