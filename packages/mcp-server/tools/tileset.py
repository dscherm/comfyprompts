"""Tileset generation tools for creating coherent game tilesets"""

import logging
import random
from typing import Optional

from mcp.server.fastmcp import FastMCP

from tools.helpers import register_and_build_response

logger = logging.getLogger("MCP_Server")


def _build_simple_workflow(
    model: str,
    prompt: str,
    negative_prompt: str,
    lora_name: Optional[str],
    lora_strength: float,
    tile_size: int,
    seed: int,
    steps: int,
    cfg: float,
    sampler_name: str,
    scheduler: str,
) -> dict:
    """Build a simple seamless texture workflow (txt2img with optional LoRA).

    Returns a ComfyUI workflow dict that chains:
    CheckpointLoaderSimple -> (optional LoraLoader) -> CLIPTextEncode x2 ->
    EmptyLatentImage -> KSampler -> VAEDecode -> SaveImage
    """
    workflow = {}
    next_id = 1

    # --- Node 1: CheckpointLoaderSimple ---
    checkpoint_id = str(next_id)
    workflow[checkpoint_id] = {
        "inputs": {"ckpt_name": model},
        "class_type": "CheckpointLoaderSimple",
        "_meta": {"title": "Load Checkpoint"},
    }
    next_id += 1

    # Track which node provides model / clip / vae outputs
    model_source = checkpoint_id
    model_output_idx = 0
    clip_source = checkpoint_id
    clip_output_idx = 1
    vae_source = checkpoint_id
    vae_output_idx = 2

    # --- Optional: LoraLoader ---
    if lora_name:
        lora_id = str(next_id)
        workflow[lora_id] = {
            "inputs": {
                "lora_name": lora_name,
                "strength_model": lora_strength,
                "strength_clip": lora_strength,
                "model": [model_source, model_output_idx],
                "clip": [clip_source, clip_output_idx],
            },
            "class_type": "LoraLoader",
            "_meta": {"title": "Load LoRA"},
        }
        model_source = lora_id
        model_output_idx = 0
        clip_source = lora_id
        clip_output_idx = 1
        next_id += 1

    # --- CLIPTextEncode (positive) ---
    pos_id = str(next_id)
    workflow[pos_id] = {
        "inputs": {
            "text": prompt,
            "clip": [clip_source, clip_output_idx],
        },
        "class_type": "CLIPTextEncode",
        "_meta": {"title": "CLIP Text Encode (Positive)"},
    }
    next_id += 1

    # --- CLIPTextEncode (negative) ---
    neg_id = str(next_id)
    workflow[neg_id] = {
        "inputs": {
            "text": negative_prompt,
            "clip": [clip_source, clip_output_idx],
        },
        "class_type": "CLIPTextEncode",
        "_meta": {"title": "CLIP Text Encode (Negative)"},
    }
    next_id += 1

    # --- EmptyLatentImage ---
    latent_id = str(next_id)
    workflow[latent_id] = {
        "inputs": {
            "width": tile_size,
            "height": tile_size,
            "batch_size": 1,
        },
        "class_type": "EmptyLatentImage",
        "_meta": {"title": "Empty Latent Image"},
    }
    next_id += 1

    # --- KSampler ---
    sampler_id = str(next_id)
    workflow[sampler_id] = {
        "inputs": {
            "seed": seed,
            "steps": steps,
            "cfg": cfg,
            "sampler_name": sampler_name,
            "scheduler": scheduler,
            "denoise": 1.0,
            "model": [model_source, model_output_idx],
            "positive": [pos_id, 0],
            "negative": [neg_id, 0],
            "latent_image": [latent_id, 0],
        },
        "class_type": "KSampler",
        "_meta": {"title": "KSampler"},
    }
    next_id += 1

    # --- VAEDecode ---
    decode_id = str(next_id)
    workflow[decode_id] = {
        "inputs": {
            "samples": [sampler_id, 0],
            "vae": [vae_source, vae_output_idx],
        },
        "class_type": "VAEDecode",
        "_meta": {"title": "VAE Decode"},
    }
    next_id += 1

    # --- SaveImage ---
    save_id = str(next_id)
    workflow[save_id] = {
        "inputs": {
            "filename_prefix": "ComfyUI_Tileset",
            "images": [decode_id, 0],
        },
        "class_type": "SaveImage",
        "_meta": {"title": "Save Image"},
    }

    return workflow


def _build_coherent_tileset_workflow(**kwargs) -> dict:
    """Build a coherent 16-tile marching squares workflow.

    TODO: Implement once comfyui-tileset-nodes custom node pack is available.
    Requires NonManifoldTilesetSampler, MarchingSquaresMasks, TilesetGridAssemble.
    """
    raise NotImplementedError(
        "Coherent tileset mode requires comfyui-tileset-nodes custom node pack. "
        "Install it first, then this workflow builder can be implemented."
    )


def _build_dual_terrain_workflow(**kwargs) -> dict:
    """Build a dual-terrain transition tileset workflow.

    TODO: Implement once comfyui-tileset-nodes custom node pack is available.
    Requires NonManifoldTilesetSampler with dual prompts, MarchingSquaresMasks,
    TilesetGridAssemble.
    """
    raise NotImplementedError(
        "Dual-terrain tileset mode requires comfyui-tileset-nodes custom node pack. "
        "Install it first, then this workflow builder can be implemented."
    )


