"""Mocked integration tests for the Blender-to-ComfyUI pipeline.

Tests the full pipeline flow with mock servers — no running services required.
Covers both the direct ComfyUI path and the MCP server path.
"""

import json
import os
import tempfile

import pytest


# =============================================================================
# DIRECT PIPELINE: Blender → ComfyUI (mock HTTP)
# =============================================================================


class TestDirectPipelineUploadRenderSubmit:
    """Full pipeline: upload Blender render → build workflow → submit → poll → download."""

    def test_img2img_full_pipeline(self, comfyui_client, sample_render_png):
        from workflows import build_img2img_workflow

        # 1. Upload the Blender render
        ok, upload = comfyui_client.upload_image(sample_render_png)
        assert ok, f"Upload failed: {upload}"
        image_name = upload["name"]

        # 2. Build img2img workflow
        wf = build_img2img_workflow(
            image_name, "oil painting of a fantasy castle", seed=42
        )
        assert wf["2"]["inputs"]["image"] == image_name
        assert wf["4"]["inputs"]["text"] == "oil painting of a fantasy castle"

        # 3. Submit to ComfyUI
        ok, queue = comfyui_client.queue_prompt(wf)
        assert ok, f"Queue failed: {queue}"
        prompt_id = queue["prompt_id"]
        assert prompt_id.startswith("integration_test_")

        # 4. Poll for completion
        ok, status = comfyui_client.get_job_status(prompt_id)
        assert ok
        assert status["status"] == "completed"
        assert status["outputs"] is not None

        # 5. Extract output images
        images = comfyui_client.extract_output_images(status["outputs"])
        assert len(images) == 1
        assert images[0]["filename"].endswith(".png")

        # 6. Download result
        ok, data = comfyui_client.download_image(
            images[0]["filename"],
            subfolder=images[0]["subfolder"],
            folder_type=images[0]["type"],
        )
        assert ok
        assert isinstance(data, bytes)
        assert data[:4] == b"\x89PNG"

    def test_txt2img_full_pipeline(self, comfyui_client):
        from workflows import build_txt2img_workflow

        # 1. Build txt2img workflow (no upload needed)
        wf = build_txt2img_workflow(
            "a photorealistic mountain landscape at sunset",
            width=768, height=512, steps=25, cfg=8.0, seed=12345,
        )

        # 2. Submit
        ok, queue = comfyui_client.queue_prompt(wf)
        assert ok
        prompt_id = queue["prompt_id"]

        # 3. Poll
        ok, status = comfyui_client.get_job_status(prompt_id)
        assert ok
        assert status["status"] == "completed"

        # 4. Extract and download
        images = comfyui_client.extract_output_images(status["outputs"])
        assert len(images) == 1

        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            output_path = f.name
        try:
            ok, path = comfyui_client.download_image_to_file(
                images[0]["filename"], output_path,
            )
            assert ok
            assert os.path.exists(output_path)
            with open(output_path, "rb") as f:
                assert f.read()[:4] == b"\x89PNG"
        finally:
            os.unlink(output_path)

    def test_img2img_with_custom_parameters(self, comfyui_client, sample_render_png):
        from workflows import build_img2img_workflow

        ok, upload = comfyui_client.upload_image(sample_render_png)
        assert ok

        wf = build_img2img_workflow(
            upload["name"],
            "cyberpunk city at night",
            negative_prompt="blurry, low quality",
            checkpoint="dreamshaper_8.safetensors",
            steps=30,
            cfg=12.0,
            denoise=0.8,
            seed=99999,
            sampler="dpmpp_2m",
            scheduler="karras",
        )

        # Verify all parameters are set in the workflow
        assert wf["1"]["inputs"]["ckpt_name"] == "dreamshaper_8.safetensors"
        assert wf["4"]["inputs"]["text"] == "cyberpunk city at night"
        assert wf["5"]["inputs"]["text"] == "blurry, low quality"
        assert wf["6"]["inputs"]["steps"] == 30
        assert wf["6"]["inputs"]["cfg"] == 12.0
        assert wf["6"]["inputs"]["denoise"] == 0.8
        assert wf["6"]["inputs"]["seed"] == 99999
        assert wf["6"]["inputs"]["sampler_name"] == "dpmpp_2m"
        assert wf["6"]["inputs"]["scheduler"] == "karras"

        ok, queue = comfyui_client.queue_prompt(wf)
        assert ok


