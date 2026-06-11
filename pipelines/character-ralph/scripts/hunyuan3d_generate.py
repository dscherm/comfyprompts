"""Generate 3D mesh from fullbody image using Hunyuan3D v2.0 via ComfyUI REST API.

Uses only urllib (no pip dependencies).
"""

import json
import os
import shutil
import sys
import time
import urllib.parse
import urllib.request
import uuid

COMFYUI_URL = "http://localhost:8188"
WORKFLOW_PATH = "D:/Projects/comfyui-toolchain/workflows/mcp/hunyuan3d_v20_image_to_3d.json"
INPUT_IMAGE = "D:/Projects/comfyui-toolchain/pipelines/character-ralph/output/fullbody/fullbody.png"
OUTPUT_GLB = "D:/Projects/comfyui-toolchain/pipelines/character-ralph/output/3d/player_raw.glb"

# Parameters
GUIDANCE_SCALE = 5.5
STEPS = 50
SEED = 42
OCTREE_RESOLUTION = 256  # Lower than default 384 to save VRAM on 8GB card
MAX_FACES = 50000

POLL_INTERVAL = 5  # seconds
TIMEOUT = 600  # 10 minutes max


def upload_image(image_path: str) -> str:
    """Upload image to ComfyUI, return the filename as stored by ComfyUI."""
    filename = os.path.basename(image_path)

    # Build multipart form data manually (no requests library)
    boundary = uuid.uuid4().hex
    with open(image_path, "rb") as f:
        image_data = f.read()

    body = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="image"; filename="{filename}"\r\n'
        f"Content-Type: image/png\r\n\r\n"
    ).encode("utf-8")
    body += image_data
    body += f"\r\n--{boundary}\r\n".encode("utf-8")
    body += (
        f'Content-Disposition: form-data; name="overwrite"\r\n\r\ntrue\r\n'
        f"--{boundary}--\r\n"
    ).encode("utf-8")

    req = urllib.request.Request(
        f"{COMFYUI_URL}/upload/image",
        data=body,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        method="POST",
    )
    with urllib.request.urlopen(req) as resp:
        result = json.loads(resp.read())
        uploaded_name = result.get("name", filename)
        subfolder = result.get("subfolder", "")
        print(f"  Uploaded: {uploaded_name} (subfolder: {subfolder!r})")
        return uploaded_name


