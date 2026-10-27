#!/usr/bin/env python3
"""PreToolUse hook on Read: refuse a whole-file read of a huge markdown doc.

Soapbox-2D's `public_api.md` is ~30,000 lines. A bare `Read` of it spends the
context window on one file and the agent still has to find the part it wanted.
This blocks (exit 2) the whole-file read and hands back the file's headings
with line numbers, so the retry is `Read(file, offset=N, limit=M)`.

## When it blocks

ALL of: the tool is `Read`; neither `offset` nor `limit` was given; the file is
markdown (`.md`); it is over the size threshold; and it is in scope -- at the
project root, under `docs/`, or named in the configured name list (any depth).

Everything else passes: reads with offset/limit, non-markdown files (a
`.gd`/`.py` file is a different question), and files under the threshold.

## Configuration

`harness.read_guard` in `schermness.config.json` (or the legacy
`ralph.config.json`):

```json
{"harness": {"read_guard": {
    "enabled": true,
    "threshold_kb": 40,
    "names": ["public_api.md", "SPEC.md", "plan.md"]
}}}
```

`names` REPLACES the default list when given. Env `SCHERMNESS_READ_GUARD=off`
disables the guard for one session.

## Failure mode

Fails OPEN. An unparseable payload, an unreadable file, or any unexpected
error allows the read, with a note on stderr. A guard that wedges Read is worse
than the cost it exists to avoid.

## Paths

Claude Code on Windows can hand a hook `D:\\x`, `D:/x`, or the MSYS form
`/d/x` (also `/cygdrive/d/x`). Windows Python cannot open `/d/x`; it fails with
a FileNotFoundError that readers swallow, which looks like "no such file" and
would make this guard silently allow everything. `normalize_path` converts the
MSYS forms first (lessons/msys-paths-break-windows-python.md).
"""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

DEFAULT_THRESHOLD_KB = 40
DEFAULT_NAMES = ("public_api.md", "SPEC.md", "plan.md")
MAX_HEADINGS = 300

# Inlined copy of tools/_internal/paths: this hook is copied into each project
# and cannot import the harness resolver. New name first, legacy second; when
# neither exists, NEW (paths.DEFAULT_ON_MISSING). The config file follows the
# same new-then-legacy rule, taken from whichever state dir name the project
# uses -- a project holding `.ralph/` is on `ralph.config.json`.
_STATE_DIR_NAMES = (".schermness", ".ralph")
_CONFIG_BY_STATE = {".schermness": "schermness.config.json", ".ralph": "ralph" + ".config.json"}


def _state_dir(root: Path) -> Path:
    for name in _STATE_DIR_NAMES:
        if (root / name).is_dir():
            return root / name
    return root / _STATE_DIR_NAMES[0]


def _config_names(root: Path) -> tuple[str, ...]:
    own = _CONFIG_BY_STATE[_state_dir(root).name]
    return tuple(dict.fromkeys((own, *_CONFIG_BY_STATE.values())))

_MSYS_DRIVE = re.compile(r"^/(?:cygdrive/|mnt/)?([A-Za-z])(?:/|$)")


def normalize_path(raw: str) -> str:
    """Turn an MSYS/Git-Bash drive path into a path this Python can open."""
    p = raw.strip()
    if os.name == "nt":
        m = _MSYS_DRIVE.match(p)
        if m:
            p = f"{m.group(1).upper()}:/" + p[m.end():]
        p = p.replace("\\", "/")
    return p


def _git_root(start: Path) -> Path:
    try:
        start = start.resolve()
    except OSError:
        return start
    for d in (start, *start.parents):
        if (d / ".git").exists():
            return d
    return start


