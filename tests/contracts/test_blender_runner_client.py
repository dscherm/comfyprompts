"""Blind-TDD contract tests for blender/client.py (task AP-1a).

The client starts a Blender process running blender/runner.py (an HTTP server
inside Blender), calls named bpy ops on it via run_op(name, **args), and stops
it. Surface (from public_api.md):

    class ConfigError(RuntimeError)
    start(port=0, config_path=None, timeout=120.0) -> RunnerHandle
    stop() -> None
    run_op(name, **args) -> dict   # keys: ok, path, log, seconds

Modules are loaded by file path (nothing here is pip-installed). The loader
raises FileNotFoundError until the implementation exists, so every behavioural
test errors/fails in the red phase; the static scans fail on the
"implementation file exists" assertion.

Live tests (AC-1, AC-2, AC-4, parts of AC-6/7/9) start a real Blender via the
repo-root schermness.config.json `tools.blender_bin`. One runner is shared per
module and always stopped in teardown.
"""

import importlib.util
import itertools
import json
import os
import queue
import re
import shutil
import struct
import subprocess
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path

import pytest

# parents[2] from tests/contracts/<this file> == repo root.
_REPO = Path(__file__).resolve().parents[2]
_CLIENT_PATH = _REPO / "blender" / "client.py"
_RUNNER_PATH = _REPO / "blender" / "runner.py"
_CONFIG_PATH = _REPO / "schermness.config.json"

# Implementation files named by the task (static scans read these as text).
_IMPL_FILES = [
    _REPO / "blender" / "client.py",
    _REPO / "blender" / "runner.py",
    _REPO / "blender" / "ops" / "__init__.py",
    _REPO / "blender" / "ops" / "mesh.py",
    _REPO / "blender" / "ops" / "rig.py",
]

_REGISTERED_OPS = ("decimate_to", "bake_uv", "apply_cycle", "export_glb")
_REPLY_KEYS = {"ok", "path", "log", "seconds"}

_DEFAULT_GLB = Path(
    "D:/Projects/comfyui-toolchain/products/grimforge_bestiary_v1/_quadrig/dire_rat_v2.glb"
)

_load_counter = itertools.count()


def load_client():
    """Load a FRESH copy of blender/client.py from its source path.

    Each call gets its own module object (own "current runner" state).
    Raises FileNotFoundError while the implementation is missing (red phase).
    """
    name = f"blender_client_under_test_{next(_load_counter)}"
    spec = importlib.util.spec_from_file_location(name, _CLIENT_PATH)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # FileNotFoundError until implemented
    return mod


def _fixture_glb() -> Path:
    return Path(os.environ.get("GRIMFORGE_CREATURE_GLB", str(_DEFAULT_GLB)))


def _glb_json(path: Path) -> dict:
    """Parse the JSON chunk of a binary glTF (GLB) file."""
    data = Path(path).read_bytes()
    assert len(data) >= 20, f"{path} too short to be a GLB"
    magic, version, _length = struct.unpack_from("<4sII", data, 0)
    assert magic == b"glTF", f"{path} is not a GLB (magic={magic!r})"
    assert version == 2, f"{path} is GLB version {version}, expected 2"
    chunk_len, chunk_type = struct.unpack_from("<I4s", data, 12)
    assert chunk_type == b"JSON", f"first GLB chunk is {chunk_type!r}, expected JSON"
    return json.loads(data[20 : 20 + chunk_len].decode("utf-8"))


def _glb_triangle_count(path: Path) -> int:
    """Sum triangles over every mesh primitive (indices count // 3)."""
    doc = _glb_json(path)
    accessors = doc.get("accessors", [])
    total = 0
    for mesh in doc.get("meshes", []):
        for prim in mesh.get("primitives", []):
            mode = prim.get("mode", 4)
            if mode != 4:  # only TRIANGLES primitives count as triangles
                continue
            if "indices" in prim:
                total += accessors[prim["indices"]]["count"] // 3
            else:
                total += accessors[prim["attributes"]["POSITION"]]["count"] // 3
    return total


