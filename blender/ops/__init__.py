"""Op registry for blender/runner.py.

An op is a function `fn(**args) -> (path, log)` registered under a name. `run`
times it and turns its outcome into the runner's reply
`{ok, path, log, seconds}`: an exception becomes `ok: False` with the traceback
in `log`, and an unknown name becomes `ok: False` naming every registered op.

Op modules (mesh.py, rig.py) import bpy, so they only load inside Blender.
"""

import contextlib
import io
import runpy
import sys
import time
import traceback
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

_OPS: dict = {}


def register(name: str):
    def deco(fn):
        _OPS[name] = fn
        return fn
    return deco


def names() -> list[str]:
    return sorted(_OPS)


def run(name: str, args: dict) -> dict:
    t0 = time.perf_counter()
    fn = _OPS.get(name)
    if fn is None:
        return {"ok": False, "path": None, "seconds": 0.0,
                "log": f"unknown op '{name}'; registered ops: {', '.join(names())}"}
    try:
        path, log = fn(**args)
        ok = True
    except Exception:  # every failure goes back to the caller, never kills the runner
        path, log, ok = None, traceback.format_exc(), False
    return {"ok": ok, "path": path, "log": log,
            "seconds": round(time.perf_counter() - t0, 3)}


def default_out(path: str, op: str) -> str:
    p = Path(path)
    return str(p.with_name(f"{p.stem}_{op}.glb"))


def run_script(script: Path, argv: list) -> str:
    """Run one of the repo's `blender -b --python X -- args` scripts in this
    process, with `sys.argv` set the way it expects, and return what it printed.
    A script error propagates (with the captured output attached to the note)."""
    if not script.is_file():
        raise FileNotFoundError(f"pipeline script missing: {script}")
    saved = sys.argv
    sys.argv = [saved[0] if saved else "blender", "--", *[str(a) for a in argv]]
    buf = io.StringIO()
    try:
        with contextlib.redirect_stdout(buf):
            runpy.run_path(str(script), run_name="__main__")
    except SystemExit as e:
        if e.code not in (None, 0):
            raise RuntimeError(f"{script.name} exited {e.code}\n{buf.getvalue()}") from e
    except Exception as e:
        raise RuntimeError(f"{script.name} failed: {e!r}\noutput:\n{buf.getvalue()}") from e
    finally:
        sys.argv = saved
    return buf.getvalue()


def require_file(path, what: str = "path") -> str:
    if not path:
        raise ValueError(f"missing required arg '{what}'")
    if not Path(path).is_file():
        raise FileNotFoundError(f"{what} does not exist: {path}")
    return str(path)


from . import mesh, rig  # noqa: E402,F401  (registers the ops)
