"""MCP-server-specific helpers that are not part of the shared SDK.

Contains functions for asset resolution, caching, and MCP response formatting.
"""

import logging
from typing import Optional

import requests

from comfyui_agent_sdk.assets import AssetRegistry, EncodedImage

logger = logging.getLogger("MCP_Server")

# Re-export fetch_asset_bytes from the SDK processor for local convenience
from comfyui_agent_sdk.assets.processor import fetch_asset_bytes


def get_cache_key(asset_id: str, max_dim: int, quality: int) -> str:
    """Generate cache key for processed preview."""
    return f"{asset_id}:{max_dim}:webp:{quality}"


def estimate_response_chars(b64_chars: int, json_overhead: int = 200) -> int:
    """Estimate total serialized response size (for logging/debugging)."""
    return b64_chars + json_overhead


def mcp_image_content(encoded: EncodedImage) -> dict:
    """Convert EncodedImage to MCP ImageContent structure."""
    return {
        "type": "image",
        "data": f"data:{encoded.mime_type};base64,{encoded.b64}",
        "mimeType": encoded.mime_type,
    }


def resolve_asset_for_workflow(
    asset_registry: AssetRegistry, asset_id: str
) -> Optional[str]:
    """Resolve an asset ID to a ComfyUI input filename for workflow chaining.

    This is the key bridge for multi-stage pipelines. It takes an asset_id
    from a previous generation step and returns the filename string that can
    be used as PARAM_STR_IMAGE_PATH (or similar) in the next workflow.

    For image assets, it downloads the asset from ComfyUI's output endpoint
    and uploads it to ComfyUI's input folder, returning the input filename.

    For 3D/mesh assets, it returns the output path directly since those are
    referenced by filesystem path.

    Args:
        asset_registry: The AssetRegistry instance.
        asset_id: The asset ID from a previous generation step.

    Returns:
        The ComfyUI input filename (e.g., "ComfyUI_00042_.png") usable as
        a workflow input parameter, or None if the asset cannot be resolved.
    """
    record = asset_registry.get_asset(asset_id)
    if not record:
        logger.warning(
            f"resolve_asset_for_workflow: asset {asset_id} not found or expired"
        )
        return None

    # For images/videos: download from ComfyUI output and upload to input
    mime = record.mime_type or ""
    if mime.startswith("image/") or mime.startswith("video/") or mime.startswith("audio/"):
        try:
            # Fetch the asset bytes from ComfyUI output
            asset_url = record.get_asset_url(asset_registry.comfyui_base_url)
            response = requests.get(asset_url, timeout=60)
            response.raise_for_status()

            # Upload to ComfyUI input folder
            upload_url = f"{asset_registry.comfyui_base_url.rstrip('/')}/upload/image"
            files = {"image": (record.filename, response.content, mime)}
            data = {"overwrite": "true"}

            upload_response = requests.post(
                upload_url, files=files, data=data, timeout=60
            )
            upload_response.raise_for_status()
            result = upload_response.json()

            input_filename = result.get("name", record.filename)
            logger.info(
                f"resolve_asset_for_workflow: uploaded {record.filename} -> input/{input_filename}"
            )
            return input_filename

        except requests.RequestException as e:
            logger.error(
                f"resolve_asset_for_workflow: failed to transfer asset {asset_id}: {e}"
            )
            return None

    # For 3D meshes and other file types: return the output filename directly
    logger.info(
        f"resolve_asset_for_workflow: returning raw filename for non-image asset: {record.filename}"
    )
    return record.filename
