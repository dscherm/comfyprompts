"""Convert character front view to 3D GLB via Hunyuan3D v2.0 on ComfyUI."""
import copy
import json
import shutil
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

COMFYUI_URL = "http://127.0.0.1:8188"
COMFYUI_OUTPUT = Path("D:/Projects/ComfyUI/output")
ROOT = Path(__file__).resolve().parent.parent.parent.parent
WORKFLOW_DIR = ROOT / "workflows" / "mcp"
OUTPUT_DIR = ROOT / "pipelines" / "character-ralph" / "output" / "3d"
INPUT_IMAGE = ROOT / "pipelines" / "character-ralph" / "output" / "multiview" / "view-front.png"


def upload_image(image_path: Path) -> str:
    with open(image_path, "rb") as f:
        img_data = f.read()
    boundary = "----FormBoundary7MA4YWxkTrZu0gW"
    body = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="image"; filename="{image_path.name}"\r\n'
        f"Content-Type: image/png\r\n\r\n"
    ).encode() + img_data + f"\r\n--{boundary}--\r\n".encode()
    req = urllib.request.Request(
        f"{COMFYUI_URL}/upload/image", data=body,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"}, method="POST")
    with urllib.request.urlopen(req, timeout=30) as resp:
        result = json.loads(resp.read())
    return result["name"]


def main():
    character_id = sys.argv[1] if len(sys.argv) > 1 else "player"
    print(f"Input image: {INPUT_IMAGE} ({INPUT_IMAGE.stat().st_size // 1024}KB)")

    # Upload image
    image_name = upload_image(INPUT_IMAGE)
    print(f"Uploaded as: {image_name}")

    # Load workflow
    with open(WORKFLOW_DIR / "hunyuan3d_v20_image_to_3d.json") as f:
        wf = json.load(f)

    # Substitute params
    params = {
        "PARAM_STR_IMAGE_PATH": image_name,
        "PARAM_FLOAT_GUIDANCE_SCALE": 5.5,
        "PARAM_INT_STEPS": 50,
        "PARAM_INT_SEED": 42,
        "PARAM_INT_OCTREE_RESOLUTION": 384,
        "PARAM_INT_MAX_FACES": 50000,
    }
    wf2 = copy.deepcopy(wf)
    for node_id, node in wf2.items():
        inputs = node.get("inputs", {})
        for key, value in list(inputs.items()):
            if isinstance(value, str) and value.startswith("PARAM_"):
                if value in params:
                    inputs[key] = params[value]

    # Set output prefixes
    prefix = f"character-ralph/{character_id}"
    wf2["11"]["inputs"]["filename_prefix"] = f"3D/{prefix}_geometry"
    wf2["24"]["inputs"]["filename_prefix"] = f"3D/{prefix}_textured"

    # Queue prompt
    payload = json.dumps({"prompt": wf2}).encode()
    req = urllib.request.Request(
        f"{COMFYUI_URL}/prompt", data=payload,
        headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read())
        prompt_id = data["prompt_id"]
        print(f"Queued prompt: {prompt_id}")
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")[:2000]
        print(f"ERROR: ComfyUI rejected prompt (HTTP {e.code}): {body}")
        sys.exit(1)

    # Poll for completion
    print("Waiting for generation (~5 min on RTX 3070)...")
    deadline = time.time() + 600
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(f"{COMFYUI_URL}/history/{prompt_id}", timeout=10) as resp:
                data = json.loads(resp.read())
            if prompt_id in data:
                entry = data[prompt_id]
                status = entry.get("status", {})
                if status.get("status_str") == "success" or status.get("completed", False):
                    print("Generation complete!")
                    return save_outputs(entry, character_id)
                elif status.get("status_str") == "error":
                    msgs = status.get("messages", [])
                    for m in msgs:
                        if m[0] == "execution_error":
                            print(f"ERROR: {m[1].get('exception_message', '')[:500]}")
                    sys.exit(1)
        except Exception:
            pass
        time.sleep(15)

    print("TIMEOUT: Generation did not complete within 10 minutes")
    sys.exit(1)


def save_outputs(entry: dict, character_id: str) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    outputs = entry.get("outputs", {})
    downloaded = False

    # Try history outputs API
    for node_id, out_name in [("24", "character-raw.glb"), ("11", "character-geometry.glb")]:
        node_out = outputs.get(node_id, {})
        gltf_list = node_out.get("3d", node_out.get("gltf", node_out.get("mesh", [])))
        for glb_info in gltf_list:
            filename = glb_info.get("filename", "")
            subfolder = glb_info.get("subfolder", "")
            glb_type = glb_info.get("type", "output")
            url = f"{COMFYUI_URL}/view?filename={filename}&subfolder={subfolder}&type={glb_type}"
            try:
                out_path = OUTPUT_DIR / out_name
                with urllib.request.urlopen(url, timeout=60) as resp:
                    with open(out_path, "wb") as f:
                        f.write(resp.read())
                size_mb = out_path.stat().st_size / (1024 * 1024)
                print(f"Saved: {out_path} ({size_mb:.1f} MB)")
                downloaded = True
            except Exception as e:
                print(f"Download via API failed for node {node_id}: {e}")

    # Fallback: scan ComfyUI output directory
    if not downloaded:
        for suffix, out_name in [("textured", "character-raw.glb"), ("geometry", "character-geometry.glb")]:
            search_dir = COMFYUI_OUTPUT / "3D" / "character-ralph"
            if search_dir.exists():
                matches = sorted(
                    search_dir.glob(f"{character_id}_{suffix}_*.glb"),
                    key=lambda p: p.stat().st_mtime, reverse=True)
                if matches:
                    out_path = OUTPUT_DIR / out_name
                    shutil.copy2(matches[0], out_path)
                    size_mb = out_path.stat().st_size / (1024 * 1024)
                    print(f"Saved: {out_path} ({size_mb:.1f} MB) [from {matches[0].name}]")
                    downloaded = True

    # Last resort: glob everything
    if not downloaded:
        search_dir = COMFYUI_OUTPUT / "3D"
        if search_dir.exists():
            all_glbs = sorted(search_dir.rglob(f"{character_id}_*.glb"),
                              key=lambda p: p.stat().st_mtime, reverse=True)
            if all_glbs:
                out_path = OUTPUT_DIR / "character-raw.glb"
                shutil.copy2(all_glbs[0], out_path)
                size_mb = out_path.stat().st_size / (1024 * 1024)
                print(f"Saved: {out_path} ({size_mb:.1f} MB) [from {all_glbs[0].name}]")
                downloaded = True

    if downloaded:
        # Copy best result as the canonical character.glb
        raw = OUTPUT_DIR / "character-raw.glb"
        if raw.exists():
            shutil.copy2(raw, OUTPUT_DIR / "character.glb")
            print("Copied character-raw.glb -> character.glb")
        print("SUCCESS")
    else:
        print("WARNING: Generation succeeded but could not find output GLB")
        print("Outputs:", json.dumps(outputs, indent=2)[:2000])
        sys.exit(1)


if __name__ == "__main__":
    main()
