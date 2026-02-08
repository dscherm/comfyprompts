"""Real-time WebSocket progress monitoring for ComfyUI workflows."""

import json
import logging
import threading
import time
from typing import Any, Callable

logger = logging.getLogger(__name__)

try:
    import websocket

    _HAS_WEBSOCKET = True
except ImportError:
    _HAS_WEBSOCKET = False


class WebSocketMonitor:
    """Connects to ComfyUI's WebSocket for real-time execution progress.

    Progress events are delivered via callbacks. Each callback receives a dict::

        {
            "type": "start" | "progress" | "node_start" | "node_complete" | "complete" | "cached" | "error",
            "prompt_id": str,
            "node": str | None,
            "value": int | None,
            "max": int | None,
            "percent": float,
            "message": str,
        }
    """

    def __init__(self, base_url: str, client_id: str):
        self.base_url = base_url.rstrip("/")
        self.client_id = client_id

        self._ws: Any = None
        self._ws_thread: threading.Thread | None = None
        self._connected = False
        self._callbacks: list[Callable[[dict], None]] = []
        self._current_prompt_id: str | None = None
        self._node_progress: dict[str, dict] = {}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @property
    def available(self) -> bool:
        return _HAS_WEBSOCKET

    @property
    def connected(self) -> bool:
        return self._connected

    def add_callback(self, cb: Callable[[dict], None]) -> None:
        self._callbacks.append(cb)

    def remove_callback(self, cb: Callable[[dict], None]) -> None:
        if cb in self._callbacks:
            self._callbacks.remove(cb)

    def connect(self, timeout: float = 5.0) -> bool:
        if not _HAS_WEBSOCKET:
            logger.warning("websocket-client not installed; WebSocket unavailable")
            return False
        if self._connected:
            return True

        ws_url = self.base_url.replace("http://", "ws://").replace("https://", "wss://")
        ws_url = f"{ws_url}/ws?clientId={self.client_id}"

        def on_message(ws: Any, message: str) -> None:
            try:
                self._handle(json.loads(message))
            except json.JSONDecodeError:
                pass

        def on_error(ws: Any, error: Any) -> None:
            logger.error("WebSocket error: %s", error)
            self._connected = False

        def on_close(ws: Any, code: Any, msg: Any) -> None:
            self._connected = False

        def on_open(ws: Any) -> None:
            self._connected = True

        self._ws = websocket.WebSocketApp(
            ws_url,
            on_message=on_message,
            on_error=on_error,
            on_close=on_close,
            on_open=on_open,
        )
        self._ws_thread = threading.Thread(target=self._ws.run_forever, daemon=True)
        self._ws_thread.start()

        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if self._connected:
                return True
            time.sleep(0.1)
        return False

    def disconnect(self) -> None:
        if self._ws:
            self._ws.close()
            self._ws = None
        self._connected = False

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _emit(self, data: dict) -> None:
        for cb in self._callbacks:
            try:
                cb(data)
            except Exception as e:
                logger.error("Progress callback error: %s", e)

    def _handle(self, data: dict) -> None:
        msg_type = data.get("type", "")
        msg_data = data.get("data", {})

        if msg_type == "execution_start":
            pid = msg_data.get("prompt_id")
            self._current_prompt_id = pid
            self._node_progress = {}
            self._emit({"type": "start", "prompt_id": pid, "percent": 0, "message": "Starting execution..."})

        elif msg_type == "executing":
            node = msg_data.get("node")
            pid = msg_data.get("prompt_id")
            if node is None:
                self._emit({"type": "complete", "prompt_id": pid, "percent": 100, "message": "Execution complete!"})
            else:
                self._emit({
                    "type": "node_start", "prompt_id": pid, "node": node,
                    "percent": self._overall_progress(), "message": f"Executing node {node}...",
                })

        elif msg_type == "progress":
            val = msg_data.get("value", 0)
            mx = msg_data.get("max", 100)
            node = msg_data.get("node", "")
            pid = msg_data.get("prompt_id")
            self._node_progress[node] = {"value": val, "max": mx}
            pct = (val / mx * 100) if mx > 0 else 0
            self._emit({
                "type": "progress", "prompt_id": pid, "node": node,
                "value": val, "max": mx, "percent": pct,
                "message": f"Node {node}: {val}/{mx} ({pct:.1f}%)",
            })

        elif msg_type == "executed":
            node = msg_data.get("node")
            pid = msg_data.get("prompt_id")
            self._emit({
                "type": "node_complete", "prompt_id": pid, "node": node,
                "output": msg_data.get("output", {}),
                "percent": self._overall_progress(), "message": f"Node {node} complete",
            })

        elif msg_type == "execution_cached":
            nodes = msg_data.get("nodes", [])
            pid = msg_data.get("prompt_id")
            self._emit({
                "type": "cached", "prompt_id": pid, "nodes": nodes,
                "message": f"Using cached results for {len(nodes)} nodes",
            })

        elif msg_type == "execution_error":
            pid = msg_data.get("prompt_id")
            err = msg_data.get("exception_message", "Unknown error")
            self._emit({"type": "error", "prompt_id": pid, "percent": 0, "message": f"Error: {err}"})

    def _overall_progress(self) -> float:
        if not self._node_progress:
            return 0.0
        total = sum(
            (p["value"] / p["max"]) if p["max"] > 0 else 0
            for p in self._node_progress.values()
        )
        return (total / len(self._node_progress)) * 100
