"""caption — Florence2 auto-caption a training folder, with a trigger-word prefix.

Stage 2 of the train_lora harness (see scripts/train_lora/README.md). For every
image in a folder, runs the `caption_image` (Florence-2) ComfyUI workflow over
the REST API and writes a sibling `<stem>.txt` caption prefixed (or suffixed)
with a trigger word — the format ai-toolkit expects for LoRA training.

- Idempotent: images that already have a .txt are skipped.
- Graceful: if ComfyUI is unreachable it fails fast with a clear message and
  writes nothing; a per-image caption error skips that one image (no partial
  .txt is ever written).

Stdlib only. Talks to ComfyUI at $COMFYUI_URL (default http://localhost:8188).

Usage:
    python scripts/train_lora/caption.py \\
        --dir scripts/train_lora/datasets/berserkr_style --trigger brsk_style
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
WORKFLOWS = REPO_ROOT / "workflows" / "mcp"
COMFY_URL = os.environ.get("COMFYUI_URL", "http://localhost:8188").rstrip("/")
PARAM_RE = re.compile(r"PARAM_[A-Z0-9_]+")
IMG_EXTS = (".png", ".jpg", ".jpeg", ".webp", ".bmp")


def http_json(path: str, payload: dict | None = None) -> dict:
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(
        COMFY_URL + path, data, {"Content-Type": "application/json"} if data else {}
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", "replace")[:500]
        raise RuntimeError(f"HTTP {e.code} {path}: {body}") from None


def preflight() -> None:
    """Confirm ComfyUI is up before touching any files."""
    try:
        with urllib.request.urlopen(f"{COMFY_URL}/system_stats", timeout=10):
            return
    except (urllib.error.URLError, OSError) as e:
        raise SystemExit(
            f"ComfyUI is not reachable at {COMFY_URL} ({e}). "
            f"Start it (system_stats must respond) and retry. Nothing was written."
        )


def upload_local(path: Path) -> str:
    """POST a local image into ComfyUI's input dir, return the input-relative name."""
    blob = path.read_bytes()
    boundary = "----trainloracaption"
    body = b"".join([
        f"--{boundary}\r\n".encode(),
        b'Content-Disposition: form-data; name="image"; '
        + f'filename="{path.name}"\r\n'.encode(),
        b"Content-Type: image/png\r\n\r\n",
        blob,
        f"\r\n--{boundary}\r\n".encode(),
        b'Content-Disposition: form-data; name="overwrite"\r\n\r\ntrue\r\n',
        f"--{boundary}--\r\n".encode(),
    ])
    req = urllib.request.Request(
        f"{COMFY_URL}/upload/image",
        body,
        {"Content-Type": f"multipart/form-data; boundary={boundary}"},
    )
    with urllib.request.urlopen(req, timeout=60) as r:
        resp = json.loads(r.read())
    name = resp.get("name", path.name)
    sub = resp.get("subfolder", "")
    return f"{sub}/{name}" if sub else name


def load_workflow(name: str) -> dict:
    wf = json.loads((WORKFLOWS / f"{name}.json").read_text(encoding="utf-8-sig"))
    return {k: v for k, v in wf.items() if not k.startswith("_")}


def fill(workflow: dict, values: dict) -> dict:
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


def queue_prompt(workflow: dict, retries: int = 4) -> str:
    last = ""
    for attempt in range(retries):
        try:
            resp = http_json("/prompt", {"prompt": workflow})
            if "prompt_id" in resp:
                return resp["prompt_id"]
            last = f"queue rejected: {resp}"
        except RuntimeError as e:
            last = str(e)
            if "failed validation" not in last and "HTTP 400" not in last:
                raise
        time.sleep(2 * (attempt + 1))
    raise RuntimeError(f"queue failed after {retries} attempts: {last[:200]}")


def run_caption(image_name: str, caption_wf: dict, model: str, task: str,
                timeout: int = 180) -> str:
    """Run caption_image over an already-uploaded input image, return raw caption.

    Raises RuntimeError on queue/execution/timeout failure so the caller can
    skip the image without writing a .txt."""
    wf = fill(caption_wf, {
        "PARAM_STR_IMAGE_PATH": image_name,
        "PARAM_STR_MODEL": model,
        "PARAM_STR_TASK": task,
        "PARAM_STR_TEXT_INPUT": "",
    })
    pid = queue_prompt(wf)
    deadline = time.time() + timeout
    empty_polls = 0
    while time.time() < deadline:
        time.sleep(2)
        hist = http_json(f"/history/{pid}")
        if pid not in hist:
            continue
        status = hist[pid].get("status", {})
        if status.get("status_str") == "error":
            msgs = [m[1].get("exception_message", "") for m in status.get("messages", [])
                    if m[0] == "execution_error"]
            raise RuntimeError(f"caption execution failed: {'; '.join(msgs)[:120]}")
        if status.get("completed"):
            for out in hist[pid].get("outputs", {}).values():
                for key in ("text", "string", "caption"):
                    val = out.get(key)
                    if isinstance(val, list) and val:
                        return " ".join(str(v) for v in val)
            empty_polls += 1
            if empty_polls >= 3:
                raise RuntimeError("no caption output found in workflow result")
    raise RuntimeError(f"caption timeout after {timeout}s")


def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def caption_dir(
    directory: str | Path,
    trigger: str,
    *,
    position: str = "prepend",
    model: str = "microsoft/Florence-2-large",
    task: str = "detailed_caption",
    overwrite: bool = False,
) -> dict:
    """Caption every image in `directory`. Returns a stats dict."""
    d = Path(directory)
    if not d.is_dir():
        raise SystemExit(f"not a directory: {d}")
    images = sorted(p for p in d.iterdir() if p.suffix.lower() in IMG_EXTS)
    stats = {"images": len(images), "captioned": 0, "skipped_existing": 0, "failed": 0}

    preflight()
    caption_wf = load_workflow("caption_image")

    for img in images:
        txt = img.with_suffix(".txt")
        if txt.exists() and not overwrite:
            stats["skipped_existing"] += 1
            continue
        try:
            uploaded = upload_local(img)
            raw = _clean(run_caption(uploaded, caption_wf, model, task))
        except RuntimeError as e:
            stats["failed"] += 1
            print(f"  ! {img.name}: {e}", file=sys.stderr)
            continue
        if not raw:
            stats["failed"] += 1
            print(f"  ! {img.name}: empty caption", file=sys.stderr)
            continue
        line = f"{trigger}, {raw}" if position == "prepend" else f"{raw}, {trigger}"
        txt.write_text(line, encoding="utf-8")
        stats["captioned"] += 1
        print(f"  + {img.name}: {line[:90]}")
    return stats


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Florence2 auto-caption a training folder.")
    ap.add_argument("--dir", required=True, help="Training folder of images.")
    ap.add_argument("--trigger", required=True, help="Trigger word, e.g. brsk_style.")
    ap.add_argument("--position", choices=("prepend", "append"), default="prepend")
    ap.add_argument("--model", default="microsoft/Florence-2-large")
    ap.add_argument("--task", default="detailed_caption")
    ap.add_argument("--overwrite", action="store_true",
                    help="Recaption images that already have a .txt.")
    args = ap.parse_args(argv)

    stats = caption_dir(args.dir, args.trigger, position=args.position,
                        model=args.model, task=args.task, overwrite=args.overwrite)
    print(json.dumps(stats, indent=2))
    return 1 if stats["captioned"] == 0 and stats["images"] > stats["skipped_existing"] else 0


if __name__ == "__main__":
    sys.exit(main())
