"""Tests for the Blender-to-ComfyUI pipeline components.

Tests the non-Blender parts of the pipeline (no bpy dependency):
- ComfyUIDirectClient HTTP interactions (mocked)
- Workflow template builders
- Output extraction helpers
"""

import json
import os
import tempfile
from http.server import BaseHTTPRequestHandler, HTTPServer
from threading import Thread
from unittest.mock import patch

import pytest

# Add blender addon to path so we can import without bpy
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "blender", "comfyui_mcp_tools"))

from comfyui_client import ComfyUIDirectClient
from workflows import (
    DEFAULT_CHECKPOINT,
    build_img2img_workflow,
    build_txt2img_workflow,
)


# =============================================================================
# WORKFLOW TEMPLATE TESTS
# =============================================================================


class TestImg2ImgWorkflow:
    def test_basic_structure(self):
        wf = build_img2img_workflow("test.png", "a cat", seed=42)
        # Must have all required nodes
        assert "1" in wf  # CheckpointLoaderSimple
        assert "2" in wf  # LoadImage
        assert "3" in wf  # VAEEncode
        assert "4" in wf  # Positive CLIP
        assert "5" in wf  # Negative CLIP
        assert "6" in wf  # KSampler
        assert "7" in wf  # VAEDecode
        assert "8" in wf  # SaveImage

    def test_image_name_set(self):
        wf = build_img2img_workflow("my_render.png", "a cat", seed=42)
        assert wf["2"]["inputs"]["image"] == "my_render.png"
        assert wf["2"]["class_type"] == "LoadImage"

    def test_prompt_set(self):
        wf = build_img2img_workflow("img.png", "beautiful landscape", seed=42)
        assert wf["4"]["inputs"]["text"] == "beautiful landscape"

    def test_negative_prompt_set(self):
        wf = build_img2img_workflow("img.png", "cat", negative_prompt="ugly", seed=42)
        assert wf["5"]["inputs"]["text"] == "ugly"

    def test_negative_prompt_default_empty(self):
        wf = build_img2img_workflow("img.png", "cat", seed=42)
        assert wf["5"]["inputs"]["text"] == ""

    def test_default_checkpoint(self):
        wf = build_img2img_workflow("img.png", "cat", seed=42)
        assert wf["1"]["inputs"]["ckpt_name"] == DEFAULT_CHECKPOINT

    def test_custom_checkpoint(self):
        wf = build_img2img_workflow("img.png", "cat", checkpoint="dreamshaper_8.safetensors", seed=42)
        assert wf["1"]["inputs"]["ckpt_name"] == "dreamshaper_8.safetensors"

    def test_denoise_set(self):
        wf = build_img2img_workflow("img.png", "cat", denoise=0.8, seed=42)
        assert wf["6"]["inputs"]["denoise"] == 0.8

    def test_seed_set(self):
        wf = build_img2img_workflow("img.png", "cat", seed=12345)
        assert wf["6"]["inputs"]["seed"] == 12345

    def test_random_seed_when_none(self):
        wf = build_img2img_workflow("img.png", "cat", seed=None)
        seed = wf["6"]["inputs"]["seed"]
        assert isinstance(seed, int)
        assert 0 <= seed < 2**32

    def test_steps_and_cfg(self):
        wf = build_img2img_workflow("img.png", "cat", steps=30, cfg=12.0, seed=42)
        assert wf["6"]["inputs"]["steps"] == 30
        assert wf["6"]["inputs"]["cfg"] == 12.0

    def test_sampler_and_scheduler(self):
        wf = build_img2img_workflow(
            "img.png", "cat", sampler="dpmpp_2m", scheduler="karras", seed=42
        )
        assert wf["6"]["inputs"]["sampler_name"] == "dpmpp_2m"
        assert wf["6"]["inputs"]["scheduler"] == "karras"

    def test_output_prefix(self):
        wf = build_img2img_workflow("img.png", "cat", seed=42)
        assert wf["8"]["inputs"]["filename_prefix"] == "blender_pipeline"

    def test_node_connections(self):
        """Verify the node graph is wired correctly."""
        wf = build_img2img_workflow("img.png", "cat", seed=42)
        # VAEEncode takes pixels from LoadImage and vae from checkpoint
        assert wf["3"]["inputs"]["pixels"] == ["2", 0]
        assert wf["3"]["inputs"]["vae"] == ["1", 2]
        # KSampler takes model, positive, negative, latent
        assert wf["6"]["inputs"]["model"] == ["1", 0]
        assert wf["6"]["inputs"]["positive"] == ["4", 0]
        assert wf["6"]["inputs"]["negative"] == ["5", 0]
        assert wf["6"]["inputs"]["latent_image"] == ["3", 0]
        # VAEDecode takes samples from KSampler
        assert wf["7"]["inputs"]["samples"] == ["6", 0]
        # SaveImage takes images from VAEDecode
        assert wf["8"]["inputs"]["images"] == ["7", 0]


