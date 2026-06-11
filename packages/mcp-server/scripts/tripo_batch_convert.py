"""Batch 2D-to-3D converter for Berserkr game assets.

Supports characters, creatures, and equipment via two backends:
  - Tripo cloud API (image_to_model + optional auto-rig)
  - Local ComfyUI TripoSR workflow (image → remove bg → 3D mesh)

Usage:
    python tripo_batch_convert.py --asset-type characters                # All characters via Tripo
    python tripo_batch_convert.py --asset-type creatures --backend local  # Creatures via local ComfyUI
    python tripo_batch_convert.py --asset-type all --dry-run             # Preview everything
    python tripo_batch_convert.py --asset-type equipment --id iron_sword # Single item
    python tripo_batch_convert.py --asset-type characters --rig          # Convert + auto-rig
    python tripo_batch_convert.py --asset-type creatures --retry-failed  # Re-process failures

Environment:
    TRIPO_API_KEY - Your Tripo API key from platform.tripo3d.ai (required for tripo backend)
"""

import argparse
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

# --- Paths ---
GODOT_PROJECT = Path("D:/Projects/berserkr-godot")
SPRITES_DIR = GODOT_PROJECT / "assets" / "sprites"
MODELS_DIR = GODOT_PROJECT / "assets" / "models"

# Tripo API
TRIPO_BASE_URL = "https://api.tripo3d.ai/v2/openapi"

# Local ComfyUI TripoSR workflow
WORKFLOW_DIR = Path("D:/Projects/comfyui-toolchain/workflows/mcp")
WORKFLOW_TEMPLATE = WORKFLOW_DIR / "image_to_3d.json"

# Asset type configuration
CHARACTER_SUBCATEGORIES = ["classes", "npcs"]
CREATURE_REALMS = [
    "midgard", "jotunheim", "helheim", "niflheim", "muspelheim", "svartalfheim",
]
EQUIPMENT_CATEGORIES = [
    "weapons_melee", "weapons_ranged", "armor", "shields",
    "accessories", "quest_items", "consumables", "adventuring_gear",
]

# Default geometry resolution for local TripoSR
DEFAULT_RESOLUTION = 256
CONVERT_DELAY_SECONDS = 2


# =============================================================================
# Tripo Cloud API functions
# =============================================================================

def get_api_key() -> str:
    """Get Tripo API key from environment."""
    key = os.environ.get("TRIPO_API_KEY", "")
    if not key:
        logger.error("TRIPO_API_KEY environment variable not set!")
        logger.error("Get your key at: https://platform.tripo3d.ai/api-keys")
        sys.exit(1)
    return key


def upload_image(api_key: str, image_path: Path) -> str:
    """Upload an image to Tripo and return the file token."""
    import requests

    url = f"{TRIPO_BASE_URL}/upload"
    headers = {"Authorization": f"Bearer {api_key}"}

    with open(image_path, "rb") as f:
        resp = requests.post(url, headers=headers, files={"file": f}, timeout=60)

    resp.raise_for_status()
    data = resp.json()

    if data.get("code") != 0:
        raise RuntimeError(f"Upload failed: {data}")

    token = data["data"]["image_token"]
    logger.info("  Uploaded %s -> token: %s", image_path.name, token[:20] + "...")
    return token


def create_image_to_model_task(api_key: str, file_token: str) -> str:
    """Submit an image-to-model task and return the task ID."""
    import requests

    url = f"{TRIPO_BASE_URL}/task"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "type": "image_to_model",
        "file": {
            "type": "png",
            "file_token": file_token,
        },
    }

    resp = requests.post(url, headers=headers, json=payload, timeout=60)
    resp.raise_for_status()
    data = resp.json()

    if data.get("code") != 0:
        raise RuntimeError(f"Task creation failed: {data}")

    task_id = data["data"]["task_id"]
    logger.info("  Task created: %s", task_id)
    return task_id


def create_rig_task(api_key: str, original_task_id: str) -> str:
    """Submit an auto-rig task for a completed model."""
    import requests

    url = f"{TRIPO_BASE_URL}/task"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "type": "animate_rig",
        "original_model_task_id": original_task_id,
    }

    resp = requests.post(url, headers=headers, json=payload, timeout=60)
    resp.raise_for_status()
    data = resp.json()

    if data.get("code") != 0:
        raise RuntimeError(f"Rig task creation failed: {data}")

    task_id = data["data"]["task_id"]
    logger.info("  Rig task created: %s", task_id)
    return task_id