def _post_op(base_url: str, name: str, args: dict | None = None) -> dict:
    """Raw HTTP POST to the runner's /op, independent of the client."""
    body = json.dumps({"name": name, "args": args or {}}).encode("utf-8")
    req = urllib.request.Request(
        base_url.rstrip("/") + "/op",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as err:  # a 4xx/5xx may still carry the reply
        return json.loads(err.read().decode("utf-8"))


def _write_config(path: Path, content: dict) -> Path:
    path.write_text(json.dumps(content), encoding="utf-8")
    return path


class _PopenSpy:
    """Records any attempt to launch a process; never launches one."""

    def __init__(self):
        self.calls = []

    def __call__(self, *args, **kwargs):
        self.calls.append((args, kwargs))
        raise FileNotFoundError("process launch blocked by test spy")


@pytest.fixture
def popen_spy(monkeypatch):
    """Patch subprocess.Popen BEFORE the client is loaded, so even a
    `from subprocess import Popen` inside client.py binds the spy."""
    spy = _PopenSpy()
    monkeypatch.setattr(subprocess, "Popen", spy)
    return spy


# --------------------------------------------------------------------------
# Module-scoped live runner (real Blender, repo-root config)
# --------------------------------------------------------------------------

@pytest.fixture(scope="module")
def runner():
    """Start one runner for the module via client.start(port=0); stop after."""
    client = load_client()
    handle = client.start(port=0)
    try:
        yield client, handle
    finally:
        client.stop()


@pytest.fixture(scope="module")
def creature_dir(tmp_path_factory):
    """Copy of the GrimForge creature GLB in its own temp dir (ops write next
    to their input). Skips when the fixture asset is absent."""
    src = _fixture_glb()
    if not src.is_file():
        pytest.skip(f"GrimForge fixture GLB not found: {src}")
    d = tmp_path_factory.mktemp("creature")
    shutil.copy2(src, d / src.name)
    return d / src.name


# --------------------------------------------------------------------------
# AC-1 — decimate_to produces a GLB with at most `tris` triangles
# --------------------------------------------------------------------------

def test_decimate_to_writes_glb_with_at_most_requested_triangles(runner, creature_dir):
    """Covers: AC-1 — run_op('decimate_to', path=glb, tris=500).

    Given a running runner and a test GLB (2509 triangles),
    when client.run_op('decimate_to', path=glb, tris=500) is called,
    then ok is true and the returned path exists and is a GLB whose
    triangle count is at most 500.
    """
    client, _handle = runner
    glb = creature_dir
    before = _glb_triangle_count(glb)
    assert before > 500, f"fixture must start above the target, has {before} tris"

    reply = client.run_op("decimate_to", path=str(glb), tris=500)

    assert isinstance(reply, dict)
    assert set(reply) == _REPLY_KEYS, f"reply keys {sorted(reply)}"
    assert reply["ok"] is True, f"decimate_to failed: {reply['log']}"
    assert isinstance(reply["seconds"], float) and reply["seconds"] >= 0.0
    assert isinstance(reply["log"], str)

    out = Path(reply["path"])
    assert out.is_file(), f"returned path does not exist: {out}"
    assert out.resolve() != glb.resolve(), "op must write a new file, not the input"
    after = _glb_triangle_count(out)  # also asserts glTF magic / v2
    assert 0 < after <= 500, f"decimated GLB has {after} triangles"


# --------------------------------------------------------------------------
# AC-2 — unknown op: ok false, log names the op and lists registered ops
# --------------------------------------------------------------------------

def test_unknown_op_returns_not_ok_naming_op_and_registered_ops(runner):
    """Covers: AC-2 — run_op('no_such_op') is refused with a useful log.

    Given a running runner,
    when client.run_op('no_such_op') is called,
    then ok is false and log contains 'no_such_op' and every registered op
    name (content an absent feature cannot produce).
    """
    client, _handle = runner
    reply = client.run_op("no_such_op")

    assert isinstance(reply, dict)
    assert set(reply) == _REPLY_KEYS, f"reply keys {sorted(reply)}"
    assert reply["ok"] is False
    assert reply["path"] is None
    assert "no_such_op" in reply["log"]
    for op in _REGISTERED_OPS:
        assert op in reply["log"], f"registered op {op!r} not listed in log"


# --------------------------------------------------------------------------
# AC-3 — no tools.blender_bin -> ConfigError naming the key, nothing started
# --------------------------------------------------------------------------

@pytest.mark.parametrize(
    "content,as_str",
    [
        ({}, False),                                  # no `tools` at all
        ({"tools": {}}, True),                        # `tools` without the key
        ({"tools": {"blender_bin": ""}}, False),      # empty value
        ({"tools": {"other_bin": "x.exe"}}, True),    # sibling key only
    ],
    ids=["no-tools", "no-key", "empty-value", "sibling-only"],
)
def test_start_without_blender_bin_raises_and_starts_nothing(
    tmp_path, popen_spy, content, as_str
):
    """Covers: AC-3 — missing tools.blender_bin refuses loudly.

    Given a config JSON with no (or an empty) tools.blender_bin,
    when client.start(config_path=...) is called,
    then it raises ConfigError (a RuntimeError) whose message contains
    'tools.blender_bin', no process is launched, and the client has no
    current runner afterwards (run_op raises RuntimeError).
    """
    cfg = _write_config(tmp_path / "schermness.config.json", content)
    client = load_client()  # loaded after the spy is installed

    assert issubclass(client.ConfigError, RuntimeError)
    with pytest.raises(client.ConfigError) as excinfo:
        client.start(port=0, config_path=str(cfg) if as_str else cfg)

    assert "tools.blender_bin" in str(excinfo.value)
    assert popen_spy.calls == [], f"a process launch was attempted: {popen_spy.calls}"
    with pytest.raises(RuntimeError):
        client.run_op("decimate_to")
    client.stop()  # safe when nothing is running


# --------------------------------------------------------------------------
# AC-4 — --port 0: the runner prints its bound port and start() reads it
# --------------------------------------------------------------------------

def test_start_port_zero_returns_bound_port_the_runner_answers_on(runner):
    """Covers: AC-4 — client.start(port=0) reads the real bound port.

    Given the runner started with --port 0 through client.start,
    when it starts,
    then the handle carries a positive int port (never 0), url
    http://127.0.0.1:<port>, a live process, and a raw HTTP POST to that
    url's /op (bypassing the client) is answered by the runner.
    """
    _client, handle = runner
    assert isinstance(handle.port, int) and not isinstance(handle.port, bool)
    assert 0 < handle.port < 65536
    assert handle.url == f"http://127.0.0.1:{handle.port}"
    assert isinstance(handle.process, subprocess.Popen)
    assert handle.process.poll() is None, "runner process is not alive"

    reply = _post_op(handle.url, "no_such_op")
    assert reply["ok"] is False
    assert "no_such_op" in reply["log"]


def _read_lines(stream, q):
    for raw in iter(stream.readline, b""):
        q.put(raw)
    q.put(None)


def test_runner_prints_runner_port_line_for_port_zero():
    """Covers: AC-4 — the runner itself prints 'RUNNER_PORT <n>'.

    Given blender --background --factory-startup --python blender/runner.py
    -- --port 0 launched directly (no client),
    when it starts,
    then its stdout carries a line 'RUNNER_PORT <n>' with n > 0, and the
    runner answers POST /op on port n.
    """
    assert _RUNNER_PATH.is_file(), f"implementation file missing: {_RUNNER_PATH}"
    cfg = json.loads(_CONFIG_PATH.read_text(encoding="utf-8"))
    blender_bin = (cfg.get("tools") or {}).get("blender_bin")
    assert blender_bin, "schermness.config.json has no tools.blender_bin"

    proc = subprocess.Popen(
        [blender_bin, "--background", "--factory-startup",
         "--python", str(_RUNNER_PATH), "--", "--port", "0"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    try:
        q: queue.Queue = queue.Queue()
        threading.Thread(target=_read_lines, args=(proc.stdout, q), daemon=True).start()
        port = None
        deadline = time.monotonic() + 120.0
        pattern = re.compile(rb"^RUNNER_PORT (\d+)\s*$")
        while port is None and time.monotonic() < deadline:
            try:
                line = q.get(timeout=max(0.1, deadline - time.monotonic()))
            except queue.Empty:
                break
            if line is None:
                break
            m = pattern.match(line.strip())
            if m:
                port = int(m.group(1))
        assert port is not None, "runner never printed a 'RUNNER_PORT <n>' line"
        assert 0 < port < 65536

        reply = _post_op(f"http://127.0.0.1:{port}", "no_such_op")
        assert reply["ok"] is False
        assert "no_such_op" in reply["log"]
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=30)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=30)


def test_stop_ends_the_blender_process_and_frees_the_port():
    """Covers: AC-4 — the process start() read the port from is the one stop() ends.

    Given a client whose runner was started with port=0,
    when stop() is called,
    then the handle's Blender process has exited and nothing answers on the
    port it reported; a second stop() is a no-op.
    """
    client = load_client()
    handle = client.start(port=0)
    try:
        assert _post_op(handle.url, "no_such_op")["ok"] is False
    finally:
        client.stop()

    assert handle.process.poll() is not None, "Blender process still running after stop()"
    with pytest.raises((urllib.error.URLError, ConnectionError, OSError)):
        _post_op(handle.url, "no_such_op")
    client.stop()  # safe when nothing is running


# --------------------------------------------------------------------------
# AC-6 — None / wrong-typed required parameters raise, no coercion
# --------------------------------------------------------------------------

@pytest.mark.parametrize(
    "bad_name",
    [None, 123, 4.5, b"decimate_to", ["decimate_to"], {"name": "decimate_to"}],
    ids=["none", "int", "float", "bytes", "list", "dict"],
)
def test_run_op_wrong_typed_name_raises(runner, bad_name):
    """Covers: AC-6 — run_op(name=<not a str>) raises TypeError/ValueError.

    Given a running runner (so a RuntimeError 'not started' cannot stand in),
    when run_op is called with None or a non-str op name,
    then it raises TypeError or ValueError and returns no reply dict (a
    coerced call would come back as an ok:false dict and fail this test).
    """
    client, _handle = runner
    with pytest.raises((TypeError, ValueError)):
        client.run_op(bad_name)


@pytest.mark.parametrize(
    "bad_port",
    [None, "0", "8080", 1.5, [0]],
    ids=["none", "str-0", "str-8080", "float", "list"],
)
def test_start_wrong_typed_port_raises_without_launching(tmp_path, popen_spy, bad_port):
    """Covers: AC-6 — start(port=<not an int>) raises, launches nothing.

    Given a config whose tools.blender_bin is set,
    when start is called with None or a non-int port,
    then it raises TypeError or ValueError and no process launch is
    attempted (the spy would turn a coerced launch into FileNotFoundError).
    """
    cfg = _write_config(
        tmp_path / "schermness.config.json",
        {"tools": {"blender_bin": str(tmp_path / "blender.exe")}},
    )
    client = load_client()
    with pytest.raises((TypeError, ValueError)):
        client.start(port=bad_port, config_path=cfg)
    assert popen_spy.calls == []


# --------------------------------------------------------------------------
# AC-7 — sink metacharacters are treated as data
# --------------------------------------------------------------------------

@pytest.mark.parametrize(
    "evil_name",
    [
        "../ops/mesh",
        "ops.mesh.decimate_to",
        "__import__('os').system('echo pwned')",
        "decimate_to\x00",
        "decimate_to'; --",
        "<script>alert(1)</script>",
        "__init__",
        "__class__",
    ],
    ids=["traversal", "dotted", "python-expr", "null-byte", "quote", "script",
         "dunder-init", "dunder-class"],
)
def test_op_name_metacharacters_are_treated_as_unknown_op(runner, evil_name):
    """Covers: AC-7 — the op-name lookup sink does not interpret metacharacters.

    Given a running runner,
    when run_op is called with an op name containing '../', a null byte,
    a quote, markup, a Python expression, or a dunder attribute,
    then the runner treats it as an unknown name: ok is false, path is None,
    and the log is the unknown-op listing (names the registered ops) — or the
    client raises ValueError before sending.
    """
    client, _handle = runner
    try:
        reply = client.run_op(evil_name)
    except ValueError:
        return
    assert reply["ok"] is False
    assert reply["path"] is None
    for op in _REGISTERED_OPS:
        assert op in reply["log"], "expected the unknown-op listing in log"


def test_null_byte_in_path_arg_fails_without_writing_files(runner, tmp_path):
    """Covers: AC-7 — a null byte in the file-path arg writes nothing.

    Given a running runner and a directory holding one input file,
    when decimate_to is called with a path containing a null byte,
    then the call raises ValueError or returns ok false with path None, and
    no file is created in (or next to) that directory.
    """
    client, _handle = runner
    work = tmp_path / "work"
    work.mkdir()
    (work / "in.glb").write_bytes(b"not a real glb")
    before_work = sorted(p.name for p in work.iterdir())
    before_parent = sorted(p.name for p in tmp_path.iterdir())

    try:
        reply = client.run_op(
            "decimate_to", path=str(work / "in.glb") + "\x00evil.glb", tris=100
        )
    except ValueError:
        reply = None
    if reply is not None:
        assert reply["ok"] is False
        assert reply["path"] is None

    assert sorted(p.name for p in work.iterdir()) == before_work
    assert sorted(p.name for p in tmp_path.iterdir()) == before_parent


# --------------------------------------------------------------------------
# AC-8 — no hardcoded secrets in the implementation source (static scan)
# --------------------------------------------------------------------------

_CREDENTIAL_PATTERNS = [
    re.compile(r"BEGIN RSA PRIVATE KEY"),
    re.compile(r"BEGIN PRIVATE KEY"),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
]
_SECRET_ASSIGN = re.compile(
    r"""(?ix)\b(password|passwd|secret|api[_-]?key|token)\b\s*[:=]\s*['"]([^'"]+)['"]"""
)
_PLACEHOLDER_VALUES = {
    "", "x", "xxx", "xxxx", "changeme", "placeholder", "your_key_here",
    "todo", "none", "example", "dummy",
}


def test_implementation_has_no_hardcoded_secrets():
    """Covers: AC-8 — scan impl sources for credential patterns.

    Given the implementation files behind blender/client.py (client, runner,
    ops package),
    when they are read as text and scanned for private-key blocks, AWS access
    keys, and secret assignments to non-placeholder literals,
    then zero matches are found; fails red because the files are missing.
    """
    for path in _IMPL_FILES:
        assert path.is_file(), f"implementation file missing: {path}"
    for path in _IMPL_FILES:
        source = path.read_text(encoding="utf-8")
        for pat in _CREDENTIAL_PATTERNS:
            assert not pat.search(source), f"{path.name}: credential pattern {pat.pattern!r}"
        for match in _SECRET_ASSIGN.finditer(source):
            value = match.group(2).strip().lower()
            assert value in _PLACEHOLDER_VALUES, (
                f"{path.name}: secret-like literal assignment {match.group(0)!r}"
            )


# --------------------------------------------------------------------------
# AC-9 — surfaced errors leak no traceback / absolute path / env value
# --------------------------------------------------------------------------

_ABS_PATH = re.compile(r"(?:[A-Za-z]:[\\/])|(?:(?:^|[\s'\"(])/(?:home|Users|etc|root|var|tmp)/)")


def test_config_error_message_leaks_no_internals(tmp_path, popen_spy, monkeypatch):
    """Covers: AC-9 — ConfigError carries no traceback, path, or env value.

    Given a config lacking tools.blender_bin and a sentinel env var,
    when start(config_path=...) fails,
    then the ConfigError message names tools.blender_bin but contains no
    traceback text, no absolute filesystem path, and no env-var value.
    """
    sentinel = "S3CRET_ENV_VALUE_should_not_leak"
    monkeypatch.setenv("BLENDER_RUNNER_TEST_SECRET", sentinel)
    cfg = _write_config(tmp_path / "schermness.config.json", {"tools": {}})
    client = load_client()

    with pytest.raises(client.ConfigError) as excinfo:
        client.start(port=0, config_path=cfg)

    message = str(excinfo.value)
    assert "tools.blender_bin" in message
    assert "Traceback (most recent call last)" not in message
    assert sentinel not in message
    assert not _ABS_PATH.search(message), f"absolute path in message: {message!r}"
    assert str(tmp_path) not in message


def test_unknown_op_log_leaks_no_internals(runner):
    """Covers: AC-9 — the unknown-op refusal log carries no internals.

    Given a running runner,
    when run_op is called with an unknown op name (invalid input),
    then the log contains no traceback text and no absolute filesystem path.
    (A failing op's log is DOCUMENTED to carry its traceback — escalated in
    triage, not asserted here.)
    """
    client, _handle = runner
    reply = client.run_op("no_such_op")
    assert reply["ok"] is False
    log = reply["log"]
    assert "Traceback (most recent call last)" not in log
    assert not _ABS_PATH.search(log), f"absolute path in log: {log!r}"
    assert str(_REPO) not in log


# --------------------------------------------------------------------------
# AC-10 — no dangerous constructs in the implementation source (static scan)
# --------------------------------------------------------------------------

_DANGEROUS_PATTERNS = [
    re.compile(r"\beval\s*\("),
    re.compile(r"\bexec\s*\("),
    re.compile(r"\bpickle\.loads\s*\("),
    re.compile(r"\bos\.system\s*\("),
    re.compile(r"shell\s*=\s*True"),
]
_YAML_LOAD = re.compile(r"\byaml\.load\s*\(")


def test_implementation_has_no_dangerous_constructs():
    """Covers: AC-10 — scan impl sources for dangerous constructs.

    Given the implementation files behind blender/client.py,
    when they are read as text and scanned for eval/exec/pickle.loads/
    os.system, shell=True, and yaml.load without SafeLoader,
    then zero matches are found; fails red because the files are missing.
    """
    for path in _IMPL_FILES:
        assert path.is_file(), f"implementation file missing: {path}"
    for path in _IMPL_FILES:
        source = path.read_text(encoding="utf-8")
        for pat in _DANGEROUS_PATTERNS:
            assert not pat.search(source), f"{path.name}: dangerous construct {pat.pattern!r}"
        for match in _YAML_LOAD.finditer(source):
            tail = source[match.start() : match.start() + 120]
            assert "SafeLoader" in tail, f"{path.name}: yaml.load without SafeLoader"
