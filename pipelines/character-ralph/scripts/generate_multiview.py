"""Generate side-view and back-view character images via ComfyUI REST API.

Loads the parametric workflow, substitutes PARAM_* placeholders,
queues each prompt sequentially, polls for completion, and downloads output images.
Also copies the existing fullbody as the front view.
Uses only stdlib (urllib) -- no pip dependencies required.
"""

import json
import os
import shutil
import sys
import time
import urllib.error
import urllib.request

COMFYUI_URL = os.environ.get("COMFYUI_URL", "http://localhost:8188")
WORKFLOW_PATH = os.path.join(
    os.path.dirname(__file__), "..", "..", "..", "workflows", "mcp", "generate_image.json"
)
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "output", "multiview")
FULLBODY_SRC = os.path.join(os.path.dirname(__file__), "..", "output", "fullbody", "fullbody.png")

POLL_INTERVAL = 2  # seconds
TIMEOUT = 300  # seconds

# Shared base parameters
BASE_PARAMS: dict[str, str | int | float] = {
    "PARAM_INT_WIDTH": 768,
    "PARAM_INT_HEIGHT": 1024,
    "PARAM_INT_STEPS": 25,
    "PARAM_FLOAT_CFG": 1.0,
    "PARAM_FLOAT_DENOISE": 1.0,
    "PARAM_STR_SAMPLER_NAME": "euler",
    "PARAM_STR_SCHEDULER": "simple",
}

# Per-view overrides
VIEWS = [
    {
        "name": "side",
        "output": "view-side.png",
        "params": {
            "PARAM_PROMPT": (
                "The Rookie, young male racer, full body character design, side view profile, "
                "facing right. Orange racing jacket with black stripes. Aviator goggles pushed "
                "up on forehead. Fingerless brown leather gloves. Dark cargo pants. Heavy boots. "
                "Short messy brown hair. Utility belt with tools. "
                "Otomo Akira meets R Crumb underground comix style, clean ink with obsessive "
                "detail. Full body visible head to toe, centered in frame, clean solid grey "
                "background, character design orthographic side view"
            ),
            "PARAM_NEGATIVE_PROMPT": (
                "blurry, low quality, deformed, ugly, photorealistic, 3D render, anime, chibi, "
                "watermark, text, multiple characters, cropped, partial body, front view, "
                "back view, three quarter view"
            ),
            "PARAM_INT_SEED": 43,
        },
    },
    {
        "name": "back",
        "output": "view-back.png",
        "params": {
            "PARAM_PROMPT": (
                "The Rookie, young male racer, full body character design, back view from behind. "
                "Orange racing jacket with black stripes. Aviator goggles on head. Dark cargo "
                "pants. Heavy boots. Short messy brown hair. Utility belt with tools. "
                "Otomo Akira meets R Crumb underground comix style, clean ink with obsessive "
                "detail. Full body visible head to toe, centered in frame, clean solid grey "
                "background, character design orthographic back view"
            ),
            "PARAM_NEGATIVE_PROMPT": (
                "blurry, low quality, deformed, ugly, photorealistic, 3D render, anime, chibi, "
                "watermark, text, multiple characters, cropped, partial body, front view, "
                "face visible, three quarter view"
            ),
            "PARAM_INT_SEED": 44,
        },
    },
]


