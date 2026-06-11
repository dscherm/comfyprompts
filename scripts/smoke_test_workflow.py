"""GPU smoke-test a parametric ComfyUI workflow at cheap settings.

Fills PARAM_* placeholders with safe test values (512px, few steps), uploads a
test image for image-input params when needed, queues the workflow via REST,
polls history, and reports the output artifact. Companion to
workflow_validator.py: the validator proves a workflow loads; this proves it
runs.

Stdlib only. Usage:
    python smoke_test_workflow.py workflows/mcp/generate_image.json
    python smoke_test_workflow.py workflows/mcp/img2img.json --image path/to/input.png
    python smoke_test_workflow.py <wf.json> --set PARAM_STR_OBJECT=cat --timeout 300

Exit codes: 0 = completed with output, 1 = execution failed/timeout, 2 = usage error.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
import urllib.error
import urllib.request
import uuid
from pathlib import Path

PARAM_RE = re.compile(r"PARAM_[A-Z0-9_]+")

# Cheap, safe test values keyed by normalized placeholder stem (type-hint
# prefixes STR_/INT_/FLOAT_/BOOL_ stripped before lookup).
TEST_VALUES: dict[str, object] = {
    "POSITIVE_PROMPT": "a small ceramic fox figurine, studio lighting",
    "PROMPT": "a small ceramic fox figurine, studio lighting",
    "NEGATIVE_PROMPT": "text, watermark, blurry",
    "WIDTH": 512,
    "HEIGHT": 512,
    "SEED": 42,
    "STEPS": 6,
    "CFG": 7.0,
    "DENOISE": 1.0,
    "SAMPLER_NAME": "euler",
    "SCHEDULER": "normal",
    "BATCH_SIZE": 1,
    "WEIGHT": 0.8,
    "WEIGHT_1": 0.6,
    "WEIGHT_2": 0.4,
    "OVERALL_WEIGHT": 0.8,
    "LORA_STRENGTH": 0.8,
    "CONTROLNET_STRENGTH": 0.8,
    "STRENGTH": 0.8,
    "RESOLUTION": 128,
    "MAX_FACES": 5000,
    "FRAMES": 8,
    "FPS": 8,
    "DURATION": 1,
    "SECONDS": 5,
    "SCALE_FACTOR": 2,
    "VARIATION_STRENGTH": 0.6,
    "NUM_VARIATIONS": 1,
    "TEXT": "Smoke test of the speech pipeline.",
    "VOICE_REFERENCE": "default",
    "FILENAME_PREFIX": "smoke_test",
}

IMAGE_PARAM_HINTS = ("IMAGE", "MASK", "STYLE_IMAGE", "CONTROL_IMAGE")


def http_json(url: str, payload: dict | None = None, timeout: int = 30) -> dict:
    data = json.dumps(payload).encode() if payload is not None else None
    headers = {"Content-Type": "application/json"} if data else {}
    req = urllib.request.Request(url, data, headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", "replace")
        print(f"HTTP {e.code} from {url}:\n{body[:3000]}", file=sys.stderr)
        raise SystemExit(1)


def free_vram(base_url: str) -> None:
    """Ask ComfyUI to unload models — helps chained heavy jobs on small GPUs."""
    try:
        req = urllib.request.Request(
            base_url + "/free",
            json.dumps({"unload_models": True, "free_memory": True}).encode(),
            {"Content-Type": "application/json"},
        )
        urllib.request.urlopen(req, timeout=30).read()
    except (urllib.error.URLError, OSError):
        pass


def upload_image(base_url: str, path: Path) -> str:
    """Upload an image via /upload/image (multipart) and return its server name."""
    boundary = uuid.uuid4().hex
    body = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="image"; filename="{path.name}"\r\n'
        f"Content-Type: application/octet-stream\r\n\r\n"
    ).encode() + path.read_bytes() + f"\r\n--{boundary}--\r\n".encode()
    req = urllib.request.Request(
        base_url + "/upload/image",
        body,
        {"Content-Type": f"multipart/form-data; boundary={boundary}"},
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read())["name"]


def normalize_stem(param: str) -> str:
    stem = param.removeprefix("PARAM_")
    for hint in ("STR_", "STRING_", "TEXT_", "INT_", "FLOAT_", "BOOL_"):
        stem = stem.removeprefix(hint)
    return stem


def coerce(param: str, value: object) -> object:
    """Coerce by the placeholder's type hint so JSON types satisfy node specs."""
    body = param.removeprefix("PARAM_")
    if body.startswith("INT_"):
        return int(value)  # type: ignore[arg-type]
    if body.startswith("FLOAT_"):
        return float(value)  # type: ignore[arg-type]
    if body.startswith("BOOL_"):
        return value in (True, "true", "True", 1)
    return value


