"""MCP server operators for Blender.

Exposes high-value ComfyUI MCP server tools as Blender operators:
- Health check / connection test
- Image generation (via MCP workflows — supports all server-side workflows)
- Image upscaling
- Image variations
- Style preset listing and application

All communication goes through the MCP streamable-http protocol (urllib only).
"""

import json
import os
import tempfile

import bpy
from bpy.types import Operator

from .comfyui_client import get_comfyui_client
from .mcp_client import MCPClientError, extract_text_content, get_mcp_client, reset_mcp_client


def _get_client(context):
    """Get MCP client configured from addon preferences."""
    prefs = context.preferences.addons[__package__].preferences
    return get_mcp_client(prefs.mcp_host, prefs.mcp_port)


# =============================================================================
# MCP CONNECTION CHECK
# =============================================================================

class COMFY_OT_mcp_connect(Operator):
    """Connect to MCP server and run health check"""
    bl_idname = "comfy.mcp_connect"
    bl_label = "Connect MCP"

    def execute(self, context):
        mcp_props = context.scene.comfy_mcp
        try:
            client = _get_client(context)
            ok, info = client.initialize()
            if not ok:
                mcp_props.mcp_connected = False
                self.report({"ERROR"}, f"MCP init failed: {info}")
                return {"FINISHED"}

            # Run health check for detailed status
            ok, result = client.call_tool("health_check", {}, timeout=15)
            if ok:
                mcp_props.mcp_connected = True
                data = extract_text_content(result)
                status = data.get("status", "unknown")
                models = data.get("models_available", 0)
                workflows = data.get("workflows_available", 0)
                self.report(
                    {"INFO"},
                    f"MCP connected — {status}, {models} models, {workflows} workflows",
                )
            else:
                mcp_props.mcp_connected = True  # Session works, tool failed
                self.report({"WARNING"}, "MCP connected but health_check failed")
        except MCPClientError as e:
            mcp_props.mcp_connected = False
            reset_mcp_client()
            self.report({"ERROR"}, f"MCP connection failed: {e}")
        return {"FINISHED"}


# =============================================================================
# MCP IMAGE GENERATION
# =============================================================================

class COMFY_OT_mcp_generate(Operator):
    """Generate image via MCP server (supports all server-side workflows)"""
    bl_idname = "comfy.mcp_generate"
    bl_label = "Generate via MCP"

    def execute(self, context):
        props = context.scene.comfy_mcp
        pipeline = context.scene.comfy_pipeline

        if not props.mcp_connected:
            self.report({"ERROR"}, "MCP server not connected. Click Connect first.")
            return {"CANCELLED"}

        prompt_text = pipeline.prompt.strip()
        if not prompt_text:
            self.report({"ERROR"}, "Enter a prompt first")
            return {"CANCELLED"}

        # Build arguments for the MCP generate_image tool
        args = {
            "prompt": prompt_text,
            "width": pipeline.capture_width,
            "height": pipeline.capture_height,
            "steps": pipeline.steps,
            "cfg": pipeline.cfg,
        }
        if pipeline.negative_prompt.strip():
            args["negative_prompt"] = pipeline.negative_prompt.strip()
        if pipeline.seed > 0:
            args["seed"] = pipeline.seed
        if pipeline.sampler != "euler":
            args["sampler_name"] = pipeline.sampler
        if pipeline.scheduler != "normal":
            args["scheduler"] = pipeline.scheduler

        # Use selected workflow or default to generate_image
        workflow_id = props.mcp_workflow if props.mcp_workflow else "generate_image"

        # For img2img mode, upload image first then use img2img workflow
        if pipeline.pipeline_mode == "IMG2IMG" and pipeline.input_image_path:
            prefs = context.preferences.addons[__package__].preferences
            comfy_client = get_comfyui_client(prefs.comfyui_url)
            ok, upload_data = comfy_client.upload_image(pipeline.input_image_path)
            if not ok:
                self.report({"ERROR"}, f"Image upload failed: {upload_data.get('error')}")
                return {"CANCELLED"}
            args["image_path"] = upload_data.get("name", "")
            args["denoise"] = pipeline.denoise
            workflow_id = "img2img"

        props.mcp_job_status = "Submitting..."
        props.mcp_last_asset_id = ""

        try:
            client = _get_client(context)
            # Generation can take a long time — use extended timeout
            ok, result = client.call_tool(workflow_id, args, timeout=600)
            if ok:
                data = extract_text_content(result)
                asset_id = data.get("asset_id", "")
                props.mcp_last_asset_id = asset_id
                props.mcp_job_status = "Complete"

                # Try to download the result image
                self._download_result(context, data)
                self.report({"INFO"}, f"Generated: {asset_id}")
            else:
                props.mcp_job_status = "Error"
                error_msg = result.get("message", str(result))
                self.report({"ERROR"}, f"Generation failed: {error_msg}")
        except MCPClientError as e:
            props.mcp_job_status = "Error"
            self.report({"ERROR"}, f"MCP error: {e}")

        return {"FINISHED"}

    def _download_result(self, context, data: dict):
        """Download generated image from ComfyUI and set as output."""
        filename = data.get("filename", "")
        subfolder = data.get("subfolder", "")
        if not filename:
            return

        prefs = context.preferences.addons[__package__].preferences
        comfy_client = get_comfyui_client(prefs.comfyui_url)

        output_dir = tempfile.mkdtemp(prefix="comfy_mcp_")
        output_path = os.path.join(output_dir, filename)
        ok, dl_data = comfy_client.download_image_to_file(
            filename, output_path, subfolder=subfolder, folder_type="output"
        )
        if ok and os.path.exists(output_path):
            context.scene.comfy_pipeline.output_image_path = output_path
            # Load into Blender
            try:
                img = bpy.data.images.load(output_path)
                img.name = f"MCP_{filename}"
            except Exception:
                pass