def load_and_substitute(workflow_path: str, params: dict) -> dict:
    """Load workflow JSON and replace PARAM_* placeholders with actual values."""
    with open(workflow_path, encoding="utf-8") as f:
        raw = f.read()

    workflow = json.loads(raw)

    def _substitute(obj):
        if isinstance(obj, str) and obj in params:
            return params[obj]
        if isinstance(obj, dict):
            return {k: _substitute(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [_substitute(v) for v in obj]
        return obj

    return _substitute(workflow)


def queue_prompt(workflow: dict) -> str:
    """POST the workflow to ComfyUI /prompt and return the prompt_id."""
    payload = json.dumps({"prompt": workflow}).encode("utf-8")
    req = urllib.request.Request(
        f"{COMFYUI_URL}/prompt",
        data=payload,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read())
    prompt_id = data["prompt_id"]
    print(f"  Queued prompt: {prompt_id}")
    return prompt_id


def poll_history(prompt_id: str, timeout: float = TIMEOUT) -> dict:
    """Poll /history/{prompt_id} until the job completes or times out."""
    start = time.time()
    while time.time() - start < timeout:
        try:
            url = f"{COMFYUI_URL}/history/{prompt_id}"
            with urllib.request.urlopen(url) as resp:
                history = json.loads(resp.read())
            if prompt_id in history:
                entry = history[prompt_id]
                status = entry.get("status", {})
                if status.get("completed", False) or "outputs" in entry:
                    print("  Job completed.")
                    return entry
                status_msg = status.get("status_str", "unknown")
                if status_msg == "error":
                    msgs = status.get("messages", [])
                    raise RuntimeError(f"ComfyUI job failed: {msgs}")
        except urllib.error.HTTPError as e:
            if e.code != 404:
                raise
        elapsed = int(time.time() - start)
        print(f"  Waiting... ({elapsed}s elapsed)", end="\r", flush=True)
        time.sleep(POLL_INTERVAL)

    raise TimeoutError(f"Job {prompt_id} did not complete within {timeout}s")


def download_output(history_entry: dict, output_path: str) -> str:
    """Download the first output image from the history entry."""
    outputs = history_entry.get("outputs", {})
    for node_id, node_out in outputs.items():
        images = node_out.get("images", [])
        if images:
            img_info = images[0]
            filename = img_info["filename"]
            subfolder = img_info.get("subfolder", "")
            img_type = img_info.get("type", "output")

            url = (
                f"{COMFYUI_URL}/view?"
                f"filename={urllib.request.quote(filename)}"
                f"&subfolder={urllib.request.quote(subfolder)}"
                f"&type={urllib.request.quote(img_type)}"
            )

            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            urllib.request.urlretrieve(url, output_path)
            size_kb = os.path.getsize(output_path) / 1024
            print(f"  Saved: {output_path} ({size_kb:.0f} KB)")
            return output_path

    raise RuntimeError("No output images found in job history")


def main():
    workflow_path = os.path.normpath(WORKFLOW_PATH)
    output_dir = os.path.normpath(OUTPUT_DIR)
    os.makedirs(output_dir, exist_ok=True)

    print(f"Workflow: {workflow_path}")
    print(f"Output dir: {output_dir}")
    print()

    # Copy fullbody as front view
    front_src = os.path.normpath(FULLBODY_SRC)
    front_dst = os.path.join(output_dir, "view-front.png")
    if os.path.exists(front_src):
        shutil.copy2(front_src, front_dst)
        size_kb = os.path.getsize(front_dst) / 1024
        print(f"[front] Copied fullbody -> {front_dst} ({size_kb:.0f} KB)")
    else:
        print(f"[front] WARNING: fullbody not found at {front_src}, skipping copy")
    print()

    # Generate side and back views sequentially
    for view in VIEWS:
        name = view["name"]
        output_file = os.path.join(output_dir, view["output"])
        print(f"[{name}] Generating...")

        # Merge base params with view-specific params
        params = {**BASE_PARAMS, **view["params"]}

        # Load, substitute, queue, poll, download
        workflow = load_and_substitute(workflow_path, params)
        print(f"  Substituted {len(params)} parameters")

        prompt_id = queue_prompt(workflow)
        entry = poll_history(prompt_id)
        download_output(entry, output_file)
        print()

    # Verify all files exist
    print("=== Verification ===")
    expected = ["view-front.png", "view-side.png", "view-back.png"]
    all_ok = True
    for fname in expected:
        fpath = os.path.join(output_dir, fname)
        if os.path.exists(fpath):
            size_kb = os.path.getsize(fpath) / 1024
            print(f"  OK: {fname} ({size_kb:.0f} KB)")
        else:
            print(f"  MISSING: {fname}")
            all_ok = False

    if all_ok:
        print("\nAll multiview images generated successfully.")
    else:
        print("\nSome images are missing!")
        sys.exit(1)


if __name__ == "__main__":
    main()
