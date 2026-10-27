#!/usr/bin/env python3
"""SubagentStop hook: warn when a subagent's promised deliverable file is missing.

ADVISORY ONLY. It never blocks and always exits 0. A subagent can stop having
answered in chat but never written the report file the orchestrator is about to
read; the orchestrator finds out a step later, as a confusing FileNotFoundError.

## The fixed phrase

The scherm dispatch template (skills/scherm/SKILL.md) ends deliverables with:

    Write your report to `<path>`

This hook finds that phrase in the dispatch prompt and checks `<path>` exists.
No phrase -> silent. Placeholder paths (`<path>`, `$VAR`) -> silent.

## Where the dispatch prompt comes from

The SubagentStop payload does NOT carry the prompt. Fields (Claude Code 2.1.310
type definitions, mods/types/claude-code.d.ts): session_id, transcript_path,
cwd, agent_id, agent_transcript_path, agent_type, stop_hook_active,
last_assistant_message. `agent_transcript_path` is the subagent's own JSONL, and
its FIRST line is the dispatch prompt (message.content, string or text blocks;
observed in ~/.claude/projects/*/subagents/agent-*.jsonl). This hook reads that.
Fallback: if the field is absent, derive
`<dirname(transcript_path)>/<session>/subagents/agent-<agent_id>.jsonl`.

Relative paths resolve against the payload `cwd`. Fails open on everything.

## Leftover resources (GD-7)

It also asks `$SCHERMNESS_HOME/tools/agent_resources.py` (dry run) whether the
stopping agent's `agent_id` still owns registered processes or dirs, and warns
if so. Agents register from their worktree, `agent-<agent_id>`, so the id
matches without the agent knowing it.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path

PHRASE = re.compile(r"Write your report to\s+`([^`\n]+)`")
_MSYS_DRIVE = re.compile(r"^/(?:cygdrive/|mnt/)?([A-Za-z])(?:/|$)")


def normalize_path(raw: str) -> str:
    p = raw.strip()
    if os.name == "nt":
        m = _MSYS_DRIVE.match(p)
        if m:
            p = f"{m.group(1).upper()}:/" + p[m.end():]
        p = p.replace("\\", "/")
    return p


def _content_text(content) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "\n".join(b.get("text", "") for b in content
                         if isinstance(b, dict) and b.get("type") == "text")
    return ""


def first_prompt(transcript: Path) -> str:
    """The dispatch prompt: first user message in the subagent transcript."""
    with transcript.open(encoding="utf-8", errors="replace") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except ValueError:
                continue
            msg = rec.get("message") if isinstance(rec, dict) else None
            if isinstance(msg, dict) and msg.get("role", "user") == "user":
                return _content_text(msg.get("content"))
    return ""


def _transcript_for(payload: dict) -> "Path | None":
    raw = payload.get("agent_transcript_path")
    if isinstance(raw, str) and raw.strip():
        return Path(normalize_path(raw))
    main, aid = payload.get("transcript_path"), payload.get("agent_id")
    if isinstance(main, str) and main.strip() and aid:
        m = Path(normalize_path(main))
        return m.parent / m.stem / "subagents" / f"agent-{aid}.jsonl"
    return None


def promised_paths(prompt: str) -> list[str]:
    out = []
    for p in PHRASE.findall(prompt):
        p = p.strip()
        if not p or "<" in p or "$" in p:
            continue
        out.append(p)
    return out


def missing_artifacts(payload: dict) -> list[str]:
    tp = _transcript_for(payload)
    if tp is None or not tp.is_file():
        return []
    cwd = payload.get("cwd")
    base = Path(normalize_path(cwd)) if isinstance(cwd, str) and cwd.strip() else Path.cwd()
    missing = []
    for p in promised_paths(first_prompt(tp)):
        path = Path(normalize_path(p))
        if not path.is_absolute():
            path = base / path
        if not path.exists():
            missing.append(p)
    return missing


def leftover_resources(payload: dict) -> list[str]:
    """GD-7: what the stopping agent registered and did not clean up.

    Runs `agent_resources.py cleanup --owner <agent_id> --dry-run --quick` from
    the harness clone. The dry run changes nothing; this only reports. No
    harness, no agent_id, or any failure -> [].
    """
    aid = payload.get("agent_id")
    home = os.environ.get("SCHERMNESS_HOME") or os.environ.get("RALPH_HOME")
    if not aid or not home:
        return []
    tool = Path(normalize_path(home)) / "tools" / "agent_resources.py"
    if not tool.is_file():
        return []
    r = subprocess.run([sys.executable, str(tool), "cleanup", "--owner", str(aid),
                        "--dry-run", "--quick", "--json"],
                       capture_output=True, text=True, timeout=10)
    if r.returncode != 0:
        return []
    items = json.loads(r.stdout).get("items", [])
    return [i.get("path") or f"pid {i.get('pid')}" for i in items
            if i.get("action") in ("would-stop", "would-delete")]


def main() -> int:
    try:
        raw = sys.stdin.read()
        if not raw.strip():
            return 0
        payload = json.loads(raw)
        if not isinstance(payload, dict):
            return 0
        missing = missing_artifacts(payload)
    except Exception as e:
        sys.stderr.write(f"agent_artifact_check: skipped ({e})\n")
        return 0
    try:
        leftovers = leftover_resources(payload)
    except Exception as e:
        sys.stderr.write(f"agent_artifact_check: resource check skipped ({e})\n")
        leftovers = []
    who = payload.get("agent_type") or "subagent"
    msgs = []
    if missing:
        msgs.append(f"agent_artifact_check: {who} stopped without writing "
                    f"{', '.join(missing)} (named in its dispatch prompt).")
    if leftovers:
        msgs.append(f"agent_artifact_check: {who} left {len(leftovers)} registered "
                    f"resource(s) running or on disk: {', '.join(leftovers)}. Run "
                    f"`agent_resources.py cleanup --owner {payload.get('agent_id')}`.")
    for msg in msgs:
        sys.stderr.write(msg + "\n")
    if msgs:
        sys.stdout.write(json.dumps({"systemMessage": " ".join(msgs)}) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