class TestTxt2ImgWorkflow:
    def test_basic_structure(self):
        wf = build_txt2img_workflow("a dog", seed=42)
        assert "1" in wf  # CheckpointLoaderSimple
        assert "2" in wf  # EmptyLatentImage
        assert "3" in wf  # Positive CLIP
        assert "4" in wf  # Negative CLIP
        assert "5" in wf  # KSampler
        assert "6" in wf  # VAEDecode
        assert "7" in wf  # SaveImage

    def test_no_load_image_node(self):
        """txt2img should NOT have a LoadImage node."""
        wf = build_txt2img_workflow("a dog", seed=42)
        for node_id, node in wf.items():
            assert node["class_type"] != "LoadImage"

    def test_dimensions_set(self):
        wf = build_txt2img_workflow("a dog", width=768, height=512, seed=42)
        assert wf["2"]["inputs"]["width"] == 768
        assert wf["2"]["inputs"]["height"] == 512
        assert wf["2"]["class_type"] == "EmptyLatentImage"

    def test_prompt_set(self):
        wf = build_txt2img_workflow("a beautiful dog", seed=42)
        assert wf["3"]["inputs"]["text"] == "a beautiful dog"

    def test_denoise_always_1(self):
        """txt2img should always denoise fully."""
        wf = build_txt2img_workflow("a dog", seed=42)
        assert wf["5"]["inputs"]["denoise"] == 1.0

    def test_node_connections(self):
        wf = build_txt2img_workflow("a dog", seed=42)
        # KSampler takes latent from EmptyLatentImage
        assert wf["5"]["inputs"]["latent_image"] == ["2", 0]
        assert wf["5"]["inputs"]["model"] == ["1", 0]
        assert wf["5"]["inputs"]["positive"] == ["3", 0]
        assert wf["5"]["inputs"]["negative"] == ["4", 0]


# =============================================================================
# COMFYUI CLIENT TESTS (mocked HTTP)
# =============================================================================


