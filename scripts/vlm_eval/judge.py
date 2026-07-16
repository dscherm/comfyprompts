"""Ask a local ollama vision model to spot defects in the VLM eval render set.

Runs a single model over `labels.json` (see `build_eval_set.py`), asking it to judge
each render for one of six known defect types (or "none"), and writes raw + parsed
verdicts to a JSON file for `score.py` to grade against ground truth.

Resumable: if `--out` already exists, images already present in it are skipped
(so a crashed 32b run, which can take ~40 minutes, does not lose prior progress).
Pass `--force` to re-judge everything from scratch.

Usage:
    python scripts/vlm_eval/judge.py --model qwen3-vl:8b
    python scripts/vlm_eval/judge.py --model qwen3-vl:32b --limit 4
    python scripts/vlm_eval/judge.py --model qwen3-vl:8b --out my_verdicts.json --force
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_LABELS = SCRIPT_DIR / "labels.json"

OLLAMA_BASE_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434").rstrip("/")
OLLAMA_CHAT_URL = f"{OLLAMA_BASE_URL}/api/chat"
OLLAMA_TAGS_URL = f"{OLLAMA_BASE_URL}/api/tags"

DEFECT_TYPES: list[str] = [
    "flipped_normals",
    "unwelded_cracks",
    "missing_texture",
    "uv_smear",
    "scale_error",
    "wrong_orientation",
]

_DEFECT_DESCRIPTIONS = {
    "flipped_normals": "faces render dark/inside-out or with visibly wrong shading",
    "unwelded_cracks": "visible seams, cracks, or gaps splitting the mesh surface",
    "missing_texture": "the asset is untextured — flat black/grey/checker, no material",
    "uv_smear": "the texture looks stretched, smeared, or misaligned across surfaces",
    "scale_error": "the asset is a wildly wrong size relative to the orange reference cube",
    "wrong_orientation": "the asset is rotated or flipped in an unnatural way",
}


def _build_prompt() -> str:
    defect_lines = "\n".join(f"  - {dt}: {_DEFECT_DESCRIPTIONS[dt]}" for dt in DEFECT_TYPES)
    return (
        "You are a QA inspector reviewing a render of ONE low-poly game-art asset "
        "(a single .glb model) on a neutral background. A small ORANGE cube in the "
        "frame is a fixed-size scale reference only — it is never the asset being "
        "judged, ignore its own appearance.\n\n"
        "Inspect the asset for exactly one of the following known defect types:\n"
        f"{defect_lines}\n\n"
        'If the asset looks correct with no defect, verdict is "pass" and defect_type '
        'is "none". Otherwise verdict is "fail" and defect_type names the single best '
        "matching type from the list above.\n\n"
        "Respond with EXACTLY one JSON object and nothing else — no markdown, no "
        "commentary before or after it:\n"
        '{"verdict": "pass"|"fail", "defect_type": "<one of the 6 types above or '
        '\\"none\\">", "confidence": 0.0-1.0, "reasoning": "<one sentence>"}'
    )


def _model_slug(model: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "-", model)


def _check_ollama_reachable(timeout: float) -> None:
    try:
        urllib.request.urlopen(OLLAMA_TAGS_URL, timeout=timeout)
    except (urllib.error.URLError, OSError) as exc:
        raise SystemExit(
            f"ERROR: cannot reach ollama at {OLLAMA_BASE_URL} — is `ollama serve` running? ({exc})"
        ) from None


def _call_ollama(model: str, image_path: Path, prompt: str, timeout: float) -> tuple[str, float]:
    b64 = base64.b64encode(image_path.read_bytes()).decode("ascii")
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt, "images": [b64]}],
        "stream": False,
        "think": False,
        "options": {"temperature": 0},
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        OLLAMA_CHAT_URL, data=data, headers={"Content-Type": "application/json"}
    )
    start = time.monotonic()
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        body = json.loads(resp.read().decode("utf-8"))
    latency_s = time.monotonic() - start
    return body["message"]["content"], latency_s


def _extract_json_object(text: str) -> str | None:
    """Find the first balanced {...} block in text, respecting quoted strings."""
    start = text.find("{")
    if start == -1:
        return None
    depth = 0
    in_string = False
    escape = False
    for i in range(start, len(text)):
        ch = text[i]
        if in_string:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == '"':
                in_string = False
            continue
        if ch == '"':
            in_string = True
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return text[start : i + 1]
    return None


def _parse_verdict(raw: str) -> dict[str, Any] | None:
    obj_str = _extract_json_object(raw.strip())
    if obj_str is None:
        return None
    try:
        obj = json.loads(obj_str)
    except json.JSONDecodeError:
        return None
    if not isinstance(obj, dict):
        return None
    verdict = obj.get("verdict")
    if verdict not in ("pass", "fail"):
        return None
    defect_type = obj.get("defect_type")
    if not isinstance(defect_type, str) or not defect_type:
        defect_type = "none" if verdict == "pass" else "unknown"
    confidence = obj.get("confidence")
    if not isinstance(confidence, (int, float)) or isinstance(confidence, bool):
        confidence = None
    reasoning = obj.get("reasoning")
    if not isinstance(reasoning, str):
        reasoning = ""
    return {
        "verdict": verdict,
        "defect_type": defect_type,
        "confidence": confidence,
        "reasoning": reasoning,
    }


def _load_labels(labels_path: Path) -> list[dict]:
    with open(labels_path, encoding="utf-8") as f:
        return json.load(f)


def _load_existing(out_path: Path) -> dict[str, dict]:
    if not out_path.exists():
        return {}
    with open(out_path, encoding="utf-8") as f:
        prior = json.load(f)
    return {r["image"]: r for r in prior}


def _write_out(out_path: Path, labels: list[dict], results_by_image: dict[str, dict]) -> None:
    ordered = [results_by_image[e["image"]] for e in labels if e["image"] in results_by_image]
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(ordered, f, indent=2)
        f.write("\n")


def judge_all(
    model: str,
    labels: list[dict],
    out_path: Path,
    limit: int | None,
    timeout: float,
    force: bool,
) -> list[dict]:
    results_by_image = {} if force else _load_existing(out_path)
    entries = labels if limit is None else labels[:limit]
    prompt = _build_prompt()
    total = len(entries)

    for i, entry in enumerate(entries, start=1):
        image_rel = entry["image"]
        if image_rel in results_by_image:
            print(f"[{i}/{total}] SKIP (already judged) {image_rel}")
            continue

        image_path = REPO_ROOT / image_rel
        print(f"[{i}/{total}] {image_rel} ...", end=" ", flush=True)
        raw, latency_s = _call_ollama(model, image_path, prompt, timeout)
        parsed = _parse_verdict(raw)
        record = {
            "model": model,
            "image": image_rel,
            "asset": entry.get("asset"),
            "true_defect_type": entry["defect_type"],
            "raw_response": raw,
            "parsed": parsed,
            "parse_error": parsed is None,
            "latency_s": latency_s,
        }
        results_by_image[image_rel] = record
        verdict_str = parsed["verdict"] if parsed else "PARSE_ERROR"
        print(f"{verdict_str} ({latency_s:.1f}s)")

        _write_out(out_path, labels, results_by_image)

    return [results_by_image[e["image"]] for e in entries if e["image"] in results_by_image]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", required=True, help="ollama model tag, e.g. qwen3-vl:8b")
    parser.add_argument("--labels", type=Path, default=DEFAULT_LABELS)
    parser.add_argument("--out", type=Path, default=None)
    parser.add_argument("--limit", type=int, default=None, help="judge only the first N entries")
    parser.add_argument("--timeout", type=float, default=180.0, help="per-image request timeout")
    parser.add_argument("--force", action="store_true", help="ignore existing --out, redo all")
    args = parser.parse_args()

    out_path = args.out or SCRIPT_DIR / f"verdicts_{_model_slug(args.model)}.json"

    labels = _load_labels(args.labels)
    if not labels:
        raise SystemExit(f"ERROR: no entries in {args.labels}")

    _check_ollama_reachable(timeout=5.0)

    results = judge_all(
        model=args.model,
        labels=labels,
        out_path=out_path,
        limit=args.limit,
        timeout=args.timeout,
        force=args.force,
    )

    parse_errors = sum(1 for r in results if r["parse_error"])
    print(f"\nWrote {len(results)} verdicts to {out_path} ({parse_errors} parse errors)")


if __name__ == "__main__":
    try:
        main()
    except urllib.error.URLError as exc:
        print(f"ERROR: ollama request failed — is `ollama serve` running? ({exc})", file=sys.stderr)
        sys.exit(1)