def poll_task(api_key: str, task_id: str, timeout_seconds: int = 300) -> dict:
    """Poll a task until completion or failure."""
    import requests

    url = f"{TRIPO_BASE_URL}/task/{task_id}"
    headers = {"Authorization": f"Bearer {api_key}"}
    start = time.time()

    while time.time() - start < timeout_seconds:
        resp = requests.get(url, headers=headers, timeout=30)
        resp.raise_for_status()
        data = resp.json()["data"]
        status = data["status"]

        if status == "success":
            return data
        elif status in ("failed", "cancelled", "unknown"):
            raise RuntimeError(f"Task {task_id} failed with status: {status}")

        progress = data.get("progress", 0)
        logger.info("  Task %s: %s (progress: %d%%)", task_id[:12], status, progress)
        time.sleep(5)

    raise TimeoutError(f"Task {task_id} timed out after {timeout_seconds}s")


def download_model(model_url: str, output_path: Path) -> Path:
    """Download a GLB model from a URL."""
    import requests

    output_path.parent.mkdir(parents=True, exist_ok=True)
    resp = requests.get(model_url, timeout=120)
    resp.raise_for_status()

    with open(output_path, "wb") as f:
        f.write(resp.content)

    size_kb = os.path.getsize(output_path) / 1024
    logger.info("  Downloaded model: %s (%.0f KB)", output_path.name, size_kb)
    return output_path


def check_balance(api_key: str) -> dict:
    """Check remaining Tripo credits."""
    import requests

    url = f"{TRIPO_BASE_URL}/user/balance"
    headers = {"Authorization": f"Bearer {api_key}"}
    resp = requests.get(url, headers=headers, timeout=30)
    resp.raise_for_status()
    data = resp.json()["data"]
    logger.info("Tripo credits -- Balance: %s, Frozen: %s",
                data.get("balance", "?"), data.get("frozen", "?"))
    return data


# =============================================================================
# Local ComfyUI TripoSR functions
# =============================================================================

def upload_image_to_comfyui(image_path: Path, comfyui_url: str) -> str:
    """Upload an image to ComfyUI via POST /upload/image.

    Returns the uploaded filename as reported by ComfyUI.
    """
    import io
    import uuid

    url = f"{comfyui_url}/upload/image"
    boundary = uuid.uuid4().hex

    # Build multipart form data manually for urllib
    body = io.BytesIO()
    filename = image_path.name

    # File field
    body.write(f"--{boundary}\r\n".encode())
    body.write(
        f'Content-Disposition: form-data; name="image"; filename="{filename}"\r\n'.encode()
    )
    body.write(b"Content-Type: image/png\r\n\r\n")
    with open(image_path, "rb") as f:
        body.write(f.read())
    body.write(b"\r\n")

    # Overwrite field — allow replacing existing uploads
    body.write(f"--{boundary}\r\n".encode())
    body.write(b'Content-Disposition: form-data; name="overwrite"\r\n\r\n')
    body.write(b"true\r\n")

    body.write(f"--{boundary}--\r\n".encode())

    data = body.getvalue()
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        method="POST",
    )

    resp = urllib.request.urlopen(req, timeout=60)
    result = json.loads(resp.read().decode())

    uploaded_name = result.get("name", filename)
    logger.info("  Uploaded %s to ComfyUI as: %s", filename, uploaded_name)
    return uploaded_name


