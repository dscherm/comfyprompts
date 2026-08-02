#!/usr/bin/env python3
"""PreToolUse hook for Bash command telemetry (no blocking).

Records every Bash invocation to `.ralph/bash_telemetry.jsonl` with the
parsed verb, flag list, and a low-risk/high-risk classification — purely
informational. Never blocks; exit 0 unconditionally.

This is the **telemetry-only first step** toward the article's Pattern 10
(Command Risk Classification). Before adding a deny/ask classifier, we
need data on what verbs the LLM actually runs. Once a few weeks of
telemetry accumulate, we can decide whether to promote any verbs to
deny/ask based on actual usage shape, not anticipated risk.

## Output schema (one JSONL row per Bash call)

```json
{
  "timestamp": "2026-05-11T20:00:00Z",
  "command_preview": "git status --short",     // first 200 chars
  "verb": "git",
  "subverb": "status",                          // 2nd token if not a flag
  "flags": ["--short"],
  "risk_class": "safe|read|write|destructive|unknown",
  "phase": "implement"                          // from phase.json if active
}
```

## Risk classification (purely heuristic)

| Class | Examples |
|---|---|
| safe | `ls`, `pwd`, `echo`, `python -c`, `cat`, `head`, `tail`, `which` |
| read | `git status`, `git log`, `git diff`, `grep`, `find`, `cat`, `jq` |
| write | `git add`, `git commit`, `git checkout`, `npm install`, `pip install`, `mkdir`, `touch`, `cp`, `mv` |
| destructive | `rm`, `git push --force`, `git reset --hard`, `git clean`, `dd`, `rmdir`, `> file`, `chmod -R 777` |
| unknown | everything else |

Classification is intentionally conservative: a command parsed as
`destructive` is one a future enforcement hook MIGHT want to block, not
necessarily one that's wrong now.

Stdlib only.

## Exit codes

Always 0 (telemetry never blocks). Failure during parse/log writing
prints to stderr but doesn't fail the tool call.
"""

from __future__ import annotations

import json
import re
import shlex
import sys
from datetime import datetime, timezone
from pathlib import Path


TELEMETRY_NAME = "bash_telemetry.jsonl"
PHASE_NAME = "phase.json"

# Verb-level risk hint (matches "first token" of the command).
SAFE_VERBS = {
    "ls", "pwd", "echo", "cat", "head", "tail", "which", "where", "wc",
    "true", "false", "date", "uname", "whoami", "hostname",
}
READ_VERBS = {
    "grep", "rg", "ripgrep", "find", "fd", "jq", "yq", "diff",
}
WRITE_VERBS = {
    "mkdir", "touch", "cp", "mv", "ln",
    "npm", "pip", "pip3", "npx", "uv",
    "python", "python3", "node", "go", "cargo", "rustc",
    "pytest", "vitest", "jest", "mocha",
    "make",
}
DESTRUCTIVE_VERBS = {
    "rm", "rmdir", "dd", "shred", "wipefs",
}

# Destructive flag patterns (apply within a known verb).
DESTRUCTIVE_FLAGS = {
    "git": [
        # ordered: (subverb_or_None, flag_pattern)
        ("push", re.compile(r"--force\b|--force-with-lease=|-f\b")),
        ("reset", re.compile(r"--hard\b")),
        ("clean", re.compile(r"-fd\b|-f\b")),
        ("checkout", re.compile(r"^--$")),  # `git checkout -- file`
        ("branch", re.compile(r"-D\b")),
    ],
}


def _read_json(path: Path) -> dict | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def _parse_command(raw: str) -> tuple[str | None, str | None, list[str]]:
    """Return (verb, subverb, flags). Robust to shell quirks via shlex.

    Best-effort: malformed quoting falls back to whitespace split.
    """
    raw = raw.strip()
    if not raw:
        return None, None, []
    try:
        tokens = shlex.split(raw, posix=True)
    except ValueError:
        tokens = raw.split()
    if not tokens:
        return None, None, []
    verb = tokens[0]
    rest = tokens[1:]
    subverb = None
    flags: list[str] = []
    for t in rest:
        if t.startswith("-"):
            flags.append(t)
        elif subverb is None and not t.startswith("-"):
            subverb = t
        else:
            # Positional argument we don't classify here; ignore for telemetry.
            pass
    return verb, subverb, flags


def _classify(verb: str | None, subverb: str | None, flags: list[str], raw: str) -> str:
    """Return one of safe|read|write|destructive|unknown."""
    if not verb:
        return "unknown"
    v = verb.lower()

    # Special-case `>` / `>>` shell redirects in the raw command.
    if re.search(r"(?<!\w)>(?!=)\s*\S", raw):
        # `>` not `>=`. Captures `cmd > file` but not `cmd >= other`.
        if not re.search(r"&\s*>\s*", raw) and " > /dev/null" not in raw:
            # Crude — flag any non-/dev/null redirect as `write`.
            base = _verb_class(v)
            if base in ("safe", "read", "unknown"):
                return "write"

    # Check destructive flag combos within a known verb.
    if v in DESTRUCTIVE_FLAGS:
        for sub, pattern in DESTRUCTIVE_FLAGS[v]:
            if sub is not None and (subverb or "") != sub:
                continue
            flag_str = " ".join(flags)
            if pattern.search(flag_str):
                return "destructive"

    # Special destructive: `chmod -R 777`, `chown -R root`.
    if v == "chmod" and "-R" in flags and any("777" in f for f in flags):
        return "destructive"

    return _verb_class(v)


def _verb_class(v: str) -> str:
    if v in DESTRUCTIVE_VERBS:
        return "destructive"
    if v in WRITE_VERBS:
        return "write"
    if v in READ_VERBS:
        return "read"
    if v in SAFE_VERBS:
        return "safe"
    if v == "git":
        # Bare `git` with a non-destructive subverb is read or write —
        # caller falls through after the destructive-flag check.
        return "read"  # conservative default; git status/log/diff dominate.
    return "unknown"


def _record(payload: dict) -> None:
    project_dir = _repo_root()
    out = _state_dir(project_dir) / TELEMETRY_NAME
    try:
        out.parent.mkdir(parents=True, exist_ok=True)
        with out.open("a", encoding="utf-8") as f:
            f.write(json.dumps(payload, ensure_ascii=False) + "\n")
    except OSError as e:
        print(f"[bash-telemetry] write failed: {e}", file=sys.stderr)


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


def main() -> int:
    try:
        raw_in = sys.stdin.read()
    except (OSError, UnicodeDecodeError):
        return 0
    if not raw_in.strip():
        return 0
    try:
        hook = json.loads(raw_in)
        _set_root_from_payload(hook)
    except json.JSONDecodeError:
        return 0

    if hook.get("tool_name") != "Bash":
        return 0

    tool_input = hook.get("tool_input") or {}
    command = tool_input.get("command")
    if not isinstance(command, str):
        return 0

    verb, subverb, flags = _parse_command(command)
    risk = _classify(verb, subverb, flags, command)

    phase = None
    phase_rec = _read_json(_state_dir(_repo_root()) / PHASE_NAME)
    if phase_rec:
        phase = phase_rec.get("phase")

    payload = {
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "command_preview": command[:200],
        "verb": verb,
        "subverb": subverb,
        "flags": flags[:20],
        "risk_class": risk,
        "phase": phase,
    }
    _record(payload)
    return 0


if __name__ == "__main__":
    sys.exit(main())
