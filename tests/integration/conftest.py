"""Shared fixtures for Blender-ComfyUI integration tests.

Provides two test modes:
- Mocked: Mock HTTP servers simulate ComfyUI and MCP endpoints (no services needed)
- Live: Real ComfyUI at localhost:8188 (@pytest.mark.integration)
"""

import json
import os
import sys
import tempfile
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from threading import Thread

import pytest

# ---------------------------------------------------------------------------
# Path setup — make Blender addon modules importable without bpy
# ---------------------------------------------------------------------------
REPO_ROOT = Path(__file__).parent.parent.parent
BLENDER_ADDON_DIR = REPO_ROOT / "blender" / "comfyui_mcp_tools"
WORKFLOWS_DIR = REPO_ROOT / "workflows" / "mcp"

sys.path.insert(0, str(BLENDER_ADDON_DIR))


# ---------------------------------------------------------------------------
# Mock ComfyUI server — simulates /prompt, /history, /upload/image, /view, etc.
# ---------------------------------------------------------------------------
class MockComfyUIHandler(BaseHTTPRequestHandler):
    """Full mock of ComfyUI HTTP API for integration testing."""

    # Class-level state that tests can override
    job_counter = 0
    queued_jobs = {}  # prompt_id -> workflow
    completed_jobs = {}  # prompt_id -> output structure

    def log_message(self, format, *args):
        pass

    def do_GET(self):
        if self.path == "/system_stats":
            self._json_response({
                "system": {
                    "os": "nt",
                    "python_version": "3.12.0",
                    "vram": {"total": 8589934592, "free": 4294967296},
                }
            })
        elif self.path.startswith("/history/"):
            prompt_id = self.path.split("/")[-1]
            if prompt_id in MockComfyUIHandler.completed_jobs:
                self._json_response({
                    prompt_id: MockComfyUIHandler.completed_jobs[prompt_id]
                })
            elif prompt_id in MockComfyUIHandler.queued_jobs:
                self._json_response({})  # Still running
            else:
                self._json_response({})
        elif self.path.startswith("/view"):
            # Return a minimal valid PNG
            self._raw_response(
                b"\x89PNG\r\n\x1a\n" + b"\x00" * 100, "image/png"
            )
        elif self.path.startswith("/object_info/CheckpointLoaderSimple"):
            self._json_response({
                "CheckpointLoaderSimple": {
                    "input": {
                        "required": {
                            "ckpt_name": [[
                                "v1-5-pruned-emaonly.ckpt",
                                "dreamshaper_8.safetensors",
                            ]]
                        }
                    }
                }
            })
        elif self.path.startswith("/object_info/KSampler"):
            self._json_response({
                "KSampler": {
                    "input": {
                        "required": {
                            "sampler_name": [["euler", "euler_ancestral", "dpmpp_2m"]],
                            "scheduler": [["normal", "karras", "exponential"]],
                        }
                    }
                }
            })
        elif self.path == "/queue":
            self._json_response({"queue_running": [], "queue_pending": []})
        else:
            self.send_error(404)

    def do_POST(self):
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length)

        if self.path == "/prompt":
            data = json.loads(body)
            MockComfyUIHandler.job_counter += 1
            prompt_id = f"integration_test_{MockComfyUIHandler.job_counter}"
            MockComfyUIHandler.queued_jobs[prompt_id] = data.get("prompt", {})
            # Auto-complete the job with fake output
            MockComfyUIHandler.completed_jobs[prompt_id] = {
                "status": {"status_str": "success"},
                "outputs": {
                    "8": {
                        "images": [{
                            "filename": f"output_{MockComfyUIHandler.job_counter:05d}.png",
                            "subfolder": "",
                            "type": "output",
                        }]
                    }
                },
            }
            self._json_response({"prompt_id": prompt_id})
        elif self.path == "/upload/image":
            self._json_response({
                "name": "uploaded_render.png",
                "subfolder": "",
                "type": "input",
            })
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


# ---------------------------------------------------------------------------
# Mock MCP server — simulates streamable-http MCP protocol
# ---------------------------------------------------------------------------
class MockMCPServerHandler(BaseHTTPRequestHandler):
    """Mock MCP server for integration testing Blender->MCP->ComfyUI pipeline."""

    session_counter = 0
    tool_responses = {}

    def log_message(self, format, *args):
        pass

    def do_POST(self):
        if self.path != "/mcp":
            self.send_error(404)
            return

        content_length = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(content_length)) if content_length else {}
        method = body.get("method", "")
        request_id = body.get("id")

        if method == "initialize":
            MockMCPServerHandler.session_counter += 1
            session_id = f"integration-session-{MockMCPServerHandler.session_counter}"
            response = {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "protocolVersion": "2025-03-26",
                    "capabilities": {"tools": {}},
                    "serverInfo": {"name": "test-comfyui-mcp", "version": "1.0.0"},
                },
            }
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Mcp-Session-Id", session_id)
            self.end_headers()
            self.wfile.write(json.dumps(response).encode())

        elif method == "notifications/initialized":
            self.send_response(202)
            self.end_headers()

        elif method == "tools/call":
            tool_name = body.get("params", {}).get("name", "")
            tool_args = body.get("params", {}).get("arguments", {})
            session_id = self.headers.get("Mcp-Session-Id", "")

            if not session_id:
                error = {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "error": {"code": -1, "message": "No session"},
                }
                self.send_response(400)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps(error).encode())
                return

            if tool_name in MockMCPServerHandler.tool_responses:
                tool_result = MockMCPServerHandler.tool_responses[tool_name]
                if callable(tool_result):
                    tool_result = tool_result(tool_args)
            elif tool_name == "health_check":
                tool_result = {
                    "content": [{"type": "text", "text": json.dumps({
                        "status": "healthy",
                        "comfyui_connected": True,
                        "models_available": 3,
                        "workflows_available": 12,
                    })}]
                }
            elif tool_name in (
                "generate_image", "blender_depth_guided",
                "blender_normal_texturing", "blender_pose_to_render",
            ):
                tool_result = {
                    "content": [{"type": "text", "text": json.dumps({
                        "asset_id": f"asset-{tool_name}-001",
                        "filename": f"ComfyUI_{tool_name}_00001_.png",
                        "subfolder": "",
                        "folder_type": "output",
                        "width": tool_args.get("width", 512),
                        "height": tool_args.get("height", 512),
                    })}]
                }
            else:
                tool_result = {
                    "content": [{"type": "text", "text": json.dumps({
                        "tool": tool_name, "args": tool_args,
                    })}]
                }

            response = {"jsonrpc": "2.0", "id": request_id, "result": tool_result}
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(response).encode())

        elif method == "tools/list":
            response = {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "tools": [
                        {"name": "health_check", "description": "Check server health"},
                        {"name": "generate_image", "description": "Generate an image"},
                        {"name": "blender_depth_guided", "description": "Depth-guided generation"},
                        {"name": "blender_normal_texturing", "description": "Normal map texturing"},
                        {"name": "blender_pose_to_render", "description": "Pose to render"},
                    ]
                },
            }
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(response).encode())

        else:
            self.send_response(200)
            self.end_headers()

    def do_DELETE(self):
        self.send_response(200)
        self.end_headers()


