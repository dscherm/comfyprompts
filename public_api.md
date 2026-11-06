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

## pipelines/godot_import.py

The Godot import stage: lands a GLB in a Godot 4 project under that project's
import contract and checks it. Plain Python; load it by file path:

```python
_MOD = Path(__file__).resolve().parents[2] / "pipelines" / "godot_import.py"
```

```
class ConfigError(RuntimeError)
class RulesError(ValueError)

load_rules(project_dir: str | Path, kit: str | Path | None = None) -> dict
import_glb(glb: str | Path, project_dir: str | Path, kit: str | Path | None = None,
           config_path: str | Path | None = None) -> dict
main(argv: list[str] | None = None) -> int
```

### The contract

`<project_dir>/import_rules.json` (schema: `pipelines/import_rules.schema.json`),
a JSON object with these optional keys:

| key | type | default | meaning |
|---|---|---|---|
| `scale` | number > 0 | `1.0` | import root scale; checked against the GLB's own size |
| `scale_tolerance` | number > 0 | `0.05` | relative tolerance of the scale check |
| `collision` | `"none"` / `"box"` / `"convex"` / `"trimesh"` | `"none"` | collision the stage builds and checks |
| `material_slots` | int ≥ 0 or null | `null` | expected material slot count (null = not checked) |
| `animation_names` | list of str | `[]` | clips that must exist in the AnimationPlayer |
| `land_in` | `res://` folder | `"res://imported/"` | where the GLB is copied |

A kit folder may hold `import_overrides.json` with any of the same keys; its
values replace the project's key by key.

- `load_rules(project_dir, kit=None)` returns the merged rules: every key above
  with defaults filled in, plus `source` (a list naming the files used). `kit`
  is a path to a kit folder (a kit folder without `import_overrides.json`
  changes nothing). A missing `import_rules.json`, an unknown key, or a bad
  value raises `RulesError`.
- `import_glb(glb, project_dir, kit=None, config_path=None)` runs the stage
  and returns the gate dict:
  `{"ok": bool, "checks": [{"name": str, "ok": bool, "detail": str}, ...], "shot": str | None, ...}`.
  `ok` is true only when every check is ok. Check names: `import`, `scale`,
  `collision` (its `detail` names the collision kind, e.g. `collision: box ...`),
  one `animation:<name>` per required clip (a missing clip's check has
  `ok: False` and its name and detail contain the clip name), `material_slots`
  (only when the rule is set), and `shot`. `shot` is the absolute path of a PNG
  screenshot of the landed asset (under `<project_dir>/_shots/`), or None.
  The Godot binary is `tools.godot_bin` in `schermness.config.json` (repo root
  by default, `config_path` for another file). Without it, `import_glb`
  raises `ConfigError` whose message contains the literal text
  `tools.godot_bin`, before anything is written into the project.
- `main(argv)` is the CLI: `godot_import.py <glb> <project_dir> [--kit KIT]
  [--config CFG]`. It prints the gate dict as JSON on stdout and returns `0`
  when ok, `1` when a check failed, and `2` (message on stderr naming the
  problem, e.g. `tools.godot_bin`) when it refused to run; in that case it
  writes nothing into the project.

Running the stage launches Godot twice (a headless import, then a short
windowed run for the screenshot); expect ~10 s per call.

### Test project and fixture

A temp Godot project needs only a `project.godot` file, e.g.
`config_version=5\n\n[application]\nconfig/name="t"\n`, plus `import_rules.json`.
The creature fixture is the same as for `blender/client.py` above
(`dire_rat_v2.glb`, env `GRIMFORGE_CREATURE_GLB`; clips `attack`, `idle`,
`run`, `walk`; 1 material slot; skip the test if the file is missing).
