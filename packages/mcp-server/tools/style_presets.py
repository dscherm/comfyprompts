"""Style presets tools for applying predefined artistic styles"""

import logging
from typing import Any, Dict, Optional

from mcp.server.fastmcp import FastMCP

logger = logging.getLogger("MCP_Server")


def register_style_preset_tools(
    mcp: FastMCP,
    style_presets_manager
):
    """Register style preset management tools"""

    @mcp.tool()
    def list_style_presets() -> dict:
        """List all available style presets for image generation.

        Returns a list of preset IDs with their names and descriptions.
        Use apply_style_preset to apply a preset to your prompt.

        Returns:
            dict: List of available presets with metadata
        """
        presets = style_presets_manager.list_presets()
        return {
            "presets": presets,
            "total": len(presets),
            "usage": "Use apply_style_preset(preset_id, prompt) to apply a style"
        }

    @mcp.tool()
    def get_style_preset(preset_id: str) -> dict:
        """Get detailed information about a specific style preset.

        Args:
            preset_id: The preset identifier (e.g., "anime", "photorealistic")

        Returns:
            dict: Full preset details including prompt modifiers and settings
        """
        preset = style_presets_manager.get_preset(preset_id)
        if not preset:
            available = [p["id"] for p in style_presets_manager.list_presets()]
            return {
                "error": f"Style preset '{preset_id}' not found",
                "available_presets": available
            }
        return {"preset": preset}

    @mcp.tool()
    def apply_style_preset(
        preset_id: str,
        prompt: str,
        override_settings: Optional[Dict[str, Any]] = None
    ) -> dict:
        """Apply a style preset to enhance your prompt with artistic style.

        This combines your prompt with the preset's style modifiers and
        returns recommended generation settings.

        Args:
            preset_id: The preset identifier (e.g., "anime", "ghibli", "cyberpunk")
            prompt: Your base prompt describing what to generate
            override_settings: Optional dict to override preset's recommended settings

        Returns:
            dict: Enhanced prompt, negative prompt, and recommended settings

        Example:
            apply_style_preset("anime", "a girl with blue hair standing in a forest")
            # Returns enhanced prompt with anime style modifiers and recommended settings

        Common presets:
            - photorealistic: Ultra-realistic photography
            - anime: Japanese anime style
            - ghibli: Studio Ghibli style (suggests matching LoRA)
            - pixel_art: Retro pixel art (suggests matching LoRA)
            - oil_painting: Classic oil painting
            - watercolor: Soft watercolor style
            - cyberpunk: Futuristic neon aesthetic
            - fantasy: Epic fantasy illustration
            - cinematic: Movie-like dramatic visuals
            - minimalist: Clean minimal design
        """
        try:
            result = style_presets_manager.apply_preset(preset_id, prompt, override_settings)
            return result
        except ValueError as e:
            available = [p["id"] for p in style_presets_manager.list_presets()]
            return {
                "error": str(e),
                "available_presets": available
            }

    @mcp.tool()
    def create_custom_style_preset(
        preset_id: str,
        name: str,
        description: str,
        prompt_prefix: str = "",
        prompt_suffix: str = "",
        negative_prompt: str = "",
        recommended_cfg: Optional[float] = None,
        recommended_steps: Optional[int] = None,
        suggested_lora: Optional[str] = None
    ) -> dict:
        """Create a custom style preset for reuse.

        Custom presets are saved to your config and persist across sessions.

        Args:
            preset_id: Unique identifier for this preset (lowercase, no spaces)
            name: Display name for the preset
            description: Brief description of the style
            prompt_prefix: Text to prepend to prompts (e.g., "oil painting, ")
            prompt_suffix: Text to append to prompts (e.g., ", masterpiece, detailed")
            negative_prompt: Default negative prompt for this style
            recommended_cfg: Recommended CFG scale (default: 1.0 for Flux)
            recommended_steps: Recommended number of steps
            suggested_lora: Optional LoRA name that works well with this style

        Returns:
            dict: Success status and created preset details

        Example:
            create_custom_style_preset(
                preset_id="my_style",
                name="My Custom Style",
                description="A unique artistic style",
                prompt_prefix="in my custom style, ",
                prompt_suffix=", artistic masterpiece",
                negative_prompt="ugly, blurry"
            )
        """
        try:
            recommended_settings = {}
            if recommended_cfg is not None:
                recommended_settings["cfg"] = recommended_cfg
            if recommended_steps is not None:
                recommended_settings["steps"] = recommended_steps

            result = style_presets_manager.create_custom_preset(
                preset_id=preset_id,
                name=name,
                description=description,
                prompt_prefix=prompt_prefix,
                prompt_suffix=prompt_suffix,
                negative_prompt=negative_prompt,
                recommended_settings=recommended_settings if recommended_settings else None,
                suggested_lora=suggested_lora
            )
            return result
        except ValueError as e:
            return {"error": str(e)}

    @mcp.tool()
    def delete_custom_style_preset(preset_id: str) -> dict:
        """Delete a custom style preset.

        Only custom presets can be deleted. Built-in presets cannot be removed.

        Args:
            preset_id: The preset identifier to delete

        Returns:
            dict: Success status
        """
        try:
            return style_presets_manager.delete_custom_preset(preset_id)
        except ValueError as e:
            return {"error": str(e)}

    logger.info("Registered style preset tools")
