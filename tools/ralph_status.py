"""Dashboard showing Ralph Loop status.

Uses only stdlib — no pip dependencies.

Usage:
    python tools/ralph_status.py            # Full dashboard
    python tools/ralph_status.py --oneline  # Compact one-liner
"""

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RALPH_DIR = ROOT / ".ralph"
PLAN_FILE = ROOT / "plan.md"
ACTIVITY_FILE = ROOT / "activity.md"
METRICS_FILE = RALPH_DIR / "metrics.jsonl"


def count_tasks() -> tuple[int, int, dict]:
    """Count total, done, and pending-by-priority from plan.md."""
    if not PLAN_FILE.exists():
        return 0, 0, {}

    text = PLAN_FILE.read_text(encoding="utf-8")
    pattern = re.compile(r"```json\s*\n(.*?)\n\s*```", re.DOTALL)

    total = 0
    done = 0
    pending_by_pri = {}

    for match in pattern.finditer(text):
        try:
            task = json.loads(match.group(1))
        except json.JSONDecodeError:
            continue
        total += 1
        if task.get("passes", False):
            done += 1
        else:
            pri = task.get("priority", 3)
            pending_by_pri[pri] = pending_by_pri.get(pri, 0) + 1

    return total, done, pending_by_pri


def load_metrics() -> list[dict]:
    if not METRICS_FILE.exists():
        return []
    entries = []
    for line in METRICS_FILE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return entries


def detect_anomalies(entries: list[dict]) -> list[str]:
    """Flag anomalous iterations."""
    if len(entries) < 3:
        return []

    anomalies = []
    durations = [e.get("duration_s", 0) for e in entries if e.get("duration_s", 0) > 0]
    avg_dur = sum(durations) / len(durations) if durations else 0

    for i, e in enumerate(entries):
        dur = e.get("duration_s", 0)
        if avg_dur > 0 and dur > avg_dur * 2:
            anomalies.append(f"Iteration {e.get('iteration', i)}: {dur:.0f}s (>2x avg {avg_dur:.0f}s)")
        if e.get("files_changed", -1) == 0:
            anomalies.append(f"Iteration {e.get('iteration', i)}: 0 files changed")

    # Consecutive gate failures
    consec = 0
    max_consec = 0
    for e in entries:
        if e.get("gate_result") == "fail":
            consec += 1
            max_consec = max(max_consec, consec)
        else:
            consec = 0
    if max_consec >= 3:
        anomalies.append(f"Max consecutive gate failures: {max_consec}")

    return anomalies


def main():
    oneline = "--oneline" in sys.argv

    total, done, pending_by_pri = count_tasks()
    pending = total - done
    metrics = load_metrics()

    if oneline:
        gate_pass = sum(1 for e in metrics if e.get("gate_result") == "pass")
        gate_total = sum(1 for e in metrics if e.get("gate_result") in ("pass", "fail"))
        rate = f"{gate_pass}/{gate_total}" if gate_total else "n/a"
        print(f"Tasks: {done}/{total} done | Pending: {pending} | Iterations: {len(metrics)} | Gate: {rate}")
        return

    pri_labels = {1: "CRITICAL", 2: "HIGH", 3: "MEDIUM", 4: "LOW"}

    print("=" * 50)
    print("  RALPH STATUS — Weather Alpha")
    print("=" * 50)
    print(f"\n  Tasks: {done}/{total} completed, {pending} pending")
    for pri in sorted(pending_by_pri.keys()):
        label = pri_labels.get(pri, f"P{pri}")
        print(f"    {label}: {pending_by_pri[pri]}")

    if metrics:
        durations = [e.get("duration_s", 0) for e in metrics if e.get("duration_s", 0) > 0]
        gate_pass = sum(1 for e in metrics if e.get("gate_result") == "pass")
        gate_fail = sum(1 for e in metrics if e.get("gate_result") == "fail")

        print(f"\n  Iterations: {len(metrics)}")
        if durations:
            avg = sum(durations) / len(durations)
            total_time = sum(durations)
            velocity = done / (total_time / 3600) if total_time > 0 else 0
            print(f"  Avg duration: {avg:.0f}s")
            print(f"  Total time:   {total_time / 60:.1f}m")
            print(f"  Velocity:     {velocity:.1f} tasks/hr")
        if gate_pass + gate_fail > 0:
            rate = gate_pass / (gate_pass + gate_fail) * 100
            print(f"  Gate pass:    {rate:.0f}% ({gate_pass}/{gate_pass + gate_fail})")

        anomalies = detect_anomalies(metrics)
        if anomalies:
            print(f"\n  ANOMALIES:")
            for a in anomalies:
                print(f"    ! {a}")
    else:
        print("\n  No iteration metrics yet.")

    print(f"\n{'=' * 50}")


if __name__ == "__main__":
    main()
