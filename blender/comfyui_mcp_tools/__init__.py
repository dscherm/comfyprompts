"""ComfyUI MCP Blender Addon

A comprehensive Blender addon for AI-powered 3D workflows:
- Auto-rigging (Rigify, UniRig, Tripo3D)
- Procedural animation generation
- Motion capture import
- MCP server integration
- Blender-to-ComfyUI generation pipeline (render → AI processing → result)

Installation:
1. In Blender, go to Edit > Preferences > Add-ons
2. Click "Install..." and select this folder
3. Enable "ComfyUI MCP Tools"

Usage:
- Access panels in the 3D View sidebar (press N)
- Look for the "ComfyUI" tab
"""

bl_info = {
    "name": "ComfyUI MCP Tools",
    "author": "ComfyUI MCP Server",
    "version": (1, 4, 0),
    "blender": (4, 0, 0),
    "location": "View3D > Sidebar > ComfyUI",
    "description": "AI-powered generation pipeline, auto-rigging, animation, and MCP integration",
    "category": "Rigging",
}

import bpy
from bpy.props import PointerProperty

from .properties import (
    ComfyMCPPreferences,
    ComfyMCPRiggingProps,
    ComfyMCPAnimationProps,
    ComfyMCPMocapProps,
    ComfyMCPExportProps,
    ComfyMCPPipelineProps,
)
from .operators import (
    COMFY_OT_auto_rig,
    COMFY_OT_generate_animation,
    COMFY_OT_import_mocap,
    COMFY_OT_export_model,
)
from .operators_pipeline import (
    COMFY_OT_check_comfyui,
    COMFY_OT_capture_viewport,
    COMFY_OT_use_render_result,
    COMFY_OT_run_pipeline,
    COMFY_OT_monitor_pipeline,
    COMFY_OT_cancel_pipeline,
    COMFY_OT_apply_as_texture,
    COMFY_OT_open_output,
)
from .panels import (
    COMFY_PT_main_panel,
    COMFY_PT_pipeline_panel,
    COMFY_PT_rigging_panel,
    COMFY_PT_animation_panel,
    COMFY_PT_mocap_panel,
    COMFY_PT_export_panel,
)

classes = (
    # Preferences and property groups (must register before operators/panels)
    ComfyMCPPreferences,
    ComfyMCPRiggingProps,
    ComfyMCPAnimationProps,
    ComfyMCPMocapProps,
    ComfyMCPExportProps,
    ComfyMCPPipelineProps,
    # Pipeline operators
    COMFY_OT_check_comfyui,
    COMFY_OT_capture_viewport,
    COMFY_OT_use_render_result,
    COMFY_OT_run_pipeline,
    COMFY_OT_monitor_pipeline,
    COMFY_OT_cancel_pipeline,
    COMFY_OT_apply_as_texture,
    COMFY_OT_open_output,
    # Existing operators
    COMFY_OT_auto_rig,
    COMFY_OT_generate_animation,
    COMFY_OT_import_mocap,
    COMFY_OT_export_model,
    # Panels
    COMFY_PT_main_panel,
    COMFY_PT_pipeline_panel,
    COMFY_PT_rigging_panel,
    COMFY_PT_animation_panel,
    COMFY_PT_mocap_panel,
    COMFY_PT_export_panel,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.comfy_rigging = PointerProperty(type=ComfyMCPRiggingProps)
    bpy.types.Scene.comfy_animation = PointerProperty(type=ComfyMCPAnimationProps)
    bpy.types.Scene.comfy_mocap = PointerProperty(type=ComfyMCPMocapProps)
    bpy.types.Scene.comfy_export = PointerProperty(type=ComfyMCPExportProps)
    bpy.types.Scene.comfy_pipeline = PointerProperty(type=ComfyMCPPipelineProps)
    print("ComfyUI MCP Tools addon registered (v1.4.0)")


def unregister():
    del bpy.types.Scene.comfy_pipeline
    del bpy.types.Scene.comfy_export
    del bpy.types.Scene.comfy_mocap
    del bpy.types.Scene.comfy_animation
    del bpy.types.Scene.comfy_rigging
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
    print("ComfyUI MCP Tools addon unregistered")


if __name__ == "__main__":
    register()
