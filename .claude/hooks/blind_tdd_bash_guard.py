#!/usr/bin/env python3
"""PreToolUse hook for blind TDD Bash enforcement (Layer 2, in-session model).

The path-guard hook deliberately does NOT guard Bash (its docstring notes it
relies on "Layer 2: SDK tool scoping or settings.json Bash(...) allow/deny").
That settings-based deny-list worked for the `claude -p` spawner, which swapped
in a role-specific settings.local.json per spawn. The in-session model (blind
agents run as Agent-tool subagents) drops that per-spawn settings swap, so Bash
would be unguarded — a blind runner could `cat src/foo.py` and defeat blindness.

This hook closes that hole. When a blind session is active it enforces, per role:

  - test_writer / arbiter : Bash is denied entirely (they have no Bash need).
  - test_runner           : Bash is allowed ONLY for test-runner commands
                            (pytest, npm test, dotnet test, ...). Inspection
                            commands (cat/grep/find/...) and command
                            substitution are blocked. Fail-closed: anything not
                            recognized as a test command is denied.

No active session => passthrough (allow all), exactly like the path guard, so it
is safe to ship always-on in the plugin.

Exit codes: 0 allow, 2 block (stderr shown to the agent). Pure stdlib, 3.9+.
"""

from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path


# Project root for this invocation. None until the payload is read, or when
# the hook is invoked outside Claude Code (direct run, tests).
_ROOT: Path | None = None


def _set_root_from_payload(payload: object) -> None:
    """Adopt the `cwd` Claude Code sent in the hook payload.

    Claude Code reports the session's working directory in every payload.
    Trusting the hook PROCESS's cwd instead is a silent-corruption bug: state
    lands wherever the shell happened to be, and nothing reports the mistake.
    That is not hypothetical -- ralph-universal accumulated a stray
    tools/.ralph/ (handoff.md, memories.md, bash_telemetry.jsonl,
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
    inside this repo made hooks write state to `tools/.ralph/` -- four files
    that then got committed. Trusting the payload cwd (2026-07-16) fixed
    hooks running from an unrelated directory; it does not fix a cwd that is
    a genuine SUBDIRECTORY of the project, which is the common case.

    Worse for the guards than for telemetry: a guard resolving to the wrong
    root reads no active session and fails OPEN, silently.

    Falls back to the unanchored path outside a repo, so tests and direct
    invocation behave as before.
    """
    return _git_root(_ROOT if _ROOT is not None else Path.cwd())


def _session_file() -> Path:
    return _repo_root() / ".themis" / "blind_tdd" / "active_session.json"


def _load_session() -> dict | None:
    p = _session_file()
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        # Corrupt session => fail closed: deny Bash until fixed.
        return {"session_id": "corrupt", "agent_role": "unknown"}


# Test-runner commands a blind runner is allowed to execute. Anchored at the
# start of each shell segment. Kept in sync with settings.blind-runner.json.
_ALLOWED_TEST = [
    r"pytest\b",
    r"python3?\s+-m\s+pytest\b",
    r"py\s+-m\s+pytest\b",
    r"coverage\s+run\b",
    r"python3?\s+-m\s+coverage\b",
    r"tox\b",
    r"npm\s+(run\s+)?test\b",
    r"yarn\s+(run\s+)?test\b",
    r"pnpm\s+(run\s+)?test\b",
    r"jest\b",
    r"vitest\b",
    r"dotnet\s+test\b",
    r"cargo\s+test\b",
    r"go\s+test\b",
    r"mvn\s+test\b",
    r"gradle\s+test\b",
    # GDScript/Godot headless test runs. The target must be a test SCENE
    # (.tscn) or GUT's cmdline runner (gut_cmdln.gd), or a cache-warming
    # --import pass. A bare `-s <arbitrary>.gd` is deliberately NOT allowed:
    # godot executes any GDScript, so an unconstrained `-s` would let the
    # runner read source and defeat its src-blindness. The binary may be
    # `godot`/`godot4`, the `$GODOT`/`${GODOT}` env override, or a quoted
    # absolute path to a Godot .exe; each match stays within one shell segment.
    r'"?(?:godot\w*(?:\.exe)?|\$\{?GODOT\}?|[^"|;&]*[Gg]odot[^"|;&]*\.exe)"?[^|;&]*--headless[^|;&]*(?:\.tscn|gut_cmdln\.gd)\b',
    r'"?(?:godot\w*(?:\.exe)?|\$\{?GODOT\}?|[^"|;&]*[Gg]odot[^"|;&]*\.exe)"?[^|;&]*--headless[^|;&]*--import\b',
]
_ALLOWED_RE = [re.compile(r"^\s*" + p, re.IGNORECASE) for p in _ALLOWED_TEST]

