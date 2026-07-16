"""VL7 capability probe — the cheap falsifier before any judge-harness investment.

Shows a vision model each good/bad exemplar pair from eval/exemplars/manifest.json
side by side (two images in ONE message), TELLS it the two differ in exactly one
production variable, and asks it to (1) articulate what differs in the rendered
result, (2) pick which image exhibits the defect, and (3) propose a reusable QA
criterion. If a model cannot name the melt when handed both images and told there
is a difference, no harness will make it a useful judge.

The bad twin's left/right placement is seeded-random per pair so "which image is
defective" is a genuine 2-alternative forced choice, but the model is never told
which is which — ground truth stays out of the prompt.

Thinking is ENABLED (VL2 ran think=False and under-elicited the model) and num_ctx
is capped: ollama defaults qwen3-vl:32b to a 32768 context, a ~29GB footprint that
spills past the 3090 Ti's 24GB onto the 3070 and CPU (>600s/image). After every
call the script polls /api/ps and records the VRAM residency split.

Usage:
    python scripts/vlm_eval/probe.py --model qwen3-vl:8b
    python scripts/vlm_eval/probe.py --model qwen3-vl:32b --num-ctx 8192
"""

from __future__ import annotations

import argparse
import base64
import json
import random
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_MANIFEST = REPO_ROOT / "eval" / "exemplars" / "manifest.json"

sys.path.insert(0, str(SCRIPT_DIR))
from judge import (  # noqa: E402
    OLLAMA_BASE_URL,
    OLLAMA_CHAT_URL,
    _check_ollama_reachable,
    _model_slug,
)

OLLAMA_PS_URL = f"{OLLAMA_BASE_URL}/api/ps"

PROMPT = (
    "You are inspecting 3D game-character rigging quality.\n\n"
    "The two images show the SAME character mesh, the SAME skeleton, in the SAME "
    "pose, rendered from the SAME camera with the SAME lighting. Exactly ONE "
    "production variable differs between them, and it produces a visible "
    "difference in the rendered result.\n\n"
    "Compare the two images carefully, then answer:\n"
    "1. WHAT DIFFERS: describe concretely, in visual terms, what is different "
    "between image 1 and image 2 (name the body region and what you see).\n"
    "2. DEFECTIVE IMAGE: which image (1 or 2) shows the defective result, and why.\n"
    "3. PROPOSED CRITERION: write one reusable QA acceptance criterion that would "
    "catch this defect on future character assets.\n"
)


def _b64(path: Path) -> str:
    return base64.b64encode(path.read_bytes()).decode("ascii")


def _call_ollama_pair(
    model: str,
    image1: Path,
    image2: Path,
    num_ctx: int,
    timeout: float,
) -> tuple[str, str, float]:
    payload = {
        "model": model,
        "messages": [
            {"role": "user", "content": PROMPT, "images": [_b64(image1), _b64(image2)]}
        ],
        "stream": False,
        "think": True,
        "options": {"temperature": 0, "num_ctx": num_ctx},
    }
    req = urllib.request.Request(
        OLLAMA_CHAT_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    start = time.monotonic()
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        body = json.loads(resp.read().decode("utf-8"))
    latency_s = time.monotonic() - start
    message = body["message"]
    return message.get("content", ""), message.get("thinking", ""), latency_s


def _gpu_residency(model: str) -> dict | None:
    """Return {size, size_vram, gpu_fraction} for the loaded model, or None."""
    try:
        with urllib.request.urlopen(OLLAMA_PS_URL, timeout=5.0) as resp:
            body = json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, OSError):
        return None
    for m in body.get("models", []):
        if m.get("name") == model or m.get("model") == model:
            size, size_vram = m.get("size", 0), m.get("size_vram", 0)
            return {
                "size": size,
                "size_vram": size_vram,
                "gpu_fraction": (size_vram / size) if size else None,
            }
    return None


