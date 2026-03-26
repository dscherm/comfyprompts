"""Pipeline operators for Blender-to-ComfyUI generation.

Provides the end-to-end flow:
  Blender render/viewport capture → upload to ComfyUI → AI processing → result download

All HTTP communication uses urllib only (Blender addon constraint).
"""

import os
import tempfile

import bpy
from bpy.types import Operator

from .comfyui_client import get_comfyui_client
from .workflows import build_img2img_workflow, build_txt2img_workflow


# =============================================================================
# CONNECTION CHECK
# =============================================================================

class COMFY_OT_check_comfyui(Operator):
    """Check connection to ComfyUI server"""
    bl_idname = "comfy.check_comfyui"
    bl_label = "Check ComfyUI"

    def execute(self, context):
        prefs = context.preferences.addons[__package__].preferences
        client = get_comfyui_client(prefs.comfyui_url)
        ok, data = client.check_connection()

        props = context.scene.comfy_pipeline
        if ok:
            props.comfyui_connected = True
            vram = data.get("system", {}).get("vram", {})
            vram_total = vram.get("total", 0) / (1024**3)
            self.report({"INFO"}, f"ComfyUI connected — {vram_total:.1f} GB VRAM")
        else:
            props.comfyui_connected = False
            self.report({"ERROR"}, f"ComfyUI not reachable: {data.get('error', 'unknown')}")
        return {"FINISHED"}


# =============================================================================
# VIEWPORT CAPTURE
# =============================================================================

class COMFY_OT_capture_viewport(Operator):
    """Capture the 3D viewport as a PNG image"""
    bl_idname = "comfy.capture_viewport_mcp"
    bl_label = "Capture Viewport"

    def execute(self, context):
        props = context.scene.comfy_pipeline
        res_x = props.capture_width
        res_y = props.capture_height

        # Render the viewport to an offscreen image
        filepath = os.path.join(tempfile.gettempdir(), "comfy_mcp_viewport.png")

        # Use OpenGL render
        old_filepath = context.scene.render.filepath
        old_res_x = context.scene.render.resolution_x
        old_res_y = context.scene.render.resolution_y
        old_pct = context.scene.render.resolution_percentage
        old_format = context.scene.render.image_settings.file_format

        try:
            context.scene.render.filepath = filepath
            context.scene.render.resolution_x = res_x
            context.scene.render.resolution_y = res_y
            context.scene.render.resolution_percentage = 100
            context.scene.render.image_settings.file_format = "PNG"
            bpy.ops.render.opengl(write_still=True)
        finally:
            context.scene.render.filepath = old_filepath
            context.scene.render.resolution_x = old_res_x
            context.scene.render.resolution_y = old_res_y
            context.scene.render.resolution_percentage = old_pct
            context.scene.render.image_settings.file_format = old_format

        if os.path.exists(filepath):
            props.input_image_path = filepath
            self.report({"INFO"}, f"Viewport captured ({res_x}x{res_y})")
        else:
            self.report({"ERROR"}, "Failed to capture viewport")
        return {"FINISHED"}


# =============================================================================
# USE RENDER RESULT
# =============================================================================

class COMFY_OT_use_render_result(Operator):
    """Save the last Blender render result as input image"""
    bl_idname = "comfy.use_render_result_mcp"
    bl_label = "Use Render Result"

    @classmethod
    def poll(cls, context):
        return bpy.data.images.get("Render Result") is not None

    def execute(self, context):
        props = context.scene.comfy_pipeline
        render_img = bpy.data.images.get("Render Result")
        if render_img is None:
            self.report({"ERROR"}, "No render result available — render a frame first")
            return {"CANCELLED"}

        filepath = os.path.join(tempfile.gettempdir(), "comfy_mcp_render.png")
        old_format = context.scene.render.image_settings.file_format
        try:
            context.scene.render.image_settings.file_format = "PNG"
            render_img.save_render(filepath)
        finally:
            context.scene.render.image_settings.file_format = old_format

        if os.path.exists(filepath):
            props.input_image_path = filepath
            self.report({"INFO"}, "Render result saved as input")
        else:
            self.report({"ERROR"}, "Failed to save render result")
        return {"FINISHED"}


# =============================================================================
# RUN PIPELINE
# =============================================================================