def resolve_value(param: str, overrides: dict[str, object], image_name: str | None) -> object:
    if param in overrides:
        return coerce(param, overrides[param])
    stem = normalize_stem(param)
    if stem in TEST_VALUES:
        return coerce(param, TEST_VALUES[stem])
    if any(h in stem for h in IMAGE_PARAM_HINTS):
        if image_name is None:
            raise SystemExit(
                f"{param} needs an input image — pass --image <path> (or --set {param}=<name>)"
            )
        return image_name
    raise SystemExit(f"no test value known for {param} — pass --set {param}=<value>")


def fill_params(workflow: dict, overrides: dict[str, object], image_name: str | None) -> dict:
    filled = json.loads(json.dumps(workflow))  # deep copy
    used: dict[str, object] = {}
    for node in filled.values():
        if not isinstance(node, dict):
            continue
        inputs = node.get("inputs", {})
        for key, value in list(inputs.items()):
            if isinstance(value, str) and PARAM_RE.fullmatch(value.strip()):
                param = value.strip()
                inputs[key] = resolve_value(param, overrides, image_name)
                used[param] = inputs[key]
            elif isinstance(value, str) and PARAM_RE.search(value):
                # Embedded placeholder inside a longer string
                def sub(m: re.Match) -> str:
                    used[m.group(0)] = resolve_value(m.group(0), overrides, image_name)
                    return str(used[m.group(0)])
                inputs[key] = PARAM_RE.sub(sub, value)
    if used:
        print("filled params:")
        for k, v in sorted(used.items()):
            print(f"  {k} = {v!r}")
    return filled


def main() -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").split("\n")[0])
    parser.add_argument("workflow", help="parametric workflow JSON (API format)")
    parser.add_argument("--url", default="http://localhost:8188")
    parser.add_argument("--image", help="input image file for image params")
    parser.add_argument("--set", action="append", default=[], metavar="PARAM=VALUE",
                        help="override a PARAM_* value (repeatable)")
    parser.add_argument("--timeout", type=int, default=420, help="seconds to wait")
    parser.add_argument("--free-vram", action="store_true",
                        help="unload models before queueing (8GB GPU hygiene)")
    args = parser.parse_args()

    overrides: dict[str, object] = {}
    for item in args.set:
        if "=" not in item:
            print(f"bad --set (need PARAM=VALUE): {item}", file=sys.stderr)
            return 2
        k, v = item.split("=", 1)
        overrides[k] = v

    wf_path = Path(args.workflow)
    workflow = json.loads(wf_path.read_text(encoding="utf-8-sig"))
    workflow = {k: v for k, v in workflow.items() if not k.startswith("_")}

    image_name = None
    if args.image:
        image_name = upload_image(args.url, Path(args.image))
        print(f"uploaded input image as: {image_name}")

    filled = fill_params(workflow, overrides, image_name)

    if args.free_vram:
        free_vram(args.url)
        print("requested model unload (--free-vram)")

    resp = http_json(args.url + "/prompt", {"prompt": filled})
    if "error" in resp:
        print("QUEUE REJECTED:", json.dumps(resp, indent=2)[:2000])
        return 1
    pid = resp["prompt_id"]
    print(f"queued: {pid}")

    deadline = time.time() + args.timeout
    while time.time() < deadline:
        time.sleep(5)
        hist = http_json(f"{args.url}/history/{pid}")
        if pid not in hist:
            continue
        entry = hist[pid]
        status = entry.get("status", {})
        if not status.get("completed") and status.get("status_str") != "error":
            continue
        if status.get("status_str") == "error" or not status.get("completed"):
            print("EXECUTION FAILED:")
            for msg in status.get("messages", []):
                if msg[0] == "execution_error":
                    detail = msg[1]
                    print(f"  node {detail.get('node_id')} ({detail.get('node_type')}): "
                          f"{detail.get('exception_message')}")
            return 1
        artifacts = []
        for out in entry.get("outputs", {}).values():
            for key in ("images", "gifs", "audio", "mesh", "files", "videos"):
                for item in out.get(key, []):
                    name = item.get("filename") if isinstance(item, dict) else item
                    artifacts.append(name)
        print(f"SUCCESS: {wf_path.name} -> {', '.join(a for a in artifacts if a) or '(no named artifact)'}")
        return 0
    print(f"TIMEOUT after {args.timeout}s (job may still be running)")
    return 1


if __name__ == "__main__":
    sys.exit(main())
