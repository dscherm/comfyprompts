"""Blender script runner: an HTTP server that lives inside a Blender process and
runs named bpy operations for the pipeline.

    blender --background --factory-startup --python blender/runner.py -- --port N

`--port 0` lets the OS pick a free port. Once bound, the runner prints
`RUNNER_PORT <n>` on stdout (blender/client.py waits for that line).

Endpoints (JSON in, JSON out):
    POST /op        {"name": str, "args": {...}} -> {ok, path, log, seconds}
    GET  /ops       {"ops": [names]}
    GET  /health    {"ok": true}
    POST /shutdown  stops serving; Blender then exits

Requests are served one at a time on Blender's main thread, which is the only
thread bpy may be called from.
"""

import argparse
import importlib
import json
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

ops = importlib.import_module("ops")  # blender/ops, found via the path insert above


def _parse_args(argv: list[str]) -> argparse.Namespace:
    user = argv[argv.index("--") + 1:] if "--" in argv else []
    ap = argparse.ArgumentParser(prog="runner.py")
    ap.add_argument("--port", type=int, default=0)
    ap.add_argument("--host", default="127.0.0.1")
    return ap.parse_args(user)


class _Server(HTTPServer):
    stop_requested = False


class _Handler(BaseHTTPRequestHandler):
    server: _Server

    server_version = "BlenderRunner/1"

    def log_message(self, format, *args):  # keep Blender's stdout for RUNNER_* lines
        sys.stderr.write("runner: " + (format % args) + "\n")

    def _reply(self, code: int, body: dict) -> None:
        data = json.dumps(body).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _body(self) -> dict:
        n = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(n) if n else b"{}"
        return json.loads(raw.decode("utf-8") or "{}")

    def do_GET(self):
        if self.path == "/health":
            self._reply(200, {"ok": True})
        elif self.path == "/ops":
            self._reply(200, {"ops": ops.names()})
        else:
            self._reply(404, {"ok": False, "log": f"no route {self.path}"})

    def do_POST(self):
        if self.path == "/shutdown":
            self._reply(200, {"ok": True})
            self.server.stop_requested = True
            return
        if self.path != "/op":
            self._reply(404, {"ok": False, "log": f"no route {self.path}"})
            return
        try:
            req = self._body()
        except (ValueError, UnicodeDecodeError) as e:
            self._reply(400, {"ok": False, "path": None,
                              "log": f"request body is not JSON: {e}", "seconds": 0.0})
            return
        name = req.get("name")
        args = req.get("args") or {}
        if not isinstance(name, str) or not isinstance(args, dict):
            self._reply(400, {"ok": False, "path": None,
                              "log": "request must be {\"name\": str, \"args\": object}",
                              "seconds": 0.0})
            return
        self._reply(200, ops.run(name, args))


def main() -> None:
    a = _parse_args(sys.argv)
    httpd = _Server((a.host, a.port), _Handler)
    print(f"RUNNER_PORT {httpd.server_address[1]}", flush=True)
    while not httpd.stop_requested:
        httpd.handle_request()
    httpd.server_close()
    print("RUNNER_STOPPED", flush=True)


main()
