"""kart_trellis.py — batch single-view TRELLIS.2 image-to-3D for kart parts.

Adapted from products/berserkr_v2_creatures_v1/_work/trellis_single.py (proven runner).
Single-view (max_views=1) is REQUIRED — multiview corrupts these meshes (project_trellis
lessons). TRELLIS reconstruction BLOCKS the ComfyUI HTTP server ~5-10 min per part; the
/history poll tolerates that (curl failures = busy, keep waiting) and trusts the job's own
DONE — never kill a busy ComfyUI.

Each part: stage <part_id>.png in ComfyUI/input, reconstruct, download geometry GLB to
../models_glb/<part_id>.glb. Geometry-only (grey) — texture is a later stage.

Usage:
    python kart_trellis.py engine_steam wheel_knobby seat_bucket wpn_flamethrower
    python kart_trellis.py --seed 42 engine_steam
"""
import argparse
import json
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

COMFY = "http://localhost:8188"
WF = Path("D:/Projects/comfyui-toolchain/workflows/mcp/trellis2_image_to_3d.json")
OUT_DIR = Path(__file__).resolve().parent.parent / "models_glb"


def http(path, payload=None, timeout=120):
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(COMFY + path, data,
                                 {"Content-Type": "application/json"} if data else {})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())


def reconstruct(part_id: str, seed: int) -> bool:
    wf = json.loads(WF.read_text(encoding="utf-8-sig"))
    wf = {k: v for k, v in wf.items() if not k.startswith("_")}
    txt = json.dumps(wf).replace("PARAM_STR_IMAGE_PATH", f"{part_id}.png")
    wf = json.loads(txt)
    wf["5"]["inputs"]["seed"] = seed
    wf["15"]["inputs"]["filename_prefix"] = f"3D/kart_{part_id}"

    pid = http("/prompt", {"prompt": wf})["prompt_id"]
    print(f"[{part_id}] queued {pid} — TRELLIS blocks server ~5-10min; trusting DONE", flush=True)
    deadline = time.time() + 1800
    while time.time() < deadline:
        time.sleep(5)
        try:
            hist = http(f"/history/{pid}", timeout=30)
        except Exception:
            continue  # server busy reconstructing -> keep waiting
        if pid not in hist:
            continue
        st = hist[pid].get("status", {})
        if st.get("status_str") == "error":
            print(f"[{part_id}] ERROR {json.dumps(hist[pid])[:400]}", flush=True)
            return False
        if st.get("completed"):
            # Trellis2ExportMesh writes the GLB straight to output/3D/ without registering
            # it in /history outputs, so retrieve from disk by the filename_prefix.
            out3d = Path("D:/Projects/ComfyUI/output/3D")
            cands = sorted(out3d.glob(f"kart_{part_id}_*.glb"), key=lambda p: p.stat().st_mtime)
            if cands:
                OUT_DIR.mkdir(parents=True, exist_ok=True)
                dst = OUT_DIR / f"{part_id}.glb"
                dst.write_bytes(cands[-1].read_bytes())
                print(f"[{part_id}] OUTPUT {dst} ({dst.stat().st_size:,} bytes)", flush=True)
                return True
            print(f"[{part_id}] DONE but no GLB on disk under {out3d}", flush=True)
            return False
    print(f"[{part_id}] TIMEOUT", flush=True)
    return False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("parts", nargs="+", help="part ids (each staged as <id>.png in ComfyUI/input)")
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()
    ok = 0
    for i, part in enumerate(args.parts, 1):
        print(f"=== [{i}/{len(args.parts)}] {part} ===", flush=True)
        if reconstruct(part, args.seed):
            ok += 1
    print(f"DONE {ok}/{len(args.parts)} parts reconstructed", flush=True)


if __name__ == "__main__":
    sys.exit(0 if main() is None else 0)
