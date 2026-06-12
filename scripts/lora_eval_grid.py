"""LoRA evaluation grid: generate a fixed-seed comparison matrix for every
installed LoRA, caption each output with Florence2, and write a report for
judging.

For each LoRA x strength x prompt cell, renders the generate_image_lora
workflow at fixed seed and cheap-but-fair settings, then runs the
caption_image workflow on the result. A no-LoRA baseline row per prompt
anchors the comparison. Results land in .omc/research/lora-eval-<date>/
as results.json + report.md (image paths + captions, ready for an AI or
human judging pass).

Stdlib only. Sequential: one job at a time so the queue stays observable.

Usage:
    python scripts/lora_eval_grid.py                # full grid
    python scripts/lora_eval_grid.py --limit 3      # first 3 LoRAs (trial)
    python scripts/lora_eval_grid.py --strengths 0.8
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
import urllib.request
from datetime import date
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS = REPO_ROOT / "workflows" / "mcp"
COMFY_URL = "http://localhost:8188"
PARAM_RE = re.compile(r"PARAM_[A-Z0-9_]+")

SEED = 123456
WIDTH = HEIGHT = 512
STEPS = 12
PROMPTS = {
    "portrait": "portrait of a woman with long red hair, forest background",
    "scene": "a small wooden cabin by a lake at sunset",
}


def http_json(path: str, payload: dict | None = None) -> dict:
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(
        COMFY_URL + path, data, {"Content-Type": "application/json"} if data else {}
    )
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read())


def load_workflow(name: str) -> dict:
    wf = json.loads((WORKFLOWS / f"{name}.json").read_text(encoding="utf-8-sig"))
    return {k: v for k, v in wf.items() if not k.startswith("_")}


def fill(workflow: dict, values: dict) -> dict:
    """Replace whole-value PARAM_* placeholders; error on leftovers."""
    filled = json.loads(json.dumps(workflow))
    for node in filled.values():
        inputs = node.get("inputs", {})
        for key, val in list(inputs.items()):
            if isinstance(val, str) and PARAM_RE.fullmatch(val.strip()):
                stem = val.strip()
                if stem not in values:
                    raise SystemExit(f"no value for {stem}")
                inputs[key] = values[stem]
    return filled


def run_job(workflow: dict, timeout: int = 300) -> list[dict]:
    """Queue, wait, return output image records."""
    resp = http_json("/prompt", {"prompt": workflow})
    if "prompt_id" not in resp:
        raise RuntimeError(f"queue rejected: {resp}")
    pid = resp["prompt_id"]
    deadline = time.time() + timeout
    while time.time() < deadline:
        time.sleep(3)
        hist = http_json(f"/history/{pid}")
        if pid not in hist:
            continue
        entry = hist[pid]
        status = entry.get("status", {})
        if status.get("status_str") == "error":
            msgs = [m[1].get("exception_message", "") for m in status.get("messages", [])
                    if m[0] == "execution_error"]
            raise RuntimeError(f"execution failed: {'; '.join(msgs)[:200]}")
        if status.get("completed"):
            images = []
            for out in entry.get("outputs", {}).values():
                images.extend(i for i in out.get("images", []) if isinstance(i, dict))
            return images
    raise RuntimeError(f"timeout waiting for {pid}")


def caption(image: dict, caption_wf: dict) -> str:
    """Run caption_image on a generated output (referenced by filename)."""
    values = {
        "PARAM_STR_IMAGE_PATH": image["filename"]
        if not image.get("subfolder")
        else f"{image['subfolder']}/{image['filename']}",
        "PARAM_STR_MODEL": "microsoft/Florence-2-large",
        "PARAM_STR_TASK": "detailed_caption",
        "PARAM_STR_TEXT_INPUT": "",
    }
    wf = fill(caption_wf, values)
    # caption workflow outputs text via a node that saves/returns text — read
    # from history outputs instead of images
    resp = http_json("/prompt", {"prompt": wf})
    pid = resp.get("prompt_id")
    if not pid:
        return "(caption queue rejected)"
    deadline = time.time() + 120
    while time.time() < deadline:
        time.sleep(2)
        hist = http_json(f"/history/{pid}")
        if pid in hist and hist[pid].get("status", {}).get("completed"):
            for out in hist[pid].get("outputs", {}).values():
                for key in ("text", "string", "caption"):
                    val = out.get(key)
                    if isinstance(val, list) and val:
                        return " ".join(str(v) for v in val)[:500]
            return "(no caption output found)"
    return "(caption timeout)"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=0, help="only first N LoRAs")
    parser.add_argument("--strengths", type=float, nargs="*", default=[0.6, 1.0])
    parser.add_argument("--no-captions", action="store_true")
    args = parser.parse_args()

    object_info = http_json("/object_info/LoraLoader")
    loras = object_info["LoraLoader"]["input"]["required"]["lora_name"][0]
    if args.limit:
        loras = loras[: args.limit]

    out_dir = REPO_ROOT / ".omc" / "research" / f"lora-eval-{date.today().isoformat()}"
    out_dir.mkdir(parents=True, exist_ok=True)

    gen_wf = load_workflow("generate_image_lora")
    base_wf = load_workflow("generate_image")
    cap_wf = None if args.no_captions else load_workflow("caption_image")

    results: list[dict] = []
    total = len(PROMPTS) * (1 + len(loras) * len(args.strengths))
    done = 0

    def record(row: dict) -> None:
        nonlocal done
        done += 1
        results.append(row)
        (out_dir / "results.json").write_text(
            json.dumps(results, indent=1), encoding="utf-8"
        )
        print(f"[{done}/{total}] {row['lora'] or 'BASELINE'} s={row['strength']} "
              f"{row['prompt_key']}: {row.get('image', row.get('error', '?'))}", flush=True)

    for pkey, ptext in PROMPTS.items():
        # baseline (no LoRA)
        try:
            images = run_job(fill(base_wf, {
                "PARAM_PROMPT": ptext,
                "PARAM_NEGATIVE_PROMPT": "text, watermark",
                "PARAM_INT_WIDTH": WIDTH, "PARAM_INT_HEIGHT": HEIGHT,
                "PARAM_INT_SEED": SEED, "PARAM_INT_STEPS": STEPS,
                "PARAM_FLOAT_CFG": 1.0,
                "PARAM_STR_SAMPLER_NAME": "euler", "PARAM_STR_SCHEDULER": "simple",
                "PARAM_FLOAT_DENOISE": 1.0,
            }))
            img = images[0] if images else {}
            cap = caption(img, cap_wf) if cap_wf and img else ""
            record({"lora": None, "strength": 0, "prompt_key": pkey, "prompt": ptext,
                    "image": img.get("filename"), "caption": cap})
        except Exception as e:
            record({"lora": None, "strength": 0, "prompt_key": pkey, "prompt": ptext,
                    "error": str(e)[:200]})

        for lora in loras:
            for strength in args.strengths:
                try:
                    images = run_job(fill(gen_wf, {
                        "PARAM_PROMPT": ptext,
                        "PARAM_NEGATIVE_PROMPT": "text, watermark",
                        "PARAM_INT_WIDTH": WIDTH, "PARAM_INT_HEIGHT": HEIGHT,
                        "PARAM_INT_SEED": SEED, "PARAM_INT_STEPS": STEPS,
                        "PARAM_FLOAT_CFG": 1.0,
                        "PARAM_STR_SAMPLER_NAME": "euler",
                        "PARAM_STR_SCHEDULER": "simple",
                        "PARAM_FLOAT_DENOISE": 1.0,
                        "PARAM_STR_LORA_NAME": lora,
                        "PARAM_FLOAT_LORA_STRENGTH": strength,
                    }))
                    img = images[0] if images else {}
                    cap = caption(img, cap_wf) if cap_wf and img else ""
                    record({"lora": lora, "strength": strength, "prompt_key": pkey,
                            "prompt": ptext, "image": img.get("filename"),
                            "caption": cap})
                except Exception as e:
                    record({"lora": lora, "strength": strength, "prompt_key": pkey,
                            "prompt": ptext, "error": str(e)[:200]})

    # report
    lines = [f"# LoRA evaluation grid — {date.today().isoformat()}",
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
    print(f"DONE: {out_dir / 'report.md'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
