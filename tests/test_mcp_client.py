"""Tests for the MCP HTTP client and MCP Blender operators.

Tests the non-Blender parts (no bpy dependency):
- MCPClient protocol handling (mocked HTTP server)
- Session management
- Tool calls
- SSE response parsing
- Error handling
- Singleton management
"""

import json
import os
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer
from threading import Thread

import pytest

# Add blender addon to path so we can import without bpy
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "blender", "comfyui_mcp_tools"))

from mcp_client import MCPClient, MCPClientError, get_mcp_client, reset_mcp_client


# =============================================================================
# MOCK MCP SERVER
# =============================================================================

class MockMCPHandler(BaseHTTPRequestHandler):
    """Mock MCP server implementing streamable-http protocol."""

    session_counter = 0
    tool_responses = {}  # Override per-test

    def log_message(self, format, *args):
        pass  # Suppress log output during tests

    def do_POST(self):
        if self.path != "/mcp":
            self.send_error(404)
            return

        content_length = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(content_length)) if content_length else {}

        method = body.get("method", "")
        request_id = body.get("id")

        if method == "initialize":
            MockMCPHandler.session_counter += 1
            session_id = f"test-session-{MockMCPHandler.session_counter}"
            response = {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "protocolVersion": "2025-03-26",
                    "capabilities": {"tools": {}},
                    "serverInfo": {"name": "test-mcp-server", "version": "1.0.0"},
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

            # Check session
            session_id = self.headers.get("Mcp-Session-Id", "")
            if not session_id:
                self.send_response(400)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                error = {"jsonrpc": "2.0", "id": request_id, "error": {"code": -1, "message": "No session"}}
                self.wfile.write(json.dumps(error).encode())
                return

            # Look up tool response
            if tool_name in MockMCPHandler.tool_responses:
                tool_result = MockMCPHandler.tool_responses[tool_name]
                if callable(tool_result):
                    tool_result = tool_result(tool_args)
            elif tool_name == "health_check":
                tool_result = {
                    "content": [
                        {
                            "type": "text",
                            "text": json.dumps({
                                "status": "healthy",
                                "models_available": 3,
                                "workflows_available": 10,
                            }),
                        }
                    ]
                }
            elif tool_name == "list_models":
                tool_result = {
                    "content": [
                        {
                            "type": "text",
                            "text": json.dumps({
                                "models": ["v1-5-pruned-emaonly.ckpt", "dreamshaper_8.safetensors"]
                            }),
                        }
                    ]
                }
            elif tool_name == "error_tool":
                response = {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "error": {"code": -32000, "message": "Tool execution failed"},
                }
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps(response).encode())
                return
            else:
                tool_result = {
                    "content": [{"type": "text", "text": json.dumps({"tool": tool_name, "args": tool_args})}]
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
                        {"name": "upscale_image", "description": "Upscale an image"},
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


@pytest.fixture(scope="module")
def mock_mcp_server():
    """Start a mock MCP server on a random port."""
    server = HTTPServer(("127.0.0.1", 0), MockMCPHandler)
    port = server.server_address[1]
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield port
    server.shutdown()


@pytest.fixture(autouse=True)
def reset_mock_state():
    """Reset mock state between tests."""
    MockMCPHandler.tool_responses = {}
    reset_mcp_client()
    yield
    reset_mcp_client()


# =============================================================================
# MCPClient PROTOCOL TESTS
# =============================================================================


class TestMCPClientInitialize:
    def test_initialize_success(self, mock_mcp_server):
        client = MCPClient("127.0.0.1", mock_mcp_server)
        ok, info = client.initialize()
        assert ok is True
        assert client.session_id is not None
        assert client.session_id.startswith("test-session-")

    def test_initialize_sets_server_info(self, mock_mcp_server):
        client = MCPClient("127.0.0.1", mock_mcp_server)
        ok, info = client.initialize()
        assert info.get("serverInfo", {}).get("name") == "test-mcp-server"

    def test_initialize_connection_refused(self):
        client = MCPClient("127.0.0.1", 1)  # Port 1 should be unreachable
        with pytest.raises(MCPClientError, match="Cannot connect"):
            client.initialize()

    def test_session_id_persists(self, mock_mcp_server):
        client = MCPClient("127.0.0.1", mock_mcp_server)
        client.initialize()
        session1 = client.session_id
        # Second initialize gets a new session
        client.session_id = None
        client.initialize()
        session2 = client.session_id
        assert session1 != session2


class TestMCPClientCallTool:
    def test_call_tool_success(self, mock_mcp_server):
        client = MCPClient("127.0.0.1", mock_mcp_server)
        client.initialize()
        ok, result = client.call_tool("health_check", {})
        assert ok is True
        assert "content" in result

    def test_call_tool_auto_initializes(self, mock_mcp_server):
        client = MCPClient("127.0.0.1", mock_mcp_server)
        # Don't call initialize() — call_tool should do it
        ok, result = client.call_tool("health_check", {})
        assert ok is True
        assert client.session_id is not None

    def test_call_tool_passes_arguments(self, mock_mcp_server):
        client = MCPClient("127.0.0.1", mock_mcp_server)
        client.initialize()
        ok, result = client.call_tool("some_tool", {"key": "value"})
        assert ok is True
        content = result.get("content", [])
        data = json.loads(content[0]["text"])
        assert data["args"]["key"] == "value"

    def test_call_tool_error_response(self, mock_mcp_server):
        client = MCPClient("127.0.0.1", mock_mcp_server)
        client.initialize()
        ok, result = client.call_tool("error_tool", {})
        assert ok is False
        assert "message" in result

    def test_call_tool_with_timeout(self, mock_mcp_server):
        client = MCPClient("127.0.0.1", mock_mcp_server)
        client.initialize()
        ok, result = client.call_tool("health_check", {}, timeout=5)
        assert ok is True

    def test_call_tool_custom_response(self, mock_mcp_server):
        MockMCPHandler.tool_responses["custom_tool"] = {
            "content": [
                {
                    "type": "text",
                    "text": json.dumps({"asset_id": "abc-123", "status": "done"}),
                }
            ]
        }
        client = MCPClient("127.0.0.1", mock_mcp_server)
        client.initialize()
        ok, result = client.call_tool("custom_tool", {})
        assert ok is True
        data = json.loads(result["content"][0]["text"])
        assert data["asset_id"] == "abc-123"

    def test_call_tool_callable_response(self, mock_mcp_server):
        def dynamic_response(args):
            return {
                "content": [
                    {"type": "text", "text": json.dumps({"echo": args.get("msg", "")})}
                ]
            }

        MockMCPHandler.tool_responses["echo"] = dynamic_response
        client = MCPClient("127.0.0.1", mock_mcp_server)
        client.initialize()
        ok, result = client.call_tool("echo", {"msg": "hello"})
        assert ok is True
        data = json.loads(result["content"][0]["text"])
        assert data["echo"] == "hello"


class TestMCPClientListTools:
    def test_list_tools(self, mock_mcp_server):
        client = MCPClient("127.0.0.1", mock_mcp_server)
        client.initialize()
        ok, tools = client.list_tools()
        assert ok is True
        assert len(tools) == 3
        names = [t["name"] for t in tools]
        assert "health_check" in names
        assert "generate_image" in names
        assert "upscale_image" in names

    def test_list_tools_auto_initializes(self, mock_mcp_server):
        client = MCPClient("127.0.0.1", mock_mcp_server)
        ok, tools = client.list_tools()
        assert ok is True
        assert client.session_id is not None


class TestMCPClientClose:
    def test_close_clears_session(self, mock_mcp_server):
        client = MCPClient("127.0.0.1", mock_mcp_server)
        client.initialize()
        assert client.session_id is not None
        client.close()
        assert client.session_id is None

    def test_close_without_session(self, mock_mcp_server):
        client = MCPClient("127.0.0.1", mock_mcp_server)
        client.close()  # Should not raise


# =============================================================================
# SSE PARSING TESTS
# =============================================================================


class TestSSEParsing:
    def test_parse_single_event(self):
        sse = 'data: {"jsonrpc":"2.0","id":1,"result":{"hello":"world"}}\n\n'
        result = MCPClient._parse_sse(sse)
        assert result["result"]["hello"] == "world"

    def test_parse_multiple_events_returns_last(self):
        sse = (
            'data: {"jsonrpc":"2.0","id":1,"result":"first"}\n\n'
            'data: {"jsonrpc":"2.0","id":2,"result":"second"}\n\n'
        )
        result = MCPClient._parse_sse(sse)
        assert result["result"] == "second"

    def test_parse_empty_sse(self):
        result = MCPClient._parse_sse("")
        assert result == {}

    def test_parse_non_data_lines_ignored(self):
        sse = "event: message\ndata: {\"ok\":true}\nid: 1\n\n"
        result = MCPClient._parse_sse(sse)
        assert result["ok"] is True

    def test_parse_invalid_json_skipped(self):
        sse = "data: not-json\ndata: {\"valid\":true}\n\n"
        result = MCPClient._parse_sse(sse)
        assert result["valid"] is True


# =============================================================================
# SINGLETON MANAGEMENT TESTS
# =============================================================================


class TestMCPClientSingleton:
    def test_get_returns_same_instance(self):
        c1 = get_mcp_client("127.0.0.1", 9000)
        c2 = get_mcp_client("127.0.0.1", 9000)
        assert c1 is c2

    def test_get_recreates_on_config_change(self):
        c1 = get_mcp_client("127.0.0.1", 9000)
        c2 = get_mcp_client("127.0.0.1", 9001)
        assert c1 is not c2

    def test_reset_clears_singleton(self):
        c1 = get_mcp_client("127.0.0.1", 9000)
        reset_mcp_client()
        c2 = get_mcp_client("127.0.0.1", 9000)
        assert c1 is not c2


# =============================================================================
# EXTRACT TEXT CONTENT HELPER TESTS
# =============================================================================


class TestExtractTextContent:
    """Test the extract_text_content helper from operators_mcp."""

    def test_extracts_json_from_content_array(self):
        # Import from operators_mcp module (already on sys.path)
        from mcp_client import extract_text_content

        result = {
            "content": [
                {"type": "text", "text": json.dumps({"asset_id": "abc", "status": "done"})}
            ]
        }
        data = extract_text_content(result)
        assert data["asset_id"] == "abc"
        assert data["status"] == "done"

    def test_handles_non_json_text(self):
        from mcp_client import extract_text_content

        result = {"content": [{"type": "text", "text": "just plain text"}]}
        data = extract_text_content(result)
        assert data["raw_text"] == "just plain text"

    def test_handles_empty_content(self):
        from mcp_client import extract_text_content

        result = {"content": []}
        data = extract_text_content(result)
        assert data == {"content": []}  # Falls through to return original result

    def test_handles_plain_dict(self):
        from mcp_client import extract_text_content

        result = {"asset_id": "xyz", "filename": "test.png"}
        data = extract_text_content(result)
        assert data["asset_id"] == "xyz"

    def test_skips_image_content(self):
        from mcp_client import extract_text_content

        result = {
            "content": [
                {"type": "image", "data": "base64..."},
                {"type": "text", "text": json.dumps({"found": True})},
            ]
        }
        data = extract_text_content(result)
        assert data["found"] is True


# =============================================================================
# INTEGRATION-STYLE TESTS (mock server, full round-trip)
# =============================================================================


class TestMCPRoundTrip:
    """Full round-trip tests: initialize → call tool → parse result."""

    def test_health_check_round_trip(self, mock_mcp_server):
        client = MCPClient("127.0.0.1", mock_mcp_server)
        from mcp_client import extract_text_content

        ok, result = client.call_tool("health_check", {})
        assert ok
        data = extract_text_content(result)
        assert data["status"] == "healthy"
        assert data["models_available"] == 3

    def test_list_models_round_trip(self, mock_mcp_server):
        client = MCPClient("127.0.0.1", mock_mcp_server)
        from mcp_client import extract_text_content

        ok, result = client.call_tool("list_models", {})
        assert ok
        data = extract_text_content(result)
        models = data["models"]
        assert "v1-5-pruned-emaonly.ckpt" in models

    def test_generate_image_round_trip(self, mock_mcp_server):
        MockMCPHandler.tool_responses["generate_image"] = {
            "content": [
                {
                    "type": "text",
                    "text": json.dumps({
                        "asset_id": "gen-001",
                        "filename": "ComfyUI_00001_.png",
                        "subfolder": "",
                        "folder_type": "output",
                        "width": 512,
                        "height": 512,
                    }),
                }
            ]
        }
        client = MCPClient("127.0.0.1", mock_mcp_server)
        from mcp_client import extract_text_content

        ok, result = client.call_tool("generate_image", {"prompt": "a cat", "steps": 20})
        assert ok
        data = extract_text_content(result)
        assert data["asset_id"] == "gen-001"
        assert data["filename"] == "ComfyUI_00001_.png"

    def test_upscale_round_trip(self, mock_mcp_server):
        MockMCPHandler.tool_responses["upscale_image"] = {
            "content": [
                {
                    "type": "text",
                    "text": json.dumps({
                        "asset_id": "up-001",
                        "filename": "upscaled.png",
                        "width": 2048,
                        "height": 2048,
                    }),
                }
            ]
        }
        client = MCPClient("127.0.0.1", mock_mcp_server)
        from mcp_client import extract_text_content

        ok, result = client.call_tool("upscale_image", {"asset_id": "gen-001", "scale_factor": 4})
        assert ok
        data = extract_text_content(result)
        assert data["asset_id"] == "up-001"
        assert data["width"] == 2048

    def test_variations_round_trip(self, mock_mcp_server):
        MockMCPHandler.tool_responses["generate_variations"] = {
            "content": [
                {
                    "type": "text",
                    "text": json.dumps({
                        "variations": [
                            {"asset_id": "var-001", "filename": "var1.png"},
                            {"asset_id": "var-002", "filename": "var2.png"},
                            {"asset_id": "var-003", "filename": "var3.png"},
                        ]
                    }),
                }
            ]
        }
        client = MCPClient("127.0.0.1", mock_mcp_server)
        from mcp_client import extract_text_content

        ok, result = client.call_tool(
            "generate_variations",
            {"asset_id": "gen-001", "num_variations": 3, "variation_strength": 0.5},
        )
        assert ok
        data = extract_text_content(result)
        assert len(data["variations"]) == 3

    def test_style_presets_round_trip(self, mock_mcp_server):
        MockMCPHandler.tool_responses["list_style_presets"] = {
            "content": [
                {
                    "type": "text",
                    "text": json.dumps({
                        "presets": [
                            {"id": "anime", "name": "Anime Style"},
                            {"id": "photorealistic", "name": "Photorealistic"},
                        ]
                    }),
                }
            ]
        }
        client = MCPClient("127.0.0.1", mock_mcp_server)
        from mcp_client import extract_text_content

        ok, result = client.call_tool("list_style_presets", {})
        assert ok
        data = extract_text_content(result)
        assert len(data["presets"]) == 2

    def test_apply_style_round_trip(self, mock_mcp_server):
        MockMCPHandler.tool_responses["apply_style_preset"] = {
            "content": [
                {
                    "type": "text",
                    "text": json.dumps({
                        "styled_prompt": "a cat, anime style, vibrant colors",
                        "styled_negative_prompt": "photorealistic, 3d render",
                    }),
                }
            ]
        }
        client = MCPClient("127.0.0.1", mock_mcp_server)
        from mcp_client import extract_text_content

        ok, result = client.call_tool(
            "apply_style_preset", {"preset_id": "anime", "prompt": "a cat"}
        )
        assert ok
        data = extract_text_content(result)
        assert "anime" in data["styled_prompt"]

    def test_list_workflows_round_trip(self, mock_mcp_server):
        MockMCPHandler.tool_responses["list_workflows"] = {
            "content": [
                {
                    "type": "text",
                    "text": json.dumps({
                        "workflows": [
                            {"id": "generate_image", "name": "Generate Image"},
                            {"id": "img2img", "name": "Image to Image"},
                        ]
                    }),
                }
            ]
        }
        client = MCPClient("127.0.0.1", mock_mcp_server)
        from mcp_client import extract_text_content

        ok, result = client.call_tool("list_workflows", {})
        assert ok
        data = extract_text_content(result)
        assert len(data["workflows"]) == 2


# =============================================================================
# ERROR HANDLING TESTS
# =============================================================================


class TestMCPErrorHandling:
    def test_connection_refused_raises(self):
        client = MCPClient("127.0.0.1", 1)
        with pytest.raises(MCPClientError):
            client.call_tool("anything", {})

    def test_tool_error_returns_false(self, mock_mcp_server):
        client = MCPClient("127.0.0.1", mock_mcp_server)
        client.initialize()
        ok, result = client.call_tool("error_tool", {})
        assert ok is False

    def test_invalid_host_raises(self):
        client = MCPClient("999.999.999.999", 9999, timeout=2)
        with pytest.raises(MCPClientError):
            client.initialize()
