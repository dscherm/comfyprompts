"""Export presets manager for social media and platform-specific image sizing"""

import io
import json
import logging
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

try:
    from PIL import Image, ImageDraw, ImageFont, ImageOps
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

logger = logging.getLogger("MCP_Server")

# Configuration paths
CONFIG_DIR = Path.home() / ".config" / "comfy-mcp"
CUSTOM_PRESETS_FILE = CONFIG_DIR / "export_presets.json"
WATERMARK_FILE = CONFIG_DIR / "watermark.png"


class CropMode(Enum):
    """Crop positioning modes"""
    CENTER = "center"
    TOP = "top"
    BOTTOM = "bottom"
    LEFT = "left"
    RIGHT = "right"
    SMART = "smart"  # Attempts to detect focal point


@dataclass
class ExportPreset:
    """Defines an export preset for a specific platform"""
    id: str
    name: str
    platform: str
    width: int
    height: int
    aspect_ratio: str
    max_file_size_mb: float
    description: str
    default_quality: int = 85
    format: str = "JPEG"  # JPEG, PNG, WEBP


class ExportPresetsManager:
    """Manages export presets for social media platforms"""

    # Built-in presets for major platforms
    BUILTIN_PRESETS: Dict[str, ExportPreset] = {
        # Instagram
        "instagram_square": ExportPreset(
            id="instagram_square",
            name="Instagram Square",
            platform="Instagram",
            width=1080,
            height=1080,
            aspect_ratio="1:1",
            max_file_size_mb=30,
            description="Square post for Instagram feed"
        ),
        "instagram_portrait": ExportPreset(
            id="instagram_portrait",
            name="Instagram Portrait",
            platform="Instagram",
            width=1080,
            height=1350,
            aspect_ratio="4:5",
            max_file_size_mb=30,
            description="Portrait post for Instagram feed (recommended for engagement)"
        ),
        "instagram_landscape": ExportPreset(
            id="instagram_landscape",
            name="Instagram Landscape",
            platform="Instagram",
            width=1080,
            height=566,
            aspect_ratio="1.91:1",
            max_file_size_mb=30,
            description="Landscape post for Instagram feed"
        ),
        "instagram_story": ExportPreset(
            id="instagram_story",
            name="Instagram Story/Reels",
            platform="Instagram",
            width=1080,
            height=1920,
            aspect_ratio="9:16",
            max_file_size_mb=30,
            description="Full-screen vertical for Stories and Reels"
        ),

        # TikTok
        "tiktok": ExportPreset(
            id="tiktok",
            name="TikTok",
            platform="TikTok",
            width=1080,
            height=1920,
            aspect_ratio="9:16",
            max_file_size_mb=287,
            description="Standard TikTok video/image size"
        ),

        # YouTube
        "youtube_thumbnail": ExportPreset(
            id="youtube_thumbnail",
            name="YouTube Thumbnail",
            platform="YouTube",
            width=1280,
            height=720,
            aspect_ratio="16:9",
            max_file_size_mb=2,
            description="YouTube video thumbnail"
        ),
        "youtube_banner": ExportPreset(
            id="youtube_banner",
            name="YouTube Channel Banner",
            platform="YouTube",
            width=2560,
            height=1440,
            aspect_ratio="16:9",
            max_file_size_mb=6,
            description="YouTube channel art/banner"
        ),

        # Twitter/X
        "twitter_post": ExportPreset(
            id="twitter_post",
            name="Twitter/X Post",
            platform="Twitter/X",
            width=1200,
            height=675,
            aspect_ratio="16:9",
            max_file_size_mb=5,
            description="Standard Twitter image post"
        ),
        "twitter_header": ExportPreset(
            id="twitter_header",
            name="Twitter/X Header",
            platform="Twitter/X",
            width=1500,
            height=500,
            aspect_ratio="3:1",
            max_file_size_mb=5,
            description="Twitter profile header image"
        ),

        # Facebook
        "facebook_post": ExportPreset(
            id="facebook_post",
            name="Facebook Post",
            platform="Facebook",
            width=1200,
            height=630,
            aspect_ratio="1.91:1",
            max_file_size_mb=30,
            description="Standard Facebook image post"
        ),
        "facebook_cover": ExportPreset(
            id="facebook_cover",
            name="Facebook Cover",
            platform="Facebook",
            width=820,
            height=312,
            aspect_ratio="2.63:1",
            max_file_size_mb=30,
            description="Facebook page/profile cover photo"
        ),
        "facebook_story": ExportPreset(
            id="facebook_story",
            name="Facebook Story",
            platform="Facebook",
            width=1080,
            height=1920,
            aspect_ratio="9:16",
            max_file_size_mb=30,
            description="Facebook Stories"
        ),

        # LinkedIn
        "linkedin_post": ExportPreset(
            id="linkedin_post",
            name="LinkedIn Post",
            platform="LinkedIn",
            width=1200,
            height=627,
            aspect_ratio="1.91:1",
            max_file_size_mb=5,
            description="LinkedIn feed post image"
        ),
        "linkedin_banner": ExportPreset(
            id="linkedin_banner",
            name="LinkedIn Banner",
            platform="LinkedIn",
            width=1584,
            height=396,
            aspect_ratio="4:1",
            max_file_size_mb=8,
            description="LinkedIn profile background image"
        ),

        # Pinterest
        "pinterest_pin": ExportPreset(
            id="pinterest_pin",
            name="Pinterest Pin",
            platform="Pinterest",
            width=1000,
            height=1500,
            aspect_ratio="2:3",
            max_file_size_mb=20,
            description="Standard Pinterest pin (recommended)"
        ),
        "pinterest_long": ExportPreset(
            id="pinterest_long",
            name="Pinterest Long Pin",
            platform="Pinterest",
            width=1000,
            height=2100,
            aspect_ratio="1:2.1",
            max_file_size_mb=20,
            description="Long-form Pinterest pin for infographics"
        ),

        # Discord
        "discord_banner": ExportPreset(
            id="discord_banner",
            name="Discord Server Banner",
            platform="Discord",
            width=960,
            height=540,
            aspect_ratio="16:9",
            max_file_size_mb=10,
            description="Discord server banner image"
        ),

        # Twitch
        "twitch_banner": ExportPreset(
            id="twitch_banner",
            name="Twitch Profile Banner",
            platform="Twitch",
            width=1200,
            height=480,
            aspect_ratio="2.5:1",
            max_file_size_mb=10,
            description="Twitch channel banner"
        ),

        # General
        "square_1k": ExportPreset(
            id="square_1k",
            name="Square 1K",
            platform="General",
            width=1024,
            height=1024,
            aspect_ratio="1:1",
            max_file_size_mb=10,
            description="General purpose square image"
        ),
        "hd_landscape": ExportPreset(
            id="hd_landscape",
            name="HD Landscape",
            platform="General",
            width=1920,
            height=1080,
            aspect_ratio="16:9",
            max_file_size_mb=10,
            description="Full HD landscape (1080p)"
        ),
        "hd_portrait": ExportPreset(
            id="hd_portrait",
            name="HD Portrait",
            platform="General",
            width=1080,
            height=1920,
            aspect_ratio="9:16",
            max_file_size_mb=10,
            description="Full HD portrait"
        ),
        "4k_landscape": ExportPreset(
            id="4k_landscape",
            name="4K Landscape",
            platform="General",
            width=3840,
            height=2160,
            aspect_ratio="16:9",
            max_file_size_mb=25,
            description="4K UHD landscape"
        ),
    }

    def __init__(self):
        self._custom_presets: Dict[str, Dict[str, Any]] = {}
        self._watermark_image: Optional[Image.Image] = None
        self._load_custom_presets()
        self._load_watermark()

        if not HAS_PIL:
            logger.warning("PIL/Pillow not installed. Export features will be limited.")

    def _load_custom_presets(self) -> None:
        """Load custom presets from config file"""
        if CUSTOM_PRESETS_FILE.exists():
            try:
                with open(CUSTOM_PRESETS_FILE, "r", encoding="utf-8") as f:
                    self._custom_presets = json.load(f)
                logger.info(f"Loaded {len(self._custom_presets)} custom export presets")
            except (json.JSONDecodeError, IOError) as e:
                logger.warning(f"Failed to load custom export presets: {e}")

    def _save_custom_presets(self) -> None:
        """Save custom presets to config file"""
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        try:
            with open(CUSTOM_PRESETS_FILE, "w", encoding="utf-8") as f:
                json.dump(self._custom_presets, f, indent=2)
        except IOError as e:
            logger.error(f"Failed to save custom export presets: {e}")

    def _load_watermark(self) -> None:
        """Load watermark image if it exists"""
        if HAS_PIL and WATERMARK_FILE.exists():
            try:
                self._watermark_image = Image.open(WATERMARK_FILE).convert("RGBA")
                logger.info(f"Loaded watermark image from {WATERMARK_FILE}")
            except Exception as e:
                logger.warning(f"Failed to load watermark image: {e}")

    def list_presets(self, platform: Optional[str] = None) -> List[Dict[str, Any]]:
        """List all available export presets, optionally filtered by platform"""
        presets = []

        # Add built-in presets
        for preset_id, preset in self.BUILTIN_PRESETS.items():
            if platform and preset.platform.lower() != platform.lower():
                continue
            presets.append({
                "id": preset_id,
                "name": preset.name,
                "platform": preset.platform,
                "dimensions": f"{preset.width}x{preset.height}",
                "aspect_ratio": preset.aspect_ratio,
                "description": preset.description,
                "type": "builtin"
            })

        # Add custom presets
        for preset_id, preset_data in self._custom_presets.items():
            if platform and preset_data.get("platform", "").lower() != platform.lower():
                continue
            presets.append({
                "id": preset_id,
                "name": preset_data.get("name", preset_id),
                "platform": preset_data.get("platform", "Custom"),
                "dimensions": f"{preset_data['width']}x{preset_data['height']}",
                "aspect_ratio": preset_data.get("aspect_ratio", "custom"),
                "description": preset_data.get("description", "Custom preset"),
                "type": "custom"
            })

        return presets

    def list_platforms(self) -> List[str]:
        """List all unique platforms"""
        platforms = set()
        for preset in self.BUILTIN_PRESETS.values():
            platforms.add(preset.platform)
        for preset_data in self._custom_presets.values():
            platforms.add(preset_data.get("platform", "Custom"))
        return sorted(list(platforms))

    def get_preset(self, preset_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific preset by ID"""
        if preset_id in self.BUILTIN_PRESETS:
            preset = self.BUILTIN_PRESETS[preset_id]
            return {
                "id": preset_id,
                "name": preset.name,
                "platform": preset.platform,
                "width": preset.width,
                "height": preset.height,
                "aspect_ratio": preset.aspect_ratio,
                "max_file_size_mb": preset.max_file_size_mb,
                "description": preset.description,
                "default_quality": preset.default_quality,
                "format": preset.format,
                "type": "builtin"
            }
        if preset_id in self._custom_presets:
            return {**self._custom_presets[preset_id], "id": preset_id, "type": "custom"}
        return None

    def export_image(
        self,
        image_path: str,
        preset_id: str,
        output_path: Optional[str] = None,
        crop_mode: str = "center",
        quality: Optional[int] = None,
        add_watermark: bool = False,
        watermark_position: str = "bottom_right",
        watermark_opacity: float = 0.5,
        watermark_scale: float = 0.15
    ) -> Dict[str, Any]:
        """Export an image using a preset

        Args:
            image_path: Path to source image
            preset_id: Export preset to use
            output_path: Optional output path (auto-generated if not provided)
            crop_mode: How to crop: center, top, bottom, left, right, smart
            quality: JPEG/WebP quality (1-100), uses preset default if not specified
            add_watermark: Whether to add watermark
            watermark_position: Position: top_left, top_right, bottom_left, bottom_right, center
            watermark_opacity: Watermark opacity (0.0-1.0)
            watermark_scale: Watermark size relative to image (0.0-1.0)

        Returns:
            Dict with output_path, dimensions, file_size, format
        """
        if not HAS_PIL:
            return {"error": "PIL/Pillow not installed. Run: pip install Pillow"}

        preset = self.get_preset(preset_id)
        if not preset:
            return {"error": f"Preset '{preset_id}' not found"}

        try:
            # Load image
            img = Image.open(image_path)
            original_size = img.size

            # Convert to RGB if necessary (for JPEG output)
            if preset.get("format", "JPEG") == "JPEG" and img.mode in ("RGBA", "P"):
                # Create white background for transparency
                background = Image.new("RGB", img.size, (255, 255, 255))
                if img.mode == "P":
                    img = img.convert("RGBA")
                background.paste(img, mask=img.split()[-1] if img.mode == "RGBA" else None)
                img = background

            # Calculate crop/resize
            target_width = preset["width"]
            target_height = preset["height"]

            # Resize and crop to target dimensions
            img = self._resize_and_crop(img, target_width, target_height, crop_mode)

            # Add watermark if requested
            if add_watermark and self._watermark_image:
                img = self._apply_watermark(
                    img,
                    watermark_position,
                    watermark_opacity,
                    watermark_scale
                )

            # Determine output path
            if not output_path:
                source_path = Path(image_path)
                suffix = ".jpg" if preset.get("format", "JPEG") == "JPEG" else ".png"
                output_path = str(source_path.parent / f"{source_path.stem}_{preset_id}{suffix}")

            # Save with quality optimization
            output_quality = quality or preset.get("default_quality", 85)
            max_size_bytes = int(preset.get("max_file_size_mb", 10) * 1024 * 1024)

            output_path = self._save_optimized(
                img,
                output_path,
                preset.get("format", "JPEG"),
                output_quality,
                max_size_bytes
            )

            # Get final file size
            file_size = Path(output_path).stat().st_size

            return {
                "success": True,
                "output_path": output_path,
                "preset_used": preset_id,
                "original_size": f"{original_size[0]}x{original_size[1]}",
                "output_size": f"{target_width}x{target_height}",
                "file_size_bytes": file_size,
                "file_size_mb": round(file_size / (1024 * 1024), 2),
                "format": preset.get("format", "JPEG"),
                "quality": output_quality,
                "watermarked": add_watermark and self._watermark_image is not None
            }

        except Exception as e:
            logger.error(f"Failed to export image: {e}")
            return {"error": str(e)}

    def batch_export(
        self,
        image_path: str,
        preset_ids: List[str],
        output_dir: Optional[str] = None,
        crop_mode: str = "center",
        add_watermark: bool = False
    ) -> Dict[str, Any]:
        """Export an image to multiple presets at once

        Args:
            image_path: Path to source image
            preset_ids: List of preset IDs to export to
            output_dir: Directory for outputs (uses source dir if not specified)
            crop_mode: How to crop images
            add_watermark: Whether to add watermark to all exports

        Returns:
            Dict with results for each preset
        """
        results = []
        errors = []

        if output_dir:
            Path(output_dir).mkdir(parents=True, exist_ok=True)

        for preset_id in preset_ids:
            if output_dir:
                source_name = Path(image_path).stem
                preset = self.get_preset(preset_id)
                suffix = ".jpg" if preset and preset.get("format", "JPEG") == "JPEG" else ".png"
                output_path = str(Path(output_dir) / f"{source_name}_{preset_id}{suffix}")
            else:
                output_path = None

            result = self.export_image(
                image_path=image_path,
                preset_id=preset_id,
                output_path=output_path,
                crop_mode=crop_mode,
                add_watermark=add_watermark
            )

            if "error" in result:
                errors.append({"preset_id": preset_id, "error": result["error"]})
            else:
                results.append(result)

        return {
            "source_image": image_path,
            "total_presets": len(preset_ids),
            "successful": len(results),
            "failed": len(errors),
            "results": results,
            "errors": errors if errors else None
        }

    def _resize_and_crop(
        self,
        img: "Image.Image",
        target_width: int,
        target_height: int,
        crop_mode: str
    ) -> "Image.Image":
        """Resize and crop image to target dimensions"""
        orig_width, orig_height = img.size
        target_ratio = target_width / target_height
        orig_ratio = orig_width / orig_height

        # Determine resize dimensions (fill the target area)
        if orig_ratio > target_ratio:
            # Image is wider - resize by height, crop width
            new_height = target_height
            new_width = int(orig_width * (target_height / orig_height))
        else:
            # Image is taller - resize by width, crop height
            new_width = target_width
            new_height = int(orig_height * (target_width / orig_width))

        # Resize
        img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)

        # Calculate crop box
        if crop_mode == "center":
            left = (new_width - target_width) // 2
            top = (new_height - target_height) // 2
        elif crop_mode == "top":
            left = (new_width - target_width) // 2
            top = 0
        elif crop_mode == "bottom":
            left = (new_width - target_width) // 2
            top = new_height - target_height
        elif crop_mode == "left":
            left = 0
            top = (new_height - target_height) // 2
        elif crop_mode == "right":
            left = new_width - target_width
            top = (new_height - target_height) // 2
        else:  # smart or fallback to center
            left = (new_width - target_width) // 2
            top = (new_height - target_height) // 2

        # Crop
        right = left + target_width
        bottom = top + target_height
        img = img.crop((left, top, right, bottom))

        return img

    def _apply_watermark(
        self,
        img: "Image.Image",
        position: str,
        opacity: float,
        scale: float
    ) -> "Image.Image":
        """Apply watermark to image"""
        if not self._watermark_image:
            return img

        # Convert to RGBA for compositing
        if img.mode != "RGBA":
            img = img.convert("RGBA")

        # Scale watermark
        wm = self._watermark_image.copy()
        wm_width = int(img.width * scale)
        wm_height = int(wm.height * (wm_width / wm.width))
        wm = wm.resize((wm_width, wm_height), Image.Resampling.LANCZOS)

        # Apply opacity
        if opacity < 1.0:
            alpha = wm.split()[3]
            alpha = alpha.point(lambda p: int(p * opacity))
            wm.putalpha(alpha)

        # Calculate position
        padding = int(img.width * 0.02)  # 2% padding

        if position == "top_left":
            pos = (padding, padding)
        elif position == "top_right":
            pos = (img.width - wm_width - padding, padding)
        elif position == "bottom_left":
            pos = (padding, img.height - wm_height - padding)
        elif position == "center":
            pos = ((img.width - wm_width) // 2, (img.height - wm_height) // 2)
        else:  # bottom_right (default)
            pos = (img.width - wm_width - padding, img.height - wm_height - padding)

        # Composite
        img.paste(wm, pos, wm)

        return img

    def _save_optimized(
        self,
        img: "Image.Image",
        output_path: str,
        format: str,
        quality: int,
        max_size_bytes: int
    ) -> str:
        """Save image with size optimization"""
        # Ensure correct extension
        if format == "JPEG" and not output_path.lower().endswith((".jpg", ".jpeg")):
            output_path = output_path.rsplit(".", 1)[0] + ".jpg"
        elif format == "PNG" and not output_path.lower().endswith(".png"):
            output_path = output_path.rsplit(".", 1)[0] + ".png"
        elif format == "WEBP" and not output_path.lower().endswith(".webp"):
            output_path = output_path.rsplit(".", 1)[0] + ".webp"

        # Convert RGBA to RGB for JPEG
        if format == "JPEG" and img.mode == "RGBA":
            background = Image.new("RGB", img.size, (255, 255, 255))
            background.paste(img, mask=img.split()[3])
            img = background

        # Try to save within size limit
        current_quality = quality
        while current_quality >= 20:
            buffer = io.BytesIO()
            if format == "PNG":
                img.save(buffer, format="PNG", optimize=True)
            else:
                img.save(buffer, format=format, quality=current_quality, optimize=True)

            if buffer.tell() <= max_size_bytes:
                break
            current_quality -= 10

        # Save to file
        if format == "PNG":
            img.save(output_path, format="PNG", optimize=True)
        else:
            img.save(output_path, format=format, quality=current_quality, optimize=True)

        return output_path

    def set_watermark(self, watermark_path: str) -> Dict[str, Any]:
        """Set the watermark image"""
        if not HAS_PIL:
            return {"error": "PIL/Pillow not installed"}

        try:
            wm = Image.open(watermark_path).convert("RGBA")

            # Save to config directory
            CONFIG_DIR.mkdir(parents=True, exist_ok=True)
            wm.save(WATERMARK_FILE, "PNG")

            self._watermark_image = wm

            return {
                "success": True,
                "watermark_path": str(WATERMARK_FILE),
                "watermark_size": f"{wm.width}x{wm.height}"
            }
        except Exception as e:
            return {"error": f"Failed to set watermark: {e}"}

    def create_custom_preset(
        self,
        preset_id: str,
        name: str,
        width: int,
        height: int,
        platform: str = "Custom",
        description: str = "",
        max_file_size_mb: float = 10,
        default_quality: int = 85,
        format: str = "JPEG"
    ) -> Dict[str, Any]:
        """Create a custom export preset"""
        if preset_id in self.BUILTIN_PRESETS:
            return {"error": f"Cannot override built-in preset '{preset_id}'"}

        # Calculate aspect ratio
        from math import gcd
        divisor = gcd(width, height)
        aspect_ratio = f"{width // divisor}:{height // divisor}"

        self._custom_presets[preset_id] = {
            "name": name,
            "platform": platform,
            "width": width,
            "height": height,
            "aspect_ratio": aspect_ratio,
            "max_file_size_mb": max_file_size_mb,
            "description": description,
            "default_quality": default_quality,
            "format": format
        }

        self._save_custom_presets()

        return {
            "success": True,
            "preset_id": preset_id,
            "preset": self._custom_presets[preset_id]
        }

    def delete_custom_preset(self, preset_id: str) -> Dict[str, Any]:
        """Delete a custom preset"""
        if preset_id in self.BUILTIN_PRESETS:
            return {"error": f"Cannot delete built-in preset '{preset_id}'"}

        if preset_id not in self._custom_presets:
            return {"error": f"Custom preset '{preset_id}' not found"}

        del self._custom_presets[preset_id]
        self._save_custom_presets()

        return {"success": True, "deleted": preset_id}