def _load_config(root: Path) -> dict:
    for name in _config_names(root):
        p = root / name
        if p.is_file():
            try:
                cfg = json.loads(p.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                return {}
            guard = (cfg.get("harness") or {}).get("read_guard") if isinstance(cfg, dict) else None
            return guard if isinstance(guard, dict) else {}
    return {}


def _in_scope(path: Path, root: Path, names: set[str]) -> bool:
    if path.name.lower() in names:
        return True
    try:
        rel = path.resolve().relative_to(root.resolve())
    except (ValueError, OSError):
        return False
    parts = rel.parts
    return len(parts) == 1 or (len(parts) > 1 and parts[0].lower() == "docs")


def headings(text: str) -> list[tuple[int, str]]:
    """(1-based line number, heading line) for each `#` heading outside code fences."""
    out: list[tuple[int, str]] = []
    fence = False
    for n, line in enumerate(text.splitlines(), 1):
        s = line.lstrip()
        if s.startswith("```") or s.startswith("~~~"):
            fence = not fence
            continue
        if not fence and re.match(r"#{1,6}\s", line):
            out.append((n, line.rstrip()))
    return out


def decide(payload: dict, env: dict | None = None) -> tuple[bool, str]:
    """(block?, stderr message). Pure apart from reading the target file."""
    env = os.environ if env is None else env
    if env.get("SCHERMNESS_READ_GUARD", "").lower() == "off":
        return False, ""
    if payload.get("tool_name") != "Read":
        return False, ""
    tin = payload.get("tool_input")
    if not isinstance(tin, dict):
        return False, ""
    if tin.get("offset") is not None or tin.get("limit") is not None:
        return False, ""
    raw = tin.get("file_path")
    if not isinstance(raw, str) or not raw.strip():
        return False, ""
    if not raw.lower().endswith(".md"):
        return False, ""

    path = Path(normalize_path(raw))
    cwd = payload.get("cwd")
    base = Path(normalize_path(cwd)) if isinstance(cwd, str) and cwd.strip() else Path.cwd()
    if not path.is_absolute():
        path = base / path
    root = _git_root(base)

    cfg = _load_config(root)
    if cfg.get("enabled") is False:
        return False, ""
    try:
        threshold = int(float(cfg.get("threshold_kb", DEFAULT_THRESHOLD_KB)) * 1024)
    except (TypeError, ValueError):
        threshold = DEFAULT_THRESHOLD_KB * 1024
    names_cfg = cfg.get("names", DEFAULT_NAMES)
    names = {str(n).lower() for n in names_cfg} if isinstance(names_cfg, (list, tuple)) else set(DEFAULT_NAMES)

    if not path.is_file() or not _in_scope(path, root, names):
        return False, ""
    size = path.stat().st_size
    if size <= threshold:
        return False, ""

    text = path.read_text(encoding="utf-8", errors="replace")
    total = text.count("\n") + 1
    hs = headings(text)
    lines = [
        f"read_guard: {path.name} is {size // 1024} KB / {total} lines "
        f"(limit {threshold // 1024} KB for a whole-file Read).",
        "Read it in pieces: Read(file_path, offset=<line>, limit=<n lines>) "
        "using the headings below (1-based line numbers).",
        "",
    ]
    if hs:
        shown = hs[:MAX_HEADINGS]
        lines += [f"{n:>7}  {h}" for n, h in shown]
        if len(hs) > len(shown):
            lines.append(f"... {len(hs) - len(shown)} more headings; Grep '^#' for the rest.")
    else:
        lines.append("(no '#' headings found; Grep for what you need, then Read with offset/limit)")
    return True, "\n".join(lines)


def main() -> int:
    try:
        raw = sys.stdin.read()
        if not raw.strip():
            return 0
        payload = json.loads(raw)
        if not isinstance(payload, dict):
            raise ValueError("payload is not an object")
    except Exception as e:  # unparseable -> fail open
        sys.stderr.write(f"read_guard: unparseable payload, allowing ({e})\n")
        return 0
    try:
        block, msg = decide(payload)
    except Exception as e:
        sys.stderr.write(f"read_guard: internal error, allowing ({e})\n")
        return 0
    if block:
        sys.stderr.write(msg + "\n")
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