class TestDirectPipelineDiscovery:
    """Test model and config discovery via mock ComfyUI API."""

    def test_list_checkpoints(self, comfyui_client):
        ok, models = comfyui_client.get_checkpoints()
        assert ok
        assert "v1-5-pruned-emaonly.ckpt" in models
        assert "dreamshaper_8.safetensors" in models

    def test_list_samplers(self, comfyui_client):
        ok, samplers = comfyui_client.get_samplers()
        assert ok
        assert "euler" in samplers
        assert "dpmpp_2m" in samplers

    def test_list_schedulers(self, comfyui_client):
        ok, schedulers = comfyui_client.get_schedulers()
        assert ok
        assert "normal" in schedulers
        assert "karras" in schedulers

    def test_check_connection(self, comfyui_client):
        ok, info = comfyui_client.check_connection()
        assert ok
        assert "system" in info
        assert info["system"]["vram"]["total"] > 0


class TestDirectPipelineErrorHandling:
    """Test pipeline handles errors gracefully."""

    def test_connection_failure(self):
        from comfyui_client import ComfyUIDirectClient

        bad_client = ComfyUIDirectClient("http://127.0.0.1:1")
        ok, info = bad_client.check_connection()
        assert ok is False
        assert "error" in info

    def test_unknown_job_returns_pending(self, comfyui_client):
        ok, status = comfyui_client.get_job_status("nonexistent_job")
        assert ok
        assert status["status"] == "pending"

    def test_upload_nonexistent_file_raises(self, comfyui_client):
        with pytest.raises(FileNotFoundError):
            comfyui_client.upload_image("/nonexistent/file.png")


class TestDirectPipelineMultipleJobs:
    """Test submitting multiple jobs in sequence."""

    def test_sequential_jobs_get_unique_ids(self, comfyui_client):
        from workflows import build_txt2img_workflow

        ids = []
        for i in range(3):
            wf = build_txt2img_workflow(f"test prompt {i}", seed=i)
            ok, queue = comfyui_client.queue_prompt(wf)
            assert ok
            ids.append(queue["prompt_id"])

        # All IDs should be unique
        assert len(set(ids)) == 3

    def test_all_jobs_complete(self, comfyui_client):
        from workflows import build_txt2img_workflow

        ids = []
        for i in range(3):
            wf = build_txt2img_workflow(f"batch prompt {i}", seed=i)
            ok, queue = comfyui_client.queue_prompt(wf)
            assert ok
            ids.append(queue["prompt_id"])

        for prompt_id in ids:
            ok, status = comfyui_client.get_job_status(prompt_id)
            assert ok
            assert status["status"] == "completed"


# =============================================================================
# MCP PIPELINE: Blender → MCP Server → ComfyUI (mock HTTP)
# =============================================================================


