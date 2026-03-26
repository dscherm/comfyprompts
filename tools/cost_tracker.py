"""Read .ralph/metrics.jsonl and report cost estimates.

Uses only stdlib — no pip dependencies.

Usage:
    python tools/cost_tracker.py          # Current run stats
    python tools/cost_tracker.py --all    # Include mini-ralph stats
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RALPH_DIR = ROOT / ".ralph"
METRICS_FILE = RALPH_DIR / "metrics.jsonl"

# Claude Opus pricing (per million tokens)
INPUT_COST_PER_M = 15.0
OUTPUT_COST_PER_M = 75.0


def load_metrics(path: Path) -> list[dict]:
    """Load metrics from a JSONL file."""
    if not path.exists():
        return []
    entries = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return entries


def format_cost(cost: float) -> str:
    return f"${cost:.2f}"


def format_duration(seconds: float) -> str:
    if seconds < 60:
        return f"{seconds:.0f}s"
    if seconds < 3600:
        return f"{seconds / 60:.1f}m"
    return f"{seconds / 3600:.1f}h"


def report(entries: list[dict], label: str = "Main Loop"):
    if not entries:
        print(f"\n{label}: No metrics recorded yet.")
        return

    total_input = sum(e.get("input_tokens_est", 0) for e in entries)
    total_output = sum(e.get("output_tokens_est", 0) for e in entries)
    total_cost = (total_input * INPUT_COST_PER_M + total_output * OUTPUT_COST_PER_M) / 1_000_000
    durations = [e.get("duration_s", 0) for e in entries if e.get("duration_s", 0) > 0]
    gate_results = [e.get("gate_result", "unknown") for e in entries]
    gate_pass = gate_results.count("pass")
    gate_fail = gate_results.count("fail")

    print(f"\n{'=' * 50}")
    print(f"  {label}")
    print(f"{'=' * 50}")
    print(f"  Iterations:       {len(entries)}")
    print(f"  Input tokens:     {total_input:,}")
    print(f"  Output tokens:    {total_output:,}")
    print(f"  Estimated cost:   {format_cost(total_cost)}")
    if durations:
        print(f"  Avg duration:     {format_duration(sum(durations) / len(durations))}")
        print(f"  Min duration:     {format_duration(min(durations))}")
        print(f"  Max duration:     {format_duration(max(durations))}")
    if gate_pass + gate_fail > 0:
        rate = gate_pass / (gate_pass + gate_fail) * 100
        print(f"  Gate pass rate:   {rate:.0f}% ({gate_pass}/{gate_pass + gate_fail})")
    print(f"{'=' * 50}")


def main():
    include_all = "--all" in sys.argv

    entries = load_metrics(METRICS_FILE)
    report(entries, "Main Loop")

    if include_all:
        mini_dir = RALPH_DIR / "mini"
        if mini_dir.exists():
            for task_dir in sorted(mini_dir.iterdir()):
                mini_metrics = task_dir / "metrics.jsonl"
                if mini_metrics.exists():
                    mini_entries = load_metrics(mini_metrics)
                    report(mini_entries, f"Mini: {task_dir.name}")


if __name__ == "__main__":
    main()