def _parse_defective_choice(content: str) -> int | None:
    """Best-effort extraction of which image the model called defective."""
    m = re.search(
        r"(?:defective|defect)[^.\n]*?\bimage\s*([12])\b|"
        r"\bimage\s*([12])\b[^.\n]{0,60}?\b(?:is|shows|contains|has)\b[^.\n]{0,60}?defect",
        content,
        re.IGNORECASE,
    )
    if m:
        return int(m.group(1) or m.group(2))
    return None


def _load_pairs(manifest_path: Path) -> list[dict]:
    with open(manifest_path, encoding="utf-8") as f:
        manifest = json.load(f)
    return [
        {**pair, "criterion_id": criterion["id"]}
        for criterion in manifest["criteria"]
        for pair in criterion["pairs"]
    ]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", required=True, help="ollama model tag, e.g. qwen3-vl:8b")
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--out", type=Path, default=None)
    parser.add_argument("--seed", type=int, default=42, help="drives bad-twin left/right placement")
    parser.add_argument("--num-ctx", type=int, default=8192,
                        help="context cap so the 32b fits on one 24GB card")
    parser.add_argument("--timeout", type=float, default=900.0, help="per-pair request timeout")
    parser.add_argument("--force", action="store_true", help="ignore existing --out, redo all")
    args = parser.parse_args()

    out_path = args.out or SCRIPT_DIR / f"probe_results_{_model_slug(args.model)}.json"
    pairs = _load_pairs(args.manifest)
    if not pairs:
        raise SystemExit(f"ERROR: no pairs in {args.manifest}")

    _check_ollama_reachable(timeout=5.0)

    done: dict[str, dict] = {}
    if out_path.exists() and not args.force:
        with open(out_path, encoding="utf-8") as f:
            done = {r["pose"]: r for r in json.load(f)}

    rng = random.Random(args.seed)
    results = []
    for i, pair in enumerate(pairs, start=1):
        # Consume the RNG for every pair regardless of resume-skips so
        # placement stays identical for a given seed across partial runs.
        bad_position = rng.choice((1, 2))
        if pair["pose"] in done:
            print(f"[{i}/{len(pairs)}] SKIP (already probed) {pair['pose']}")
            results.append(done[pair["pose"]])
            continue

        good, bad = REPO_ROOT / pair["good"], REPO_ROOT / pair["bad"]
        image1, image2 = (bad, good) if bad_position == 1 else (good, bad)
        print(f"[{i}/{len(pairs)}] {pair['pose']} (bad twin is image {bad_position}) ...",
              end=" ", flush=True)
        content, thinking, latency_s = _call_ollama_pair(
            args.model, image1, image2, args.num_ctx, args.timeout
        )
        choice = _parse_defective_choice(content)
        record = {
            "model": args.model,
            "criterion_id": pair["criterion_id"],
            "pose": pair["pose"],
            "project_type": pair.get("project_type"),
            "bad_position": bad_position,
            "model_choice": choice,
            "choice_correct": (choice == bad_position) if choice is not None else None,
            "content": content,
            "thinking": thinking,
            "latency_s": latency_s,
            "gpu_residency": _gpu_residency(args.model),
            "num_ctx": args.num_ctx,
        }
        results.append(record)
        status = ("correct" if record["choice_correct"]
                  else "WRONG" if record["choice_correct"] is False
                  else "choice-unparsed")
        print(f"{status} ({latency_s:.1f}s)")

        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2)
            f.write("\n")

    n_correct = sum(1 for r in results if r["choice_correct"])
    residency = results[-1].get("gpu_residency") if results else None
    gpu_pct = (f"{residency['gpu_fraction'] * 100:.0f}% GPU"
               if residency and residency.get("gpu_fraction") is not None else "unknown")
    print(f"\n{args.model}: {n_correct}/{len(results)} defective-image picks correct, "
          f"residency {gpu_pct}. Wrote {out_path}")


if __name__ == "__main__":
    try:
        main()
    except urllib.error.URLError as exc:
        print(f"ERROR: ollama request failed — is `ollama serve` running? ({exc})", file=sys.stderr)
        sys.exit(1)
