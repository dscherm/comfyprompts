"""Export tools for resizing images to social media platform dimensions"""

import logging
from typing import Any, Dict, List, Optional

from mcp.server.fastmcp import FastMCP

logger = logging.getLogger("MCP_Server")


def register_export_tools(
    mcp: FastMCP,
    export_presets_manager,
    asset_registry
):
    """Register export preset tools"""

    @mcp.tool()
    def list_export_presets(platform: Optional[str] = None) -> dict:
        """List all available export presets for social media platforms.

        Args:
            platform: Optional filter by platform (e.g., "Instagram", "TikTok")

        Returns:
            dict: List of presets with dimensions and descriptions

        Available platforms:
            - Instagram (square, portrait, landscape, story)
            - TikTok
            - YouTube (thumbnail, banner)
            - Twitter/X (post, header)
            - Facebook (post, cover, story)
            - LinkedIn (post, banner)
            - Pinterest (pin, long pin)
            - Discord (banner)
            - Twitch (banner)
            - General (square_1k, hd_landscape, hd_portrait, 4k_landscape)
        """
        presets = export_presets_manager.list_presets(platform)
        platforms = export_presets_manager.list_platforms()

        return {
            "presets": presets,
            "total": len(presets),
            "platforms": platforms,
            "usage": "Use export_image(asset_id, preset_id) to export"
        }

    @mcp.tool()
    def get_export_preset(preset_id: str) -> dict:
        """Get detailed information about an export preset.

        Args:
            preset_id: The preset identifier (e.g., "instagram_square")

        Returns:
            dict: Full preset details including dimensions and file limits
        """
        preset = export_presets_manager.get_preset(preset_id)
        if not preset:
            available = [p["id"] for p in export_presets_manager.list_presets()]
            return {
                "error": f"Preset '{preset_id}' not found",
                "available_presets": available[:20]
            }
        return {"preset": preset}

    @mcp.tool()
    def export_image(
        asset_id: str,
        preset_id: str,
        crop_mode: str = "center",
        quality: Optional[int] = None,
        add_watermark: bool = False,
        watermark_position: str = "bottom_right",
        watermark_opacity: float = 0.5
    ) -> dict:
        """Export an image to a specific social media format.

        Intelligently resizes and crops your generated image to match
        platform-specific dimensions and file size requirements.

        Args:
            asset_id: ID of the generated image asset
            preset_id: Export preset (e.g., "instagram_square", "youtube_thumbnail")
            crop_mode: How to crop - "center", "top", "bottom", "left", "right"
            quality: JPEG quality 1-100 (uses preset default if not specified)
            add_watermark: Add watermark to exported image
            watermark_position: "top_left", "top_right", "bottom_left", "bottom_right", "center"
            watermark_opacity: Watermark opacity 0.0-1.0

        Returns:
            dict: Export result with output path, dimensions, file size

        Example:
            export_image("abc123", "instagram_portrait")
            export_image("abc123", "youtube_thumbnail", crop_mode="center", quality=90)
        """
        # Get asset
        asset = asset_registry.get_asset(asset_id)
        if not asset:
            return {"error": f"Asset '{asset_id}' not found"}

        # Get image path from asset
        image_path = asset_registry.get_asset_local_path(asset_id)
        if not image_path:
            return {"error": f"Could not resolve local path for asset '{asset_id}'"}

        # Export
        result = export_presets_manager.export_image(
            image_path=image_path,
            preset_id=preset_id,
            crop_mode=crop_mode,
            quality=quality,
            add_watermark=add_watermark,
            watermark_position=watermark_position,
            watermark_opacity=watermark_opacity
        )

        if "error" in result:
            return result

        result["source_asset_id"] = asset_id
        return result

    @mcp.tool()
    def batch_export_image(
        asset_id: str,
        preset_ids: List[str],
        crop_mode: str = "center",
        add_watermark: bool = False
    ) -> dict:
        """Export an image to multiple social media formats at once.

        Perfect for creating all your social media assets from one generation.

        Args:
            asset_id: ID of the generated image asset
            preset_ids: List of preset IDs to export to
            crop_mode: How to crop all exports
            add_watermark: Add watermark to all exports

        Returns:
            dict: Results for each preset export

        Example:
            batch_export_image(
                "abc123",
                ["instagram_square", "instagram_story", "twitter_post", "youtube_thumbnail"]
            )
        """
        # Get asset
        asset = asset_registry.get_asset(asset_id)
        if not asset:
            return {"error": f"Asset '{asset_id}' not found"}

        # Get image path
        image_path = asset_registry.get_asset_local_path(asset_id)
        if not image_path:
            return {"error": f"Could not resolve local path for asset '{asset_id}'"}

        # Batch export
        result = export_presets_manager.batch_export(
            image_path=image_path,
            preset_ids=preset_ids,
            crop_mode=crop_mode,
            add_watermark=add_watermark
        )

        result["source_asset_id"] = asset_id
        return result

    @mcp.tool()
    def set_watermark(watermark_path: str) -> dict:
        """Set a watermark image to use when exporting.

        The watermark will be saved and reused for future exports.
        Use a PNG with transparency for best results.

        Args:
            watermark_path: Path to watermark image file (PNG recommended)

        Returns:
            dict: Success status and watermark info
        """
        return export_presets_manager.set_watermark(watermark_path)

    @mcp.tool()
    def create_export_preset(
        preset_id: str,
        name: str,
        width: int,
        height: int,
        platform: str = "Custom",
        description: str = "",
        max_file_size_mb: float = 10,
        quality: int = 85
    ) -> dict:
        """Create a custom export preset for your specific needs.

        Args:
            preset_id: Unique identifier (lowercase, no spaces)
            name: Display name for the preset
            width: Target width in pixels
            height: Target height in pixels
            platform: Platform name for organization
            description: What this preset is for
            max_file_size_mb: Maximum file size limit
            quality: Default JPEG quality (1-100)

        Returns:
            dict: Created preset details

        Example:
            create_export_preset(
                preset_id="my_blog",
                name="My Blog Header",
                width=1200,
                height=400,
                platform="Blog",
                description="Header image for my blog posts"
            )
        """
        return export_presets_manager.create_custom_preset(
            preset_id=preset_id,
            name=name,
            width=width,
            height=height,
            platform=platform,
            description=description,
            max_file_size_mb=max_file_size_mb,
            default_quality=quality
        )

    @mcp.tool()
    def delete_export_preset(preset_id: str) -> dict:
        """Delete a custom export preset.

        Only custom presets can be deleted. Built-in presets cannot be removed.

        Args:
            preset_id: The preset identifier to delete

        Returns:
            dict: Success status
        """
        return export_presets_manager.delete_custom_preset(preset_id)

    logger.info("Registered export tools")
