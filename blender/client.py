"""Client for the Blender script runner (blender/runner.py).

    from blender import client          # or load by file path
    client.start()                      # launches Blender, waits for RUNNER_PORT
    r = client.run_op("decimate_to", path="in.glb", tris=500)
    client.stop()

The Blender binary is `tools.blender_bin` in schermness.config.json. When it is
not set, `start` raises ConfigError naming that key and launches nothing: the
pipeline never silently skips its Blender stage.
"""

from __future__ import annotations

import collections
import json
import re
import subprocess
import threading
import urllib.error
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = REPO_ROOT / "schermness.config.json"
RUNNER = Path(__file__).resolve().parent / "runner.py"
CONFIG_KEY = "tools.blender_bin"
OP_TIMEOUT = 1800.0

_PORT_LINE = re.compile(r"^RUNNER_PORT (\d+)\s*$")


class ConfigError(RuntimeError):
    """The config lacks a value the runner needs (message names the key)."""


class RunnerHandle:
    """A started runner: `port` it bound, its `url`, the Blender `process`, and
    the recent lines of Blender's `output`. (A plain class, not a dataclass, so
    the module also works when loaded by file path without a sys.modules entry.)"""

    def __init__(self, port: int, url: str, process: subprocess.Popen,
                 output: collections.deque) -> None:
        self.port = port
        self.url = url
        self.process = process
        self.output = output


_current: RunnerHandle | None = None


def blender_bin(config_path: str | Path | None = None) -> str:
    """`tools.blender_bin` from the config, or ConfigError naming the key."""
    path = Path(config_path) if config_path else DEFAULT_CONFIG
    try:
        cfg = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as e:
        raise ConfigError(f"{CONFIG_KEY} is not set: config file {path.name} not found") from None
    value = (cfg.get("tools") or {}).get("blender_bin") if isinstance(cfg, dict) else None
    if not value:
        raise ConfigError(f"{CONFIG_KEY} is not set in {path.name}; add the Blender executable path "
                          f"under \"tools\": {{\"blender_bin\": ...}}")
    if not Path(value).is_file():
        raise ConfigError(f"{CONFIG_KEY} points at a file that does not exist "
                          f"({Path(value).name}); fix it in {path.name}")
    return str(value)


def start(port: int = 0, config_path: str | Path | None = None,
          timeout: float = 120.0) -> RunnerHandle:
    """Launch Blender running the runner on `port` (0 = OS-chosen) and return
    once it reports the port it bound. Replaces any runner this client started."""
    global _current
    if isinstance(port, bool) or not isinstance(port, int):
        raise TypeError(f"port must be an int, got {type(port).__name__}")
    if not 0 <= port <= 65535:
        raise ValueError(f"port must be 0..65535, got {port}")
    exe = blender_bin(config_path)  # raises before anything is launched
    stop()
    cmd = [exe, "--background", "--factory-startup", "--python", str(RUNNER),
           "--", "--port", str(port)]
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                            stdin=subprocess.DEVNULL, text=True, encoding="utf-8",
                            errors="replace", bufsize=1)
    lines: collections.deque = collections.deque(maxlen=2000)
    found: list[int] = []
    ready = threading.Event()

    def reader() -> None:
        assert proc.stdout is not None
        for line in proc.stdout:
            line = line.rstrip("\n")
            lines.append(line)
            m = _PORT_LINE.match(line)
            if m and not found:
                found.append(int(m.group(1)))
                ready.set()
        ready.set()  # EOF: Blender exited

    threading.Thread(target=reader, daemon=True).start()
    if not ready.wait(timeout) or not found:
        exited = proc.poll()
        if exited is None:
            proc.kill()
            proc.wait(10)
        tail = "\n".join(list(lines)[-30:])
        why = f"timed out after {timeout:.0f}s" if exited is None else f"Blender exited {exited}"
        raise RuntimeError(f"Blender runner did not report RUNNER_PORT ({why}).\n{tail}")
    bound = found[0]
    _current = RunnerHandle(port=bound, url=f"http://127.0.0.1:{bound}", process=proc,
                            output=lines)
    return _current


def _post(url: str, body: dict, timeout: float) -> dict:
    req = urllib.request.Request(url, data=json.dumps(body).encode("utf-8"),
                                 headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def run_op(name: str, **args) -> dict:
    """Run op `name` with keyword `args` on the current runner and return
    {ok, path, log, seconds}."""
    if not isinstance(name, str):
        raise TypeError(f"op name must be a str, got {type(name).__name__}")
    if _current is None:
        raise RuntimeError("no Blender runner is running; call start() first")
    if _current.process.poll() is not None:
        raise RuntimeError(f"Blender runner exited ({_current.process.returncode})")
    try:
        reply = _post(f"{_current.url}/op", {"name": name, "args": args}, OP_TIMEOUT)
    except urllib.error.HTTPError as e:
        reply = json.loads(e.read().decode("utf-8") or "{}")
    return {"ok": bool(reply.get("ok")), "path": reply.get("path"),
            "log": reply.get("log") or "", "seconds": float(reply.get("seconds") or 0.0)}


def stop() -> None:
    """Shut the current runner down and wait for Blender to exit. No-op when
    nothing is running."""
    global _current
    h, _current = _current, None
    if h is None:
        return
    if h.process.poll() is None:
        try:
            _post(f"{h.url}/shutdown", {}, 10.0)
        except (urllib.error.URLError, OSError, ValueError):
            pass
        try:
            h.process.wait(30)
        except subprocess.TimeoutExpired:
            h.process.kill()
            h.process.wait(10)
    if h.process.stdout:
        h.process.stdout.close()

