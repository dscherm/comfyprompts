"""Run the single-view TRELLIS2 image-to-3D workflow (max_views=1) for one image.
The MultiView queue script leaves the 2nd (back) loader on a stale default; this
uses the dedicated single-image workflow instead."""
import json, sys, time, urllib.request, urllib.parse
from pathlib import Path

COMFY = "http://localhost:8188"
WF = Path("D:/Projects/comfyui-toolchain/workflows/mcp/trellis2_image_to_3d.json")


def http(path, payload=None, timeout=120):
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(COMFY + path, data,
                                 {"Content-Type": "application/json"} if data else {})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())


def main():
    image = sys.argv[1] if len(sys.argv) > 1 else "wolf_concept.png"
    seed = int(sys.argv[2]) if len(sys.argv) > 2 else 12345
    out = sys.argv[3] if len(sys.argv) > 3 else "../models_glb/wolf.glb"

    wf = json.loads(WF.read_text(encoding="utf-8-sig"))
    wf = {k: v for k, v in wf.items() if not k.startswith("_")}
    # substitute PARAM_* placeholders
    txt = json.dumps(wf).replace("PARAM_STR_IMAGE_PATH", image)
    wf = json.loads(txt)
    wf["5"]["inputs"]["seed"] = seed
    wf["15"]["inputs"]["filename_prefix"] = "3D/wolf_trellis"

    pid = http("/prompt", {"prompt": wf})["prompt_id"]
    print(f"queued {pid} (TRELLIS reconstruction blocks the server ~5-10min; trust DONE)", flush=True)
    deadline = time.time() + 1800
    while time.time() < deadline:
        time.sleep(5)
        try:
            hist = http(f"/history/{pid}", timeout=30)
        except Exception:
            continue  # server busy reconstructing -> keep waiting (memory note)
        if pid not in hist:
            continue
        st = hist[pid].get("status", {})
        if st.get("status_str") == "error":
            raise SystemExit("ERROR " + json.dumps(hist[pid])[:500])
        if st.get("completed"):
            for node_out in hist[pid].get("outputs", {}).values():
                for key in ("meshes", "gltf", "3d", "files", "result"):
                    for m in node_out.get(key, []) or []:
                        if isinstance(m, dict) and m.get("filename", "").endswith((".glb", ".gltf")):
                            qs = urllib.parse.urlencode({"filename": m["filename"],
                                                         "subfolder": m.get("subfolder", ""),
                                                         "type": m.get("type", "output")})
                            Path(out).parent.mkdir(parents=True, exist_ok=True)
                            with urllib.request.urlopen(f"{COMFY}/view?{qs}", timeout=300) as r:
                                Path(out).write_bytes(r.read())
                            print(f"OUTPUT {out} ({Path(out).stat().st_size:,} bytes)", flush=True)
                            return
            print("DONE but no GLB in outputs:", json.dumps(hist[pid].get("outputs", {}))[:600], flush=True)
            return
    raise SystemExit("timeout")


if __name__ == "__main__":
    main()
