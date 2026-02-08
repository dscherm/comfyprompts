"""UI panels for ComfyUI MCP Blender addon."""

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