class COMFY_OT_run_pipeline(Operator):
    """Run the full Blender-to-ComfyUI generation pipeline"""
    bl_idname = "comfy.run_pipeline"
    bl_label = "Generate"

    @classmethod
    def poll(cls, context):
        props = context.scene.comfy_pipeline
        if props.pipeline_mode == "IMG2IMG":
            return bool(props.prompt) and bool(props.input_image_path)
        return bool(props.prompt)

    def execute(self, context):
        props = context.scene.comfy_pipeline
        prefs = context.preferences.addons[__package__].preferences
        client = get_comfyui_client(prefs.comfyui_url)

        # Step 1: For IMG2IMG, capture viewport if no input image yet
        if props.pipeline_mode == "IMG2IMG":
            if not props.input_image_path or not os.path.exists(props.input_image_path):
                self.report({"ERROR"}, "No input image — capture viewport or use render result first")
                return {"CANCELLED"}

            # Step 2: Upload image to ComfyUI
            ok, upload_result = client.upload_image(props.input_image_path)
            if not ok:
                self.report({"ERROR"}, f"Upload failed: {upload_result.get('error')}")
                return {"CANCELLED"}

            image_name = upload_result.get("name", os.path.basename(props.input_image_path))

            # Step 3: Build img2img workflow
            workflow = build_img2img_workflow(
                image_name=image_name,
                prompt=props.prompt,
                negative_prompt=props.negative_prompt,
                checkpoint=props.checkpoint,
                steps=props.steps,
                cfg=props.cfg,
                denoise=props.denoise,
                seed=props.seed if props.seed != 0 else None,
                sampler=props.sampler,
                scheduler=props.scheduler,
            )
        else:
            # TXT2IMG mode
            workflow = build_txt2img_workflow(
                prompt=props.prompt,
                negative_prompt=props.negative_prompt,
                checkpoint=props.checkpoint,
                width=props.capture_width,
                height=props.capture_height,
                steps=props.steps,
                cfg=props.cfg,
                seed=props.seed if props.seed != 0 else None,
                sampler=props.sampler,
                scheduler=props.scheduler,
            )

        # Step 4: Submit workflow
        ok, queue_result = client.queue_prompt(workflow)
        if not ok:
            self.report({"ERROR"}, f"Queue failed: {queue_result.get('error')}")
            return {"CANCELLED"}

        prompt_id = queue_result.get("prompt_id")
        if not prompt_id:
            self.report({"ERROR"}, "No prompt_id returned from ComfyUI")
            return {"CANCELLED"}

        # Step 5: Start monitoring
        props.job_prompt_id = prompt_id
        props.job_status = "Queued"
        props.job_progress = "Waiting..."
        props.output_image_path = ""

        bpy.ops.comfy.monitor_pipeline("INVOKE_DEFAULT")
        self.report({"INFO"}, f"Pipeline started (prompt_id: {prompt_id[:8]}...)")
        return {"FINISHED"}


# =============================================================================
# MONITOR PIPELINE (Modal Timer)
# =============================================================================

class COMFY_OT_monitor_pipeline(Operator):
    """Poll ComfyUI for job completion (modal timer)"""
    bl_idname = "comfy.monitor_pipeline"
    bl_label = "Monitor Pipeline"

    _timer = None

    def modal(self, context, event):
        if event.type != "TIMER":
            return {"PASS_THROUGH"}

        props = context.scene.comfy_pipeline
        if props.job_status == "Cancelled":
            self._cleanup(context)
            self.report({"WARNING"}, "Pipeline cancelled")
            return {"CANCELLED"}

        prefs = context.preferences.addons[__package__].preferences
        client = get_comfyui_client(prefs.comfyui_url)

        ok, status = client.get_job_status(props.job_prompt_id)
        if not ok:
            props.job_status = "Error"
            props.job_progress = status.get("error", "Connection lost")
            self._cleanup(context)
            return {"CANCELLED"}

        job_status = status["status"]

        if job_status == "pending":
            props.job_status = "Pending"
            props.job_progress = "In queue..."
            return {"PASS_THROUGH"}

        if job_status == "running":
            props.job_status = "Running"
            props.job_progress = "Processing..."
            return {"PASS_THROUGH"}

        if job_status == "error":
            props.job_status = "Error"
            props.job_progress = status.get("error", "Unknown error")
            self._cleanup(context)
            self.report({"ERROR"}, f"Generation failed: {props.job_progress}")
            return {"CANCELLED"}

        if job_status == "completed":
            outputs = status.get("outputs", {})
            images = client.extract_output_images(outputs)

            if not images:
                props.job_status = "Error"
                props.job_progress = "No output images found"
                self._cleanup(context)
                self.report({"ERROR"}, "Generation produced no images")
                return {"CANCELLED"}

            # Download the first output image
            first = images[0]
            output_path = os.path.join(
                tempfile.gettempdir(), f"comfy_mcp_output_{first['filename']}"
            )
            ok, result = client.download_image_to_file(
                first["filename"], output_path,
                subfolder=first["subfolder"],
                folder_type=first["type"],
            )

            if ok:
                props.output_image_path = output_path
                props.job_status = "Completed"
                props.job_progress = f"Done — {first['filename']}"

                # Auto-load into Blender's image editor
                if os.path.exists(output_path):
                    img = bpy.data.images.load(output_path, check_existing=True)
                    img.name = f"ComfyUI_{first['filename']}"

                self.report({"INFO"}, f"Generation complete: {first['filename']}")
            else:
                props.job_status = "Error"
                props.job_progress = f"Download failed: {result.get('error')}"
                self.report({"ERROR"}, props.job_progress)

            self._cleanup(context)
            return {"FINISHED"}

        # Unknown status — keep polling
        return {"PASS_THROUGH"}

    def execute(self, context):
        return self.invoke(context, None)

    def invoke(self, context, event):
        props = context.scene.comfy_pipeline
        poll_seconds = props.poll_interval / 1000.0
        self._timer = context.window_manager.event_timer_add(
            poll_seconds, window=context.window
        )
        context.window_manager.modal_handler_add(self)
        return {"RUNNING_MODAL"}

    def _cleanup(self, context):
        if self._timer:
            context.window_manager.event_timer_remove(self._timer)
            self._timer = None