class TestMCPPipelineGeneration:
    """Test the MCP-based generation pipeline with mock server."""

    def test_mcp_health_check(self, mcp_client):
        from mcp_client import extract_text_content

        ok, result = mcp_client.call_tool("health_check", {})
        assert ok
        data = extract_text_content(result)
        assert data["status"] == "healthy"
        assert data["comfyui_connected"] is True

    def test_mcp_generate_image(self, mcp_client):
        from mcp_client import extract_text_content

        ok, result = mcp_client.call_tool("generate_image", {
            "prompt": "a cute cat sitting on a windowsill",
            "width": 512,
            "height": 512,
            "steps": 20,
        })
        assert ok
        data = extract_text_content(result)
        assert "asset_id" in data
        assert "filename" in data
        assert data["width"] == 512
        assert data["height"] == 512

    def test_mcp_blender_depth_guided(self, mcp_client):
        from mcp_client import extract_text_content

        ok, result = mcp_client.call_tool("blender_depth_guided", {
            "prompt": "fantasy landscape, oil painting",
            "depth_image": "depth_001.png",
            "source_image": "render_001.png",
            "controlnet_strength": 0.85,
        })
        assert ok
        data = extract_text_content(result)
        assert data["asset_id"] == "asset-blender_depth_guided-001"

    def test_mcp_blender_normal_texturing(self, mcp_client):
        from mcp_client import extract_text_content

        ok, result = mcp_client.call_tool("blender_normal_texturing", {
            "prompt": "weathered stone texture, mossy cracks, photorealistic",
            "normal_image": "normals_001.png",
            "width": 512,
            "height": 512,
        })
        assert ok
        data = extract_text_content(result)
        assert data["asset_id"] == "asset-blender_normal_texturing-001"

    def test_mcp_blender_pose_to_render(self, mcp_client):
        from mcp_client import extract_text_content

        ok, result = mcp_client.call_tool("blender_pose_to_render", {
            "prompt": "a warrior in medieval armor, fantasy art",
            "pose_image": "pose_001.png",
            "width": 512,
            "height": 768,
        })
        assert ok
        data = extract_text_content(result)
        assert data["asset_id"] == "asset-blender_pose_to_render-001"

    def test_mcp_list_tools_includes_blender_workflows(self, mcp_client):
        ok, tools = mcp_client.list_tools()
        assert ok
        names = [t["name"] for t in tools]
        assert "blender_depth_guided" in names
        assert "blender_normal_texturing" in names
        assert "blender_pose_to_render" in names


class TestMCPPipelineSessionManagement:
    """Test MCP session lifecycle during pipeline operations."""

    def test_auto_initialize_on_tool_call(self, mcp_client):
        assert mcp_client.session_id is None
        ok, _ = mcp_client.call_tool("health_check", {})
        assert ok
        assert mcp_client.session_id is not None

    def test_session_persists_across_calls(self, mcp_client):
        mcp_client.call_tool("health_check", {})
        session1 = mcp_client.session_id
        mcp_client.call_tool("generate_image", {"prompt": "test"})
        assert mcp_client.session_id == session1

    def test_close_and_reconnect(self, mcp_client):
        mcp_client.call_tool("health_check", {})
        old_session = mcp_client.session_id
        mcp_client.close()
        assert mcp_client.session_id is None
        mcp_client.call_tool("health_check", {})
        assert mcp_client.session_id is not None
        assert mcp_client.session_id != old_session


class TestMCPPipelineCustomResponses:
    """Test pipeline with custom mock responses for complex scenarios."""

    def test_generation_with_preview(self, mcp_client, mock_mcp_handler):
        from mcp_client import extract_text_content

        mock_mcp_handler.tool_responses["generate_image"] = {
            "content": [
                {"type": "image", "data": "base64_preview_data_here", "mimeType": "image/png"},
                {"type": "text", "text": json.dumps({
                    "asset_id": "gen-preview-001",
                    "filename": "ComfyUI_00042_.png",
                    "width": 512,
                    "height": 512,
                    "preview_included": True,
                })},
            ]
        }

        ok, result = mcp_client.call_tool("generate_image", {"prompt": "test"})
        assert ok
        data = extract_text_content(result)
        assert data["asset_id"] == "gen-preview-001"
        assert data["preview_included"] is True

    def test_dynamic_response_uses_arguments(self, mcp_client, mock_mcp_handler):
        from mcp_client import extract_text_content

        def echo_args(args):
            return {
                "content": [{"type": "text", "text": json.dumps({
                    "received_prompt": args.get("prompt", ""),
                    "received_width": args.get("width", 512),
                })}]
            }

        mock_mcp_handler.tool_responses["generate_image"] = echo_args

        ok, result = mcp_client.call_tool("generate_image", {
            "prompt": "a dog", "width": 768,
        })
        assert ok
        data = extract_text_content(result)
        assert data["received_prompt"] == "a dog"
        assert data["received_width"] == 768
