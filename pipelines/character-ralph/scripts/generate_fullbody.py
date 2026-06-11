"""Generate a fullbody character image via ComfyUI REST API.

Loads the parametric workflow, substitutes PARAM_* placeholders,
queues the prompt, polls for completion, and downloads the output image.
Uses only stdlib (urllib) -- no pip dependencies required.
"""

import json
import os
import time
import urllib.error
import urllib.request

COMFYUI_URL = os.environ.get("COMFYUI_URL", "http://localhost:8188")
WORKFLOW_PATH = os.path.join(
    os.path.dirname(__file__), "..", "..", "..", "workflows", "mcp", "generate_image.json"
)
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "output", "fullbody")
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "fullbody.png")

# Parameter substitutions -- keys must match the exact placeholder strings in the workflow JSON
PARAMS: dict[str, str | int | float] = {
    "PARAM_PROMPT": (
        "The Rookie, young male racer, full body character design, A-pose with arms at 45 "
        "degrees from sides, legs slightly apart, front view, symmetrical pose. Orange racing "
        "jacket with black stripes. Aviator goggles pushed up on forehead. Fingerless brown "
        "leather gloves. Dark cargo pants. Heavy boots. Short messy brown hair. Utility belt "
        "with tools. Confident stance. Otomo Akira meets R Crumb underground comix style, "
        "clean ink with obsessive detail, post-apocalyptic character design. Full body visible "
        "head to toe, centered in frame, clean solid grey background, character concept art, "
        "high quality, detailed costume design"
    ),
    "PARAM_NEGATIVE_PROMPT": (
        "blurry, low quality, deformed, ugly, photorealistic, 3D render, smooth digital art, "
        "anime, chibi, cute, Disney, watermark, text, signature, multiple characters, cropped, "
        "partial body, cut off legs, cut off arms, missing limbs, side view, back view, "
        "sitting, seated, weapons in hands"
    ),
    "PARAM_INT_WIDTH": 768,
    "PARAM_INT_HEIGHT": 1024,
    "PARAM_INT_SEED": 42,
    "PARAM_INT_STEPS": 25,
    "PARAM_FLOAT_CFG": 1.0,
    "PARAM_FLOAT_DENOISE": 1.0,
    "PARAM_STR_SAMPLER_NAME": "euler",
    "PARAM_STR_SCHEDULER": "simple",
}

POLL_INTERVAL = 2  # seconds
TIMEOUT = 300  # seconds


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
    print(f"Queued prompt: {prompt_id}")
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
                    print("Job completed.")
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
            print(f"Saved: {output_path} ({size_kb:.0f} KB)")
            return output_path

    raise RuntimeError("No output images found in job history")


def main():
    workflow_path = os.path.normpath(WORKFLOW_PATH)
    output_path = os.path.normpath(OUTPUT_FILE)

    print(f"Workflow: {workflow_path}")
    print(f"Output:   {output_path}")

    # 1. Load and substitute
    workflow = load_and_substitute(workflow_path, PARAMS)
    print(f"Substituted {len(PARAMS)} parameters")

    # 2. Queue
    prompt_id = queue_prompt(workflow)

    # 3. Poll
    entry = poll_history(prompt_id)

    # 4. Download
    download_output(entry, output_path)

    print("Done.")


if __name__ == "__main__":
    main()
