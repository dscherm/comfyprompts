#!/usr/bin/env python3
"""PreToolUse hook (Write): refuse a new .py named after a stdlib module.

A file called `bisect.py` on PYTHONPATH, or next to a script, replaces the
stdlib `bisect` for every Python that searches there. If that file starts
Python, each start imports it again: a fork bomb (2026-10-25, ~8,800
processes, 31 GB, a reboot). See
lessons/a-script-named-after-a-stdlib-module-shadows-it-and-can-fork-bomb.md.

Behaviour
  * Write of `<name>.py` where `<name>` is a stdlib module -> exit 2, naming
    the module and suggesting a `scratch_` prefix.
  * The project-relative path listed in `gate.import_shadow_allow`
    (schermness.config.json, or the legacy ralph.config.json) is let through.
  * `<name>` is an installed package, not stdlib -> exit 0, warning on stderr.
  * Anything else, and any malformed input -> exit 0, silent.

The name lists come from tools/import_bombs.py under $SCHERMNESS_HOME (alias
$RALPH_HOME), which caches them; its shadow_reason() decides. If that module
cannot be located, imported or called, the lists inlined below decide instead,
so stdlib names are still blocked.

The message never prints an absolute path. Fails open: a bug here must not
block writes.
"""
from __future__ import annotations

import json
import os
import re
import sys
import sysconfig
from pathlib import Path

_CONFIG_NAMES = ("schermness.config.json", "ralph" + ".config.json")
_GENERIC_INSTALLED = frozenset({"tests", "test", "scripts", "tools", "docs",
                                "examples", "src", "benchmarks"})
_MSYS_DRIVE = re.compile(r"^/(?:cygdrive/|mnt/)?([A-Za-z])(?:/|$)")


def normalize_path(raw: str) -> str:
    p = raw.strip()
    if os.name == "nt":
        m = _MSYS_DRIVE.match(p)
        if m:
            p = f"{m.group(1).upper()}:/" + p[m.end():]
        p = p.replace("\\", "/")
    return p


def stdlib_names() -> set:
    names = getattr(sys, "stdlib_module_names", None)
    if names is not None:
        return set(names)
    out = set(sys.builtin_module_names)
    paths = sysconfig.get_paths()
    stdlib = Path(paths["stdlib"])
    for d in (stdlib, stdlib.parent / "DLLs", stdlib / "lib-dynload"):
        try:
            entries = list(d.iterdir())
        except OSError:
            continue
        for e in entries:
            if e.name in ("site-packages", "__pycache__"):
                continue
            if e.suffix in (".py", ".pyd", ".so"):
                out.add(e.name.split(".")[0])
            elif e.is_dir() and e.name.isidentifier() and (e / "__init__.py").exists():
                out.add(e.name)
    return out


def installed_names() -> set:
    out: set = set()
    try:
        from importlib import metadata
        for dist in metadata.distributions():
            try:
                top = dist.read_text("top_level.txt")
            except Exception:  # noqa: BLE001
                top = None
            if top:
                out.update(t.strip() for t in top.split() if t.strip())
                continue
            for f in dist.files or ():
                head = f.parts[0] if f.parts else ""
                if head.endswith((".dist-info", ".egg-info")) or head in ("..", "__pycache__"):
                    continue
                out.add(head[:-3] if head.endswith(".py") else head)
    except Exception:  # noqa: BLE001
        pass
    return out - _GENERIC_INSTALLED


def _delegated_reason(path: str):
    """(True, reason) from import_bombs.shadow_reason, or (False, None) on any failure."""
    try:
        import importlib.util
        home = os.environ.get("SCHERMNESS_HOME") or os.environ.get("RALPH_HOME")
        if not home:
            return False, None
        tools = os.path.join(home, "tools")
        target = os.path.join(tools, "import_bombs.py")
        if not os.path.isfile(target):
            return False, None
        spec = importlib.util.spec_from_file_location("_hk_import_bombs", target)
        if spec is None or spec.loader is None:
            return False, None
        mod = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = mod
        added = tools not in sys.path
        if added:
            sys.path.append(tools)
        try:
            spec.loader.exec_module(mod)
        finally:
            if added and tools in sys.path:
                sys.path.remove(tools)
        reason = mod.shadow_reason(path)
        if reason is not None and not (isinstance(reason, str) and reason.count(":") >= 1):
            return False, None
        return True, reason
    except Exception:  # noqa: BLE001
        return False, None


