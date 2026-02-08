"""UI panels for ComfyUI Blender addon.

All panels live under a single "ComfyUI" sidebar tab, organized by pipeline stage:
Connection -> Generate (Input/Workflow/Action/Output) -> Rig -> Animate -> Mocap -> Export
"""

import bpy
from bpy.types import Panel


# =============================================================================
# MAIN PANEL
# =============================================================================

class COMFYUI_PT_main_panel(Panel):
    bl_label = "ComfyUI Tools"
    bl_idname = "COMFYUI_PT_main"
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


# =============================================================================
# CONNECTION PANEL
# =============================================================================

class COMFYUI_PT_connection_panel(Panel):
    bl_label = "Connection"
    bl_idname = "COMFYUI_PT_connection"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "ComfyUI"
    bl_parent_id = "COMFYUI_PT_main"
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        layout = self.layout
        props = context.scene.comfyui_gen
        from .preferences import get_preferences
        prefs = get_preferences()

        # Prompter API status
        box = layout.box()
        box.label(text="Prompter API (Generation)", icon='URL')
        row = box.row()
        api_icon = 'CHECKMARK' if props.api_connected else 'X'
        comfy_icon = 'CHECKMARK' if props.comfyui_connected else 'X'
        row.label(text=f"API: {'OK' if props.api_connected else 'No'}", icon=api_icon)
        row.label(text=f"ComfyUI: {'OK' if props.comfyui_connected else 'No'}", icon=comfy_icon)
        if prefs:
            box.label(text=prefs.api_url, icon='BLANK1')

        # MCP Server status
        box = layout.box()
        box.label(text="MCP Server (Rigging)", icon='LINKED')
        if prefs:
            box.label(text=f"{prefs.mcp_host}:{prefs.mcp_port}", icon='BLANK1')

        layout.operator("comfyui.check_connection", icon='FILE_REFRESH')

        # Queue management
        layout.separator()
        layout.label(text="Queue Management:")
        row = layout.row(align=True)
        row.operator("comfyui.interrupt", text="Interrupt", icon='CANCEL')
        row.operator("comfyui.clear_queue", text="Clear Queue", icon='TRASH')


# =============================================================================
# GENERATION PANELS
# =============================================================================

class COMFYUI_PT_generate_input_panel(Panel):
    bl_label = "Generate - Input"
    bl_idname = "COMFYUI_PT_gen_input"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "ComfyUI"
    bl_parent_id = "COMFYUI_PT_main"

    def draw(self, context):
        layout = self.layout
        props = context.scene.comfyui_gen

        layout.prop(props, "input_mode", text="Mode")

        if props.input_mode == 'VIEWPORT':
            layout.operator("comfyui.capture_viewport", icon='RESTRICT_VIEW_OFF')
            if props.image_path:
                layout.label(text=f"Captured: {_filename(props.image_path)}")

        elif props.input_mode == 'RENDER':
            layout.operator("comfyui.use_render_result", icon='RENDER_RESULT')
            if props.image_path:
                layout.label(text=f"Using: {_filename(props.image_path)}")

        elif props.input_mode == 'FILE':
            layout.prop(props, "image_path", text="")

        elif props.input_mode == 'TEXT':
            layout.prop(props, "text_prompt", text="")
            row = layout.row(align=True)
            row.operator("comfyui.analyze_prompt", text="Analyze", icon='INFO')

            if props.ai_reasoning:
                box = layout.box()
                box.label(text="AI Suggestion:", icon='LIGHT')
                for line in _wrap_text(props.ai_reasoning, 35):
                    box.label(text=line)
                if props.recommended_workflow and props.recommended_workflow != props.workflow:
                    box.operator("comfyui.use_recommended", text="Use Recommended", icon='FORWARD')


class COMFYUI_PT_generate_workflow_panel(Panel):
    bl_label = "Generate - Workflow"
    bl_idname = "COMFYUI_PT_gen_workflow"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "ComfyUI"
    bl_parent_id = "COMFYUI_PT_main"

    def draw(self, context):
        layout = self.layout
        props = context.scene.comfyui_gen

        row = layout.row(align=True)
        row.prop(props, "workflow", text="")
        row.operator("comfyui.refresh_workflows", text="", icon='FILE_REFRESH')

        if props.workflows_loaded:
            layout.label(text="Workflows loaded from server", icon='CHECKMARK')
        else:
            layout.label(text="Using default workflows", icon='INFO')

        layout.prop(props, "auto_import")


