"""Style presets manager for applying predefined artistic styles"""

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("MCP_Server")

# Configuration paths
CONFIG_DIR = Path.home() / ".config" / "comfy-mcp"
CUSTOM_PRESETS_FILE = CONFIG_DIR / "custom_presets.json"


class StylePresetsManager:
    """Manages style presets for image generation"""

    # Built-in style presets with prompt modifiers and recommended settings
    BUILTIN_PRESETS: Dict[str, Dict[str, Any]] = {
        "photorealistic": {
            "name": "Photorealistic",
            "description": "Ultra-realistic photography style",
            "prompt_prefix": "photorealistic, highly detailed photograph, ",
            "prompt_suffix": ", 8k uhd, dslr, soft lighting, high quality, film grain, Fujifilm XT3",
            "negative_prompt": "cartoon, anime, illustration, painting, drawing, art, sketch, unrealistic, fake, cgi, 3d render",
            "recommended_settings": {
                "cfg": 1.0,
                "steps": 25,
                "sampler_name": "euler",
                "scheduler": "simple"
            }
        },
        "anime": {
            "name": "Anime",
            "description": "Japanese anime art style",
            "prompt_prefix": "anime style, ",
            "prompt_suffix": ", anime key visual, sharp focus, studio lighting, highly detailed",
            "negative_prompt": "photorealistic, photograph, 3d render, western cartoon, poorly drawn, bad anatomy",
            "recommended_settings": {
                "cfg": 1.0,
                "steps": 20,
                "sampler_name": "euler",
                "scheduler": "simple"
            }
        },
        "ghibli": {
            "name": "Studio Ghibli",
            "description": "Studio Ghibli anime style",
            "prompt_prefix": "studio ghibli style, ghibli anime, ",
            "prompt_suffix": ", hayao miyazaki art style, whimsical, soft colors, hand-drawn animation style",
            "negative_prompt": "photorealistic, 3d, cgi, dark, gritty, violent",
            "recommended_settings": {
                "cfg": 1.0,
                "steps": 25,
                "sampler_name": "euler",
                "scheduler": "simple"
            },
            "suggested_lora": "Ghibli_Flux_Lora.safetensors"
        },
        "pixel_art": {
            "name": "Pixel Art",
            "description": "Retro pixel art style",
            "prompt_prefix": "pixel art, 16-bit, retro game style, ",
            "prompt_suffix": ", pixelated, sprite art, limited color palette",
            "negative_prompt": "high resolution, photorealistic, smooth, gradient, anti-aliased",
            "recommended_settings": {
                "cfg": 1.0,
                "steps": 20,
                "sampler_name": "euler",
                "scheduler": "simple"
            },
            "suggested_lora": "pixel-art-flux-lora.safetensors"
        },
        "oil_painting": {
            "name": "Oil Painting",
            "description": "Classic oil painting style",
            "prompt_prefix": "oil painting, ",
            "prompt_suffix": ", masterpiece, traditional art, canvas texture, visible brushstrokes, classical painting technique",
            "negative_prompt": "photograph, digital art, 3d render, anime, cartoon, low quality",
            "recommended_settings": {
                "cfg": 1.0,
                "steps": 30,
                "sampler_name": "euler",
                "scheduler": "simple"
            }
        },
        "watercolor": {
            "name": "Watercolor",
            "description": "Soft watercolor painting style",
            "prompt_prefix": "watercolor painting, ",
            "prompt_suffix": ", soft edges, flowing colors, paper texture, artistic, traditional watercolor technique",
            "negative_prompt": "photograph, digital, sharp edges, 3d render, anime",
            "recommended_settings": {
                "cfg": 1.0,
                "steps": 25,
                "sampler_name": "euler",
                "scheduler": "simple"
            }
        },
        "cyberpunk": {
            "name": "Cyberpunk",
            "description": "Futuristic cyberpunk aesthetic",
            "prompt_prefix": "cyberpunk style, neon lights, ",
            "prompt_suffix": ", futuristic, sci-fi, high tech low life, neon colors, dark atmosphere, blade runner aesthetic",
            "negative_prompt": "natural, pastoral, bright daylight, historical, medieval, fantasy",
            "recommended_settings": {
                "cfg": 1.0,
                "steps": 25,
                "sampler_name": "euler",
                "scheduler": "simple"
            }
        },
        "fantasy": {
            "name": "Fantasy Art",
            "description": "Epic fantasy illustration style",
            "prompt_prefix": "fantasy art, epic, ",
            "prompt_suffix": ", detailed fantasy illustration, magical atmosphere, dramatic lighting, concept art",
            "negative_prompt": "modern, photograph, realistic, mundane, boring",
            "recommended_settings": {
                "cfg": 1.0,
                "steps": 25,
                "sampler_name": "euler",
                "scheduler": "simple"
            }
        },
        "minimalist": {
            "name": "Minimalist",
            "description": "Clean minimalist design",
            "prompt_prefix": "minimalist, simple, clean design, ",
            "prompt_suffix": ", minimal color palette, negative space, modern, elegant simplicity",
            "negative_prompt": "cluttered, busy, detailed, complex, ornate, baroque",
            "recommended_settings": {
                "cfg": 1.0,
                "steps": 20,
                "sampler_name": "euler",
                "scheduler": "simple"
            }
        },
        "cinematic": {
            "name": "Cinematic",
            "description": "Movie-like dramatic visuals",
            "prompt_prefix": "cinematic, movie still, ",
            "prompt_suffix": ", dramatic lighting, film grain, anamorphic lens, color grading, depth of field, epic composition",
            "negative_prompt": "amateur, low quality, flat lighting, boring composition",
            "recommended_settings": {
                "cfg": 1.0,
                "steps": 30,
                "sampler_name": "euler",
                "scheduler": "simple"
            }
        },
        "comic_book": {
            "name": "Comic Book",
            "description": "American comic book style",
            "prompt_prefix": "comic book style, ",
            "prompt_suffix": ", bold outlines, halftone dots, dynamic composition, vibrant colors, graphic novel art",
            "negative_prompt": "photorealistic, 3d render, anime, soft edges",
            "recommended_settings": {
                "cfg": 1.0,
                "steps": 20,
                "sampler_name": "euler",
                "scheduler": "simple"
            }
        },
        "noir": {
            "name": "Film Noir",
            "description": "Classic film noir aesthetic",
            "prompt_prefix": "film noir style, black and white, ",
            "prompt_suffix": ", high contrast, dramatic shadows, moody atmosphere, vintage cinema",
            "negative_prompt": "colorful, bright, cheerful, modern, digital",
            "recommended_settings": {
                "cfg": 1.0,
                "steps": 25,
                "sampler_name": "euler",
                "scheduler": "simple"
            }
        }
    }

    def __init__(self):
        self._custom_presets: Dict[str, Dict[str, Any]] = {}
        self._load_custom_presets()

    def _load_custom_presets(self) -> None:
        """Load custom presets from config file"""
        if CUSTOM_PRESETS_FILE.exists():
            try:
                with open(CUSTOM_PRESETS_FILE, "r", encoding="utf-8") as f:
                    self._custom_presets = json.load(f)
                logger.info(f"Loaded {len(self._custom_presets)} custom style presets")
            except (json.JSONDecodeError, IOError) as e:
                logger.warning(f"Failed to load custom presets: {e}")

    def _save_custom_presets(self) -> None:
        """Save custom presets to config file"""
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        try:
            with open(CUSTOM_PRESETS_FILE, "w", encoding="utf-8") as f:
                json.dump(self._custom_presets, f, indent=2)
        except IOError as e:
            logger.error(f"Failed to save custom presets: {e}")

    def list_presets(self) -> List[Dict[str, Any]]:
        """List all available style presets"""
        presets = []

        # Add built-in presets
        for preset_id, preset in self.BUILTIN_PRESETS.items():
            presets.append({
                "id": preset_id,
                "name": preset["name"],
                "description": preset["description"],
                "type": "builtin",
                "has_suggested_lora": "suggested_lora" in preset
            })

        # Add custom presets
        for preset_id, preset in self._custom_presets.items():
            presets.append({
                "id": preset_id,
                "name": preset.get("name", preset_id),
                "description": preset.get("description", "Custom preset"),
                "type": "custom",
                "has_suggested_lora": "suggested_lora" in preset
            })

        return presets

    def get_preset(self, preset_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific preset by ID"""
        if preset_id in self.BUILTIN_PRESETS:
            return {**self.BUILTIN_PRESETS[preset_id], "id": preset_id, "type": "builtin"}
        if preset_id in self._custom_presets:
            return {**self._custom_presets[preset_id], "id": preset_id, "type": "custom"}
        return None

    def apply_preset(self, preset_id: str, prompt: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Apply a style preset to a prompt and parameters

        Args:
            preset_id: The preset identifier
            prompt: The base prompt to enhance
            params: Optional existing parameters to merge with preset recommendations

        Returns:
            Dict with enhanced_prompt, negative_prompt, and recommended_settings
        """
        preset = self.get_preset(preset_id)
        if not preset:
            raise ValueError(f"Style preset '{preset_id}' not found")

        # Build enhanced prompt
        prefix = preset.get("prompt_prefix", "")
        suffix = preset.get("prompt_suffix", "")
        enhanced_prompt = f"{prefix}{prompt}{suffix}"

        # Get negative prompt
        negative_prompt = preset.get("negative_prompt", "")

        # Merge recommended settings with provided params
        recommended = preset.get("recommended_settings", {}).copy()
        if params:
            # User params take precedence
            for key, value in params.items():
                if value is not None:
                    recommended[key] = value

        result = {
            "enhanced_prompt": enhanced_prompt,
            "negative_prompt": negative_prompt,
            "settings": recommended,
            "preset_applied": preset_id
        }

        # Include suggested LoRA if available
        if "suggested_lora" in preset:
            result["suggested_lora"] = preset["suggested_lora"]

        return result

    def create_custom_preset(
        self,
        preset_id: str,
        name: str,
        description: str,
        prompt_prefix: str = "",
        prompt_suffix: str = "",
        negative_prompt: str = "",
        recommended_settings: Optional[Dict[str, Any]] = None,
        suggested_lora: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create a new custom style preset"""
        if preset_id in self.BUILTIN_PRESETS:
            raise ValueError(f"Cannot override built-in preset '{preset_id}'")

        preset = {
            "name": name,
            "description": description,
            "prompt_prefix": prompt_prefix,
            "prompt_suffix": prompt_suffix,
            "negative_prompt": negative_prompt,
            "recommended_settings": recommended_settings or {}
        }

        if suggested_lora:
            preset["suggested_lora"] = suggested_lora

        self._custom_presets[preset_id] = preset
        self._save_custom_presets()

        return {"success": True, "preset_id": preset_id, "preset": preset}

    def delete_custom_preset(self, preset_id: str) -> Dict[str, Any]:
        """Delete a custom preset"""
        if preset_id in self.BUILTIN_PRESETS:
            raise ValueError(f"Cannot delete built-in preset '{preset_id}'")

        if preset_id not in self._custom_presets:
            raise ValueError(f"Custom preset '{preset_id}' not found")

        del self._custom_presets[preset_id]
        self._save_custom_presets()

        return {"success": True, "deleted": preset_id}