def find_root(start: str) -> str:
    """Nearest ancestor holding a harness config, else a .git, else start."""
    cur = os.path.abspath(start)
    git = None
    while True:
        if any(os.path.isfile(os.path.join(cur, n)) for n in _CONFIG_NAMES):
            return cur
        if git is None and os.path.exists(os.path.join(cur, ".git")):
            git = cur
        parent = os.path.dirname(cur)
        if parent == cur:
            break
        cur = parent
    return git or os.path.abspath(start)


def load_allow(root: str) -> set:
    for name in _CONFIG_NAMES:
        p = os.path.join(root, name)
        if not os.path.isfile(p):
            continue
        try:
            with open(p, encoding="utf-8") as fh:
                cfg = json.load(fh)
        except (OSError, ValueError):
            return set()
        gate = cfg.get("gate") if isinstance(cfg, dict) else None
        entries = gate.get("import_shadow_allow") if isinstance(gate, dict) else None
        if isinstance(entries, list):
            return {os.path.normcase(os.path.normpath(e)).replace("\\", "/")
                    for e in entries if isinstance(e, str)}
        return set()
    return set()


def relative_to_root(file_path: str, cwd: str, root: str) -> str:
    p = normalize_path(file_path)
    full = os.path.normpath(p if os.path.isabs(p) else os.path.join(cwd, p))
    try:
        rel = os.path.relpath(full, root)
    except ValueError:
        return full
    return rel


def decide(payload: dict) -> tuple:
    """(exit_code, stderr_message)."""
    if not isinstance(payload, dict) or payload.get("tool_name") != "Write":
        return 0, ""
    tin = payload.get("tool_input")
    fp = tin.get("file_path") if isinstance(tin, dict) else None
    if not isinstance(fp, str) or not fp.lower().endswith(".py"):
        return 0, ""
    stem = os.path.basename(normalize_path(fp))[:-3]
    if not stem or stem.startswith("__"):
        return 0, ""
    ok, reason = _delegated_reason(fp)
    if ok:
        kind, _, name = (reason or "").partition(":")
        is_stdlib = kind == "stdlib"
        is_installed = kind == "installed"
        if is_stdlib or is_installed:
            stem = name or stem
    else:
        is_stdlib = stem in stdlib_names()
        is_installed = not is_stdlib and stem in installed_names()
    if not is_stdlib:
        if is_installed:
            return 0, (f"import_shadow_guard: warning: '{stem}.py' has the same name as the "
                       f"installed package '{stem}'. Anything importing it from this "
                       f"directory gets this file instead. Prefer scratch_{stem}.py.\n")
        return 0, ""
    cwd = payload.get("cwd") if isinstance(payload.get("cwd"), str) else os.getcwd()
    root = find_root(cwd)
    rel = relative_to_root(fp, cwd, root)
    if os.path.normcase(rel).replace("\\", "/") in load_allow(root):
        return 0, ""
    return 2, (f"import_shadow_guard: blocked. '{stem}' is a Python standard-library module, so a "
               f"file named {stem}.py shadows it for every Python that searches its directory "
               f"(a script that then starts Python becomes a fork bomb). Name it "
               f"scratch_{stem}.py instead, or list its project-relative path in "
               f"gate.import_shadow_allow in schermness.config.json.\n")


def main() -> int:
    try:
        payload = json.loads(sys.stdin.read())
        code, msg = decide(payload)
    except Exception:  # noqa: BLE001
        return 0
    if msg:
        sys.stderr.write(msg)
    return code


if __name__ == "__main__":
    sys.exit(main())
