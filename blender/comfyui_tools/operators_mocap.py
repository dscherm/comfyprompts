"""Motion capture import operators for ComfyUI Blender addon."""

from pathlib import Path

import bpy
from bpy.types import Operator


class COMFYUI_OT_import_mocap(Operator):
    """Import motion capture data"""
    bl_idname = "comfyui.import_mocap"
    bl_label = "Import Mocap"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return obj is not None and obj.type == 'ARMATURE'

    def execute(self, context):
        props = context.scene.comfyui_mocap

        if not props.mocap_file:
            self.report({'ERROR'}, "Select a mocap file")
            return {'CANCELLED'}

        mocap_path = Path(bpy.path.abspath(props.mocap_file))
        if not mocap_path.exists():
            self.report({'ERROR'}, f"File not found: {mocap_path}")
            return {'CANCELLED'}

        ext = mocap_path.suffix.lower()
        if ext == '.bvh':
            bpy.ops.import_anim.bvh(
                filepath=str(mocap_path),
                global_scale=props.scale,
                frame_start=props.start_frame,
                use_fps_scale=props.use_fps_scale,
            )
        elif ext == '.fbx':
            bpy.ops.import_scene.fbx(
                filepath=str(mocap_path),
                use_anim=True,
                global_scale=props.scale,
            )
        else:
            self.report({'ERROR'}, f"Unsupported format: {ext}")
            return {'CANCELLED'}

        self.report({'INFO'}, f"Imported: {mocap_path.name}")
        return {'FINISHED'}