# =============================================================================
# MCP UPSCALE
# =============================================================================

class COMFY_OT_mcp_upscale(Operator):
    """Upscale last generated image via MCP server"""
    bl_idname = "comfy.mcp_upscale"
    bl_label = "Upscale"

    def execute(self, context):
        props = context.scene.comfy_mcp
        if not props.mcp_connected:
            self.report({"ERROR"}, "MCP server not connected")
            return {"CANCELLED"}

        if not props.mcp_last_asset_id:
            self.report({"ERROR"}, "No asset to upscale. Generate an image first.")
            return {"CANCELLED"}

        args = {
            "asset_id": props.mcp_last_asset_id,
            "scale_factor": props.upscale_factor,
        }

        props.mcp_job_status = "Upscaling..."
        try:
            client = _get_client(context)
            ok, result = client.call_tool("upscale_image", args, timeout=300)
            if ok:
                data = extract_text_content(result)
                new_asset_id = data.get("asset_id", "")
                if new_asset_id:
                    props.mcp_last_asset_id = new_asset_id
                props.mcp_job_status = "Upscaled"

                # Download upscaled result
                COMFY_OT_mcp_generate._download_result(None, context, data)
                self.report({"INFO"}, f"Upscaled to {props.upscale_factor}x: {new_asset_id}")
            else:
                props.mcp_job_status = "Error"
                self.report({"ERROR"}, f"Upscale failed: {result.get('message', str(result))}")
        except MCPClientError as e:
            props.mcp_job_status = "Error"
            self.report({"ERROR"}, f"MCP error: {e}")
        return {"FINISHED"}


# =============================================================================
# MCP VARIATIONS
# =============================================================================

class COMFY_OT_mcp_variations(Operator):
    """Generate variations of last image via MCP server"""
    bl_idname = "comfy.mcp_variations"
    bl_label = "Variations"

    def execute(self, context):
        props = context.scene.comfy_mcp
        if not props.mcp_connected:
            self.report({"ERROR"}, "MCP server not connected")
            return {"CANCELLED"}

        if not props.mcp_last_asset_id:
            self.report({"ERROR"}, "No asset for variations. Generate an image first.")
            return {"CANCELLED"}

        args = {
            "asset_id": props.mcp_last_asset_id,
            "num_variations": props.variation_count,
            "variation_strength": props.variation_strength,
        }

        props.mcp_job_status = "Generating variations..."
        try:
            client = _get_client(context)
            ok, result = client.call_tool("generate_variations", args, timeout=600)
            if ok:
                data = extract_text_content(result)
                variations = data.get("variations", [])
                count = len(variations)
                # Store first variation as current asset
                if variations:
                    first = variations[0]
                    first_id = first.get("asset_id", "")
                    if first_id:
                        props.mcp_last_asset_id = first_id
                    COMFY_OT_mcp_generate._download_result(None, context, first)

                props.mcp_job_status = f"{count} variations"
                self.report({"INFO"}, f"Generated {count} variations")
            else:
                props.mcp_job_status = "Error"
                self.report({"ERROR"}, f"Variations failed: {result.get('message', str(result))}")
        except MCPClientError as e:
            props.mcp_job_status = "Error"
            self.report({"ERROR"}, f"MCP error: {e}")
        return {"FINISHED"}


# =============================================================================
# MCP STYLE PRESETS
# =============================================================================

