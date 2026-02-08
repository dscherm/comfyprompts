"""Model management tools for ComfyUI MCP Server"""

import logging

from mcp.server.fastmcp import FastMCP

logger = logging.getLogger("MCP_Server")


def register_model_management_tools(
    mcp: FastMCP,
    comfyui_client,
):
    """Register model management tools with the MCP server"""

    @mcp.tool()
    def list_loras() -> dict:
        """List all available LoRA models in ComfyUI.

        Returns LoRA model filenames that can be used with generation workflows
        that support LoRA (e.g., generate_image_lora). LoRAs are typically stored
        in ComfyUI's models/loras/ directory.
        """
        models = comfyui_client.get_lora_models()
        return {
            "loras": models,
            "count": len(models),
        }

    @mcp.tool()
    def list_controlnet_models() -> dict:
        """List all available ControlNet models in ComfyUI.

        Returns ControlNet model filenames that can be used with ControlNet-based
        generation workflows (e.g., generate_image_controlnet). ControlNet models
        are typically stored in ComfyUI's models/controlnet/ directory.
        """
        models = comfyui_client.get_controlnet_models()
        return {
            "controlnet_models": models,
            "count": len(models),
        }

    @mcp.tool()
    def list_vae_models() -> dict:
        """List all available VAE models in ComfyUI.

        Returns VAE model filenames. Most workflows use the VAE bundled with the
        checkpoint, but specialized VAEs can improve quality for specific use cases.
        VAE models are typically stored in ComfyUI's models/vae/ directory.
        """
        models = comfyui_client.get_vae_models()
        return {
            "vae_models": models,
            "count": len(models),
        }

    @mcp.tool()
    def list_upscale_models() -> dict:
        """List all available upscale models in ComfyUI.

        Returns upscale model filenames that can be used with the upscale_image tool.
        Upscale models are typically stored in ComfyUI's models/upscale_models/ directory.
        """
        models = comfyui_client.get_upscale_models()
        return {
            "upscale_models": models,
            "count": len(models),
        }

    @mcp.tool()
    def list_samplers() -> dict:
        """List all available sampler algorithms in ComfyUI.

        Returns sampler names that can be used as the `sampler_name` parameter
        in generation workflows (e.g., "euler", "dpmpp_2m", "ddim").
        """
        try:
            info = comfyui_client.get_object_info("KSampler")
            if not info:
                return {"error": "Failed to fetch sampler list from ComfyUI"}

            samplers = (
                info.get("KSampler", {})
                .get("input", {})
                .get("required", {})
                .get("sampler_name", [])
            )
            if isinstance(samplers, list) and samplers:
                sampler_list = samplers[0] if isinstance(samplers[0], list) else samplers
            else:
                sampler_list = []

            return {
                "samplers": sampler_list,
                "count": len(sampler_list),
            }
        except Exception as e:
            logger.exception("Failed to list samplers")
            return {"error": f"Failed to list samplers: {str(e)}"}

    @mcp.tool()
    def list_schedulers() -> dict:
        """List all available noise schedulers in ComfyUI.

        Returns scheduler names that can be used as the `scheduler` parameter
        in generation workflows (e.g., "normal", "karras", "exponential", "simple").
        """
        try:
            info = comfyui_client.get_object_info("KSampler")
            if not info:
                return {"error": "Failed to fetch scheduler list from ComfyUI"}

            schedulers = (
                info.get("KSampler", {})
                .get("input", {})
                .get("required", {})
                .get("scheduler", [])
            )
            if isinstance(schedulers, list) and schedulers:
                scheduler_list = schedulers[0] if isinstance(schedulers[0], list) else schedulers
            else:
                scheduler_list = []

            return {
                "schedulers": scheduler_list,
                "count": len(scheduler_list),
            }
        except Exception as e:
            logger.exception("Failed to list schedulers")
            return {"error": f"Failed to list schedulers: {str(e)}"}

    @mcp.tool()
    def refresh_model_cache() -> dict:
        """Refresh the cached model lists from ComfyUI.

        Call this after installing new models or checkpoints to update the server's
        model cache without restarting. Refreshes checkpoint models (used by list_models).
        """
        comfyui_client.refresh_models()
        return {
            "success": True,
            "checkpoint_count": len(comfyui_client.available_models),
        }