# =============================================================================
# CANCEL PIPELINE
# =============================================================================

class COMFY_OT_cancel_pipeline(Operator):
    """Cancel the running pipeline"""
    bl_idname = "comfy.cancel_pipeline"
    bl_label = "Cancel"

    @classmethod
    def poll(cls, context):
        props = context.scene.comfy_pipeline
        return props.job_status in ("Queued", "Pending", "Running")

    def execute(self, context):
        props = context.scene.comfy_pipeline
        props.job_status = "Cancelled"

        prefs = context.preferences.addons[__package__].preferences
        client = get_comfyui_client(prefs.comfyui_url)
        client.interrupt()

        self.report({"INFO"}, "Pipeline cancelled")
        return {"FINISHED"}


# =============================================================================
# APPLY RESULT AS TEXTURE
# =============================================================================

class COMFY_OT_apply_as_texture(Operator):
    """Apply the generated image as a texture on the selected object"""
    bl_idname = "comfy.apply_as_texture"
    bl_label = "Apply as Texture"

    @classmethod
    def poll(cls, context):
        props = context.scene.comfy_pipeline
        return (
            bool(props.output_image_path)
            and os.path.exists(props.output_image_path)
            and context.active_object is not None
            and context.active_object.type == "MESH"
        )

    def execute(self, context):
        props = context.scene.comfy_pipeline
        obj = context.active_object

        # Load image
        img = bpy.data.images.load(props.output_image_path, check_existing=True)

        # Create material if needed
        if not obj.data.materials:
            mat = bpy.data.materials.new(name=f"ComfyUI_{obj.name}")
            obj.data.materials.append(mat)
        else:
            mat = obj.data.materials[0]

        mat.use_nodes = True
        nodes = mat.node_tree.nodes
        links = mat.node_tree.links

        # Find or create Principled BSDF
        bsdf = None
        for node in nodes:
            if node.type == "BSDF_PRINCIPLED":
                bsdf = node
                break
        if bsdf is None:
            bsdf = nodes.new("ShaderNodeBsdfPrincipled")

        # Create image texture node
        tex_node = nodes.new("ShaderNodeTexImage")
        tex_node.image = img
        tex_node.location = (bsdf.location.x - 300, bsdf.location.y)

        # Connect to Base Color
        links.new(tex_node.outputs["Color"], bsdf.inputs["Base Color"])

        self.report({"INFO"}, f"Applied texture to {obj.name}")
        return {"FINISHED"}


# =============================================================================
# OPEN OUTPUT IMAGE
# =============================================================================

class COMFY_OT_open_output(Operator):
    """Open the output image in the system viewer"""
    bl_idname = "comfy.open_output"
    bl_label = "Open Output"

    @classmethod
    def poll(cls, context):
        props = context.scene.comfy_pipeline
        return bool(props.output_image_path) and os.path.exists(props.output_image_path)

    def execute(self, context):
        import subprocess
        import sys

        props = context.scene.comfy_pipeline
        path = props.output_image_path

        if sys.platform == "win32":
            os.startfile(path)
        elif sys.platform == "darwin":
            subprocess.Popen(["open", path])
        else:
            subprocess.Popen(["xdg-open", path])

        return {"FINISHED"}
