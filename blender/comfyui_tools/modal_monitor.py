"""Async job polling with timer modal for ComfyUI Blender addon."""

import bpy
from bpy.types import Operator

from . import api_client
from .preferences import get_preferences


class COMFYUI_OT_monitor_job(Operator):
    """Monitor a running generation job"""
    bl_idname = "comfyui.monitor_job"
    bl_label = "Monitor Job"
    bl_description = "Monitor generation job progress"

    _timer = None
    _job_id = None

    def modal(self, context, event):
        if event.type == 'TIMER':
            props = context.scene.comfyui_gen

            if not props.job_id or props.job_status == "Cancelled":
                self.cancel(context)
                return {'CANCELLED'}

            prefs = get_preferences()
            client = api_client.get_client(prefs.api_url if prefs else None)
            success, result = client.get_job_status(props.job_id)

            if success:
                status = result.get('status', 'unknown')
                progress = result.get('progress', 0)
                output_path = result.get('output_path')

                props.job_progress = progress

                if status == 'completed':
                    props.job_status = "Completed"
                    props.output_path = output_path or ""

                    if output_path and props.auto_import:
                        self._import_result(context, output_path)

                    self.cancel(context)
                    self.report({'INFO'}, f"Generation complete: {output_path}")
                    return {'FINISHED'}

                elif status == 'error':
                    error = result.get('error', 'Unknown error')
                    props.job_status = f"Error: {error}"
                    self.cancel(context)
                    self.report({'ERROR'}, f"Generation failed: {error}")
                    return {'CANCELLED'}

                elif status == 'running':
                    props.job_status = f"Running ({progress:.0f}%)"

                elif status == 'pending':
                    props.job_status = "Pending..."

            else:
                error = result.get('error', 'Connection failed')
                props.job_status = f"Error: {error}"

        return {'PASS_THROUGH'}

    def execute(self, context):
        props = context.scene.comfyui_gen

        if not props.job_id:
            self.report({'ERROR'}, "No job to monitor")
            return {'CANCELLED'}

        prefs = get_preferences()
        interval = (prefs.poll_interval / 1000.0) if prefs else 2.0

        wm = context.window_manager
        self._timer = wm.event_timer_add(interval, window=context.window)
        self._job_id = props.job_id

        wm.modal_handler_add(self)
        props.job_status = "Monitoring..."

        return {'RUNNING_MODAL'}

    def cancel(self, context):
        if self._timer:
            wm = context.window_manager
            wm.event_timer_remove(self._timer)
            self._timer = None

    def _import_result(self, context, filepath):
        """Import a GLB file into the scene."""
        try:
            bpy.ops.import_scene.gltf(filepath=filepath)
            self.report({'INFO'}, f"Imported: {filepath}")
        except Exception as e:
            self.report({'WARNING'}, f"Failed to import result: {e}")


class COMFYUI_OT_cancel_job(Operator):
    """Cancel the current generation job"""
    bl_idname = "comfyui.cancel_job"
    bl_label = "Cancel Job"
    bl_description = "Cancel the current generation job"

    def execute(self, context):
        props = context.scene.comfyui_gen
        props.job_status = "Cancelled"
        props.job_id = ""
        props.job_progress = 0
        self.report({'INFO'}, "Job cancelled")
        return {'FINISHED'}
