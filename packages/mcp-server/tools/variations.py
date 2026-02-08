"""Image variations tool for generating style/composition variations of existing images"""

import logging
import random
from typing import Optional, List

import requests
from mcp.server.fastmcp import FastMCP

from tools.helpers import register_and_build_response

logger = logging.getLogger("MCP_Server")


def register_variations_tools(
    mcp: FastMCP,
    comfyui_client,
    defaults_manager,
    asset_registry,
    webhook_manager=None
):
    """Register image variations tools with the MCP server"""

    @mcp.tool()
    def generate_variations(
        asset_id: str,
        num_variations: int = 4,
        variation_strength: float = 0.7,
        seed: Optional[int] = None,
        prompt: Optional[str] = None,
        negative_prompt: Optional[str] = None,
        model: Optional[str] = None
    ) -> dict:
        """Generate variations of an existing image using img2img processing.

        Creates multiple variations of a source image by encoding it to latent space,
        adding noise based on variation_strength, and decoding with optional prompt guidance.

        Args:
            asset_id: ID of the source image asset to create variations from.
            num_variations: Number of variations to generate (1-8). Default: 4.
            variation_strength: How different variations should be from original (0.0-1.0).
                - 0.0 = Nearly identical to original
                - 0.5 = Moderate changes
                - 1.0 = Maximum variation (essentially new image)
                Default: 0.7
            seed: Base random seed. Each variation uses seed+i. If None, random seed is generated.
            prompt: Optional text prompt to guide variations. If None, variations are purely
                visual/structural without text guidance.
            negative_prompt: Optional negative prompt. Default: "text, watermark, blurry"
            model: Checkpoint model to use. If None, uses default model.

        Returns:
            Dict with:
            - variations: List of variation assets, each with asset_id, asset_url, etc.
            - count: Number of variations generated
            - original_asset_id: Source asset ID
            - variation_strength: Strength used
            - base_seed: Base seed used

        Examples:
            # Generate 4 variations with default settings
            generate_variations(asset_id="abc123")

            # Generate 2 subtle variations
            generate_variations(asset_id="abc123", num_variations=2, variation_strength=0.3)

            # Generate variations with prompt guidance
            generate_variations(
                asset_id="abc123",
                prompt="oil painting style, dramatic lighting",
                variation_strength=0.6
            )
        """
        try:
            # Validate parameters
            if num_variations < 1 or num_variations > 8:
                return {"error": f"num_variations must be between 1 and 8, got {num_variations}"}

            if variation_strength < 0.0 or variation_strength > 1.0:
                return {"error": f"variation_strength must be between 0.0 and 1.0, got {variation_strength}"}

            # Get the source asset
            asset = asset_registry.get_asset(asset_id)
            if not asset:
                return {
                    "error": f"Asset {asset_id} not found or expired. Assets are session-scoped and die on server restart."
                }

            # Verify it's an image
            if asset.mime_type and not asset.mime_type.startswith("image/"):
                return {"error": f"Asset {asset_id} is not an image (mime_type: {asset.mime_type})."}

            # Fetch the source image bytes
            asset_url = asset.asset_url or asset.get_asset_url(asset_registry.comfyui_base_url)
            try:
                response = requests.get(asset_url, timeout=30)
                response.raise_for_status()
                image_bytes = response.content
            except requests.RequestException as e:
                return {"error": f"Failed to fetch source image: {e}"}

            # Upload image to ComfyUI
            upload_filename = f"variation_input_{asset_id[:8]}.png"
            upload_result = comfyui_client.upload_image(image_bytes, upload_filename)
            uploaded_name = upload_result.get("name", upload_filename)
            uploaded_subfolder = upload_result.get("subfolder", "")

            # Build image path for workflow
            if uploaded_subfolder:
                image_path = f"{uploaded_subfolder}/{uploaded_name}"
            else:
                image_path = uploaded_name

            # Get defaults
            resolved_model = defaults_manager.get_default("image", "model", model)
            resolved_negative = negative_prompt or defaults_manager.get_default(
                "image", "negative_prompt", "text, watermark, blurry"
            )
            resolved_steps = defaults_manager.get_default("image", "steps", 20)
            resolved_cfg = defaults_manager.get_default("image", "cfg", 7.0)
            resolved_sampler = defaults_manager.get_default("image", "sampler_name", "euler")
            resolved_scheduler = defaults_manager.get_default("image", "scheduler", "normal")

            # Use provided prompt or empty string (pure img2img)
            resolved_prompt = prompt or ""

            # Generate base seed if not provided
            base_seed = seed if seed is not None else random.randint(0, 2**32 - 1)

            # Generate variations
            variations: List[dict] = []
            errors: List[str] = []

            for i in range(num_variations):
                variation_seed = base_seed + i

                # Build workflow for this variation
                workflow = {
                    "1": {
                        "inputs": {
                            "ckpt_name": resolved_model
                        },
                        "class_type": "CheckpointLoaderSimple",
                        "_meta": {"title": "Load Checkpoint"}
                    },
                    "2": {
                        "inputs": {
                            "image": image_path,
                            "upload": "image"
                        },
                        "class_type": "LoadImage",
                        "_meta": {"title": "Load Image"}
                    },
                    "3": {
                        "inputs": {
                            "pixels": ["2", 0],
                            "vae": ["1", 2]
                        },
                        "class_type": "VAEEncode",
                        "_meta": {"title": "VAE Encode"}
                    },
                    "4": {
                        "inputs": {
                            "text": resolved_prompt,
                            "clip": ["1", 1]
                        },
                        "class_type": "CLIPTextEncode",
                        "_meta": {"title": "CLIP Text Encode (Positive)"}
                    },
                    "5": {
                        "inputs": {
                            "text": resolved_negative,
                            "clip": ["1", 1]
                        },
                        "class_type": "CLIPTextEncode",
                        "_meta": {"title": "CLIP Text Encode (Negative)"}
                    },
                    "6": {
                        "inputs": {
                            "seed": variation_seed,
                            "steps": resolved_steps,
                            "cfg": resolved_cfg,
                            "sampler_name": resolved_sampler,
                            "scheduler": resolved_scheduler,
                            "denoise": variation_strength,
                            "model": ["1", 0],
                            "positive": ["4", 0],
                            "negative": ["5", 0],
                            "latent_image": ["3", 0]
                        },
                        "class_type": "KSampler",
                        "_meta": {"title": "KSampler"}
                    },
                    "7": {
                        "inputs": {
                            "samples": ["6", 0],
                            "vae": ["1", 2]
                        },
                        "class_type": "VAEDecode",
                        "_meta": {"title": "VAE Decode"}
                    },
                    "8": {
                        "inputs": {
                            "filename_prefix": f"ComfyUI_Variation_{i+1}",
                            "images": ["7", 0]
                        },
                        "class_type": "SaveImage",
                        "_meta": {"title": "Save Image"}
                    }
                }

                try:
                    # Run the workflow
                    result = comfyui_client.run_custom_workflow(
                        workflow,
                        preferred_output_keys=("images", "image")
                    )

                    # Register the result
                    response_data = register_and_build_response(
                        result,
                        "image_variations",
                        asset_registry,
                        tool_name="generate_variations",
                        return_inline_preview=False,
                        session_id=asset.session_id
                    )

                    # Add variation-specific metadata
                    response_data["variation_index"] = i + 1
                    response_data["seed"] = variation_seed
                    response_data["variation_strength"] = variation_strength

                    variations.append(response_data)

                except Exception as e:
                    logger.warning(f"Failed to generate variation {i+1}: {e}")
                    errors.append(f"Variation {i+1}: {str(e)}")

            if not variations:
                return {"error": f"Failed to generate any variations. Errors: {errors}"}

            result_data = {
                "variations": variations,
                "count": len(variations),
                "original_asset_id": asset_id,
                "variation_strength": variation_strength,
                "base_seed": base_seed,
                "prompt": resolved_prompt if resolved_prompt else None,
                "model": resolved_model
            }

            if errors:
                result_data["warnings"] = errors

            # Dispatch webhook if available
            if webhook_manager:
                webhook_manager.dispatch("generation_completed", {
                    "tool": "generate_variations",
                    "count": len(variations),
                    "original_asset_id": asset_id,
                    "asset_ids": [v.get("asset_id") for v in variations]
                })

            return result_data

        except Exception as e:
            logger.exception(f"Failed to generate variations for asset {asset_id}")
            return {"error": f"Failed to generate variations: {str(e)}"}

    logger.info("Registered variations tool: generate_variations")
