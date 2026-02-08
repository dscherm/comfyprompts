"""Configuration tools for ComfyUI MCP Server"""

import logging
from typing import Any, Dict, List, Optional

from mcp.server.fastmcp import FastMCP

logger = logging.getLogger("MCP_Server")


def register_configuration_tools(
    mcp: FastMCP,
    comfyui_client,
    defaults_manager,
    workflow_manager=None
):
    """Register configuration tools with the MCP server"""

    @mcp.tool()
    def health_check() -> dict:
        """Check the health of the ComfyUI MCP Server and its dependencies.

        Returns connection status, VRAM info, available models, and workflow status.
        Use this to diagnose issues before running generation tools.
        """
        result = {
            "status": "healthy",
            "issues": [],
            "comfyui": {},
            "workflows": {},
            "models": {}
        }

        # Check ComfyUI connection
        conn_status = comfyui_client.check_connection()
        result["comfyui"]["connected"] = conn_status.get("connected", False)

        if not conn_status.get("connected"):
            result["status"] = "unhealthy"
            result["issues"].append(f"ComfyUI not reachable: {conn_status.get('error', 'Unknown error')}")
        else:
            # Get VRAM info if available
            vram_total = conn_status.get("vram_total")
            vram_free = conn_status.get("vram_free")
            if vram_total and vram_free:
                result["comfyui"]["vram_total_gb"] = round(vram_total / (1024**3), 2)
                result["comfyui"]["vram_free_gb"] = round(vram_free / (1024**3), 2)
                result["comfyui"]["vram_used_pct"] = round((1 - vram_free/vram_total) * 100, 1)

                # Warn if low VRAM
                if vram_free < 2 * (1024**3):  # Less than 2GB free
                    result["issues"].append("Low VRAM: Less than 2GB free. Large models may fail.")

        # Check available models
        models = comfyui_client.available_models or []
        result["models"]["count"] = len(models)
        result["models"]["available"] = models[:10]  # First 10

        if not models:
            result["issues"].append("No checkpoint models found in ComfyUI")

        # Check workflows
        if workflow_manager:
            workflow_count = len(workflow_manager.tool_definitions)
            result["workflows"]["count"] = workflow_count
            result["workflows"]["available"] = [d.tool_name for d in workflow_manager.tool_definitions]

            if workflow_count == 0:
                result["issues"].append("No workflows found. Add JSON files with PARAM_* placeholders to workflows/")

        # Set overall status
        if result["issues"]:
            if not conn_status.get("connected"):
                result["status"] = "unhealthy"
            else:
                result["status"] = "degraded"

        return result

    @mcp.tool()
    def list_models() -> dict:
        """List all available checkpoint models in ComfyUI.
        
        Returns a list of model names that can be used with generation tools.
        This helps AI agents choose appropriate models for different use cases.
        """
        models = comfyui_client.available_models
        return {
            "models": models,
            "count": len(models),
            "default": "v1-5-pruned-emaonly.ckpt" if models else None
        }

    @mcp.tool()
    def get_defaults() -> dict:
        """Get current effective defaults for image, audio, and video generation.
        
        Returns merged defaults from all sources (runtime, config, env, hardcoded).
        Shows what values will be used when parameters are not explicitly provided.
        """
        return defaults_manager.get_all_defaults()

    @mcp.tool()
    def set_defaults(
        image: Optional[Dict[str, Any]] = None,
        audio: Optional[Dict[str, Any]] = None,
        video: Optional[Dict[str, Any]] = None,
        persist: bool = False
    ) -> dict:
        """Set runtime defaults for image, audio, and/or video generation.
        
        Args:
            image: Optional dict of default values for image generation (e.g., {"model": "sd_xl_base_1.0.safetensors", "width": 1024})
            audio: Optional dict of default values for audio generation (e.g., {"model": "ace_step_v1_3.5b.safetensors", "seconds": 30})
            video: Optional dict of default values for video generation (e.g., {"model": "wan2.2_vae.safetensors", "width": 1280, "duration": 5})
            persist: If True, write defaults to config file (~/.config/comfy-mcp/config.json). Otherwise, changes are ephemeral.
        
        Returns:
            Success status and any validation errors (e.g., invalid model names).
        """
        results = {}
        errors = []
        
        if image:
            result = defaults_manager.set_defaults("image", image, validate_models=True)
            if "error" in result or "errors" in result:
                errors.extend(result.get("errors", [result.get("error")]))
            else:
                results["image"] = result
                if persist:
                    persist_result = defaults_manager.persist_defaults("image", image)
                    if "error" in persist_result:
                        errors.append(f"Failed to persist image defaults: {persist_result['error']}")
        
        if audio:
            result = defaults_manager.set_defaults("audio", audio, validate_models=True)
            if "error" in result or "errors" in result:
                errors.extend(result.get("errors", [result.get("error")]))
            else:
                results["audio"] = result
                if persist:
                    persist_result = defaults_manager.persist_defaults("audio", audio)
                    if "error" in persist_result:
                        errors.append(f"Failed to persist audio defaults: {persist_result['error']}")
        
        if video:
            result = defaults_manager.set_defaults("video", video, validate_models=True)
            if "error" in result or "errors" in result:
                errors.extend(result.get("errors", [result.get("error")]))
            else:
                results["video"] = result
                if persist:
                    persist_result = defaults_manager.persist_defaults("video", video)
                    if "error" in persist_result:
                        errors.append(f"Failed to persist video defaults: {persist_result['error']}")
        
        if errors:
            return {"success": False, "errors": errors}
        
        return {"success": True, "updated": results}