def build_local_workflow(
    uploaded_image_name: str,
    resolution: int = DEFAULT_RESOLUTION,
    filename_prefix: str = "ComfyUI_3D",
) -> dict:
    """Build a TripoSR image-to-3D workflow using available ComfyUI nodes.

    Pipeline: LoadImage -> Image Rembg -> TripoSRSampler -> SaveGLB
    Node signatures verified against ComfyUI /object_info.
    """
    return {
        "1": {
            "inputs": {"image": uploaded_image_name, "upload": "image"},
            "class_type": "LoadImage",
            "_meta": {"title": "Load Image"},
        },
        "2": {
            "inputs": {"model": "tripoSR.ckpt", "chunk_size": 8192},
            "class_type": "TripoSRModelLoader",
            "_meta": {"title": "Load TripoSR Model"},
        },
        "3": {
            "inputs": {
                "images": ["1", 0],
                "transparency": True,
                "model": "u2net",
                "post_processing": False,
                "only_mask": False,
                "alpha_matting": False,
                "alpha_matting_foreground_threshold": 240,
                "alpha_matting_background_threshold": 10,
                "alpha_matting_erode_size": 10,
                "background_color": "none",
            },
            "class_type": "Image Rembg (Remove Background)",
            "_meta": {"title": "Remove Background"},
        },
        "4": {
            "inputs": {
                "model": ["2", 0],
                "reference_image": ["3", 0],
                "geometry_resolution": resolution,
                "threshold": 25.0,
            },
            "class_type": "TripoSRSampler",
            "_meta": {"title": "TripoSR Sampler"},
        },
        "5": {
            "inputs": {"mesh": ["4", 0]},
            "class_type": "TripoSRViewer",
            "_meta": {"title": "Save/View 3D Mesh"},
        },
    }


