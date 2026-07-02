"""Soapbox Kart Kit — convert the 5 LoRA mascot-racer refs to low-poly 3D meshes
via Hunyuan3D v2.0 geometry-only (built-in bg removal). Reuses the proven
character-ralph batch logic. Output: products/.../mascots/<name>-raw.glb.

    D:/Projects/ComfyUI/venv/Scripts/python.exe mascot_to_3d.py
    D:/Projects/ComfyUI/venv/Scripts/python.exe mascot_to_3d.py robot,frog
"""
import copy
import json
import shutil
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

COMFYUI_URL = "http://localhost:8188"
COMFYUI_OUTPUT = Path("D:/Projects/ComfyUI/output")
ROOT = Path("D:/Projects/comfyui-toolchain/products/soapbox_kart_kit_v1")
REFS = ROOT / "refs"
DEST = ROOT / "mascots"

MASCOTS = ["robot", "frog", "wizard", "shark", "skeleton"]
GUIDANCE, STEPS, OCTREE, MAX_FACES = 5.5, 40, 256, 20000  # low-poly kit target

# textured mode -> hunyuan3d_v20_image_to_3d.json, export node 24, output <name>.glb (final)
# geometry mode -> hunyuan3d_v20_geometry_only.json, export node 11, output <name>-raw.glb
TEXTURED = "--textured" in sys.argv
if TEXTURED:
    sys.argv = [a for a in sys.argv if a != "--textured"]
WORKFLOW = Path("D:/Projects/comfyui-toolchain/workflows/mcp/"
                + ("hunyuan3d_v20_image_to_3d.json" if TEXTURED else "hunyuan3d_v20_geometry_only.json"))
EXPORT_NODE = "24" if TEXTURED else "11"
SUFFIX = ".glb" if TEXTURED else "-raw.glb"


def upload_image(p: Path) -> str:
    data = p.read_bytes()
    b = "----FB7MA4YWxkTrZu0gW"
    body = (f"--{b}\r\nContent-Disposition: form-data; name=\"image\"; filename=\"{p.name}\"\r\n"
            f"Content-Type: image/png\r\n\r\n").encode() + data + f"\r\n--{b}--\r\n".encode()
    req = urllib.request.Request(f"{COMFYUI_URL}/upload/image", data=body,
                                 headers={"Content-Type": f"multipart/form-data; boundary={b}"}, method="POST")
    return json.loads(urllib.request.urlopen(req, timeout=30).read())["name"]


def build(image_name: str, prefix: str, seed: int) -> dict:
    wf = copy.deepcopy(json.load(open(WORKFLOW)))
    params = {
        "PARAM_STR_IMAGE_PATH": image_name, "PARAM_FLOAT_GUIDANCE_SCALE": GUIDANCE,
        "PARAM_INT_STEPS": STEPS, "PARAM_INT_SEED": seed,
        "PARAM_INT_OCTREE_RESOLUTION": OCTREE, "PARAM_INT_MAX_FACES": MAX_FACES,
    }
    for node in wf.values():
        for k, v in list(node.get("inputs", {}).items()):
            if isinstance(v, str) and v in params:
                node["inputs"][k] = params[v]
    wf[EXPORT_NODE]["inputs"]["filename_prefix"] = prefix
    return wf


def queue(wf: dict) -> str:
    req = urllib.request.Request(f"{COMFYUI_URL}/prompt", data=json.dumps({"prompt": wf}).encode(),
                                 headers={"Content-Type": "application/json"})
    try:
        return json.loads(urllib.request.urlopen(req, timeout=30).read())["prompt_id"]
    except urllib.error.HTTPError as e:
        print("  HTTP", e.code, e.read().decode()[:800])
        raise


def poll(pid: str, timeout=600, interval=8):
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            d = json.loads(urllib.request.urlopen(f"{COMFYUI_URL}/history/{pid}", timeout=10).read())
            if pid in d:
                st = d[pid].get("status", {})
                if st.get("status_str") == "success" or st.get("completed"):
                    return d[pid]
                if st.get("status_str") == "error":
                    for m in st.get("messages", []):
                        if m[0] == "execution_error":
                            print("  ERR", m[1].get("exception_message", "")[:300])
                    return None
        except Exception:
            pass
        time.sleep(interval)
    print("  TIMEOUT")
    return None


def retrieve(entry: dict, prefix: str, dest: Path) -> bool:
    out = entry.get("outputs", {}).get(EXPORT_NODE, {})
    for key in ("3d", "gltf", "mesh"):
        for item in out.get(key, []):
            url = (f"{COMFYUI_URL}/view?filename={item.get('filename','')}"
                   f"&subfolder={item.get('subfolder','')}&type={item.get('type','output')}")
            try:
                data = urllib.request.urlopen(url, timeout=60).read()
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_bytes(data)
                print(f"  saved via API -> {dest} ({dest.stat().st_size/1e6:.1f} MB)")
                return True
            except Exception:
                pass
    for t in out.get("text", []):
        src = Path(t) if isinstance(t, str) else None
        if src and src.exists():
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dest)
            print(f"  copied from text -> {dest} ({dest.stat().st_size/1e6:.1f} MB)")
            return True
    parts = prefix.split("/")
    scan = COMFYUI_OUTPUT / parts[0] if len(parts) == 2 else COMFYUI_OUTPUT
    pref = parts[1] if len(parts) == 2 else prefix
    if scan.exists():
        c = sorted(scan.glob(f"{pref}*.glb"), key=lambda p: p.stat().st_mtime, reverse=True)
        if c:
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(c[0], dest)
            print(f"  copied from fs {c[0].name} -> {dest} ({dest.stat().st_size/1e6:.1f} MB)")
            return True
    print("  COULD NOT FIND GLB for", prefix)
    return False


def main():
    which = sys.argv[1].split(",") if len(sys.argv) > 1 else MASCOTS
    ok = 0
    for i, name in enumerate(which):
        img = REFS / f"mascot_{name}.png"
        if not img.exists():
            print(f"[{name}] SKIP — no ref {img}")
            continue
        dest = DEST / f"{name}{SUFFIX}"
        print(f"[{i+1}/{len(which)}] {name} ({'textured' if TEXTURED else 'geometry'}): uploading {img.name}")
        up = upload_image(img)
        prefix = f"3D/soapbox_{name}{'_tex' if TEXTURED else ''}"
        pid = queue(build(up, prefix, seed=42 + i))
        print(f"  queued {pid}; waiting…")
        t0 = time.time()
        entry = poll(pid)
        if entry and retrieve(entry, prefix, dest):
            ok += 1
            print(f"  DONE {name} in {time.time()-t0:.0f}s")
        else:
            print(f"  FAILED {name}")
    print(f"MASCOTS 3D DONE: {ok}/{len(which)} -> {DEST}")


if __name__ == "__main__":
    main()
