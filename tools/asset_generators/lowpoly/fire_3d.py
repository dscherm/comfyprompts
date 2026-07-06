"""Fire a single image-to-3D job on ComfyUI and stream progress, so a long
TRELLIS/Hunyuan reconstruction is never an opaque block. POSTs the workflow with
the image (and seed) substituted, then polls /queue + /history, printing a
heartbeat line every ~20s and a terminal DONE/ERROR/TIMEOUT line. Meant to be run
under Monitor (each stdout line becomes a live notification) or in the background.

    python fire_3d.py <workflow.json> <image_name_in_comfy_input> [seed] [out_copy_dir]

Exits 0 with "DONE <img> -> <glb>" on success; 1 with ERROR/TIMEOUT otherwise.
"""
import glob
import json
import os
import shutil
import sys
import time
import urllib.request

COMFY = "http://localhost:8188"
COMFY_OUT = r"D:/Projects/ComfyUI/output"
TIMEOUT = 2400  # TRELLIS dual-contouring reconstruction can run 13+ min on complex meshes
HEARTBEAT = 20


def api(path, data=None):
    url = f"{COMFY}{path}"
    if data is not None:
        req = urllib.request.Request(url, data=json.dumps(data).encode(),
                                     headers={"Content-Type": "application/json"})
    else:
        req = urllib.request.Request(url)
    return json.loads(urllib.request.urlopen(req, timeout=30).read())


def sub(wf, m):
    def walk(x):
        if isinstance(x, dict):
            return {k: walk(v) for k, v in x.items()}
        if isinstance(x, list):
            return [walk(v) for v in x]
        return m.get(x, x) if isinstance(x, str) else x
    return walk(wf)


def find_glb(hist_entry, since):
    # prefer the export node's reported file; fall back to newest glb in output/3D
    for node in (hist_entry or {}).get("outputs", {}).values():
        for key in ("mesh", "result", "glb", "images", "gltf"):
            for it in node.get(key, []) if isinstance(node.get(key), list) else []:
                fn = it.get("filename") if isinstance(it, dict) else None
                if fn and fn.lower().endswith((".glb", ".gltf")):
                    return os.path.join(COMFY_OUT, it.get("subfolder", ""), fn)
    cands = [p for p in glob.glob(os.path.join(COMFY_OUT, "**", "*.glb"), recursive=True)
             if os.path.getmtime(p) >= since - 2]
    return max(cands, key=os.path.getmtime) if cands else None


def main():
    wf_path, image = sys.argv[1], sys.argv[2]
    seed = int(sys.argv[3]) if len(sys.argv) > 3 else 1234
    out_copy = sys.argv[4] if len(sys.argv) > 4 else None
    wf = json.load(open(wf_path))
    graph = sub(wf, {"PARAM_STR_IMAGE_PATH": image, "PARAM_INT_SEED": seed})

    t0 = time.time()
    pid = api("/prompt", {"prompt": graph, "client_id": "lowpoly-3d"})["prompt_id"]
    print(f"QUEUED {image} prompt_id={pid[:8]}", flush=True)

    last_hb, was_running = 0, False
    while time.time() - t0 < TIMEOUT:
        try:
            hist = api(f"/history/{pid}")
        except Exception:
            hist = {}
        if pid in hist:
            entry = hist[pid]
            status = entry.get("status", {})
            if status.get("status_str") == "error":
                print(f"ERROR {image}: execution failed (see ComfyUI log)", flush=True)
                sys.exit(1)
            if status.get("completed") or entry.get("outputs"):
                glb = find_glb(entry, t0)
                if not glb or not os.path.exists(glb):
                    print(f"ERROR {image}: completed but no GLB found", flush=True)
                    sys.exit(1)
                dst = glb
                if out_copy:
                    os.makedirs(out_copy, exist_ok=True)
                    dst = os.path.join(out_copy, os.path.splitext(image)[0] + ".glb")
                    shutil.copy2(glb, dst)
                print(f"DONE {image} -> {dst} ({int(time.time()-t0)}s)", flush=True)
                sys.exit(0)
        else:
            try:
                q = api("/queue")
                running = any(pid == r[1] for r in q.get("queue_running", []))
                if running and not was_running:
                    print(f"RUNNING {image}", flush=True)
                    was_running = True
            except Exception:
                pass
        if time.time() - last_hb >= HEARTBEAT:
            print(f"...{image} {int(time.time()-t0)}s elapsed", flush=True)
            last_hb = time.time()
        time.sleep(4)
    print(f"TIMEOUT {image} after {TIMEOUT}s", flush=True)
    sys.exit(1)


if __name__ == "__main__":
    main()
