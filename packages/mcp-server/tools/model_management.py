"""Model management tools for ComfyUI MCP Server"""

import logging

from mcp.server.fastmcp import FastMCP

from tools.lora_metadata import (
    active_checkpoint_family,
    detect_lora_base_model,
    load_lora_blocklist,
    resolve_loras_dir,
)

logger = logging.getLogger("MCP_Server")


def register_model_management_tools(
    mcp: FastMCP,
    comfyui_client,
    defaults_manager=None,
):
    """Register model management tools with the MCP server"""

    @mcp.tool()
    def list_loras(
        base_model: str | None = None,
        include_incompatible: bool = False,
    ) -> dict:
        """List available LoRA models, pruned to ones compatible with your checkpoint.

        Each LoRA is tagged with its base-model family ('flux', 'sdxl', 'sd15',
        or 'unknown') by reading the safetensors header. A LoRA built for one
        architecture (e.g. SDXL) has ZERO effect when loaded onto a checkpoint of
        another architecture (e.g. FLUX) -- ComfyUI silently ignores it and the
        image is unchanged.

        BY DEFAULT this prunes LoRAs that won't work with your active checkpoint:
          - Architecture mismatches: if the active checkpoint family is known
            (e.g. flux) and a LoRA is a DIFFERENT known family (e.g. sdxl/sd15),
            it is hidden. LoRAs tagged 'unknown' are NEVER hidden (we don't hide
            what we couldn't classify).
          - Blocklisted LoRAs: names listed in
            ~/.config/comfy-mcp/lora_blocklist.json (shape
            {"blocked": [...]}) or the COMFY_MCP_LORA_BLOCKLIST env var
            (comma-separated). Edit that file to curate confirmed no-effect LoRAs.

        The active checkpoint family is resolved from the COMFY_MCP_CHECKPOINT_FAMILY
        env override, else inferred from the default image checkpoint name.

        Args:
            base_model: Force the target family for the architecture filter
                (e.g. "sdxl"). Overrides the auto-detected checkpoint family.
            include_incompatible: If True, return ALL LoRAs with no pruning
                (no architecture filter, no blocklist), still tagged. Use this to
                see everything available, including incompatible ones.

        Returns:
            Dict with:
            - loras: list of LoRA filenames (pruned unless include_incompatible)
            - count: number of names in `loras`
            - tagged: list of {"name": str, "base_model": str} (pruned to match)
            - excluded: count of LoRAs hidden by the default prune
            - target_family: the checkpoint family used for the architecture filter
        """
        models = comfyui_client.get_lora_models()
        loras_dir = resolve_loras_dir()

        tagged = [
            {"name": name, "base_model": detect_lora_base_model(name, loras_dir)}
            for name in models
        ]
        total = len(tagged)

        target_family = (base_model or "").lower() or active_checkpoint_family(
            defaults_manager
        )

        if include_incompatible:
            kept = tagged
        else:
            blocklist = load_lora_blocklist()
            kept = []
            for entry in tagged:
                if entry["name"] in blocklist:
                    continue
                fam = entry["base_model"]
                if (
                    target_family != "unknown"
                    and fam != "unknown"
                    and fam != target_family
                ):
                    continue
                kept.append(entry)

        names = [entry["name"] for entry in kept]
        return {
            "loras": names,
            "count": len(names),
            "tagged": kept,
            "excluded": total - len(kept),
            "target_family": target_family,
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
