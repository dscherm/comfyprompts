"""Asset viewing tools for ComfyUI MCP Server"""

import logging
from typing import Optional

import requests

from mcp.server.fastmcp import FastMCP, Image as FastMCPImage
from comfyui_agent_sdk.assets import AssetRegistry, encode_preview_for_mcp
from mcp_helpers import (
    estimate_response_chars,
    fetch_asset_bytes,
    get_cache_key,
    resolve_asset_for_workflow,
)

logger = logging.getLogger("MCP_Server")


def register_asset_tools(
    mcp: FastMCP,
    asset_registry
):
    """Register asset viewing tools with the MCP server"""
    
    @mcp.tool()
    def view_image(
        asset_id: str,
        mode: str = "thumb",
        max_dim: Optional[int] = None,
        max_b64_chars: Optional[int] = None,
    ) -> dict:
        """View a generated image inline in chat (thumbnail preview only).
        
        This tool allows the AI agent to view generated images inline in the chat interface,
        enabling closed-loop iteration: generate → view → adjust → regenerate.
        
        Only supports image assets (PNG, JPEG, WebP, GIF). For audio/video assets, use the
        asset_url directly or implement separate viewing tools.
        
        Args:
            asset_id: Asset ID returned from generation tools (e.g., generate_image)
            mode: Display mode - "thumb" (thumbnail preview, default) or "metadata" (info only)
            max_dim: Maximum dimension in pixels (default: 512, hard cap)
            max_b64_chars: Maximum base64 character count (default: 100000, ~100KB)
        
        Returns:
            MCP ImageContent structure for inline display, or metadata dict if mode="metadata"
            or if image exceeds budget (refuse-inline branch).
        """
        # Cleanup expired assets periodically
        asset_registry.cleanup_expired()
        
        # Validate asset_id exists in registry (security: only our assets)
        asset_record = asset_registry.get_asset(asset_id)
        if not asset_record:
            return {"error": f"Asset {asset_id} not found (registry is in-memory and resets on restart). Generate a new asset to regenerate."}
        
        # Get asset URL (computed from stable identity)
        asset_url = asset_record.asset_url or asset_record.get_asset_url(asset_registry.comfyui_base_url)
        
        # If metadata mode, return info only
        if mode == "metadata":
            return {
                "asset_id": asset_record.asset_id,
                "asset_url": asset_url,
                "filename": asset_record.filename,
                "subfolder": asset_record.subfolder,
                "folder_type": asset_record.folder_type,
                "mime_type": asset_record.mime_type,
                "width": asset_record.width,
                "height": asset_record.height,
                "bytes_size": asset_record.bytes_size,
                "workflow_id": asset_record.workflow_id,
                "prompt_id": asset_record.prompt_id,
                "created_at": asset_record.created_at.isoformat(),
                "expires_at": asset_record.expires_at.isoformat() if asset_record.expires_at else None
            }
        
        # Enforce: only "thumb" mode for scoped version
        if mode != "thumb":
            return {
                "error": f"Mode '{mode}' not supported in scoped version. Use 'thumb' or 'metadata'."
            }
        
        # Validate content type (only images supported for inline viewing)
        supported_types = ("image/png", "image/jpeg", "image/jpg", "image/webp", "image/gif")
        if asset_record.mime_type not in supported_types:
            return {
                "error": f"Asset type '{asset_record.mime_type}' not supported for inline viewing. "
                         f"Supported types: {', '.join(supported_types)}"
            }
        
        # Set conservative defaults
        if max_dim is None:
            max_dim = 512  # Hard cap for scoped version
        if max_b64_chars is None:
            max_b64_chars = 100_000  # 100KB base64 payload (conservative to prevent hangs)
        
        # Process image for inline viewing
        try:
            # Fetch image bytes using computed URL
            image_url = asset_url
            image_bytes = fetch_asset_bytes(image_url)
            
            # Encode with new function (accepts bytes directly)
            cache_key = get_cache_key(asset_id, max_dim, 70)  # Use quality=70 for cache key
            encoded = encode_preview_for_mcp(
                image_bytes,
                max_dim=max_dim,
                max_b64_chars=max_b64_chars,
                quality=70,
                cache_key=cache_key,
            )
            
            # Log telemetry
            logger.info(
                f"view_image success: asset_id={asset_id} "
                f"src={asset_record.bytes_size}B src_dims={asset_record.width}x{asset_record.height} "
                f"preview_dims={encoded.size_px[0]}x{encoded.size_px[1]} format=webp "
                f"encoded={encoded.bytes_len}B b64_chars={encoded.b64_chars} "
                f"response_est={estimate_response_chars(encoded.b64_chars)}chars"
            )
            
            # Use FastMCP.Image for inline display (not dict)
            # FastMCP.Image takes raw bytes and format string
            return FastMCPImage(data=encoded.raw_bytes, format="webp")
            
        except ValueError as e:
            # Image too large or processing failed - REFUSE-INLINE (non-lethal failure)
            logger.warning(f"Refusing to inline image for {asset_id}: {e}")
            return {
                "content": [{
                    "type": "text",
                    "text": (
                        f"Could not inline image (exceeds budget: {e}). "
                        f"Asset ID: {asset_id}. "
                        f"URL: {asset_record.asset_url}. "
                        f"Source size: {asset_record.bytes_size} bytes. "
                        f"Source dimensions: {asset_record.width}x{asset_record.height}. "
                        f"Hint: Open URL locally or use metadata mode."
                    )
                }]
            }
        except ImportError as e:
            return {"error": f"Image processing not available: {e}. Install Pillow: pip install Pillow"}
        except Exception as e:
            logger.exception(f"Failed to process asset {asset_id} for viewing")
            return {"error": f"Failed to process asset: {str(e)}"}

    @mcp.tool()
    def view_video(
        asset_id: str,
    ) -> dict:
        """Get a video asset's URL and metadata for viewing.

        Unlike images, videos cannot be inlined in chat. This tool returns the
        video URL and metadata so the AI agent or user can open it externally.

        Args:
            asset_id: Asset ID returned from video generation tools (e.g., generate_video, image_to_video)

        Returns:
            Dict with video URL, metadata, and playback info.
        """
        asset_registry.cleanup_expired()

        asset_record = asset_registry.get_asset(asset_id)
        if not asset_record:
            return {"error": f"Asset {asset_id} not found (registry is in-memory and resets on restart). Generate a new asset."}

        asset_url = asset_record.asset_url or asset_record.get_asset_url(asset_registry.comfyui_base_url)

        # Validate it's a video type
        video_types = ("video/mp4", "video/webm", "video/avi", "video/mov", "image/gif")
        if asset_record.mime_type and asset_record.mime_type not in video_types:
            return {
                "error": f"Asset type '{asset_record.mime_type}' is not a video. "
                         f"Use view_image for image assets."
            }

        result = {
            "asset_id": asset_record.asset_id,
            "asset_url": asset_url,
            "filename": asset_record.filename,
            "mime_type": asset_record.mime_type,
            "width": asset_record.width,
            "height": asset_record.height,
            "bytes_size": asset_record.bytes_size,
            "workflow_id": asset_record.workflow_id,
            "prompt_id": asset_record.prompt_id,
            "created_at": asset_record.created_at.isoformat(),
            "hint": "Open the asset_url in a browser or media player to view the video.",
        }

        return result

    @mcp.tool()
    def get_video_info(
        asset_id: str,
    ) -> dict:
        """Get detailed metadata about a video asset.

        Fetches the video file and extracts technical metadata including
        duration, dimensions, codec info, and file size.

        Args:
            asset_id: Asset ID returned from video generation tools

        Returns:
            Dict with detailed video metadata (dimensions, file size, format).
        """
        asset_registry.cleanup_expired()

        asset_record = asset_registry.get_asset(asset_id)
        if not asset_record:
            return {"error": f"Asset {asset_id} not found (registry is in-memory and resets on restart). Generate a new asset."}

        asset_url = asset_record.asset_url or asset_record.get_asset_url(asset_registry.comfyui_base_url)

        info = {
            "asset_id": asset_record.asset_id,
            "asset_url": asset_url,
            "filename": asset_record.filename,
            "subfolder": asset_record.subfolder,
            "folder_type": asset_record.folder_type,
            "mime_type": asset_record.mime_type,
            "width": asset_record.width,
            "height": asset_record.height,
            "bytes_size": asset_record.bytes_size,
            "workflow_id": asset_record.workflow_id,
            "prompt_id": asset_record.prompt_id,
            "created_at": asset_record.created_at.isoformat(),
            "expires_at": asset_record.expires_at.isoformat() if asset_record.expires_at else None,
        }

        # Try to fetch actual file size from ComfyUI if not already known
        if not info["bytes_size"]:
            try:
                head_resp = requests.head(asset_url, timeout=10)
                if head_resp.status_code == 200:
                    content_length = head_resp.headers.get("Content-Length")
                    if content_length:
                        info["bytes_size"] = int(content_length)
                    content_type = head_resp.headers.get("Content-Type")
                    if content_type and not info["mime_type"]:
                        info["mime_type"] = content_type.split(";")[0].strip()
            except Exception as e:
                logger.debug(f"Could not fetch video headers: {e}")

        # Add human-readable file size
        if info["bytes_size"]:
            size_mb = info["bytes_size"] / (1024 * 1024)
            info["size_human"] = f"{size_mb:.2f} MB"

        return info

    @mcp.tool()
    def resolve_asset(asset_id: str) -> dict:
        """Resolve an asset from a previous generation step into a ComfyUI input filename.

        This is the key bridge for multi-stage pipelines: it takes an asset_id
        from a prior tool (e.g., generate_image) and makes it available as an
        input file for the next workflow stage (e.g., image_to_3d, image_to_video,
        style_transfer).

        For image/video/audio assets it downloads from ComfyUI output and uploads
        to the ComfyUI input folder. For 3D meshes it returns the output filename
        directly.

        Args:
            asset_id: Asset ID returned by a generation tool

        Returns:
            Dict with 'input_filename' usable as PARAM_STR_IMAGE_PATH (or similar)
            in subsequent workflow tools, plus asset metadata.
        """
        record = asset_registry.get_asset(asset_id)
        if not record:
            return {
                "error": f"Asset {asset_id} not found or expired. "
                         "Generate a new asset first."
            }

        input_filename = resolve_asset_for_workflow(asset_registry, asset_id)
        if not input_filename:
            return {
                "error": f"Failed to resolve asset {asset_id} for workflow chaining. "
                         "The asset may be inaccessible or ComfyUI may be unreachable."
            }

        return {
            "input_filename": input_filename,
            "asset_id": asset_id,
            "original_filename": record.filename,
            "mime_type": record.mime_type,
            "workflow_id": record.workflow_id,
            "hint": (
                f"Use '{input_filename}' as the image_path or similar input "
                f"parameter in your next workflow tool call."
            ),
        }

    @mcp.tool()
    def get_asset_local_path(asset_id: str) -> dict:
        """Get the local filesystem path for an asset.

        Useful when you need to pass an asset to external tools (Blender, ffmpeg)
        that require a local file path rather than a ComfyUI input filename.

        Args:
            asset_id: Asset ID returned by a generation tool

        Returns:
            Dict with 'local_path' if the file is found on disk, or error.
        """
        record = asset_registry.get_asset(asset_id)
        if not record:
            return {
                "error": f"Asset {asset_id} not found or expired."
            }

        local_path = asset_registry.get_asset_local_path(asset_id)
        if not local_path:
            return {
                "error": f"Could not resolve local path for asset {asset_id}. "
                         "Set COMFYUI_OUTPUT_ROOT environment variable to the ComfyUI output directory.",
                "asset_url": record.get_asset_url(asset_registry.comfyui_base_url),
            }

        return {
            "local_path": local_path,
            "asset_id": asset_id,
            "filename": record.filename,
            "mime_type": record.mime_type,
        }