# Split a command line into independently-executed segments.
_SEGMENT_SPLIT = re.compile(r"&&|\|\||;|\||\n|&")


def _segments(command: str) -> list[str]:
    return [s.strip() for s in _SEGMENT_SPLIT.split(command) if s.strip()]


def evaluate(command: str, role: str) -> tuple[bool, str]:
    """Return (allowed, reason) for a Bash command under an active blind session."""
    if role in ("test_writer", "arbiter"):
        return False, f"role {role!r} may not use Bash during a blind session"

    if role != "test_runner":
        # Unknown/other role with an active session -> fail closed.
        return False, f"Bash denied for role {role!r} during a blind session"

    if not command or not command.strip():
        return False, "empty Bash command"

    # Command substitution can smuggle a file read into an allowed command.
    if "$(" in command or "`" in command:
        return False, "command substitution ($(...) / backticks) is not allowed"

    segments = _segments(command)
    for seg in segments:
        if not any(rx.match(seg) for rx in _ALLOWED_RE):
            return False, (
                f"segment {seg!r} is not an allowed test command; the blind "
                f"runner may run only test-runner commands (pytest, npm test, "
                f"dotnet test, ...)"
            )
    return True, "all segments are allowed test commands"


def _write_audit(session: dict, command: str, allowed: bool, reason: str) -> None:
    audit_dir = _repo_root() / ".themis" / "blind_audit"
    try:
        audit_dir.mkdir(parents=True, exist_ok=True)
        sid = session.get("session_id", "unknown")
        rec = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "session_id": sid,
            "agent_role": session.get("agent_role"),
            "task_id": session.get("task_id"),
            "tool_name": "Bash",
            "command": command[:500],
            "allowed": allowed,
            "reason": reason,
            "source": "pretooluse_hook",
        }
        with (audit_dir / f"{sid}.jsonl").open("a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    except OSError:
        pass  # audit failure never blocks the call


def main() -> int:
    try:
        raw = sys.stdin.read()
    except (OSError, UnicodeDecodeError):
        return 0  # fail open on hook I/O error
    if not raw.strip():
        return 0
    try:
        hook_data = json.loads(raw)
        _set_root_from_payload(hook_data)
    except json.JSONDecodeError:
        return 0

    if hook_data.get("tool_name") != "Bash":
        return 0

    session = _load_session()
    if session is None:
        return 0  # no active blind session => passthrough

    # A session IS active from here, so the failure direction inverts. Above
    # this line the hook fails OPEN (no session, nothing to protect, and a
    # guard bug must not wedge every Bash call in every enrolled project);
    # below it, failing open lets a blind agent read implementation through
    # the shell -- the exact bypass this guard exists to close. An unhandled
    # raise exits 1, and Claude Code treats any non-2 exit as a NON-blocking
    # error, so the command runs. `_load_session` already applies this rule to
    # its own branch: a corrupt session file denies rather than passes through.
    try:
        return _decide(hook_data, session)
    except Exception as e:  # noqa: BLE001 -- deliberate catch-all, see above
        print(
            f"[blind-tdd] BLOCKED Bash: guard raised {type(e).__name__}: {e} "
            f"while a blind-TDD session is active (session "
            f"{session.get('session_id', '?')}). Blocking rather than allowing "
            f"-- a guard that cannot decide must not grant access.",
            file=sys.stderr,
        )
        return 2


def _decide(hook_data: dict, session: dict) -> int:
    """Allow (0) or block (2) one Bash call against an ACTIVE blind session."""
    command = (hook_data.get("tool_input") or {}).get("command", "") or ""
    role = session.get("agent_role", "unknown")
    allowed, reason = evaluate(command, role)
    _write_audit(session, command, allowed, reason)

    if allowed:
        return 0

    print(
        f"[blind-tdd] BLOCKED Bash: {reason}. Session {session.get('session_id', '?')}, "
        f"role {role}. Blind agents must not inspect implementation via the shell; "
        f"use the Read tool for allowed paths, or run only test commands.",
        file=sys.stderr,
    )
    return 2


if __name__ == "__main__":
    sys.exit(main())