class COMFY_OT_mcp_list_styles(Operator):
    """Fetch available style presets from MCP server"""
    bl_idname = "comfy.mcp_list_styles"
    bl_label = "Refresh Styles"

    def execute(self, context):
        props = context.scene.comfy_mcp
        if not props.mcp_connected:
            self.report({"ERROR"}, "MCP server not connected")
            return {"CANCELLED"}

        try:
            client = _get_client(context)
            ok, result = client.call_tool("list_style_presets", {}, timeout=15)
            if ok:
                data = extract_text_content(result)
                presets = data.get("presets", [])
                # Store as JSON string for the enum callback
                names = [p.get("name", p.get("id", "?")) for p in presets]
                props.available_styles = json.dumps(
                    [{"id": p.get("id", ""), "name": p.get("name", "")} for p in presets]
                )
                self.report({"INFO"}, f"Loaded {len(names)} style presets")
            else:
                self.report({"WARNING"}, "Could not load style presets")
        except MCPClientError as e:
            self.report({"ERROR"}, f"MCP error: {e}")
        return {"FINISHED"}


class COMFY_OT_mcp_apply_style(Operator):
    """Apply selected style preset to the prompt"""
    bl_idname = "comfy.mcp_apply_style"
    bl_label = "Apply Style"

    def execute(self, context):
        props = context.scene.comfy_mcp
        pipeline = context.scene.comfy_pipeline

        if not props.mcp_connected:
            self.report({"ERROR"}, "MCP server not connected")
            return {"CANCELLED"}

        style_id = props.selected_style
        if not style_id:
            self.report({"ERROR"}, "No style selected")
            return {"CANCELLED"}

        prompt_text = pipeline.prompt.strip()
        if not prompt_text:
            self.report({"ERROR"}, "Enter a prompt first")
            return {"CANCELLED"}

        args = {"preset_id": style_id, "prompt": prompt_text}

        try:
            client = _get_client(context)
            ok, result = client.call_tool("apply_style_preset", args, timeout=15)
            if ok:
                data = extract_text_content(result)
                styled = data.get("styled_prompt", "")
                styled_neg = data.get("styled_negative_prompt", "")
                if styled:
                    pipeline.prompt = styled
                if styled_neg:
                    pipeline.negative_prompt = styled_neg
                self.report({"INFO"}, f"Applied style: {style_id}")
            else:
                self.report({"ERROR"}, f"Style apply failed: {result.get('message', str(result))}")
        except MCPClientError as e:
            self.report({"ERROR"}, f"MCP error: {e}")
        return {"FINISHED"}


# =============================================================================
# MCP LIST MODELS
# =============================================================================

class COMFY_OT_mcp_list_models(Operator):
    """Fetch available models from MCP server"""
    bl_idname = "comfy.mcp_list_models"
    bl_label = "Refresh Models"

    def execute(self, context):
        props = context.scene.comfy_mcp
        if not props.mcp_connected:
            self.report({"ERROR"}, "MCP server not connected")
            return {"CANCELLED"}

        try:
            client = _get_client(context)
            ok, result = client.call_tool("list_models", {}, timeout=15)
            if ok:
                data = extract_text_content(result)
                models = data.get("models", data.get("checkpoints", []))
                if isinstance(models, list):
                    props.available_models = json.dumps(models)
                    self.report({"INFO"}, f"Found {len(models)} models")
                else:
                    self.report({"WARNING"}, "Unexpected model list format")
            else:
                self.report({"WARNING"}, "Could not list models")
        except MCPClientError as e:
            self.report({"ERROR"}, f"MCP error: {e}")
        return {"FINISHED"}


# =============================================================================
# MCP LIST WORKFLOWS
# =============================================================================

class COMFY_OT_mcp_list_workflows(Operator):
    """Fetch available workflows from MCP server"""
    bl_idname = "comfy.mcp_list_workflows"
    bl_label = "Refresh Workflows"

    def execute(self, context):
        props = context.scene.comfy_mcp
        if not props.mcp_connected:
            self.report({"ERROR"}, "MCP server not connected")
            return {"CANCELLED"}

        try:
            client = _get_client(context)
            ok, result = client.call_tool("list_workflows", {}, timeout=15)
            if ok:
                data = extract_text_content(result)
                workflows = data.get("workflows", [])
                if isinstance(workflows, list):
                    props.available_workflows = json.dumps(
                        [{"id": w.get("id", ""), "name": w.get("name", "")} for w in workflows]
                    )
                    self.report({"INFO"}, f"Found {len(workflows)} workflows")
                else:
                    self.report({"WARNING"}, "Unexpected workflow list format")
            else:
                self.report({"WARNING"}, "Could not list workflows")
        except MCPClientError as e:
            self.report({"ERROR"}, f"MCP error: {e}")
        return {"FINISHED"}
