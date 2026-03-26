"""UI panels for ComfyUI MCP Blender addon."""

import json
import os

import bpy
from bpy.types import Panel


class COMFY_PT_main_panel(Panel):
    bl_label = "ComfyUI MCP"
    bl_idname = "COMFY_PT_main"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "ComfyUI"

    def draw(self, context):
        layout = self.layout
        obj = context.active_object
        if obj:
            layout.label(text=f"Selected: {obj.name} ({obj.type})")
        else:
            layout.label(text="No object selected")


class COMFY_PT_pipeline_panel(Panel):
    bl_label = "AI Pipeline"
    bl_idname = "COMFY_PT_pipeline"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "ComfyUI"

    def draw(self, context):
        layout = self.layout
        props = context.scene.comfy_pipeline

        # --- Connection ---
        row = layout.row(align=True)
        if props.comfyui_connected:
            row.label(text="ComfyUI: Connected", icon='CHECKMARK')
        else:
            row.label(text="ComfyUI: Not connected", icon='ERROR')
        row.operator("comfy.check_comfyui", text="", icon='FILE_REFRESH')

        layout.separator()

        # --- Mode ---
        layout.prop(props, "pipeline_mode", expand=True)

        layout.separator()

        # --- Input (IMG2IMG only) ---
        if props.pipeline_mode == "IMG2IMG":
            box = layout.box()
            box.label(text="Input Image:", icon='IMAGE_DATA')
            row = box.row(align=True)
            row.operator("comfy.capture_viewport_mcp", text="Capture Viewport", icon='RESTRICT_VIEW_OFF')
            row.operator("comfy.use_render_result_mcp", text="Use Render", icon='RENDER_STILL')

            if props.input_image_path:
                box.label(text=os.path.basename(props.input_image_path), icon='FILE_IMAGE')

            box.prop(props, "denoise", slider=True)

            layout.separator()

        # --- Prompt ---
        layout.prop(props, "prompt", text="", icon='TEXT')
        layout.prop(props, "negative_prompt", text="", icon='CANCEL')

        # --- Generation settings ---
        col = layout.column(align=True)
        col.prop(props, "checkpoint")
        row = col.row(align=True)
        row.prop(props, "steps")
        row.prop(props, "cfg")
        row = col.row(align=True)
        row.prop(props, "sampler")
        row.prop(props, "scheduler")
        row = col.row(align=True)
        row.prop(props, "capture_width", text="W")
        row.prop(props, "capture_height", text="H")
        col.prop(props, "seed")

        layout.separator()

        # --- Generate / Cancel ---
        is_running = props.job_status in ("Queued", "Pending", "Running")
        if is_running:
            row = layout.row()
            row.scale_y = 1.5
            row.operator("comfy.cancel_pipeline", icon='CANCEL')
            layout.label(text=f"Status: {props.job_status}", icon='SORTTIME')
            layout.label(text=props.job_progress)
        else:
            row = layout.row()
            row.scale_y = 1.5
            row.operator("comfy.run_pipeline", icon='PLAY')

        # --- Output ---
        if props.output_image_path and os.path.exists(props.output_image_path):
            layout.separator()
            box = layout.box()
            box.label(text="Output:", icon='RENDER_RESULT')
            box.label(text=os.path.basename(props.output_image_path), icon='FILE_IMAGE')
            row = box.row(align=True)
            row.operator("comfy.apply_as_texture", text="Apply as Texture", icon='MATERIAL')
            row.operator("comfy.open_output", text="", icon='FILE_FOLDER')


