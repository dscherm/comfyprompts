"""Batch generation tools for generating multiple images/videos at once"""

import copy
import logging
import random
from typing import Any, Dict, List, Optional

from mcp.server.fastmcp import FastMCP
from tools.helpers import register_and_build_response

logger = logging.getLogger("MCP_Server")


def register_batch_tools(
    mcp: FastMCP,
    workflow_manager,
    comfyui_client,
    defaults_manager,
    asset_registry,
    style_presets_manager
):
    """Register batch generation tools"""

    @mcp.tool()
    def batch_generate(
        workflow_id: str,
        base_params: Dict[str, Any],
        variations: List[Dict[str, Any]],
        common_seed: Optional[int] = None
    ) -> dict:
        """Generate multiple images/videos with parameter variations.

        Runs the same workflow multiple times with different parameters.
        Useful for exploring prompt variations, testing different settings,
        or generating multiple versions of an image.

        Args:
            workflow_id: The workflow to use (e.g., "generate_image", "generate_video")
            base_params: Base parameters applied to all generations
            variations: List of parameter overrides for each generation
            common_seed: If provided, use this seed for all generations

        Returns:
            dict: Results for each generation

        Example:
            # Generate 3 images with different prompts
            batch_generate(
                workflow_id="generate_image",
                base_params={"width": 512, "height": 512, "steps": 20},
                variations=[
                    {"prompt": "a red apple"},
                    {"prompt": "a green apple"},
                    {"prompt": "a golden apple"}
                ]
            )

            # Generate same image with different step counts
            batch_generate(
                workflow_id="generate_image",
                base_params={"prompt": "a beautiful landscape", "width": 512},
                variations=[
                    {"steps": 10},
                    {"steps": 20},
                    {"steps": 30}
                ],
                common_seed=42  # Same seed for comparison
            )
        """
        # Find the workflow definition
        definition = None
        for defn in workflow_manager.tool_definitions:
            if defn.workflow_id == workflow_id or defn.tool_name == workflow_id:
                definition = defn
                break

        if not definition:
            available = [d.workflow_id for d in workflow_manager.tool_definitions]
            return {
                "error": f"Workflow '{workflow_id}' not found",
                "available_workflows": available
            }

        results = []
        errors = []

        for i, variation in enumerate(variations):
            try:
                # Merge base params with variation
                params = {**base_params, **variation}

                # Handle seed
                if common_seed is not None:
                    params["seed"] = common_seed
                elif "seed" not in params:
                    params["seed"] = random.randint(0, 2**32 - 1)

                # Render and run workflow
                workflow = workflow_manager.render_workflow(definition, params, defaults_manager)
                result = comfyui_client.run_custom_workflow(
                    workflow,
                    preferred_output_keys=definition.output_preferences
                )

                # Register asset
                asset_result = register_and_build_response(
                    result,
                    definition.workflow_id,
                    asset_registry,
                    tool_name=f"batch_generate[{i}]",
                    return_inline_preview=False
                )

                results.append({
                    "index": i,
                    "params": params,
                    "result": asset_result
                })

            except Exception as e:
                logger.error(f"Batch item {i} failed: {e}")
                errors.append({
                    "index": i,
                    "params": params,
                    "error": str(e)
                })

        return {
            "workflow_id": workflow_id,
            "total_requested": len(variations),
            "successful": len(results),
            "failed": len(errors),
            "results": results,
            "errors": errors if errors else None
        }

    @mcp.tool()
    def batch_generate_with_styles(
        prompt: str,
        style_preset_ids: List[str],
        base_params: Optional[Dict[str, Any]] = None,
        common_seed: Optional[int] = None
    ) -> dict:
        """Generate the same prompt with multiple style presets applied.

        Useful for comparing how different artistic styles interpret your prompt.

        Args:
            prompt: Base prompt to use for all generations
            style_preset_ids: List of style preset IDs to apply
            base_params: Optional base parameters (width, height, steps, etc.)
            common_seed: If provided, use this seed for all generations

        Returns:
            dict: Results for each style variation

        Example:
            batch_generate_with_styles(
                prompt="a cat sitting on a windowsill",
                style_preset_ids=["anime", "photorealistic", "oil_painting", "pixel_art"],
                base_params={"width": 512, "height": 512},
                common_seed=42
            )
        """
        # Find generate_image workflow
        definition = None
        for defn in workflow_manager.tool_definitions:
            if defn.workflow_id == "generate_image":
                definition = defn
                break

        if not definition:
            return {"error": "generate_image workflow not found"}

        results = []
        errors = []
        base_params = base_params or {}

        for i, preset_id in enumerate(style_preset_ids):
            try:
                # Apply style preset
                preset = style_presets_manager.get_preset(preset_id)
                if not preset:
                    errors.append({
                        "index": i,
                        "preset_id": preset_id,
                        "error": f"Style preset '{preset_id}' not found"
                    })
                    continue

                # Apply preset to get enhanced prompt
                styled = style_presets_manager.apply_preset(preset_id, prompt, base_params)

                # Build params
                params = {
                    "prompt": styled["enhanced_prompt"],
                    "negative_prompt": styled["negative_prompt"],
                    **base_params,
                    **styled.get("settings", {})
                }

                # Handle seed
                if common_seed is not None:
                    params["seed"] = common_seed
                elif "seed" not in params:
                    params["seed"] = random.randint(0, 2**32 - 1)

                # Render and run workflow
                workflow = workflow_manager.render_workflow(definition, params, defaults_manager)
                result = comfyui_client.run_custom_workflow(
                    workflow,
                    preferred_output_keys=definition.output_preferences
                )

                # Register asset
                asset_result = register_and_build_response(
                    result,
                    definition.workflow_id,
                    asset_registry,
                    tool_name=f"batch_styles[{preset_id}]",
                    return_inline_preview=False
                )

                results.append({
                    "index": i,
                    "preset_id": preset_id,
                    "preset_name": preset.get("name", preset_id),
                    "enhanced_prompt": styled["enhanced_prompt"],
                    "result": asset_result
                })

            except Exception as e:
                logger.error(f"Style '{preset_id}' failed: {e}")
                errors.append({
                    "index": i,
                    "preset_id": preset_id,
                    "error": str(e)
                })

        return {
            "original_prompt": prompt,
            "total_styles": len(style_preset_ids),
            "successful": len(results),
            "failed": len(errors),
            "results": results,
            "errors": errors if errors else None
        }

    @mcp.tool()
    def batch_generate_seeds(
        workflow_id: str,
        params: Dict[str, Any],
        count: int = 4,
        start_seed: Optional[int] = None
    ) -> dict:
        """Generate multiple variations of the same image using different seeds.

        Creates multiple versions of the same parameters with different random seeds,
        useful for finding the best variation of a prompt.

        Args:
            workflow_id: The workflow to use (e.g., "generate_image")
            params: Parameters for generation (prompt, width, height, etc.)
            count: Number of variations to generate (1-8, default: 4)
            start_seed: Starting seed (subsequent seeds will be random)

        Returns:
            dict: Results for each seed variation

        Example:
            batch_generate_seeds(
                workflow_id="generate_image",
                params={
                    "prompt": "a majestic dragon flying over mountains",
                    "width": 512,
                    "height": 512,
                    "steps": 20
                },
                count=4
            )
        """
        # Validate count
        count = max(1, min(8, count))

        # Find the workflow definition
        definition = None
        for defn in workflow_manager.tool_definitions:
            if defn.workflow_id == workflow_id or defn.tool_name == workflow_id:
                definition = defn
                break

        if not definition:
            available = [d.workflow_id for d in workflow_manager.tool_definitions]
            return {
                "error": f"Workflow '{workflow_id}' not found",
                "available_workflows": available
            }

        # Generate seeds
        if start_seed is not None:
            seeds = [start_seed + i for i in range(count)]
        else:
            seeds = [random.randint(0, 2**32 - 1) for _ in range(count)]

        results = []
        errors = []

        for i, seed in enumerate(seeds):
            try:
                # Build params with seed
                run_params = {**params, "seed": seed}

                # Render and run workflow
                workflow = workflow_manager.render_workflow(definition, run_params, defaults_manager)
                result = comfyui_client.run_custom_workflow(
                    workflow,
                    preferred_output_keys=definition.output_preferences
                )

                # Register asset
                asset_result = register_and_build_response(
                    result,
                    definition.workflow_id,
                    asset_registry,
                    tool_name=f"batch_seeds[{i}]",
                    return_inline_preview=False
                )

                results.append({
                    "index": i,
                    "seed": seed,
                    "result": asset_result
                })

            except Exception as e:
                logger.error(f"Seed {seed} failed: {e}")
                errors.append({
                    "index": i,
                    "seed": seed,
                    "error": str(e)
                })

        return {
            "workflow_id": workflow_id,
            "params": params,
            "seeds_used": seeds,
            "total_requested": count,
            "successful": len(results),
            "failed": len(errors),
            "results": results,
            "errors": errors if errors else None
        }

    logger.info("Registered batch generation tools")