def queue_workflow(
    comfyui_url: str,
    uploaded_image_name: str,
    resolution: int = DEFAULT_RESOLUTION,
    filename_prefix: str = "ComfyUI_3D",
) -> str:
    """Build and queue a TripoSR workflow on ComfyUI.

    Returns the prompt_id.
    """
    workflow = build_local_workflow(uploaded_image_name, resolution, filename_prefix)

    payload = json.dumps({"prompt": workflow}).encode()
    req = urllib.request.Request(
        f"{comfyui_url}/prompt",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    resp = urllib.request.urlopen(req, timeout=60)
    result = json.loads(resp.read().decode())
    prompt_id = result["prompt_id"]
    logger.info("  Queued workflow, prompt_id: %s", prompt_id)
    return prompt_id


def poll_history(comfyui_url: str, prompt_id: str, timeout_seconds: int = 300) -> dict:
    """Poll ComfyUI /history/{prompt_id} until the workflow completes.

    Returns the history entry for the prompt.
    """
    url = f"{comfyui_url}/history/{prompt_id}"
    start = time.time()

    while time.time() - start < timeout_seconds:
        try:
            req = urllib.request.Request(url, method="GET")
            resp = urllib.request.urlopen(req, timeout=30)
            history = json.loads(resp.read().decode())

            if prompt_id in history:
                entry = history[prompt_id]
                status = entry.get("status", {})
                status_str = status.get("status_str", "")
                if status_str == "success" or status.get("completed", False):
                    logger.info("  Workflow completed")
                    return entry
                if status_str == "error":
                    raise RuntimeError(
                        f"Workflow {prompt_id} failed: {status.get('messages', '')}"
                    )
        except urllib.error.URLError:
            pass  # Server might be busy

        logger.info("  Waiting for workflow %s...", prompt_id[:12])
        time.sleep(5)

    raise TimeoutError(f"Workflow {prompt_id} timed out after {timeout_seconds}s")


def download_mesh(
    comfyui_url: str,
    history_entry: dict,
    output_path: Path,
) -> Path:
    """Extract mesh output from workflow history and save to output_path.

    TripoSRViewer saves .obj files and reports them in ui->mesh.
    We download the .obj and convert to .glb if output_path ends with .glb.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Find the mesh filename from TripoSRViewer's ui output
    mesh_filename = None

    # Check ui outputs first (TripoSRViewer returns {"ui": {"mesh": [...]}})
    outputs = history_entry.get("outputs", {})
    for node_id, node_output in outputs.items():
        if "mesh" in node_output:
            mesh_list = node_output["mesh"]
            if mesh_list and isinstance(mesh_list, list):
                mesh_filename = mesh_list[0].get("filename")
                break

    if not mesh_filename:
        # Fallback: scan for any file output with mesh extension
        for node_id, node_output in outputs.items():
            for key, val_list in node_output.items():
                if isinstance(val_list, list):
                    for item in val_list:
                        if isinstance(item, dict):
                            fn = item.get("filename", "")
                            if fn.endswith((".glb", ".obj", ".ply")):
                                mesh_filename = fn
                                break
                    if mesh_filename:
                        break
            if mesh_filename:
                break

    if not mesh_filename:
        raise RuntimeError(
            f"No mesh output found in workflow history. Output keys: "
            f"{[(nid, list(no.keys())) for nid, no in outputs.items()]}"
        )

    logger.info("  Mesh file: %s", mesh_filename)

    # Download from ComfyUI output directory
    # TripoSRViewer saves to ComfyUI's output folder
    comfyui_output = Path("D:/Projects/ComfYUI/output")
    source_file = comfyui_output / mesh_filename
    if not source_file.exists():
        # Try /view endpoint
        view_url = (
            f"{comfyui_url}/view?filename={urllib.request.quote(mesh_filename)}"
            f"&type=output&subfolder="
        )
        try:
            resp = urllib.request.urlopen(view_url, timeout=120)
            source_data = resp.read()
            # Save as temp .obj
            temp_obj = output_path.with_suffix(".obj")
            with open(temp_obj, "wb") as f:
                f.write(source_data)
            source_file = temp_obj
        except urllib.error.URLError as e:
            raise RuntimeError(
                f"Could not download mesh '{mesh_filename}': {e}"
            )

    # Convert .obj to .glb if needed
    if output_path.suffix == ".glb" and source_file.suffix == ".obj":
        try:
            import trimesh
            mesh = trimesh.load(str(source_file))
            mesh.export(str(output_path), file_type="glb")
            size_kb = os.path.getsize(output_path) / 1024
            logger.info("  Converted OBJ->GLB: %s (%.0f KB)", output_path.name, size_kb)
            return output_path
        except ImportError:
            # trimesh not available - save as .obj instead
            import shutil
            obj_path = output_path.with_suffix(".obj")
            shutil.copy2(source_file, obj_path)
            size_kb = os.path.getsize(obj_path) / 1024
            logger.info("  Saved OBJ (trimesh not available for GLB conversion): %s (%.0f KB)",
                        obj_path.name, size_kb)
            return obj_path
    else:
        import shutil
        shutil.copy2(source_file, output_path)
        size_kb = os.path.getsize(output_path) / 1024
        logger.info("  Saved mesh: %s (%.0f KB)", output_path.name, size_kb)
        return output_path


# =============================================================================
# Asset discovery
# =============================================================================

def find_character_images(specific_id: str = None) -> list[dict]:
    """Find character concept art images (classes + NPCs)."""
    entries = []
    characters_dir = SPRITES_DIR / "characters" / "concepts"

    for subcat in CHARACTER_SUBCATEGORIES:
        subdir = characters_dir / subcat
        if not subdir.exists():
            continue
        for png in sorted(subdir.glob("*.png")):
            cid = png.stem
            if specific_id and cid != specific_id:
                continue
            entries.append({
                "id": cid,
                "subcategory": subcat,
                "source_image": png,
                "output_glb": MODELS_DIR / "characters" / subcat / f"{cid}.glb",
                "output_rigged": MODELS_DIR / "characters" / subcat / f"{cid}_rigged.glb",
            })

    return entries


def find_creature_images(specific_id: str = None) -> list[dict]:
    """Find creature sprite images organized by realm."""
    entries = []
    creatures_dir = SPRITES_DIR / "creatures"

    for realm in CREATURE_REALMS:
        realm_dir = creatures_dir / realm
        if not realm_dir.exists():
            continue
        for png in sorted(realm_dir.glob("*.png")):
            cid = png.stem
            if specific_id and cid != specific_id:
                continue
            entries.append({
                "id": cid,
                "subcategory": realm,
                "source_image": png,
                "output_glb": MODELS_DIR / "creatures" / realm / f"{cid}.glb",
                "output_rigged": MODELS_DIR / "creatures" / realm / f"{cid}_rigged.glb",
            })

    return entries


def find_equipment_images(specific_id: str = None) -> list[dict]:
    """Find equipment sprite images organized by category."""
    entries = []
    equipment_dir = SPRITES_DIR / "equipment"

    for category in EQUIPMENT_CATEGORIES:
        cat_dir = equipment_dir / category
        if not cat_dir.exists():
            continue
        for png in sorted(cat_dir.glob("*.png")):
            cid = png.stem
            if specific_id and cid != specific_id:
                continue
            entries.append({
                "id": cid,
                "subcategory": category,
                "source_image": png,
                "output_glb": MODELS_DIR / "equipment" / category / f"{cid}.glb",
                "output_rigged": MODELS_DIR / "equipment" / category / f"{cid}_rigged.glb",
            })

    return entries


def find_source_images(asset_type: str, specific_id: str = None) -> list[dict]:
    """Find source images for the given asset type."""
    if asset_type == "characters":
        return find_character_images(specific_id)
    elif asset_type == "creatures":
        return find_creature_images(specific_id)
    elif asset_type == "equipment":
        return find_equipment_images(specific_id)
    elif asset_type == "all":
        entries = []
        entries.extend(find_character_images(specific_id))
        entries.extend(find_creature_images(specific_id))
        entries.extend(find_equipment_images(specific_id))
        return entries
    else:
        raise ValueError(f"Unknown asset type: {asset_type}")


def get_manifest_path(asset_type: str) -> Path:
    """Get the manifest file path for a given asset type."""
    if asset_type == "characters":
        return MODELS_DIR / "characters" / "tripo_manifest.json"
    elif asset_type == "creatures":
        return MODELS_DIR / "creatures" / "tripo_manifest.json"
    elif asset_type == "equipment":
        return MODELS_DIR / "equipment" / "tripo_manifest.json"
    else:
        raise ValueError(f"No single manifest for asset type: {asset_type}")


def load_manifest(manifest_path: Path) -> dict:
    """Load an existing manifest file, or return an empty structure."""
    if manifest_path.exists():
        with open(manifest_path, "r") as f:
            return json.load(f)
    return {"generated_at": None, "total_elapsed_seconds": 0, "entries": []}


def get_failed_ids(manifest_path: Path) -> list[str]:
    """Get IDs of failed entries from a manifest."""
    manifest = load_manifest(manifest_path)
    return [e["id"] for e in manifest.get("entries", []) if e.get("status") == "failed"]


# =============================================================================
# Conversion dispatcher
# =============================================================================

def convert_tripo(api_key: str, entry: dict, do_rig: bool = False) -> dict:
    """Convert a single asset via Tripo cloud API."""
    result = {
        "id": entry["id"],
        "subcategory": entry["subcategory"],
        "source": str(entry["source_image"]),
    }

    logger.info("CONVERT [tripo] %s (%s)", entry["id"], entry["subcategory"])

    try:
        # Step 1: Upload image
        file_token = upload_image(api_key, entry["source_image"])

        # Step 2: Create image-to-model task
        task_id = create_image_to_model_task(api_key, file_token)
        result["model_task_id"] = task_id

        # Step 3: Wait for completion
        task_data = poll_task(api_key, task_id, timeout_seconds=300)
        output = task_data.get("output", {})
        model_url = (
            output.get("model")
            or output.get("pbr_model")
            or output.get("base_model")
        )

        if not model_url:
            logger.error("  No model URL in task output keys: %s", list(output.keys()))
            result["status"] = "failed"
            result["error"] = f"No model URL in output keys: {list(output.keys())}"
            return result

        # Step 4: Download GLB
        download_model(model_url, entry["output_glb"])
        result["glb_path"] = str(entry["output_glb"])
        result["status"] = "converted"

        # Optional Step 5: Auto-rig
        if do_rig:
            logger.info("  Rigging %s...", entry["id"])
            rig_task_id = create_rig_task(api_key, task_id)
            result["rig_task_id"] = rig_task_id

            rig_data = poll_task(api_key, rig_task_id, timeout_seconds=300)
            rigged_url = rig_data.get("output", {}).get("model", "")

            if rigged_url:
                download_model(rigged_url, entry["output_rigged"])
                result["rigged_path"] = str(entry["output_rigged"])
                result["status"] = "rigged"
            else:
                logger.warning("  Rigging produced no model URL")

    except Exception as e:
        logger.error("  Failed: %s", e)
        result["status"] = "failed"
        result["error"] = str(e)

    return result


def convert_local(
    entry: dict,
    comfyui_url: str,
    resolution: int = DEFAULT_RESOLUTION,
) -> dict:
    """Convert a single asset via local ComfyUI TripoSR workflow."""
    result = {
        "id": entry["id"],
        "subcategory": entry["subcategory"],
        "source": str(entry["source_image"]),
    }

    logger.info("CONVERT [local] %s (%s)", entry["id"], entry["subcategory"])

    try:
        # Step 1: Upload image to ComfyUI
        uploaded_name = upload_image_to_comfyui(entry["source_image"], comfyui_url)

        # Step 2: Queue the workflow
        prefix = f"berserkr_{entry['id']}"
        prompt_id = queue_workflow(comfyui_url, uploaded_name, resolution, prefix)
        result["prompt_id"] = prompt_id

        # Step 3: Poll for completion
        history_entry = poll_history(comfyui_url, prompt_id, timeout_seconds=300)

        # Step 4: Download the mesh
        download_mesh(comfyui_url, history_entry, entry["output_glb"])
        result["glb_path"] = str(entry["output_glb"])
        result["status"] = "converted"

    except Exception as e:
        logger.error("  Failed: %s", e)
        result["status"] = "failed"
        result["error"] = str(e)

    return result


def convert_single(
    entry: dict,
    backend: str,
    api_key: str = "",
    do_rig: bool = False,
    dry_run: bool = False,
    comfyui_url: str = "http://127.0.0.1:8188",
    resolution: int = DEFAULT_RESOLUTION,
) -> dict:
    """Convert a single asset image to a 3D model."""
    # Skip if already converted
    if entry["output_glb"].exists():
        logger.info("SKIP %s -- GLB already exists", entry["id"])
        return {
            "id": entry["id"],
            "subcategory": entry["subcategory"],
            "source": str(entry["source_image"]),
            "status": "skipped",
            "glb_path": str(entry["output_glb"]),
        }

    if dry_run:
        logger.info(
            "DRY RUN -- %s (%s) -> %s [%s]",
            entry["id"], entry["subcategory"], entry["output_glb"], backend,
        )
        return {
            "id": entry["id"],
            "subcategory": entry["subcategory"],
            "source": str(entry["source_image"]),
            "status": "dry_run",
        }

    if backend == "tripo":
        return convert_tripo(api_key, entry, do_rig=do_rig)
    elif backend == "local":
        return convert_local(entry, comfyui_url, resolution)
    else:
        raise ValueError(f"Unknown backend: {backend}")


# =============================================================================
# Main
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Batch convert Berserkr 2D art to 3D models via Tripo or local ComfyUI"
    )
    parser.add_argument(
        "--asset-type",
        choices=["characters", "creatures", "equipment", "all"],
        default="characters",
        help="Type of assets to convert (default: characters)",
    )
    parser.add_argument(
        "--backend",
        choices=["tripo", "local"],
        default="tripo",
        help="Conversion backend (default: tripo)",
    )
    parser.add_argument(
        "--id",
        type=str,
        default=None,
        help="Convert only this specific asset ID",
    )
    parser.add_argument(
        "--rig",
        action="store_true",
        help="Auto-rig models after conversion (Tripo backend only)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview what would be converted without doing it",
    )
    parser.add_argument(
        "--retry-failed",
        action="store_true",
        help="Re-process only failed entries from the manifest",
    )
    parser.add_argument(
        "--comfyui-url",
        type=str,
        default="http://127.0.0.1:8188",
        help="ComfyUI server URL for local backend (default: http://127.0.0.1:8188)",
    )
    parser.add_argument(
        "--resolution",
        type=int,
        default=DEFAULT_RESOLUTION,
        help=f"Geometry resolution for local TripoSR (default: {DEFAULT_RESOLUTION})",
    )
    args = parser.parse_args()

    if args.rig and args.backend != "tripo":
        logger.error("--rig is only supported with the tripo backend")
        sys.exit(1)

    # Get API key for tripo backend
    api_key = "dry-run"
    if not args.dry_run and args.backend == "tripo":
        api_key = get_api_key()
        check_balance(api_key)

    # Find source images
    entries = find_source_images(args.asset_type, specific_id=args.id)

    if not entries:
        logger.error(
            "No source images found for asset type '%s'%s",
            args.asset_type,
            f" with id '{args.id}'" if args.id else "",
        )
        sys.exit(1)

    # Filter to only failed entries if --retry-failed
    if args.retry_failed and args.asset_type != "all":
        manifest_path = get_manifest_path(args.asset_type)
        failed_ids = get_failed_ids(manifest_path)
        if not failed_ids:
            logger.info("No failed entries in manifest. Nothing to retry.")
            sys.exit(0)
        # Remove existing GLBs for failed entries so they get re-processed
        entries = [e for e in entries if e["id"] in failed_ids]
        for entry in entries:
            if entry["output_glb"].exists():
                entry["output_glb"].unlink()
                logger.info("Removed stale GLB for retry: %s", entry["id"])
        logger.info("Retrying %d failed entries: %s", len(entries), failed_ids)
    elif args.retry_failed and args.asset_type == "all":
        # For 'all', collect failed IDs from each asset type's manifest
        all_failed_ids = set()
        for at in ["characters", "creatures", "equipment"]:
            mp = get_manifest_path(at)
            all_failed_ids.update(get_failed_ids(mp))
        if not all_failed_ids:
            logger.info("No failed entries in any manifest. Nothing to retry.")
            sys.exit(0)
        entries = [e for e in entries if e["id"] in all_failed_ids]
        for entry in entries:
            if entry["output_glb"].exists():
                entry["output_glb"].unlink()
        logger.info("Retrying %d failed entries across all types", len(entries))

    logger.info(
        "Found %d assets to process [type=%s, backend=%s]",
        len(entries), args.asset_type, args.backend,
    )

    # Ensure output directories exist
    output_dirs = {e["output_glb"].parent for e in entries}
    for d in output_dirs:
        d.mkdir(parents=True, exist_ok=True)

    # Process entries
    all_results = []
    total_start = time.time()

    for i, entry in enumerate(entries, 1):
        logger.info("[%d/%d] Processing %s", i, len(entries), entry["id"])
        result = convert_single(
            entry,
            backend=args.backend,
            api_key=api_key,
            do_rig=args.rig,
            dry_run=args.dry_run,
            comfyui_url=args.comfyui_url,
            resolution=args.resolution,
        )
        all_results.append(result)

        # Delay between conversions to be gentle on API/GPU
        if not args.dry_run and result.get("status") in ("converted", "rigged"):
            time.sleep(CONVERT_DELAY_SECONDS)

    elapsed = time.time() - total_start

    # Write manifests (per asset type)
    if not args.dry_run and all_results:
        if args.asset_type == "all":
            # Split results by asset type and write separate manifests
            for at in ["characters", "creatures", "equipment"]:
                at_results = [
                    r for r in all_results
                    if _result_belongs_to_type(r, at)
                ]
                if at_results:
                    _write_manifest(get_manifest_path(at), at_results, elapsed)
        else:
            manifest_path = get_manifest_path(args.asset_type)
            _write_manifest(manifest_path, all_results, elapsed)

    # Summary
    converted = sum(1 for r in all_results if r.get("status") in ("converted", "rigged"))
    skipped = sum(1 for r in all_results if r.get("status") == "skipped")
    failed = sum(1 for r in all_results if r.get("status") == "failed")
    logger.info("")
    logger.info("=" * 60)
    logger.info(
        "COMPLETE -- %d converted, %d skipped, %d failed in %.1fs",
        converted, skipped, failed, elapsed,
    )
    logger.info("=" * 60)


def _result_belongs_to_type(result: dict, asset_type: str) -> bool:
    """Check if a result entry belongs to a given asset type based on subcategory."""
    subcat = result.get("subcategory", "")
    if asset_type == "characters":
        return subcat in CHARACTER_SUBCATEGORIES
    elif asset_type == "creatures":
        return subcat in CREATURE_REALMS
    elif asset_type == "equipment":
        return subcat in EQUIPMENT_CATEGORIES
    return False


def _write_manifest(manifest_path: Path, results: list[dict], elapsed: float):
    """Write or merge results into a manifest file.

    Merges with existing entries: updates entries with matching IDs,
    appends new entries, preserves entries not in the current batch.
    """
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    existing = load_manifest(manifest_path)

    # Build lookup of existing entries by ID
    existing_by_id = {e["id"]: e for e in existing.get("entries", [])}

    # Merge: current batch results override existing entries with same ID
    for r in results:
        existing_by_id[r["id"]] = r

    manifest = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "total_elapsed_seconds": round(elapsed, 1),
        "entries": list(existing_by_id.values()),
    }

    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)

    logger.info("Wrote manifest: %s (%d entries)", manifest_path, len(manifest["entries"]))


if __name__ == "__main__":
    main()
