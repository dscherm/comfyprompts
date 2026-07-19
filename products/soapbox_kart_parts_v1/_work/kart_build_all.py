"""kart_build_all.py — automode: reconstruct + clean + render every kit part.

Driven by kit.json (48 parts). For each part, resumable and fault-tolerant:
  1. pick the source concept image (prefer the s42 seed, else the first kept seed)
  2. stage it into ComfyUI/input as <part_id>.png
  3. TRELLIS.2 single-view -> raw_glb/<part_id>.glb   (disk retrieval; long deadline)
  4. strip the fused ground slab -> models_glb/<part_id>.glb   (strip_base.py)
  5. clay render 4 views -> review/<part_id>_*.png            (render_clay.py)

Skips a part whose models_glb/<id>.glb AND review/<id>_front.png already exist, so the
batch can be killed and relaunched. Logs one line per part; a per-part failure is logged
and skipped, never aborts the run. TRELLIS blocks the ComfyUI server ~6-15 min per part
(denser parts longer) — the poller tolerates that and trusts the job's own DONE.

Run with ComfyUI venv python (urllib only; spawns Blender for strip/render):
    python kart_build_all.py            # all pending parts
    python kart_build_all.py engine_steam wheel_mag   # just these ids
"""
import json
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path("D:/Projects/comfyui-toolchain/products/soapbox_kart_parts_v1")
WORK = ROOT / "_work"
RESCUE = Path("D:/Projects/comfyui-toolchain/_RESCUE_soapbox_kart_dataset")
COMFY_INPUT = Path("D:/Projects/ComfyUI/input")
OUT3D = Path("D:/Projects/ComfyUI/output/3D")
COMFY = "http://localhost:8188"
WF = Path("D:/Projects/comfyui-toolchain/workflows/mcp/trellis2_image_to_3d.json")
BLENDER = "C:/Program Files/Blender Foundation/Blender 5.0/blender.exe"
DEADLINE_S = 3000  # 50 min per part; dense meshes reconstruct slowly

RAW = ROOT / "raw_glb"; MODELS = ROOT / "models_glb"; REVIEW = WORK / "review"
for d in (RAW, MODELS, REVIEW):
    d.mkdir(parents=True, exist_ok=True)
LOG = WORK / "build_all.log"


def log(msg):
    line = f"[{time.strftime('%H:%M:%S')}] {msg}"
    print(line, flush=True)
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def http(path, payload=None, timeout=120):
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(COMFY + path, data,
                                 {"Content-Type": "application/json"} if data else {})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())


def pick_image(part):
    srcs = part.get("source_2d") or []
    if not srcs:
        return None
    for s in srcs:
        if s.endswith("s42.png"):
            return s
    return srcs[0]


def trellis(part_id):
    wf = json.loads(WF.read_text(encoding="utf-8-sig"))
    wf = {k: v for k, v in wf.items() if not k.startswith("_")}
    wf = json.loads(json.dumps(wf).replace("PARAM_STR_IMAGE_PATH", f"{part_id}.png"))
    wf["5"]["inputs"]["seed"] = 42
    wf["15"]["inputs"]["filename_prefix"] = f"3D/kart_{part_id}"
    pid = http("/prompt", {"prompt": wf})["prompt_id"]
    deadline = time.time() + DEADLINE_S
    while time.time() < deadline:
        time.sleep(6)
        try:
            hist = http(f"/history/{pid}", timeout=30)
        except Exception:
            continue  # server busy reconstructing
        if pid in hist:
            st = hist[pid].get("status", {})
            if st.get("status_str") == "error":
                return None
            if st.get("completed"):
                cands = sorted(OUT3D.glob(f"kart_{part_id}_*.glb"), key=lambda p: p.stat().st_mtime)
                if cands:
                    dst = RAW / f"{part_id}.glb"
                    dst.write_bytes(cands[-1].read_bytes())
                    return dst
                return None
    return None  # timed out; job may finish later, retrieved on a rerun


def blender(script, args):
    r = subprocess.run([BLENDER, "--background", "--python", str(WORK / script), "--", *args],
                       capture_output=True, text=True, timeout=600)
    return r.returncode == 0, r.stdout


def build_part(part):
    pid = part["id"]
    if (MODELS / f"{pid}.glb").exists() and (REVIEW / f"{pid}_front.png").exists():
        log(f"SKIP {pid} (already built)")
        return True
    img = pick_image(part)
    if not img or not (RESCUE / img).exists():
        log(f"FAIL {pid}: no source image ({img})")
        return False
    (COMFY_INPUT / f"{pid}.png").write_bytes((RESCUE / img).read_bytes())

    log(f"TRELLIS {pid} <- {img}")
    raw = trellis(pid)
    if not raw:
        log(f"FAIL {pid}: TRELLIS produced no mesh")
        return False

    ok, _ = blender("strip_base.py", ["--input", str(raw), "--output", str(MODELS / f"{pid}.glb")])
    if not ok or not (MODELS / f"{pid}.glb").exists():
        log(f"FAIL {pid}: strip failed")
        return False

    blender("render_clay.py", [str(MODELS / f"{pid}.glb"), pid, str(REVIEW), "512"])
    sz = (MODELS / f"{pid}.glb").stat().st_size
    log(f"OK {pid} ({sz:,} bytes)")
    return True


def main():
    kit = json.loads((ROOT / "kit.json").read_text(encoding="utf-8"))
    parts = kit["parts"]
    only = set(sys.argv[1:])
    if only:
        parts = [p for p in parts if p["id"] in only]
    log(f"=== BUILD ALL: {len(parts)} parts ===")
    done = 0
    for i, part in enumerate(parts, 1):
        log(f"--- [{i}/{len(parts)}] {part['id']} ({part['category']}) ---")
        try:
            if build_part(part):
                done += 1
        except Exception as e:
            log(f"FAIL {part['id']}: {type(e).__name__} {e}")
    log(f"=== DONE {done}/{len(parts)} built ===")


if __name__ == "__main__":
    main()