class COMFY_PT_mcp_tools_panel(Panel):
    bl_label = "MCP Server Tools"
    bl_idname = "COMFY_PT_mcp_tools"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "ComfyUI"

    def draw(self, context):
        layout = self.layout
        props = context.scene.comfy_mcp
        pipeline = context.scene.comfy_pipeline

        # --- MCP Connection ---
        row = layout.row(align=True)
        if props.mcp_connected:
            row.label(text="MCP Server: Connected", icon='CHECKMARK')
        else:
            row.label(text="MCP Server: Not connected", icon='ERROR')
        row.operator("comfy.mcp_connect", text="", icon='FILE_REFRESH')

        if not props.mcp_connected:
            layout.label(text="Connect to MCP server to use these tools", icon='INFO')
            return

        layout.separator()

        # --- Workflow selection ---
        box = layout.box()
        box.label(text="MCP Generation:", icon='RENDER_RESULT')
        row = box.row(align=True)
        row.prop(props, "mcp_workflow", text="Workflow")
        row.operator("comfy.mcp_list_workflows", text="", icon='FILE_REFRESH')
        # Show available workflows if loaded
        try:
            workflows = json.loads(props.available_workflows)
            if workflows:
                box.label(text=f"{len(workflows)} workflows available", icon='COLLAPSEMENU')
        except (json.JSONDecodeError, TypeError):
            pass

        row = box.row()
        row.scale_y = 1.3
        row.operator("comfy.mcp_generate", icon='PLAY')
        row.enabled = bool(pipeline.prompt.strip())

        # --- Status ---
        if props.mcp_job_status != "Idle":
            box.label(text=f"Status: {props.mcp_job_status}", icon='SORTTIME')

        # --- Asset ID ---
        if props.mcp_last_asset_id:
            box.label(text=f"Asset: {props.mcp_last_asset_id[:20]}...", icon='FILE_IMAGE')

        layout.separator()

        # --- Post-processing tools ---
        has_asset = bool(props.mcp_last_asset_id)

        # Upscale
        box = layout.box()
        box.label(text="Upscale:", icon='FULLSCREEN_ENTER')
        row = box.row(align=True)
        row.prop(props, "upscale_factor", text="Factor")
        row.operator("comfy.mcp_upscale", text="Upscale", icon='FULLSCREEN_ENTER')
        row.enabled = has_asset

        # Variations
        box = layout.box()
        box.label(text="Variations:", icon='MOD_ARRAY')
        col = box.column(align=True)
        col.prop(props, "variation_count")
        col.prop(props, "variation_strength", slider=True)
        row = box.row()
        row.operator("comfy.mcp_variations", text="Generate Variations", icon='MOD_ARRAY')
        row.enabled = has_asset

        layout.separator()

        # --- Style presets ---
        box = layout.box()
        box.label(text="Style Presets:", icon='BRUSHES_ALL')
        row = box.row(align=True)
        row.prop(props, "selected_style", text="Style")
        row.operator("comfy.mcp_list_styles", text="", icon='FILE_REFRESH')
        # Show count
        try:
            styles = json.loads(props.available_styles)
            if styles:
                box.label(text=f"{len(styles)} styles available", icon='COLLAPSEMENU')
        except (json.JSONDecodeError, TypeError):
            pass
        row = box.row()
        row.operator("comfy.mcp_apply_style", icon='BRUSHES_ALL')
        row.enabled = bool(props.selected_style and pipeline.prompt.strip())

        layout.separator()

        # --- Models ---
        row = layout.row(align=True)
        row.operator("comfy.mcp_list_models", icon='OUTLINER_OB_MESH')
        try:
            models = json.loads(props.available_models)
            if models:
                row.label(text=f"{len(models)} models")
        except (json.JSONDecodeError, TypeError):
            pass


class COMFY_PT_rigging_panel(Panel):
    bl_label = "Auto-Rigging"
    bl_idname = "COMFY_PT_rigging"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "ComfyUI"
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        layout = self.layout
        props = context.scene.comfy_rigging
        layout.prop(props, "rig_backend")
        layout.prop(props, "rig_type")
        col = layout.column(align=True)
        col.prop(props, "auto_weights")
        col.prop(props, "generate_ik")
        layout.separator()
        row = layout.row()
        row.scale_y = 1.5
        row.operator("comfy.auto_rig", icon='ARMATURE_DATA')


class COMFY_PT_animation_panel(Panel):
    bl_label = "Animation"
    bl_idname = "COMFY_PT_animation"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "ComfyUI"
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        layout = self.layout
        props = context.scene.comfy_animation
        layout.prop(props, "animation_type")
        col = layout.column(align=True)
        col.prop(props, "duration")
        col.prop(props, "fps")
        col.prop(props, "intensity")
        col.prop(props, "loop")
        layout.separator()
        row = layout.row()
        row.scale_y = 1.5
        row.operator("comfy.generate_animation", icon='ANIM')


class COMFY_PT_mocap_panel(Panel):
    bl_label = "Mocap Import"
    bl_idname = "COMFY_PT_mocap"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "ComfyUI"
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        layout = self.layout
        props = context.scene.comfy_mocap
        layout.prop(props, "mocap_file")
        col = layout.column(align=True)
        col.prop(props, "scale")
        col.prop(props, "start_frame")
        col.prop(props, "use_fps_scale")
        layout.separator()
        row = layout.row()
        row.scale_y = 1.5
        row.operator("comfy.import_mocap", icon='IMPORT')


class COMFY_PT_export_panel(Panel):
    bl_label = "Export"
    bl_idname = "COMFY_PT_export"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "ComfyUI"
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        layout = self.layout
        props = context.scene.comfy_export
        layout.prop(props, "export_format")
        layout.prop(props, "include_animation")
        layout.separator()
        row = layout.row()
        row.scale_y = 1.5
        row.operator("comfy.export_model", icon='EXPORT')
