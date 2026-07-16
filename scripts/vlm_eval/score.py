"""Score judge.py verdicts against scripts/vlm_eval/labels.json ground truth.

Reports aggregate binary (defect present / not) accuracy, per-defect-type recall,
false-positive rate on clean renders (the metric that matters most for a QA gate —
a judge that cries wolf on good assets is useless), defect-type identification
accuracy, parse-error count, and latency stats.

Pass multiple --verdicts files to print a side-by-side model comparison.

Usage:
    python scripts/vlm_eval/score.py --verdicts scripts/vlm_eval/verdicts_qwen3-vl-8b.json
    python scripts/vlm_eval/score.py \\
        --verdicts scripts/vlm_eval/verdicts_qwen3-vl-8b.json \\
        --verdicts scripts/vlm_eval/verdicts_qwen3-vl-32b.json
"""

from __future__ import annotations

import argparse
import json
import statistics
from dataclasses import dataclass
from pathlib import Path

DEFECT_TYPES: list[str] = [
    "flipped_normals",
    "unwelded_cracks",
    "missing_texture",
    "uv_smear",
    "scale_error",
    "wrong_orientation",
]


@dataclass
class Metrics:
    model: str
    source: str
    total: int
    parsed: int
    parse_errors: int
    binary_accuracy: float
    per_defect_recall: dict[str, float]
    false_positive_rate: float
    defect_id_accuracy: float
    mean_latency_s: float
    median_latency_s: float


def _load_verdicts(path: Path) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def compute_metrics(records: list[dict], source: str) -> Metrics:
    if not records:
        raise ValueError(f"{source}: no records to score")

    total = len(records)
    parsed_records = [r for r in records if r.get("parsed") is not None]
    parse_errors = total - len(parsed_records)

    binary_correct = 0
    for r in parsed_records:
        true_is_defect = r["true_defect_type"] != "none"
        pred_is_fail = r["parsed"]["verdict"] == "fail"
        if true_is_defect == pred_is_fail:
            binary_correct += 1
    binary_accuracy = binary_correct / len(parsed_records) if parsed_records else 0.0

    per_defect_recall: dict[str, float] = {}
    for dt in DEFECT_TYPES:
        subset = [r for r in records if r["true_defect_type"] == dt]
        if not subset:
            per_defect_recall[dt] = float("nan")
            continue
        flagged = sum(1 for r in subset if r.get("parsed") and r["parsed"]["verdict"] == "fail")
        per_defect_recall[dt] = flagged / len(subset)

    clean = [r for r in records if r["true_defect_type"] == "none"]
    false_positives = sum(1 for r in clean if r.get("parsed") and r["parsed"]["verdict"] == "fail")
    false_positive_rate = false_positives / len(clean) if clean else float("nan")

    caught_defects = [
        r
        for r in parsed_records
        if r["true_defect_type"] != "none" and r["parsed"]["verdict"] == "fail"
    ]
    defect_id_correct = sum(
        1 for r in caught_defects if r["parsed"]["defect_type"] == r["true_defect_type"]
    )
    defect_id_accuracy = defect_id_correct / len(caught_defects) if caught_defects else float("nan")

    latencies = [r["latency_s"] for r in records if isinstance(r.get("latency_s"), (int, float))]
    mean_latency = statistics.fmean(latencies) if latencies else 0.0
    median_latency = statistics.median(latencies) if latencies else 0.0

    model = records[0].get("model", "unknown")
    return Metrics(
        model=model,
        source=source,
        total=total,
        parsed=len(parsed_records),
        parse_errors=parse_errors,
        binary_accuracy=binary_accuracy,
        per_defect_recall=per_defect_recall,
        false_positive_rate=false_positive_rate,
        defect_id_accuracy=defect_id_accuracy,
        mean_latency_s=mean_latency,
        median_latency_s=median_latency,
    )


def _fmt_pct(value: float) -> str:
    if value != value:  # NaN
        return "n/a"
    return f"{value * 100:.1f}%"


def print_report(m: Metrics) -> None:
    print(f"=== {m.model}  ({m.source}) ===")
    print(f"  images judged:            {m.total}")
    print(f"  parse errors:             {m.parse_errors}")
    print(f"  binary accuracy:          {_fmt_pct(m.binary_accuracy)} (of {m.parsed} parsed)")
    print(f"  false-positive rate:      {_fmt_pct(m.false_positive_rate)} (clean flagged as fail)")
    print(f"  defect-type ID accuracy:  {_fmt_pct(m.defect_id_accuracy)} (when correctly caught)")
    print(f"  latency: mean={m.mean_latency_s:.1f}s  median={m.median_latency_s:.1f}s")
    print("  per-defect-type recall:")
    for dt in DEFECT_TYPES:
        print(f"    {dt:<20} {_fmt_pct(m.per_defect_recall[dt])}")
    print()


def print_comparison(metrics_list: list[Metrics]) -> None:
    headers = [m.model for m in metrics_list]
    col_w = max(12, max(len(h) for h in headers) + 2)

    def row(label: str, values: list[str]) -> str:
        cells = "".join(v.ljust(col_w) for v in values)
        return f"  {label:<26}{cells}"

    print("=== Side-by-side comparison ===")
    print(row("", [h.ljust(col_w) for h in headers]))
    print(row("images judged", [str(m.total) for m in metrics_list]))
    print(row("parse errors", [str(m.parse_errors) for m in metrics_list]))
    print(row("binary accuracy", [_fmt_pct(m.binary_accuracy) for m in metrics_list]))
    print(row("false-positive rate", [_fmt_pct(m.false_positive_rate) for m in metrics_list]))
    print(
        row(
            "defect-type ID accuracy",
            [_fmt_pct(m.defect_id_accuracy) for m in metrics_list],
        )
    )
    print(row("mean latency (s)", [f"{m.mean_latency_s:.1f}" for m in metrics_list]))
    print(row("median latency (s)", [f"{m.median_latency_s:.1f}" for m in metrics_list]))
    print("  per-defect-type recall:")
    for dt in DEFECT_TYPES:
        print(row(f"  {dt}", [_fmt_pct(m.per_defect_recall[dt]) for m in metrics_list]))
    print()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--verdicts",
        type=Path,
        action="append",
        required=True,
        help="path to a verdicts JSON file (repeat for a side-by-side comparison)",
    )
    args = parser.parse_args()

    metrics_list = [
        compute_metrics(_load_verdicts(path), source=str(path)) for path in args.verdicts
    ]

    for m in metrics_list:
        print_report(m)

    if len(metrics_list) > 1:
        print_comparison(metrics_list)


if __name__ == "__main__":
    main()
