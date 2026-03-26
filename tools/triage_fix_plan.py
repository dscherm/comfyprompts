"""Convert fix_plan.md issues into plan.md JSON task blocks.

Bridges plan mode (fix_plan.md) to build mode (plan.md).
Uses only stdlib — no pip dependencies.

Usage:
    python tools/triage_fix_plan.py              # Interactive
    python tools/triage_fix_plan.py --dry-run    # Preview only
    python tools/triage_fix_plan.py --auto       # No confirmation
    python tools/triage_fix_plan.py --min-priority 2  # Only priority 1-2
"""

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FIX_PLAN_FILE = ROOT / "fix_plan.md"
PLAN_FILE = ROOT / "plan.md"

# Map section keywords to priorities
PRIORITY_MAP = {
    "known bugs": 1,
    "critical": 1,
    "phase 8": 2,
    "phase 9": 2,
    "high": 2,
    "medium": 3,
    "low": 4,
}


def extract_unchecked_items(text: str) -> list[dict]:
    """Find unchecked items in fix_plan.md and convert to task dicts."""
    items = []
    current_section = ""

    for line in text.splitlines():
        # Track section headers
        header_match = re.match(r"^#{1,4}\s+(.+)", line)
        if header_match:
            current_section = header_match.group(1).strip().lower()

        # Find unchecked items: - [ ] **[N] description** ...
        item_match = re.match(
            r"^- \[ \] \*\*\[(\w+)\]\s*(.+?)\*\*\s*[—-]?\s*(.*)",
            line,
        )
        if not item_match:
            continue

        task_id = item_match.group(1)
        title = item_match.group(2).strip()
        description = item_match.group(3).strip()

        # Determine priority from section
        priority = 3  # default medium
        for keyword, pri in PRIORITY_MAP.items():
            if keyword in current_section:
                priority = pri
                break

        # Determine category
        category = "feature"
        if "bug" in current_section.lower() or "fix" in title.lower():
            category = "bugfix"

        items.append({
            "id": task_id,
            "title": title,
            "description": description or title,
            "priority": priority,
            "category": category,
        })

    return items


def make_task_block(item: dict) -> str:
    """Convert an extracted item into a plan.md JSON task block."""
    task = {
        "category": item["category"],
        "priority": item["priority"],
        "description": f"[{item['id']}] {item['title']}",
        "steps": [
            f"Read existing code related to: {item['title']}",
            f"Implement: {item['description'][:200]}",
            "Write or update tests for the new functionality",
            "Run targeted tests to verify",
            "Update activity.md with changes and verification results",
        ],
        "passes": False,
    }
    return "```json\n" + json.dumps(task, indent=2) + "\n```"


def check_duplicate(plan_text: str, description: str) -> bool:
    """Check if a task with similar description already exists in plan.md."""
    # Normalize for comparison
    desc_lower = description.lower()
    return desc_lower in plan_text.lower()


def main():
    dry_run = "--dry-run" in sys.argv
    auto = "--auto" in sys.argv
    min_priority = 4
    if "--min-priority" in sys.argv:
        idx = sys.argv.index("--min-priority")
        if idx + 1 < len(sys.argv):
            min_priority = int(sys.argv[idx + 1])

    if not FIX_PLAN_FILE.exists():
        print("[triage] No fix_plan.md found.")
        sys.exit(1)

    fix_text = FIX_PLAN_FILE.read_text(encoding="utf-8")
    items = extract_unchecked_items(fix_text)

    # Filter by priority
    items = [i for i in items if i["priority"] <= min_priority]

    print(f"[triage] Found {len(items)} unchecked item(s) in fix_plan.md")

    if not items:
        return

    # Check for duplicates
    plan_text = ""
    if PLAN_FILE.exists():
        plan_text = PLAN_FILE.read_text(encoding="utf-8")

    new_items = []
    for item in items:
        desc = f"[{item['id']}] {item['title']}"
        if check_duplicate(plan_text, desc):
            print(f"  SKIP (duplicate): [{item['id']}] {item['title']}")
        else:
            new_items.append(item)

    print(f"[triage] {len(new_items)} new task(s) to add (filtered {len(items) - len(new_items)} duplicates)")

    if not new_items:
        return

    # Show preview
    for item in new_items:
        pri_label = {1: "CRITICAL", 2: "HIGH", 3: "MEDIUM", 4: "LOW"}.get(item["priority"], "?")
        print(f"  [{pri_label}] [{item['id']}] {item['title']} ({item['category']})")

    if dry_run:
        print("\n[triage] Dry run — no changes written.")
        return

    if not auto:
        response = input("\nAppend these tasks to plan.md? [y/N] ").strip().lower()
        if response != "y":
            print("[triage] Cancelled.")
            return

    # Build the append block
    blocks = ["\n\n### Phase: Triaged from fix_plan.md\n"]
    for item in new_items:
        blocks.append(make_task_block(item))
        blocks.append("")

    append_text = "\n".join(blocks) + "\n"

    # Append to plan.md
    if PLAN_FILE.exists():
        existing = PLAN_FILE.read_text(encoding="utf-8")
    else:
        existing = "# plan.md — Weather Alpha Task Queue\n\n"

    PLAN_FILE.write_text(existing + append_text, encoding="utf-8")
    print(f"[triage] Appended {len(new_items)} task(s) to plan.md")


if __name__ == "__main__":
    main()
