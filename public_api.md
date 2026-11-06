# Public API

Curated surface documentation for blind-TDD gated tasks. The blind test
writer's only view of the codebase beyond the task spec and `tests/`.

## tools/security/filename_guard.py

Validation for user-supplied asset/kit names before they become output
filenames (under `products/` and `output/`). Nothing here exists yet — it is
the surface the current gated task adds.

```
safe_filename(name: str, max_length: int = 128) -> str
```

Returns `name` unchanged when it is a safe filename; raises `ValueError`
otherwise. There is no sanitize-and-continue mode: an unsafe name is an
error, never silently rewritten.

### Import convention

Nothing in this repo is pip-installed (`pyproject.toml` has `packages = []`).
Tests load modules by file path, mirroring `tests/test_kitlib.py`:

```python
import importlib.util
from pathlib import Path

_MOD = Path(__file__).resolve().parents[2] / "tools" / "security" / "filename_guard.py"
spec = importlib.util.spec_from_file_location("filename_guard", _MOD)
filename_guard = importlib.util.module_from_spec(spec)
spec.loader.exec_module(filename_guard)  # raises FileNotFoundError until implemented
```

(`parents[2]` from a test in `tests/contracts/`.)

## blender/client.py

Python client for the Blender script runner (`blender/runner.py`). The runner is
an HTTP server that runs **inside** Blender, started as
`blender --background --factory-startup --python blender/runner.py -- --port N`;
it serves named bpy operations registered in `blender/ops/*.py`. `client.py`
starts and stops that Blender process and calls ops on it. Plain Python (no
`bpy` import); load it by file path like any module here:

```python
_MOD = Path(__file__).resolve().parents[2] / "blender" / "client.py"
```

```
class ConfigError(RuntimeError)

start(port: int = 0, config_path: str | Path | None = None,
      timeout: float = 120.0) -> RunnerHandle
stop() -> None
run_op(name: str, **args) -> dict
```

- `start` reads `tools.blender_bin` from `schermness.config.json` (the repo-root
  file by default; `config_path` points at another JSON file). If the file has
  no `tools.blender_bin` (missing key, missing `tools`, or an empty value) it
  raises `ConfigError` whose message contains the literal text
  `tools.blender_bin`, and **no process is started**. Otherwise it launches the
  runner with `--port <port>` (`0` = let the OS pick a free port), waits for the
  runner to print the line `RUNNER_PORT <n>` on stdout, and returns a
  `RunnerHandle` with attributes `port: int` (the bound port read from that
  line, never 0), `url: str` (`http://127.0.0.1:<port>`) and `process`
  (the `subprocess.Popen`). The handle also becomes the client's current runner.
- `run_op(name, **args)` POSTs `{"name": name, "args": args}` to the current
  runner's `/op` and returns its reply, a dict with exactly these keys:
  `ok: bool`, `path: str | None` (the output file the op wrote), `log: str`,
  `seconds: float`. An unknown op name returns `ok: False` with a `log` that
  contains the requested name and every registered op name. A failing op
  returns `ok: False` with the Python traceback in `log`. Calling `run_op`
  before `start` raises `RuntimeError`.
- `stop()` shuts the runner down and waits for the Blender process to exit.
  Safe to call when nothing is running.

### Registered ops (args are keyword arguments to `run_op`)

| op | args | output (`path`) |
|---|---|---|
| `decimate_to` | `path` (input GLB), `tris: int`, `out` (optional GLB path) | a GLB whose triangle count is **at most** `tris` |
| `bake_uv` | `path` (low-poly GLB), `textured` (high-res textured GLB), `out` (optional), `px: int = 1024` | textured low-poly GLB |
| `apply_cycle` | `path` (UniRig-rigged quadruped GLB), `clip` (`idle`/`walk`/`run`/`attack`/`all`), `out` (optional) | GLB carrying that animation clip |
| `export_glb` | `path` (GLB/glTF/FBX/OBJ/.blend), `out` (GLB path) | the scene re-exported as GLB |

When `out` is omitted the op writes next to the input with a suffix
(`<stem>_<op>.glb`).

### Fixture

A GrimForge creature GLB (git-ignored, so it lives in the main checkout, not
in worktrees): `D:/Projects/comfyui-toolchain/products/grimforge_bestiary_v1/_quadrig/dire_rat_v2.glb`
— one skinned mesh, 2509 triangles, one material, animation clips `attack`,
`idle`, `run`, `walk`. Tests should read the path from the env var
`GRIMFORGE_CREATURE_GLB` when set, else that default, and `pytest.skip` if the
file does not exist. Tests that start Blender should copy the fixture into
`tmp_path` first (ops write next to their input) and always call `stop()` in
teardown. A Blender start takes a few seconds; one runner per test module is
fine.

GLB is the standard binary glTF container (12-byte header, then a JSON chunk);
tests can count triangles from the JSON's mesh primitives (`indices` accessor
`count // 3`) without Blender.
