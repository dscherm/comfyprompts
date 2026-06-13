"""Back-fill captions for an existing LoRA eval grid.

The original grid run captioned every cell with a broken caption_image
workflow: LoadImage validated against ComfyUI's *input* dir while the renders
lived in *output* (HTTP 400), and the workflow had no text-output node so even
a success returned nothing. Both are now fixed (caption_image.json emits via
ShowText; lora_eval_grid.stage_for_caption round-trips the image into input).

This script re-runs captioning over the rows that never got a real caption —
empty strings (skipped) and "(...)" failure placeholders — updating
results.json in place and regenerating report.md. Idempotent and resumable:
rows that already hold a real caption are left untouched.

Usage:
    python scripts/recaption_grid.py --out-dir .omc/research/lora-eval-2026-06-12
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from lora_eval_grid import (  # noqa: E402 — sibling module in scripts/
    HEIGHT,
    PROMPTS,
    SEED,
    STEPS,
    WIDTH,
    caption,
    load_workflow,
)


def needs_caption(row: dict) -> bool:
    """True when the row has an image but no real caption yet.

    A placeholder like "(caption timeout)" or "(caption queue failed: ...)"
    counts as missing — those are the failures we are back-filling.
    """
    if row.get("error") or not row.get("image"):
        return False
    cap = row.get("caption") or ""
    return cap == "" or cap.startswith("(")


def write_report(out_dir: Path, results: list[dict]) -> None:
    lines = ["# LoRA evaluation grid — captions back-filled",
             "", f"Seed {SEED}, {WIDTH}x{HEIGHT}, {STEPS} steps, flux1-dev-fp8.",
             f"Outputs in D:/Projects/ComfyUI/output. {len(results)} cells.", ""]
    for pkey, ptext in PROMPTS.items():
        lines += [f"## Prompt: {pkey} — \"{ptext}\"", "",
                  "| LoRA | strength | image | caption |", "|---|---|---|---|"]
        for r in results:
            if r["prompt_key"] != pkey:
                continue
            lines.append(
                f"| {r['lora'] or '(baseline)'} | {r['strength']} "
                f"| {r.get('image', 'ERROR')} | {r.get('caption', r.get('error', ''))[:160]} |"
            )
        lines.append("")
    (out_dir / "report.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", required=True,
                        help="grid directory holding results.json")
    args = parser.parse_args()

    out_dir = Path(args.out_dir)
    results_path = out_dir / "results.json"
    if not results_path.exists():
        print(f"no results.json in {out_dir}", file=sys.stderr)
        return 1

    results = json.loads(results_path.read_text(encoding="utf-8"))
    cap_wf = load_workflow("caption_image")

    todo = [r for r in results if needs_caption(r)]
    print(f"{len(todo)}/{len(results)} cells need captions", flush=True)

    done = 0
    for row in results:
        if not needs_caption(row):
            continue
        label = f"{row['lora'] or 'BASELINE'} s={row['strength']} {row['prompt_key']}"
        try:
            cap = caption({"filename": row["image"], "subfolder": ""}, cap_wf)
        except Exception as e:  # never let one bad cell abort the back-fill
            cap = f"(recaption failed: {str(e)[:80]})"
        row["caption"] = cap
        done += 1
        results_path.write_text(json.dumps(results, indent=1), encoding="utf-8")
        print(f"[{done}/{len(todo)}] {label}: {cap[:80]}", flush=True)

    write_report(out_dir, results)
    real = sum(1 for r in results if (r.get("caption") or "")
               and not r["caption"].startswith("("))
    print(f"DONE: {real}/{len(results)} cells now have real captions "
          f"-> {out_dir / 'report.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
