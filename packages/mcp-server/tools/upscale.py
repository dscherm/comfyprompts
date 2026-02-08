"""Upscaling tool for AI-powered image upscaling"""

import logging
from typing import Optional

import requests
from mcp.server.fastmcp import FastMCP

from tools.helpers import register_and_build_response

logger = logging.getLogger("MCP_Server")

# Default upscale models (common ESRGAN models)
DEFAULT_UPSCALE_MODELS = [
    "RealESRGAN_x4plus.pth",
    "RealESRGAN_x4plus_anime_6B.pth",
    "4x_NMKD-Siax_200k.pth",
    "4x-UltraSharp.pth",
]


def register_upscale_tools(
    mcp: FastMCP,
    comfyui_client,
    asset_registry,
    webhook_manager=None
):
    """Register upscaling tools with the MCP server"""

    @mcp.tool()
    def upscale_image(
        asset_id: str,
        scale_factor: int = 4,
        upscale_model: Optional[str] = None
    ) -> dict:
        """Upscale an existing image asset using AI upscaling models.

        Uses ESRGAN-based models to intelligently upscale images while preserving
        and enhancing details. Supports 2x and 4x upscaling.

        Args:
            asset_id: ID of the image asset to upscale (from generate_image or other tools).
            scale_factor: Upscale multiplier (2 or 4). Default: 4.
                Note: The actual scale is determined by the model, most models are 4x.
            upscale_model: Name of the upscale model to use.
                Common models: RealESRGAN_x4plus.pth, RealESRGAN_x4plus_anime_6B.pth,
                4x_NMKD-Siax_200k.pth, 4x-UltraSharp.pth.
                If not specified, uses the first available model.

        Returns:
            Dict with upscaled image info:
            - asset_id: New asset ID for the upscaled image
            - asset_url: URL to view the upscaled image
            - filename: Output filename
            - original_asset_id: The source asset ID
            - upscale_model: Model used for upscaling
            - scale_factor: Requested scale factor

        Examples:
            # Upscale with default settings (4x)
            upscale_image(asset_id="abc123")

            # Use specific model
            upscale_image(asset_id="abc123", upscale_model="RealESRGAN_x4plus_anime_6B.pth")

            # 2x upscale (will use appropriate 2x model if available)
            upscale_image(asset_id="abc123", scale_factor=2)
        """
        try:
            # Validate scale factor
            if scale_factor not in (2, 4):
                return {"error": f"Invalid scale_factor: {scale_factor}. Must be 2 or 4."}

            # Get the source asset
            asset = asset_registry.get_asset(asset_id)
            if not asset:
                return {
                    "error": f"Asset {asset_id} not found or expired. Assets are session-scoped and die on server restart."
                }

            # Verify it's an image
            if asset.mime_type and not asset.mime_type.startswith("image/"):
                return {"error": f"Asset {asset_id} is not an image (mime_type: {asset.mime_type}). Upscaling only works on images."}

            # Get available upscale models
            available_models = comfyui_client.get_upscale_models()
            if not available_models:
                return {"error": "No upscale models found in ComfyUI. Install ESRGAN models in ComfyUI/models/upscale_models/"}

            # Select model
            if upscale_model:
                # Validate model exists
                if upscale_model not in available_models:
                    return {
                        "error": f"Upscale model '{upscale_model}' not found. Available models: {available_models[:5]}"
                    }
                selected_model = upscale_model
            else:
                # Auto-select based on scale factor preference
                # Try to find a model matching the scale factor
                scale_prefix = f"{scale_factor}x"
                matching = [m for m in available_models if scale_prefix.lower() in m.lower()]
                if matching:
                    selected_model = matching[0]
                else:
                    # Fall back to first available
                    selected_model = available_models[0]
                logger.info(f"Auto-selected upscale model: {selected_model}")

            # Fetch the source image bytes
            asset_url = asset.asset_url or asset.get_asset_url(asset_registry.comfyui_base_url)
            try:
                response = requests.get(asset_url, timeout=30)
                response.raise_for_status()
                image_bytes = response.content
            except requests.RequestException as e:
                return {"error": f"Failed to fetch source image: {e}"}

            # Upload image to ComfyUI
            upload_filename = f"upscale_input_{asset_id[:8]}.png"
            upload_result = comfyui_client.upload_image(image_bytes, upload_filename)
            uploaded_name = upload_result.get("name", upload_filename)
            uploaded_subfolder = upload_result.get("subfolder", "")

            # Build the upscale workflow
            # Reference the uploaded image using its ComfyUI path
            if uploaded_subfolder:
                image_path = f"{uploaded_subfolder}/{uploaded_name}"
            else:
                image_path = uploaded_name

            workflow = {
                "1": {
                    "inputs": {
                        "image": image_path,
                        "upload": "image"
                    },
                    "class_type": "LoadImage",
                    "_meta": {"title": "Load Image"}
                },
                "2": {
                    "inputs": {
                        "model_name": selected_model
                    },
                    "class_type": "UpscaleModelLoader",
                    "_meta": {"title": "Load Upscale Model"}
                },
                "3": {
                    "inputs": {
                        "upscale_model": ["2", 0],
                        "image": ["1", 0]
                    },
                    "class_type": "ImageUpscaleWithModel",
                    "_meta": {"title": "Upscale Image"}
                },
                "4": {
                    "inputs": {
                        "filename_prefix": "ComfyUI_Upscaled",
                        "images": ["3", 0]
                    },
                    "class_type": "SaveImage",
                    "_meta": {"title": "Save Image"}
                }
            }

            # Run the workflow
            result = comfyui_client.run_custom_workflow(
                workflow,
                preferred_output_keys=("images", "image")
            )

            # Register the result
            response_data = register_and_build_response(
                result,
                "upscale",
                asset_registry,
                tool_name="upscale_image",
                return_inline_preview=False,
                session_id=asset.session_id
            )

            # Add upscale-specific metadata
            response_data["original_asset_id"] = asset_id
            response_data["upscale_model"] = selected_model
            response_data["scale_factor"] = scale_factor

            # Calculate expected dimensions
            if asset.width and asset.height:
                # Note: actual scale depends on model, but we estimate
                model_scale = 4 if "4x" in selected_model.lower() or "x4" in selected_model.lower() else scale_factor
                response_data["expected_width"] = asset.width * model_scale
                response_data["expected_height"] = asset.height * model_scale

            # Dispatch webhook if available
            if webhook_manager:
                webhook_manager.dispatch("generation_completed", {
                    "tool": "upscale_image",
                    "asset_id": response_data.get("asset_id"),
                    "original_asset_id": asset_id,
                    "upscale_model": selected_model
                })

            return response_data

        except Exception as e:
            logger.exception(f"Failed to upscale asset {asset_id}")
            return {"error": f"Failed to upscale image: {str(e)}"}

    logger.info("Registered upscale tools: upscale_image")
