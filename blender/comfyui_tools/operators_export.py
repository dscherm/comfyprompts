"""Export operators for ComfyUI Blender addon."""

import bpy
from bpy.props import StringProperty
from bpy.types import Operator


class COMFYUI_OT_export_model(Operator):
    """Export rigged/animated model"""
    bl_idname = "comfyui.export_model"
    bl_label = "Export Model"

    filepath: StringProperty(subtype='FILE_PATH')

    def execute(self, context):
        props = context.scene.comfyui_export
        fmt = props.export_format

        if fmt == 'GLB':
            bpy.ops.export_scene.gltf(
                filepath=self.filepath,
                export_format='GLB',
                export_animations=props.include_animation,
            )
        elif fmt == 'FBX':
            bpy.ops.export_scene.fbx(
                filepath=self.filepath,
                bake_anim=props.include_animation,
            )
        elif fmt == 'BLEND':
            bpy.ops.wm.save_as_mainfile(filepath=self.filepath)

        self.report({'INFO'}, f"Exported: {self.filepath}")
        return {'FINISHED'}

    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}
