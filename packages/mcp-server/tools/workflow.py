"""Workflow management tools for ComfyUI MCP Server"""

import json
import logging
from pathlib import Path
from typing import Any, Dict, Optional

import requests
from mcp.server.fastmcp import FastMCP
from tools.helpers import register_and_build_response

logger = logging.getLogger("MCP_Server")


def register_workflow_tools(
    mcp: FastMCP,
    workflow_manager,
    comfyui_client,
    defaults_manager,
    asset_registry
):
    """Register workflow tools with the MCP server"""

    @mcp.tool()
    def list_workflows() -> dict:
        """List all available workflows in the workflow directory.
        
        Returns a catalog of workflows with their IDs, names, descriptions,
        available inputs, and optional metadata.
        """
        catalog = workflow_manager.get_workflow_catalog()
        return {
            "workflows": catalog,
            "count": len(catalog),
            "workflow_dir": str(workflow_manager.workflows_dir)
        }

    @mcp.tool()
    def run_workflow(
        workflow_id: str,
        overrides: Optional[Dict[str, Any]] = None,
        options: Optional[Dict[str, Any]] = None,
        return_inline_preview: bool = False
    ) -> dict:
        """Run a saved ComfyUI workflow with constrained parameter overrides.
        
        Args:
            workflow_id: The workflow ID (filename stem, e.g., "generate_image")
            overrides: Optional dict of parameter overrides (e.g., {"prompt": "a cat", "width": 1024})
            options: Optional dict of execution options (reserved for future use)
            return_inline_preview: If True, include a small thumbnail base64 in response (256px, ~100KB)
        
        Returns:
            Result with asset_url, workflow_id, and execution metadata. If return_inline_preview=True,
            also includes inline_preview_base64 for immediate viewing.
        """
        if overrides is None:
            overrides = {}
        
        # Load workflow
        workflow = workflow_manager.load_workflow(workflow_id)
        if not workflow:
            return {"error": f"Workflow '{workflow_id}' not found"}
        
        try:
            # Apply overrides with constraints
            workflow = workflow_manager.apply_workflow_overrides(
                workflow, workflow_id, overrides, defaults_manager
            )
            
            # Determine output preferences
            output_preferences = workflow_manager._guess_output_preferences(workflow)
            
            # Execute workflow
            result = comfyui_client.run_custom_workflow(
                workflow,
                preferred_output_keys=output_preferences,
            )
            
            # Register asset and build response
            return register_and_build_response(
                result,
                workflow_id,
                asset_registry,
                tool_name=None,
                return_inline_preview=return_inline_preview,
                session_id=None  # Session tracking can be added via request context in the future
            )
        except Exception as exc:
            logger.exception("Workflow '%s' failed", workflow_id)
            return {"error": str(exc)}

    @mcp.tool()
    def validate_workflow(workflow_id: str) -> dict:
        """Check if a workflow can run on the current ComfyUI setup.

        Reads the workflow's meta.json to determine required nodes, models,
        and VRAM, then checks each requirement against the running ComfyUI
        instance.

        Args:
            workflow_id: The workflow ID (e.g., "generate_image", "generate_video")

        Returns:
            Dict with:
            - workflow_id: The checked workflow
            - ready: True if all requirements are met
            - missing_nodes: List of required but missing custom nodes
            - missing_models: Dict of model type -> missing model name
            - vram_ok: Whether VRAM meets the minimum requirement (or None if unknown)
            - vram_required_gb: Minimum VRAM from metadata (if specified)
            - vram_free_gb: Current free VRAM (if available)
            - warnings: Any non-blocking issues
        """
        result = {
            "workflow_id": workflow_id,
            "ready": True,
            "missing_nodes": [],
            "missing_models": {},
            "vram_ok": None,
            "vram_required_gb": None,
            "vram_free_gb": None,
            "warnings": [],
        }

        # Load metadata
        workflow_path = workflow_manager._safe_workflow_path(workflow_id)
        if not workflow_path:
            return {"error": f"Workflow '{workflow_id}' not found"}

        metadata = workflow_manager._load_workflow_metadata(workflow_path)
        if not metadata:
            result["warnings"].append("No meta.json found; cannot validate requirements")
            return result

        requirements = metadata.get("requirements", {})
        if not requirements:
            result["warnings"].append("meta.json has no requirements section")
            return result

        # Check required nodes
        required_nodes = requirements.get("nodes", [])
        if required_nodes:
            try:
                resp = requests.get(
                    f"{comfyui_client.base_url}/object_info", timeout=30
                )
                if resp.status_code == 200:
                    available_nodes = set(resp.json().keys())
                    for node in required_nodes:
                        if node not in available_nodes:
                            result["missing_nodes"].append(node)
                            result["ready"] = False
                else:
                    result["warnings"].append(
                        "Could not fetch /object_info to check nodes"
                    )
            except requests.RequestException as e:
                result["warnings"].append(f"Node check failed: {e}")

        # Check required models
        required_models = requirements.get("models", {})
        if required_models:
            # Checkpoint models
            checkpoint = required_models.get("checkpoint")
            if checkpoint:
                available = comfyui_client.available_models or []
                if checkpoint not in available:
                    result["missing_models"]["checkpoint"] = checkpoint
                    result["ready"] = False

            # Other model types that can be queried generically
            model_checks = {
                "lora": ("LoraLoader", "lora_name"),
                "controlnet": ("ControlNetLoader", "control_net_name"),
                "vae": ("VAELoader", "vae_name"),
                "upscale": ("UpscaleModelLoader", "model_name"),
            }
            for model_type, (node_class, param_name) in model_checks.items():
                model_name = required_models.get(model_type)
                if model_name:
                    try:
                        resp = requests.get(
                            f"{comfyui_client.base_url}/object_info/{node_class}",
                            timeout=10,
                        )
                        if resp.status_code == 200:
                            info = (
                                resp.json()
                                .get(node_class, {})
                                .get("input", {})
                                .get("required", {})
                                .get(param_name, [])
                            )
                            model_list = info[0] if isinstance(info, list) and info and isinstance(info[0], list) else (info if isinstance(info, list) else [])
                            if model_name not in model_list:
                                result["missing_models"][model_type] = model_name
                                result["ready"] = False
                    except Exception:
                        result["warnings"].append(
                            f"Could not verify {model_type} model '{model_name}'"
                        )

        # Check VRAM
        min_vram_gb = requirements.get("minimum_vram_gb")
        if min_vram_gb is not None:
            result["vram_required_gb"] = min_vram_gb
            conn = comfyui_client.check_connection()
            if conn.get("connected"):
                vram_free = conn.get("vram_free")
                if vram_free is not None:
                    free_gb = round(vram_free / (1024 ** 3), 2)
                    result["vram_free_gb"] = free_gb
                    result["vram_ok"] = free_gb >= min_vram_gb
                    if not result["vram_ok"]:
                        result["ready"] = False
                        result["warnings"].append(
                            f"Insufficient VRAM: {free_gb} GB free, "
                            f"{min_vram_gb} GB required"
                        )

        # Add custom node install hints
        custom_nodes = requirements.get("custom_nodes", {})
        for node_name in result["missing_nodes"]:
            install_info = custom_nodes.get(node_name, {})
            if isinstance(install_info, dict) and install_info.get("install"):
                result["warnings"].append(
                    f"Install '{install_info['install']}' for node {node_name}"
                )

        return result
