"""Live integration tests requiring a running ComfyUI instance.

All tests are marked with @pytest.mark.integration and will be skipped
if ComfyUI is not running at localhost:8188.

Run with: pytest tests/integration/test_pipeline_live.py -m integration -v
"""

import os
import tempfile

import pytest


@pytest.mark.integration
class TestLiveComfyUIConnection:
    """Verify live ComfyUI is reachable and has expected capabilities."""

    def test_connection(self, live_comfyui_client):
        ok, info = live_comfyui_client.check_connection()
        assert ok
        assert "system" in info

    def test_has_default_checkpoint(self, live_comfyui_client):
        ok, checkpoints = live_comfyui_client.get_checkpoints()
        assert ok, f"Failed to get checkpoints: {checkpoints}"
        assert "sd_xl_base_1.0.safetensors" in checkpoints, (
            f"default SDXL checkpoint not found. Available: {checkpoints}"
        )

    def test_has_samplers(self, live_comfyui_client):
        ok, samplers = live_comfyui_client.get_samplers()
        assert ok
        assert "euler" in samplers

    def test_has_schedulers(self, live_comfyui_client):
        ok, schedulers = live_comfyui_client.get_schedulers()
        assert ok
        assert "normal" in schedulers


@pytest.mark.integration
class TestLiveImageUpload:
    """Test image upload to live ComfyUI."""

    def test_upload_png(self, live_comfyui_client, sample_render_png):
        ok, result = live_comfyui_client.upload_image(sample_render_png)
        assert ok, f"Upload failed: {result}"
        assert "name" in result
        assert result["type"] == "input"


@pytest.mark.integration
@pytest.mark.slow
class TestLiveTxt2ImgGeneration:
    """Test actual image generation on live ComfyUI.

    These tests run real inference and may take 30-120 seconds each.
    Run with: pytest tests/integration/test_pipeline_live.py -m "integration and slow" -v
    """

    def test_minimal_txt2img(self, live_comfyui_client):
        """Generate a tiny image (256x256, 8 steps) to verify the pipeline works."""
        from workflows import build_txt2img_workflow

        wf = build_txt2img_workflow(
            "a red circle on white background, simple",
            width=256, height=256, steps=8, seed=42,
            checkpoint="sd_xl_base_1.0.safetensors",
        )

        ok, queue = live_comfyui_client.queue_prompt(wf)
        assert ok, f"Queue failed: {queue}"
        prompt_id = queue["prompt_id"]

        # Poll until done (max 120 seconds)
        import time
        for _ in range(60):
            ok, status = live_comfyui_client.get_job_status(prompt_id)
            assert ok
            if status["status"] == "completed":
                break
            if status["status"] == "error":
                pytest.fail(f"Generation failed: {status['error']}")
            time.sleep(2)
        else:
            pytest.fail("Generation timed out after 120 seconds")

        images = live_comfyui_client.extract_output_images(status["outputs"])
        assert len(images) >= 1

        # Download and verify it's a valid PNG
        ok, data = live_comfyui_client.download_image(
            images[0]["filename"],
            subfolder=images[0]["subfolder"],
            folder_type=images[0]["type"],
        )
        assert ok
        assert data[:4] == b"\x89PNG"
        assert len(data) > 1000  # Real PNG should be > 1KB


@pytest.mark.integration
@pytest.mark.slow
class TestLiveImg2ImgGeneration:
    """Test img2img pipeline with live ComfyUI."""

    def test_minimal_img2img(self, live_comfyui_client, sample_render_png):
        from workflows import build_img2img_workflow

        # Upload
        ok, upload = live_comfyui_client.upload_image(sample_render_png)
        assert ok, f"Upload failed: {upload}"

        wf = build_img2img_workflow(
            upload["name"],
            "a colorful abstract painting",
            steps=8, denoise=0.7, seed=42,
            checkpoint="sd_xl_base_1.0.safetensors",
        )

        ok, queue = live_comfyui_client.queue_prompt(wf)
        assert ok, f"Queue failed: {queue}"
        prompt_id = queue["prompt_id"]

        import time
        for _ in range(60):
            ok, status = live_comfyui_client.get_job_status(prompt_id)
            assert ok
            if status["status"] == "completed":
                break
            if status["status"] == "error":
                pytest.fail(f"Generation failed: {status['error']}")
            time.sleep(2)
        else:
            pytest.fail("Generation timed out after 120 seconds")

        images = live_comfyui_client.extract_output_images(status["outputs"])
        assert len(images) >= 1


@pytest.mark.integration
class TestLiveSDKClient:
    """Test the SDK ComfyUIClient against live ComfyUI."""

    def test_sdk_connection(self, live_sdk_client):
        info = live_sdk_client.check_connection()
        assert info["connected"] is True

    def test_sdk_models(self, live_sdk_client):
        models = live_sdk_client.available_models
        assert models is not None
        assert len(models) > 0


@pytest.mark.integration
class TestLiveWorkflowManager:
    """Test WorkflowManager with live ComfyUI for rendering Blender workflows."""

    def test_blender_workflows_discovered(self, workflow_manager):
        tool_names = [d.tool_name for d in workflow_manager.tool_definitions]
        assert "blender_depth_guided" in tool_names
        assert "blender_normal_texturing" in tool_names
        assert "blender_pose_to_render" in tool_names

    def test_render_depth_guided_produces_valid_workflow(self, workflow_manager):
        defn = next(
            d for d in workflow_manager.tool_definitions
            if d.tool_name == "blender_depth_guided"
        )
        rendered = workflow_manager.render_workflow(defn, {
            "prompt": "test scene",
            "depth_image": "depth.png",
            "source_image": "render.png",
        })
        assert rendered is not None
        # Check all required nodes are present
        class_types = {node["class_type"] for node in rendered.values()}
        assert "CheckpointLoaderSimple" in class_types
        assert "ControlNetLoader" in class_types
        assert "KSampler" in class_types
        assert "SaveImage" in class_types
