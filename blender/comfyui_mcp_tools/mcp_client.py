"""Minimal MCP client for streamable-http transport.

Implements just enough of the MCP protocol to call tools on the ComfyUI MCP server.
Uses only urllib (no pip dependencies) per Blender addon constraints.

Protocol: MCP streamable-http (JSON-RPC 2.0 over HTTP with session management).
Server endpoint: POST http://{host}:{port}/mcp
"""

import json
import threading
import urllib.error
import urllib.request


class MCPClientError(Exception):
    """Error communicating with the MCP server."""


class MCPClient:
    """Minimal MCP client that connects to a streamable-http MCP server.

    Usage:
        client = MCPClient("127.0.0.1", 9000)
        ok, result = client.initialize()
        ok, result = client.call_tool("health_check", {})
        ok, result = client.call_tool("generate_image", {"prompt": "a cat"})
    """

    def __init__(self, host: str = "127.0.0.1", port: int = 9000, timeout: int = 300):
        self.base_url = f"http://{host}:{port}/mcp"
        self.timeout = timeout
        self.session_id = None
        self._request_id = 0
        self._lock = threading.Lock()

    def _next_id(self) -> int:
        with self._lock:
            self._request_id += 1
            return self._request_id

    def _post(self, body: dict, timeout: int | None = None) -> tuple[int, dict, dict]:
        """Send a JSON-RPC request to the MCP server.

        Returns (status_code, response_json, response_headers).
        """
        data = json.dumps(body).encode("utf-8")
        req = urllib.request.Request(
            self.base_url,
            data=data,
            method="POST",
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json, text/event-stream",
            },
        )
        if self.session_id:
            req.add_header("Mcp-Session-Id", self.session_id)

        effective_timeout = timeout if timeout is not None else self.timeout
        try:
            with urllib.request.urlopen(req, timeout=effective_timeout) as resp:
                status = resp.status
                headers = {k.lower(): v for k, v in resp.getheaders()}
                raw = resp.read()

                content_type = headers.get("content-type", "")
                if "text/event-stream" in content_type:
                    # Parse SSE: extract the last JSON data event
                    return status, self._parse_sse(raw.decode("utf-8")), headers
                else:
                    return status, json.loads(raw) if raw else {}, headers
        except urllib.error.HTTPError as e:
            body_text = ""
            try:
                body_text = e.read().decode("utf-8", errors="replace")
            except Exception:
                pass
            raise MCPClientError(
                f"MCP server returned HTTP {e.code}: {e.reason}. {body_text}"
            ) from e
        except urllib.error.URLError as e:
            raise MCPClientError(
                f"Cannot connect to MCP server at {self.base_url}: {e.reason}"
            ) from e
        except Exception as e:
            raise MCPClientError(f"MCP request failed: {e}") from e

    @staticmethod
    def _parse_sse(text: str) -> dict:
        """Parse Server-Sent Events stream and return the last JSON data payload."""
        last_data = None
        for line in text.splitlines():
            if line.startswith("data: "):
                try:
                    last_data = json.loads(line[6:])
                except json.JSONDecodeError:
                    pass
        return last_data or {}

    def initialize(self) -> tuple[bool, dict]:
        """Initialize the MCP session. Must be called before calling tools.

        Returns (success, server_info).
        """
        body = {
            "jsonrpc": "2.0",
            "id": self._next_id(),
            "method": "initialize",
            "params": {
                "protocolVersion": "2025-03-26",
                "capabilities": {},
                "clientInfo": {"name": "blender-comfyui-mcp", "version": "1.0.0"},
            },
        }
        try:
            status, resp, headers = self._post(body, timeout=15)
        except MCPClientError:
            raise
        except Exception as e:
            raise MCPClientError(f"Failed to initialize MCP session: {e}") from e

        # Store session ID from response header
        session_id = headers.get("mcp-session-id")
        if session_id:
            self.session_id = session_id

        if "error" in resp:
            return False, resp["error"]

        # Send initialized notification (no response expected, but protocol requires it)
        notif = {
            "jsonrpc": "2.0",
            "method": "notifications/initialized",
        }
        try:
            self._post(notif, timeout=5)
        except MCPClientError:
            pass  # Notification delivery is best-effort

        return True, resp.get("result", resp)

    def call_tool(
        self, tool_name: str, arguments: dict | None = None, timeout: int | None = None
    ) -> tuple[bool, dict]:
        """Call an MCP tool by name.

        Args:
            tool_name: The tool name (e.g. "health_check", "generate_image").
            arguments: Tool arguments dict.
            timeout: Override timeout for this call (seconds). Useful for long generations.

        Returns (success, result_dict).
        """
        if not self.session_id:
            ok, info = self.initialize()
            if not ok:
                return False, {"error": f"Failed to initialize session: {info}"}

        body = {
            "jsonrpc": "2.0",
            "id": self._next_id(),
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": arguments or {},
            },
        }
        try:
            status, resp, headers = self._post(body, timeout=timeout)
        except MCPClientError:
            raise

        if "error" in resp:
            return False, resp["error"]

        result = resp.get("result", resp)
        # MCP tool results have a "content" array with text/image items
        return True, result

    def list_tools(self) -> tuple[bool, list]:
        """List available MCP tools.

        Returns (success, tools_list).
        """
        if not self.session_id:
            ok, info = self.initialize()
            if not ok:
                return False, []

        body = {
            "jsonrpc": "2.0",
            "id": self._next_id(),
            "method": "tools/list",
            "params": {},
        }
        try:
            status, resp, headers = self._post(body, timeout=15)
        except MCPClientError:
            raise

        if "error" in resp:
            return False, []

        result = resp.get("result", resp)
        return True, result.get("tools", [])

    def close(self):
        """Close the session (best-effort DELETE)."""
        if not self.session_id:
            return
        try:
            req = urllib.request.Request(
                self.base_url,
                method="DELETE",
                headers={"Mcp-Session-Id": self.session_id},
            )
            with urllib.request.urlopen(req, timeout=5):
                pass
        except Exception:
            pass
        self.session_id = None


# ---------------------------------------------------------------------------
# Helper to parse MCP tool responses
# ---------------------------------------------------------------------------


def extract_text_content(result: dict) -> dict:
    """Extract parsed JSON from MCP tool result content array.

    MCP tools return: {"content": [{"type": "text", "text": "{...json...}"}]}
    This extracts and parses the first text content item.
    """
    content = result.get("content", [])
    for item in content:
        if isinstance(item, dict) and item.get("type") == "text":
            try:
                return json.loads(item["text"])
            except (json.JSONDecodeError, TypeError):
                return {"raw_text": item.get("text", "")}
    # Fallback: result might already be a plain dict (non-MCP format)
    return result


# ---------------------------------------------------------------------------
# Singleton for shared access across operators
# ---------------------------------------------------------------------------

_client_instance = None
_client_lock = threading.Lock()


def get_mcp_client(host: str = "127.0.0.1", port: int = 9000) -> MCPClient:
    """Get or create the shared MCP client singleton."""
    global _client_instance
    with _client_lock:
        if _client_instance is None:
            _client_instance = MCPClient(host, port)
        elif _client_instance.base_url != f"http://{host}:{port}/mcp":
            # Settings changed, recreate
            _client_instance.close()
            _client_instance = MCPClient(host, port)
        return _client_instance


def reset_mcp_client():
    """Reset the shared MCP client (e.g. on connection failure)."""
    global _client_instance
    with _client_lock:
        if _client_instance is not None:
            _client_instance.close()
            _client_instance = None