def build_workflow(image_filename: str) -> dict:
    """Load workflow JSON and substitute PARAM_* placeholders."""
    with open(WORKFLOW_PATH) as f:
        workflow = json.load(f)

    # Substitute parameters
    substitutions = {
        "PARAM_STR_IMAGE_PATH": image_filename,
        "PARAM_FLOAT_GUIDANCE_SCALE": GUIDANCE_SCALE,
        "PARAM_INT_STEPS": STEPS,
        "PARAM_INT_SEED": SEED,
        "PARAM_INT_OCTREE_RESOLUTION": OCTREE_RESOLUTION,
        "PARAM_INT_MAX_FACES": MAX_FACES,
    }

    def substitute(obj):
        if isinstance(obj, str) and obj in substitutions:
            return substitutions[obj]
        if isinstance(obj, dict):
            return {k: substitute(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [substitute(v) for v in obj]
        return obj

    workflow = substitute(workflow)
    return workflow


def queue_prompt(workflow: dict) -> str:
    """Queue the workflow and return the prompt_id."""
    client_id = uuid.uuid4().hex
    payload = json.dumps({"prompt": workflow, "client_id": client_id}).encode("utf-8")
    req = urllib.request.Request(
        f"{COMFYUI_URL}/prompt",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req) as resp:
        result = json.loads(resp.read())

    if "error" in result:
        print(f"ERROR queueing prompt: {json.dumps(result['error'], indent=2)}")
        if "node_errors" in result:
            print(f"Node errors: {json.dumps(result['node_errors'], indent=2)}")
        sys.exit(1)

    prompt_id = result["prompt_id"]
    print(f"  Queued prompt: {prompt_id}")
    return prompt_id


def poll_until_complete(prompt_id: str) -> dict:
    """Poll /history/{prompt_id} until the job completes or fails."""
    start = time.time()
    last_status = ""
    while True:
        elapsed = time.time() - start
        if elapsed > TIMEOUT:
            print(f"TIMEOUT after {TIMEOUT}s")
            sys.exit(1)

        # Check queue status
        try:
            with urllib.request.urlopen(f"{COMFYUI_URL}/queue") as resp:
                queue = json.loads(resp.read())
            running = len(queue.get("queue_running", []))
            pending = len(queue.get("queue_pending", []))
            status = f"running={running}, pending={pending}"
            if status != last_status:
                print(f"  [{elapsed:.0f}s] Queue: {status}")
                last_status = status
        except Exception:
            pass

        # Check history for completion
        try:
            with urllib.request.urlopen(f"{COMFYUI_URL}/history/{prompt_id}") as resp:
                history = json.loads(resp.read())
        except Exception:
            time.sleep(POLL_INTERVAL)
            continue

        if prompt_id in history:
            entry = history[prompt_id]
            status_info = entry.get("status", {})
            if status_info.get("completed", False) or status_info.get("status_str") == "success":
                print(f"  Completed in {elapsed:.0f}s")
                return entry
            if status_info.get("status_str") == "error":
                print(f"  FAILED after {elapsed:.0f}s")
                # Print error messages from nodes
                msgs = status_info.get("messages", [])
                for msg in msgs:
                    print(f"    {msg}")
                outputs = entry.get("outputs", {})
                for node_id, out in outputs.items():
                    if "error" in str(out).lower():
                        print(f"    Node {node_id}: {out}")
                sys.exit(1)

        time.sleep(POLL_INTERVAL)


def find_and_download_glb(history_entry: dict) -> bool:
    """Find GLB output in history and download it."""
    outputs = history_entry.get("outputs", {})

    # Look for GLB files in outputs - check nodes 11 (geometry) and 24 (textured)
    glb_files = []
    for node_id, node_output in outputs.items():
        # Hy3DExportMesh outputs might be in 'mesh' or 'result' key
        for key in ("mesh", "result", "gltf", "glb", "3d", "file"):
            if key in node_output:
                items = node_output[key]
                if isinstance(items, list):
                    for item in items:
                        if isinstance(item, dict) and "filename" in item:
                            glb_files.append(item)
                elif isinstance(items, dict) and "filename" in items:
                    glb_files.append(items)

        # Also check for any dict with filename ending in .glb
        for key, val in node_output.items():
            if isinstance(val, list):
                for item in val:
                    if isinstance(item, dict) and item.get("filename", "").endswith(".glb"):
                        if item not in glb_files:
                            glb_files.append(item)

    if not glb_files:
        print(f"  No GLB files found in outputs. Output keys:")
        for nid, out in outputs.items():
            print(f"    Node {nid}: {list(out.keys())}")
        # Dump full output for debugging
        print(f"  Full outputs: {json.dumps(outputs, indent=2, default=str)[:2000]}")
        return False

    print(f"  Found {len(glb_files)} GLB file(s):")
    for g in glb_files:
        print(f"    {g}")

    # Prefer textured (node 24) over geometry-only (node 11)
    # If textured exists, use it; otherwise use geometry
    target = glb_files[-1]  # Last one is usually textured
    for g in glb_files:
        if "textured" in g.get("filename", ""):
            target = g
            break

    filename = target["filename"]
    subfolder = target.get("subfolder", "")
    ftype = target.get("type", "output")

    # Download the file
    params = urllib.parse.urlencode({
        "filename": filename,
        "subfolder": subfolder,
        "type": ftype,
    })
    url = f"{COMFYUI_URL}/view?{params}"
    print(f"  Downloading: {url}")

    req = urllib.request.Request(url)
    with urllib.request.urlopen(req) as resp:
        data = resp.read()

    os.makedirs(os.path.dirname(OUTPUT_GLB), exist_ok=True)
    with open(OUTPUT_GLB, "wb") as f:
        f.write(data)
    print(f"  Saved to: {OUTPUT_GLB} ({len(data)} bytes)")
    return True


def main():
    print("=" * 60)
    print("Hunyuan3D v2.0 Image-to-3D Generation")
    print("=" * 60)
    print(f"Input:  {INPUT_IMAGE}")
    print(f"Output: {OUTPUT_GLB}")
    print(f"Params: guidance={GUIDANCE_SCALE}, steps={STEPS}, seed={SEED}")
    print(f"        octree_resolution={OCTREE_RESOLUTION}, max_faces={MAX_FACES}")
    print()

    print("[1/4] Uploading image to ComfyUI...")
    image_filename = upload_image(INPUT_IMAGE)

    print("[2/4] Building workflow...")
    workflow = build_workflow(image_filename)
    # Verify key substitutions
    assert workflow["1"]["inputs"]["image"] == image_filename
    assert workflow["8"]["inputs"]["guidance_scale"] == GUIDANCE_SCALE
    assert workflow["8"]["inputs"]["steps"] == STEPS
    assert workflow["9"]["inputs"]["octree_resolution"] == OCTREE_RESOLUTION
    print(f"  Workflow has {len(workflow)} nodes")

    print("[3/4] Queueing prompt...")
    prompt_id = queue_prompt(workflow)

    print("[4/4] Waiting for generation (this may take 2-5 minutes)...")
    history_entry = poll_until_complete(prompt_id)

    print("Downloading GLB output...")
    success = find_and_download_glb(history_entry)

    if success:
        size_mb = os.path.getsize(OUTPUT_GLB) / (1024 * 1024)
        print(f"\nSUCCESS: {OUTPUT_GLB} ({size_mb:.1f} MB)")
    else:
        # Fallback: scan ComfyUI output directory directly
        comfyui_output = "D:/Projects/ComfyUI/output/3D"
        print(f"\n  Scanning {comfyui_output} for recent GLB files...")
        if os.path.isdir(comfyui_output):
            glbs = sorted(
                [f for f in os.listdir(comfyui_output) if f.endswith(".glb")],
                key=lambda f: os.path.getmtime(os.path.join(comfyui_output, f)),
                reverse=True,
            )
            if glbs:
                source = os.path.join(comfyui_output, glbs[0])
                age = time.time() - os.path.getmtime(source)
                if age < 600:  # Created in last 10 minutes
                    print(f"  Found recent GLB: {glbs[0]} ({age:.0f}s ago)")
                    shutil.copy2(source, OUTPUT_GLB)
                    size_mb = os.path.getsize(OUTPUT_GLB) / (1024 * 1024)
                    print(f"  SUCCESS (fallback): {OUTPUT_GLB} ({size_mb:.1f} MB)")
                    return
        print("\nFAILED: Could not find output GLB file")
        sys.exit(1)


if __name__ == "__main__":
    main()
