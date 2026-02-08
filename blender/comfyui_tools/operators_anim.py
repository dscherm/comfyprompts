"""Animation operators for ComfyUI Blender addon."""

import bpy
from bpy.types import Operator


class COMFYUI_OT_generate_animation(Operator):
    """Generate procedural animation for the rig"""
    bl_idname = "comfyui.generate_animation"
    bl_label = "Generate Animation"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        if obj is None or obj.type != 'ARMATURE':
            return False
        try:
            from .animations import ANIMATION_GENERATORS
            return True
        except ImportError:
            return False

    def execute(self, context):
        from .animations import ANIMATION_GENERATORS

        props = context.scene.comfyui_anim
        armature = context.active_object

        generator = ANIMATION_GENERATORS.get(props.animation_type)
        if not generator:
            self.report({'ERROR'}, f"Unknown animation type: {props.animation_type}")
            return {'CANCELLED'}

        bpy.ops.object.mode_set(mode='POSE')

        try:
            generator(
                armature,
                duration=props.duration,
                fps=props.fps,
                intensity=props.intensity,
                loop=props.loop,
            )
            frame_count = int(props.fps * props.duration)
            self.report({'INFO'}, f"Generated {props.animation_type}: {frame_count} frames")
        except Exception as e:
            self.report({'ERROR'}, str(e))
            bpy.ops.object.mode_set(mode='OBJECT')
            return {'CANCELLED'}

        bpy.ops.object.mode_set(mode='OBJECT')
        return {'FINISHED'}
