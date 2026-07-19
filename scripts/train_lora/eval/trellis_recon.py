"""trellis_recon — reconstruct a 3D GLB from an isolated clay image via TRELLIS.2.

Fills the workflows/mcp/trellis2_image_to_3d.json params (image + seed + export
prefix) and queues it. TRELLIS.2 BLOCKS ComfyUI's HTTP server 10+ min per mesh
during reconstruction — this waits patiently, tolerating connection errors while
the server is busy, and NEVER assumes "down" (project_trellis_reconstruction_
blocks_server). Image must already be in ComfyUI/input/.

  python trellis_recon.py --image trellis_crank.png --prefix 3D/trellis_crank
"""
from __future__ import annotations

import argparse
import json
import time
import urllib.error
import urllib.request
from pathlib import Path

COMFY = "http://localhost:8188"
WF = json.loads((Path(__file__).resolve().parents[3] / "workflows" / "mcp"
                 / "trellis2_image_to_3d.json").read_text())
OUT = Path("D:/Projects/ComfyUI/output")


def build(image: str, seed: int, prefix: str) -> dict:
    wf = json.loads(json.dumps(WF))
    wf["2"]["inputs"]["image"] = image
    wf["5"]["inputs"]["seed"] = seed
    wf["15"]["inputs"]["filename_prefix"] = prefix
    return wf


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--image", required=True, help="filename already in ComfyUI/input/")
    ap.add_argument("--prefix", required=True, help="export filename_prefix, e.g. 3D/trellis_crank")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--timeout-min", type=float, default=30.0)
    a = ap.parse_args()

    data = json.dumps({"prompt": build(a.image, a.seed, a.prefix)}).encode()
    req = urllib.request.Request(f"{COMFY}/prompt", data=data,
                                 headers={"Content-Type": "application/json"})
    pid = json.loads(urllib.request.urlopen(req, timeout=30).read())["prompt_id"]
    print(f"queued {pid} for {a.image} -> {a.prefix}. TRELLIS blocks the server "
          f"~10+ min; waiting patiently (never killing)...", flush=True)

    t0 = time.time()
    while time.time() - t0 < a.timeout_min * 60:
        time.sleep(15)
        try:
            h = json.loads(urllib.request.urlopen(f"{COMFY}/history/{pid}", timeout=20).read())
        except (urllib.error.URLError, TimeoutError, OSError):
            print(f"  ...busy ({int(time.time() - t0)}s) — server blocked by reconstruction, waiting",
                  flush=True)
            continue
        if pid in h and h[pid].get("status", {}).get("completed"):
            outs = h[pid].get("outputs", {})
            found = []
            for node in outs.values():
                for key in ("result", "glb", "meshes", "gltf"):
                    for v in (node.get(key) or []):
                        if isinstance(v, str) and v.endswith(".glb"):
                            found.append(v)
            globbed = sorted(OUT.glob(f"{a.prefix}*.glb"))
            print(f"DONE in {int(time.time() - t0)}s. exported: "
                  f"{found or [str(p.relative_to(OUT)) for p in globbed]}", flush=True)
            return 0
    print(f"TIMEOUT after {a.timeout_min} min (may still be running — check {OUT / a.prefix}*)")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