class MockComfyUIHandler(BaseHTTPRequestHandler):
    """Mock HTTP handler simulating ComfyUI's API."""

    def log_message(self, format, *args):
        pass  # Suppress log output during tests

    def do_GET(self):
        if self.path == "/system_stats":
            self._json_response({"system": {"vram": {"total": 8589934592, "free": 4294967296}}})
        elif self.path.startswith("/history/"):
            prompt_id = self.path.split("/")[-1]
            if prompt_id == "completed_job":
                self._json_response({
                    "completed_job": {
                        "status": {"status_str": "success"},
                        "outputs": {
                            "8": {
                                "images": [
                                    {"filename": "output_001.png", "subfolder": "", "type": "output"}
                                ]
                            }
                        },
                    }
                })
            elif prompt_id == "pending_job":
                self._json_response({})
            elif prompt_id == "error_job":
                self._json_response({
                    "error_job": {
                        "status": {
                            "status_str": "error",
                            "messages": ["Node 6: Model not found"],
                        },
                        "outputs": {},
                    }
                })
            else:
                self._json_response({})
        elif self.path.startswith("/view?"):
            # Return fake image bytes
            self._raw_response(b"\x89PNG\r\n\x1a\n" + b"\x00" * 100, "image/png")
        elif self.path.startswith("/object_info/CheckpointLoaderSimple"):
            self._json_response({
                "CheckpointLoaderSimple": {
                    "input": {
                        "required": {
                            "ckpt_name": [["v1-5-pruned-emaonly.ckpt", "dreamshaper_8.safetensors"]]
                        }
                    }
                }
            })
        else:
            self.send_error(404)

    def do_POST(self):
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length)

        if self.path == "/prompt":
            data = json.loads(body)
            assert "prompt" in data
            self._json_response({"prompt_id": "test_prompt_123"})
        elif self.path == "/upload/image":
            # Multipart upload — just return success
            self._json_response({"name": "uploaded_image.png", "subfolder": "", "type": "input"})
        elif self.path == "/interrupt":
            self._json_response({})
        else:
            self.send_error(404)

    def _json_response(self, data, status=200):
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        body = json.dumps(data).encode("utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _raw_response(self, data, content_type, status=200):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


@pytest.fixture(scope="module")
def mock_comfyui_server():
    """Start a mock ComfyUI HTTP server for testing."""
    server = HTTPServer(("127.0.0.1", 0), MockComfyUIHandler)
    port = server.server_address[1]
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{port}"
    server.shutdown()


@pytest.fixture
def client(mock_comfyui_server):
    return ComfyUIDirectClient(base_url=mock_comfyui_server)


class TestComfyUIDirectClient:
    def test_check_connection(self, client):
        ok, data = client.check_connection()
        assert ok is True
        assert "system" in data
        assert data["system"]["vram"]["total"] == 8589934592

    def test_check_connection_failure(self):
        bad_client = ComfyUIDirectClient("http://127.0.0.1:1")
        ok, data = bad_client.check_connection()
        assert ok is False
        assert "error" in data

    def test_queue_prompt(self, client):
        wf = build_txt2img_workflow("test", seed=42)
        ok, data = client.queue_prompt(wf)
        assert ok is True
        assert data["prompt_id"] == "test_prompt_123"

    def test_get_job_status_pending(self, client):
        ok, data = client.get_job_status("pending_job")
        assert ok is True
        assert data["status"] == "pending"

    def test_get_job_status_completed(self, client):
        ok, data = client.get_job_status("completed_job")
        assert ok is True
        assert data["status"] == "completed"
        assert data["outputs"] is not None

    def test_get_job_status_error(self, client):
        ok, data = client.get_job_status("error_job")
        assert ok is True
        assert data["status"] == "error"
        assert "Model not found" in data["error"]

    def test_upload_image(self, client):
        # Create a temp image file
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            f.write(b"\x89PNG\r\n\x1a\n" + b"\x00" * 100)
            filepath = f.name
        try:
            ok, data = client.upload_image(filepath)
            assert ok is True
            assert data["name"] == "uploaded_image.png"
        finally:
            os.unlink(filepath)

    def test_download_image(self, client):
        ok, data = client.download_image("output_001.png")
        assert ok is True
        assert isinstance(data, bytes)
        assert data[:4] == b"\x89PNG"

    def test_download_image_to_file(self, client):
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            output_path = f.name
        try:
            ok, result = client.download_image_to_file("output_001.png", output_path)
            assert ok is True
            assert os.path.exists(output_path)
            with open(output_path, "rb") as f:
                assert f.read()[:4] == b"\x89PNG"
        finally:
            os.unlink(output_path)

    def test_get_checkpoints(self, client):
        ok, data = client.get_checkpoints()
        assert ok is True
        assert "v1-5-pruned-emaonly.ckpt" in data
        assert "dreamshaper_8.safetensors" in data

    def test_interrupt(self, client):
        ok, data = client.interrupt()
        assert ok is True

    def test_extract_output_images(self):
        outputs = {
            "8": {
                "images": [
                    {"filename": "out1.png", "subfolder": "", "type": "output"},
                    {"filename": "out2.png", "subfolder": "sub", "type": "output"},
                ]
            },
            "9": {"text": ["some text"]},  # Non-image output
        }
        images = ComfyUIDirectClient.extract_output_images(outputs)
        assert len(images) == 2
        assert images[0]["filename"] == "out1.png"
        assert images[1]["subfolder"] == "sub"

    def test_extract_output_images_empty(self):
        images = ComfyUIDirectClient.extract_output_images({})
        assert images == []


class TestClientSingleton:
    def test_get_client_creates_new(self):
        from comfyui_client import get_comfyui_client

        c = get_comfyui_client("http://localhost:9999")
        assert c.base_url == "http://localhost:9999"

    def test_get_client_reuses(self):
        from comfyui_client import get_comfyui_client

        c1 = get_comfyui_client("http://localhost:9998")
        c2 = get_comfyui_client("http://localhost:9998")
        assert c1 is c2


# =============================================================================
# INTEGRATION: Workflow → Client round-trip
# =============================================================================


class TestPipelineRoundTrip:
    """Test that workflows built by the builder can be submitted to the mock server."""

    def test_img2img_round_trip(self, client):
        wf = build_img2img_workflow("test.png", "a painting", seed=42)
        ok, data = client.queue_prompt(wf)
        assert ok is True
        assert "prompt_id" in data

    def test_txt2img_round_trip(self, client):
        wf = build_txt2img_workflow("a landscape", seed=42)
        ok, data = client.queue_prompt(wf)
        assert ok is True
        assert "prompt_id" in data

    def test_full_pipeline_flow(self, client):
        """Simulate the full pipeline: upload → build workflow → queue → poll → download."""
        # 1. Upload (mock)
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            f.write(b"\x89PNG\r\n\x1a\n" + b"\x00" * 100)
            filepath = f.name
        try:
            ok, upload = client.upload_image(filepath)
            assert ok
            image_name = upload["name"]

            # 2. Build workflow
            wf = build_img2img_workflow(image_name, "oil painting style", seed=42)

            # 3. Queue
            ok, queue = client.queue_prompt(wf)
            assert ok
            prompt_id = queue["prompt_id"]

            # 4. Poll (use completed_job for instant completion)
            ok, status = client.get_job_status("completed_job")
            assert ok
            assert status["status"] == "completed"

            # 5. Extract and download
            images = client.extract_output_images(status["outputs"])
            assert len(images) > 0

            with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
                output_path = f.name
            ok, path = client.download_image_to_file(
                images[0]["filename"], output_path,
                subfolder=images[0]["subfolder"],
                folder_type=images[0]["type"],
            )
            assert ok
            assert os.path.exists(output_path)
            os.unlink(output_path)
        finally:
            os.unlink(filepath)
