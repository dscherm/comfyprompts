#!/usr/bin/env python3
"""PreToolUse hook for explore-phase write-tool gating.

Implements the article's Pattern 6 (Explore-Plan-Act loop) at the
permission-enforcement layer. When the bridge pipeline is in the `explore`
or `plan` fine-grained phase (per `.schermness/phase.json`), this hook flags or
blocks Edit/Write/NotebookEdit/NotebookRead tool calls and tells the LLM
to advance the phase first.

## Activation

No-op unless ALL three are true:

1. `.schermness/phase.json` exists (i.e., bridge mode is active and a phase has
   been emitted at least once).
2. The current phase is in `{explore, plan}` — i.e., the agent is supposed
   to be reading, not writing.
3. The tool name is one of Edit / Write / NotebookEdit / NotebookRead.

Bash is intentionally NOT guarded — the `!` shortcut and existing
PowerShell/Bash workflows depend on it during exploration. The blind-TDD
path guard precedent (templates/hooks/blind_tdd_path_guard.py) sets the
same convention.

## Modes

Read from `ralph.config.json` under `bridge.enforce_phase_permissions`:

- `"off"`   — passthrough, no print
- `"warn"`  — print stderr nudge, exit 0 (default — matches gate-coupling)
- `"strict"`— exit 2 with stderr message, blocking the tool call

## Exit codes

- 0: allow (and print warning if mode=warn)
- 2: block (only in strict mode)

## Input

Reads PreToolUse hook JSON on stdin:
```json
{
  "tool_name": "Write",
  "tool_input": {"file_path": "src/foo.py", "content": "..."}
}
```
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path


PHASE_NAME = "phase.json"
CONFIG_FILE = "ralph.config.json"

# Tool names that perform writes. Bash deliberately excluded — see module docstring.
WRITE_TOOLS = {"Edit", "Write", "NotebookEdit"}

# Read-only phases — Edit/Write should be flagged here.
READ_ONLY_PHASES = {"explore", "plan"}


# Project root for this invocation. None until the payload is read, or when
# the hook is invoked outside Claude Code (direct run, tests).
_ROOT: Path | None = None


def _set_root_from_payload(payload: object) -> None:
    """Adopt the `cwd` Claude Code sent in the hook payload.

    Claude Code reports the session's working directory in every payload.
    Trusting the hook PROCESS's cwd instead is a silent-corruption bug: state
    lands wherever the shell happened to be, and nothing reports the mistake.
    That is not hypothetical -- ralph-universal accumulated a stray
    tools/.schermness/ (handoff.md, memories.md, bash_telemetry.jsonl,
    reflection_state.json) on 2026-07-16 from hooks that ran with cwd=tools/.

    Falls back to process cwd when the payload has no usable `cwd`, so direct
    invocation and tests keep working unchanged.
    """
    global _ROOT
    if not isinstance(payload, dict):
        return
    cwd = payload.get("cwd")
    if not isinstance(cwd, str) or not cwd.strip():
        return
    try:
        candidate = Path(cwd)
        if candidate.is_dir():
            _ROOT = candidate
    except (OSError, ValueError):
        pass


# Inlined copy of tools/_internal/paths.state_dir. These hooks are COPIED into
# each project, so they cannot import the harness resolver -- keep the rule in
# sync with it and with .git/hooks/post-commit, which carries a third copy in
# shell. Prefer the new name when it exists, else the legacy one; when neither
# exists, return NEW -- matching paths.DEFAULT_ON_MISSING, flipped at cutover
# 2026-08-01. All three copies must agree, or a project splits its state
# between two directories with no error.
_STATE_DIR_NAMES = (".schermness", ".ralph")


def _state_dir(root: Path) -> Path:
    for name in _STATE_DIR_NAMES:
        if (root / name).is_dir():
            return root / name
    return root / _STATE_DIR_NAMES[0]


def _git_root(start: Path) -> Path:
    """Nearest ancestor holding `.git`, else `start` unchanged.

    `.exists()` rather than `.is_dir()`: in a worktree or submodule `.git` is
    a FILE containing a gitdir pointer, and treating that as "not a repo"
    would walk straight past the root it was looking for.
    """
    try:
        start = start.resolve()
    except OSError:
        return start
    for d in (start, *start.parents):
        if (d / ".git").exists():
            return d
    return start


def _repo_root() -> Path:
    """Project root: the git root at or above the session cwd.

    Anchoring to the git root, not to the cwd itself. The cwd is where the
    session happens to be standing, which is not the same thing: `cd tools`
    inside this repo made hooks write state to `tools/.schermness/` -- four files
    that then got committed. Trusting the payload cwd (2026-07-16) fixed
    hooks running from an unrelated directory; it does not fix a cwd that is
    a genuine SUBDIRECTORY of the project, which is the common case.

    Worse for the guards than for telemetry: a guard resolving to the wrong
    root reads no active session and fails OPEN, silently.

    Falls back to the unanchored path outside a repo, so tests and direct
    invocation behave as before.
    """
    return _git_root(_ROOT if _ROOT is not None else Path.cwd())


def _read_json(path: Path) -> dict | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def _mode_from_config(project_dir: Path) -> str:
    """Resolve enforcement mode. Default: warn."""
    env = os.environ.get("RALPH_PHASE_GUARD")
    if env in ("off", "warn", "strict"):
        return env
    cfg = _read_json(project_dir / CONFIG_FILE) or {}
    bridge = cfg.get("bridge") or {}
    mode = bridge.get("enforce_phase_permissions")
    if mode in ("off", "warn", "strict"):
        return mode
    return "warn"


def _file_path_from_input(tool_name: str, tool_input: dict) -> str:
    if tool_name in {"Edit", "Write"}:
        return str(tool_input.get("file_path") or "")
    if tool_name == "NotebookEdit":
        return str(tool_input.get("notebook_path") or "")
    return ""


def main() -> int:
    try:
        raw = sys.stdin.read()
    except (OSError, UnicodeDecodeError):
        return 0
    if not raw.strip():
        return 0

    try:
        hook = json.loads(raw)
        _set_root_from_payload(hook)
    except json.JSONDecodeError:
        return 0

    tool_name = hook.get("tool_name") or ""
    if tool_name not in WRITE_TOOLS:
        return 0

    project_dir = _repo_root()
    phase_rec = _read_json(_state_dir(project_dir) / PHASE_NAME)
    if not phase_rec:
        return 0  # no bridge phase tracking → no-op

    phase = phase_rec.get("phase")
    if phase not in READ_ONLY_PHASES:
        return 0

    mode = _mode_from_config(project_dir)
    if mode == "off":
        return 0

    tool_input = hook.get("tool_input") or {}
    target = _file_path_from_input(tool_name, tool_input)
    target_str = f" on `{target}`" if target else ""

    suggestion_phase = "implement"
    task_id = phase_rec.get("active_task_id") or "<task-id>"

    msg_lines = [
        f"[phase-guard] {tool_name}{target_str} during phase `{phase}` — "
        f"this phase is intended to be read-only.",
        f"  Advance to `{suggestion_phase}` first:",
        f"    python $RALPH_HOME/tools/phase_state.py set {suggestion_phase} --task {task_id}",
    ]
    if mode == "warn":
        msg_lines.append(
            "  Mode: warn (set `bridge.enforce_phase_permissions: \"strict\"` in "
            "ralph.config.json to block instead of nudge)."
        )
    elif mode == "strict":
        msg_lines.append(
            "  Mode: strict — call blocked. Advance the phase, then retry."
        )

    print("\n".join(msg_lines), file=sys.stderr)

    if mode == "strict":
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