def register_tileset_tools(
    mcp: FastMCP,
    comfyui_client,
    defaults_manager,
    asset_registry,
    webhook_manager=None,
):
    """Register tileset generation tools with the MCP server"""

    @mcp.tool()
    def generate_game_tileset(
        prompt: str,
        prompt_b: Optional[str] = None,
        negative_prompt: str = "blurry, text, watermark, 3d render",
        mode: str = "simple",
        output_format: str = "godot_minimal",
        tile_size: int = 512,
        lora_name: Optional[str] = None,
        lora_strength: float = 0.85,
        seed: Optional[int] = None,
        steps: int = 25,
        cfg: float = 7.0,
        export_godot: bool = False,
        godot_project_path: Optional[str] = None,
        return_inline_preview: bool = False,
    ) -> dict:
        """Generate game tilesets with coherent terrain transitions.

        Modes:
        - "simple": Single seamless texture using standard SDXL pipeline
        - "coherent": 16 marching squares tiles via non-manifold diffusion (requires comfyui-tileset-nodes)
        - "dual_terrain": Two-terrain transition tileset (requires comfyui-tileset-nodes)

        Args:
            prompt: Terrain description (e.g., "grass terrain, top-down RPG, sometile")
            prompt_b: Second terrain prompt for dual_terrain mode
            negative_prompt: Things to avoid in generation
            mode: Generation mode - "simple", "coherent", or "dual_terrain"
            output_format: Autotile format - "godot_minimal" (47), "godot_full" (256), "rpgmaker" (48), "generic" (256)
            tile_size: Pixel size per tile (default 512)
            lora_name: Optional LoRA model name (e.g., "style/SomeTile.safetensors")
            lora_strength: LoRA strength (0.0-1.0, default 0.85)
            seed: Random seed (None for random)
            steps: Sampling steps (default 25)
            cfg: CFG scale (default 7.0)
            export_godot: If True, export Godot .tres + atlas
            godot_project_path: Path to Godot project for direct export
            return_inline_preview: Include base64 preview in response

        Returns:
            Dict with asset info, mode, tile_count, and metadata
        """
        try:
            # Validate mode
            valid_modes = ("simple", "coherent", "dual_terrain")
            if mode not in valid_modes:
                return {"error": f"Invalid mode '{mode}'. Must be one of: {valid_modes}"}

            # Validate output_format
            valid_formats = ("godot_minimal", "godot_full", "rpgmaker", "generic")
            if output_format not in valid_formats:
                return {"error": f"Invalid output_format '{output_format}'. Must be one of: {valid_formats}"}

            # Validate tile_size
            if tile_size < 64 or tile_size > 2048:
                return {"error": f"tile_size must be between 64 and 2048, got {tile_size}"}

            # Validate lora_strength
            if lora_strength < 0.0 or lora_strength > 1.0:
                return {"error": f"lora_strength must be between 0.0 and 1.0, got {lora_strength}"}

            # dual_terrain requires prompt_b
            if mode == "dual_terrain" and not prompt_b:
                return {"error": "dual_terrain mode requires prompt_b (second terrain description)"}

            # Resolve defaults from DefaultsManager
            resolved_model = defaults_manager.get_default("image", "model", None)
            resolved_sampler = defaults_manager.get_default("image", "sampler_name", "euler")
            resolved_scheduler = defaults_manager.get_default("image", "scheduler", "normal")

            # Generate seed if not provided
            resolved_seed = seed if seed is not None else random.randint(0, 2**32 - 1)

            if mode == "simple":
                # Build and run the simple txt2img workflow
                workflow = _build_simple_workflow(
                    model=resolved_model,
                    prompt=prompt,
                    negative_prompt=negative_prompt,
                    lora_name=lora_name,
                    lora_strength=lora_strength,
                    tile_size=tile_size,
                    seed=resolved_seed,
                    steps=steps,
                    cfg=cfg,
                    sampler_name=resolved_sampler,
                    scheduler=resolved_scheduler,
                )

                result = comfyui_client.run_custom_workflow(
                    workflow, preferred_output_keys=("images", "image")
                )

                response_data = register_and_build_response(
                    result,
                    "generate_game_tileset",
                    asset_registry,
                    tool_name="generate_game_tileset",
                    return_inline_preview=return_inline_preview,
                    webhook_manager=webhook_manager,
                )

                # Add tileset-specific metadata
                response_data["mode"] = mode
                response_data["tile_size"] = tile_size
                response_data["tile_count"] = 1
                response_data["output_format"] = output_format
                response_data["seed"] = resolved_seed
                response_data["prompt"] = prompt

                if lora_name:
                    response_data["lora_name"] = lora_name
                    response_data["lora_strength"] = lora_strength

                return response_data

            elif mode == "coherent":
                return {
                    "error": (
                        "Coherent tileset mode requires comfyui-tileset-nodes custom node pack. "
                        "Install it first, then retry. See: "
                        "https://github.com/dscherm/comfyprompts for setup instructions."
                    )
                }

            elif mode == "dual_terrain":
                return {
                    "error": (
                        "Dual-terrain tileset mode requires comfyui-tileset-nodes custom node pack. "
                        "Install it first, then retry. See: "
                        "https://github.com/dscherm/comfyprompts for setup instructions."
                    )
                }

        except Exception as e:
            logger.exception("Failed to generate game tileset")
            return {"error": f"Failed to generate game tileset: {str(e)}"}

    logger.info("Registered tileset tool: generate_game_tileset")