# ---------------------------------------------------------------------------
# Fixtures — mock servers
# ---------------------------------------------------------------------------
@pytest.fixture(scope="session")
def mock_comfyui_server():
    """Start a mock ComfyUI HTTP server for the entire test session."""
    server = HTTPServer(("127.0.0.1", 0), MockComfyUIHandler)
    port = server.server_address[1]
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{port}"
    server.shutdown()


@pytest.fixture(scope="session")
def mock_mcp_server():
    """Start a mock MCP HTTP server for the entire test session."""
    server = HTTPServer(("127.0.0.1", 0), MockMCPServerHandler)
    port = server.server_address[1]
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield port
    server.shutdown()


@pytest.fixture(autouse=True)
def reset_mock_state():
    """Reset mock state between tests."""
    MockComfyUIHandler.job_counter = 0
    MockComfyUIHandler.queued_jobs = {}
    MockComfyUIHandler.completed_jobs = {}
    MockMCPServerHandler.tool_responses = {}
    yield


@pytest.fixture
def mock_mcp_handler():
    """Expose MockMCPServerHandler class for tests that need to set custom responses."""
    return MockMCPServerHandler


# ---------------------------------------------------------------------------
# Fixtures — clients
# ---------------------------------------------------------------------------
@pytest.fixture
def comfyui_client(mock_comfyui_server):
    """ComfyUIDirectClient pointed at the mock server."""
    from comfyui_client import ComfyUIDirectClient

    return ComfyUIDirectClient(base_url=mock_comfyui_server)


@pytest.fixture
def mcp_client(mock_mcp_server):
    """MCPClient pointed at the mock MCP server."""
    from mcp_client import MCPClient, reset_mcp_client

    reset_mcp_client()
    client = MCPClient("127.0.0.1", mock_mcp_server)
    yield client
    reset_mcp_client()


# ---------------------------------------------------------------------------
# Fixtures — workflow manager
# ---------------------------------------------------------------------------
@pytest.fixture
def workflow_manager():
    """WorkflowManager pointing at the repo-root workflows/mcp/ directory."""
    from managers.workflow_manager import WorkflowManager

    return WorkflowManager(WORKFLOWS_DIR)


# ---------------------------------------------------------------------------
# Fixtures — sample data
# ---------------------------------------------------------------------------
@pytest.fixture
def sample_render_png(tmp_path):
    """Create a minimal fake PNG file simulating a Blender render."""
    png_path = tmp_path / "blender_render.png"
    # Minimal PNG header + IHDR chunk (1x1 pixel)
    png_path.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 100)
    return str(png_path)


@pytest.fixture
def sample_depth_png(tmp_path):
    """Create a minimal fake PNG file simulating a Blender depth pass."""
    png_path = tmp_path / "blender_depth.png"
    png_path.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 100)
    return str(png_path)


@pytest.fixture
def sample_normal_png(tmp_path):
    """Create a minimal fake PNG file simulating a Blender normal pass."""
    png_path = tmp_path / "blender_normal.png"
    png_path.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 100)
    return str(png_path)


@pytest.fixture
def sample_pose_png(tmp_path):
    """Create a minimal fake PNG file simulating a Blender pose visualization."""
    png_path = tmp_path / "blender_pose.png"
    png_path.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 100)
    return str(png_path)


# ---------------------------------------------------------------------------
# Fixtures — live ComfyUI (skips if unavailable)
# ---------------------------------------------------------------------------
@pytest.fixture
def live_comfyui_client():
    """ComfyUIDirectClient connected to real ComfyUI. Skips if unreachable."""
    from comfyui_client import ComfyUIDirectClient

    client = ComfyUIDirectClient("http://127.0.0.1:8188")
    ok, _ = client.check_connection()
    if not ok:
        pytest.skip("ComfyUI not running at localhost:8188")
    return client


@pytest.fixture
def live_sdk_client():
    """SDK ComfyUIClient connected to real ComfyUI. Skips if unreachable."""
    from comfyui_agent_sdk.client import ComfyUIClient

    client = ComfyUIClient(base_url="http://localhost:8188")
    if not client.is_available():
        pytest.skip("ComfyUI not available at localhost:8188")
    return client
