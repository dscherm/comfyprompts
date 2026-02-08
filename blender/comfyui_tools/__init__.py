"""ComfyUI Blender Addon - Unified AI-Powered 3D Workflow

Combines generation, rigging, animation, and export into a single addon:
- 3D model generation via ComfyUI (text-to-3D, image-to-3D)
- AI-powered auto-rigging (Rigify, UniRig, Tripo3D)
- Procedural animation generation
- Motion capture import
- Model export (GLB, FBX, Blend)

Installation:
1. In Blender, go to Edit > Preferences > Add-ons
2. Click "Install..." and select this folder
3. Enable "ComfyUI Tools"

Usage:
- Access panels in the 3D View sidebar (press N)
- Look for the "ComfyUI" tab
"""

bl_info = {
    "name": "ComfyUI Tools",
    "author": "ComfyUI Agent SDK",
    "version": (2, 0, 0),
    "blender": (4, 0, 0),
    "location": "View3D > Sidebar > ComfyUI",
    "description": "AI-powered 3D generation, rigging, animation, and export",
    "category": "3D View",
}

import bpy
from bpy.props import PointerProperty

from .preferences import ComfyUIPreferences
from .properties import (
    ComfyUIGenerationProps,
    ComfyUIRiggingProps,
    ComfyUIAnimationProps,
    ComfyUIMocapProps,
    ComfyUIExportProps,
)
from .operators_generate import (
    COMFYUI_OT_check_connection,
    COMFYUI_OT_refresh_workflows,
    COMFYUI_OT_analyze_prompt,
    COMFYUI_OT_capture_viewport,
    COMFYUI_OT_use_render_result,
    COMFYUI_OT_generate,
    COMFYUI_OT_import_result,
    COMFYUI_OT_open_output_folder,
    COMFYUI_OT_use_recommended,
    COMFYUI_OT_interrupt,
    COMFYUI_OT_clear_queue,
)
from .operators_rig import COMFYUI_OT_auto_rig
from .operators_anim import COMFYUI_OT_generate_animation
from .operators_mocap import COMFYUI_OT_import_mocap
from .operators_export import COMFYUI_OT_export_model
from .modal_monitor import COMFYUI_OT_monitor_job, COMFYUI_OT_cancel_job
from .panels import (
    COMFYUI_PT_main_panel,
    COMFYUI_PT_connection_panel,
    COMFYUI_PT_generate_input_panel,
    COMFYUI_PT_generate_workflow_panel,
    COMFYUI_PT_generate_action_panel,
    COMFYUI_PT_generate_output_panel,
    COMFYUI_PT_rigging_panel,
    COMFYUI_PT_animation_panel,
    COMFYUI_PT_mocap_panel,
    COMFYUI_PT_export_panel,
)

classes = (
    # Preferences
    ComfyUIPreferences,
    # Property groups
    ComfyUIGenerationProps,
    ComfyUIRiggingProps,
    ComfyUIAnimationProps,
    ComfyUIMocapProps,
    ComfyUIExportProps,
    # Generation operators
    COMFYUI_OT_check_connection,
    COMFYUI_OT_refresh_workflows,
    COMFYUI_OT_analyze_prompt,
    COMFYUI_OT_capture_viewport,
    COMFYUI_OT_use_render_result,
    COMFYUI_OT_generate,
    COMFYUI_OT_import_result,
    COMFYUI_OT_open_output_folder,
    COMFYUI_OT_use_recommended,
    COMFYUI_OT_interrupt,
    COMFYUI_OT_clear_queue,
    # Pipeline operators
    COMFYUI_OT_auto_rig,
    COMFYUI_OT_generate_animation,
    COMFYUI_OT_import_mocap,
    COMFYUI_OT_export_model,
    # Modal operators
    COMFYUI_OT_monitor_job,
    COMFYUI_OT_cancel_job,
    # Panels (order matters for UI)
    COMFYUI_PT_main_panel,
    COMFYUI_PT_connection_panel,
    COMFYUI_PT_generate_input_panel,
    COMFYUI_PT_generate_workflow_panel,
    COMFYUI_PT_generate_action_panel,
    COMFYUI_PT_generate_output_panel,
    COMFYUI_PT_rigging_panel,
    COMFYUI_PT_animation_panel,
    COMFYUI_PT_mocap_panel,
    COMFYUI_PT_export_panel,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.comfyui_gen = PointerProperty(type=ComfyUIGenerationProps)
    bpy.types.Scene.comfyui_rig = PointerProperty(type=ComfyUIRiggingProps)
    bpy.types.Scene.comfyui_anim = PointerProperty(type=ComfyUIAnimationProps)
    bpy.types.Scene.comfyui_mocap = PointerProperty(type=ComfyUIMocapProps)
    bpy.types.Scene.comfyui_export = PointerProperty(type=ComfyUIExportProps)
    print("ComfyUI Tools addon registered (v2.0.0)")


def unregister():
    del bpy.types.Scene.comfyui_export
    del bpy.types.Scene.comfyui_mocap
    del bpy.types.Scene.comfyui_anim
    del bpy.types.Scene.comfyui_rig
    del bpy.types.Scene.comfyui_gen
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
    print("ComfyUI Tools addon unregistered")


if __name__ == "__main__":
    register()
