"""Extract pending tasks and recent activity into slim context files.

Runs before each iteration to minimize token usage.
Uses only stdlib — no pip dependencies.

Usage: python tools/prepare_context.py
"""

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RALPH_DIR = ROOT / ".ralph"
PLAN_FILE = ROOT / "plan.md"
ACTIVITY_FILE = ROOT / "activity.md"
PENDING_OUT = RALPH_DIR / "pending_tasks.md"
RECENT_OUT = RALPH_DIR / "recent_activity.md"

RECENT_ACTIVITY_COUNT = 5  # Keep last N activity entries


def extract_pending_tasks() -> str:
    """Parse plan.md, extract pending tasks sorted by priority."""
    if not PLAN_FILE.exists():
        return "# Pending Tasks (auto-generated)\n\nNo plan.md found.\n"

    text = PLAN_FILE.read_text(encoding="utf-8")

    # Find all JSON blocks inside triple-backtick fences
    pattern = re.compile(r"```json\s*\n(.*?)\n\s*```", re.DOTALL)
    tasks = []

    for match in pattern.finditer(text):
        try:
            task = json.loads(match.group(1))
        except json.JSONDecodeError:
            continue

        if task.get("passes", False):
            continue  # Skip completed tasks

        tasks.append(task)

    # Sort by priority (ascending — 1=critical first)
    tasks.sort(key=lambda t: t.get("priority", 3))

    lines = ["# Pending Tasks (auto-generated)", ""]
    if not tasks:
        lines.append("No pending tasks. All tasks complete.")
    else:
        lines.append(f"{len(tasks)} pending task(s), sorted by priority:\n")
        for i, task in enumerate(tasks, 1):
            pri = task.get("priority", 3)
            pri_label = {1: "CRITICAL", 2: "HIGH", 3: "MEDIUM", 4: "LOW"}.get(pri, "?")
            cat = task.get("category", "?")
            desc = task.get("description", "No description")
            lines.append(f"### Task {i} [{pri_label}] ({cat})")
            lines.append(f"**{desc}**\n")
            steps = task.get("steps", [])
            for j, step in enumerate(steps, 1):
                lines.append(f"{j}. {step}")
            lines.append("")

    return "\n".join(lines) + "\n"


def extract_recent_activity() -> str:
    """Extract the last N activity entries from activity.md."""
    if not ACTIVITY_FILE.exists():
        return "# Recent Activity (auto-generated)\n\nNo activity.md found.\n"

    text = ACTIVITY_FILE.read_text(encoding="utf-8")

    # Split on entry headers (## YYYY-MM-DD ...)
    entry_pattern = re.compile(r"^(## \d{4}-\d{2}-\d{2}\b.*)$", re.MULTILINE)
    positions = [m.start() for m in entry_pattern.finditer(text)]

    if not positions:
        return "# Recent Activity (auto-generated)\n\nNo activity entries yet.\n"

    # Extract entries (each entry is from one ## header to the next)
    entries = []
    for i, pos in enumerate(positions):
        end = positions[i + 1] if i + 1 < len(positions) else len(text)
        entries.append(text[pos:end].rstrip())

    # Keep last N
    recent = entries[-RECENT_ACTIVITY_COUNT:]

    lines = [
        "# Recent Activity (auto-generated)",
        f"Showing last {len(recent)} of {len(entries)} total entries.\n",
    ]
    for entry in recent:
        lines.append(entry)
        lines.append("")

    return "\n".join(lines) + "\n"


def main():
    RALPH_DIR.mkdir(parents=True, exist_ok=True)

    pending = extract_pending_tasks()
    PENDING_OUT.write_text(pending, encoding="utf-8")
    task_count = pending.count("### Task ")
    print(f"[prepare_context] Wrote {task_count} pending task(s) to {PENDING_OUT.name}")

    recent = extract_recent_activity()
    RECENT_OUT.write_text(recent, encoding="utf-8")
    entry_count = recent.count("## 20")
    print(f"[prepare_context] Wrote {entry_count} recent activity entry(s) to {RECENT_OUT.name}")


if __name__ == "__main__":
    main()