class COMFYUI_PT_generate_action_panel(Panel):
    bl_label = "Generate - Run"
    bl_idname = "COMFYUI_PT_gen_action"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "ComfyUI"
    bl_parent_id = "COMFYUI_PT_main"

    def draw(self, context):
        layout = self.layout
        props = context.scene.comfyui_gen

        row = layout.row(align=True)
        row.scale_y = 1.5

        is_running = props.job_status in ["Queued", "Pending...", "Monitoring..."] or \
                     props.job_status.startswith("Running")

        if is_running:
            row.operator("comfyui.cancel_job", text="Cancel", icon='CANCEL')
        else:
            btn_text = "Generate 3D from Text" if props.input_mode == 'TEXT' else "Generate 3D"
            row.operator("comfyui.generate", text=btn_text, icon='MESH_MONKEY')

        if props.job_id:
            box = layout.box()
            box.label(text=f"Job: {props.job_id[:8]}...")
            box.label(text=f"Status: {props.job_status}")
            if props.job_progress > 0:
                box.prop(props, "job_progress", text="Progress", slider=True)


class COMFYUI_PT_generate_output_panel(Panel):
    bl_label = "Generate - Output"
    bl_idname = "COMFYUI_PT_gen_output"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "ComfyUI"
    bl_parent_id = "COMFYUI_PT_main"

    def draw(self, context):
        layout = self.layout
        props = context.scene.comfyui_gen

        if props.output_path:
            layout.label(text="Output:", icon='CHECKMARK')
            box = layout.box()
            box.label(text=_filename(props.output_path))
            row = layout.row(align=True)
            row.operator("comfyui.import_result", text="Import", icon='IMPORT')
            row.operator("comfyui.open_output_folder", text="", icon='FILE_FOLDER')
        else:
            layout.label(text="No output yet", icon='INFO')
            layout.operator("comfyui.open_output_folder", text="Open Output Folder", icon='FILE_FOLDER')


# =============================================================================
# RIGGING PANEL
# =============================================================================

class COMFYUI_PT_rigging_panel(Panel):
    bl_label = "Auto-Rigging"
    bl_idname = "COMFYUI_PT_rigging"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "ComfyUI"
    bl_parent_id = "COMFYUI_PT_main"
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        layout = self.layout
        props = context.scene.comfyui_rig

        layout.prop(props, "rig_backend")
        layout.prop(props, "rig_type")

        col = layout.column(align=True)
        col.prop(props, "auto_weights")
        col.prop(props, "generate_ik")

        layout.separator()
        row = layout.row()
        row.scale_y = 1.5
        row.operator("comfyui.auto_rig", icon='ARMATURE_DATA')


# =============================================================================
# ANIMATION PANEL
# =============================================================================

class COMFYUI_PT_animation_panel(Panel):
    bl_label = "Animation"
    bl_idname = "COMFYUI_PT_animation"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "ComfyUI"
    bl_parent_id = "COMFYUI_PT_main"
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        layout = self.layout
        props = context.scene.comfyui_anim

        layout.prop(props, "animation_type")

        col = layout.column(align=True)
        col.prop(props, "duration")
        col.prop(props, "fps")
        col.prop(props, "intensity")
        col.prop(props, "loop")

        layout.separator()
        row = layout.row()
        row.scale_y = 1.5
        row.operator("comfyui.generate_animation", icon='ANIM')


# =============================================================================
# MOCAP PANEL
# =============================================================================

class COMFYUI_PT_mocap_panel(Panel):
    bl_label = "Mocap Import"
    bl_idname = "COMFYUI_PT_mocap"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "ComfyUI"
    bl_parent_id = "COMFYUI_PT_main"
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        layout = self.layout
        props = context.scene.comfyui_mocap

        layout.prop(props, "mocap_file")

        col = layout.column(align=True)
        col.prop(props, "scale")
        col.prop(props, "start_frame")
        col.prop(props, "use_fps_scale")

        layout.separator()
        row = layout.row()
        row.scale_y = 1.5
        row.operator("comfyui.import_mocap", icon='IMPORT')


# =============================================================================
# EXPORT PANEL
# =============================================================================

class COMFYUI_PT_export_panel(Panel):
    bl_label = "Export"
    bl_idname = "COMFYUI_PT_export"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "ComfyUI"
    bl_parent_id = "COMFYUI_PT_main"
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        layout = self.layout
        props = context.scene.comfyui_export

        layout.prop(props, "export_format")
        layout.prop(props, "include_animation")

        layout.separator()
        row = layout.row()
        row.scale_y = 1.5
        row.operator("comfyui.export_model", icon='EXPORT')


# =============================================================================
# HELPERS
# =============================================================================

def _filename(path):
    """Extract filename from a path string."""
    return path.replace('\\', '/').split('/')[-1]


def _wrap_text(text, max_width):
    """Wrap text to multiple lines."""
    words = text.split()
    lines = []
    current_line = []
    current_length = 0

    for word in words:
        if current_length + len(word) + 1 <= max_width:
            current_line.append(word)
            current_length += len(word) + 1
        else:
            if current_line:
                lines.append(' '.join(current_line))
            current_line = [word]
            current_length = len(word)

    if current_line:
        lines.append(' '.join(current_line))

    return lines if lines else ['']
