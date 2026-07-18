"""Drive Meshy's Image-to-3D API (openapi/v1) for the berserkr v3 full regen.

Submits a concept PNG as a base64 Data URI, polls to completion, and downloads
the textured GLB/FBX plus the base-color texture. Single-shot (no preview/refine).
Auth: keyring ('comfyui-toolchain'/'meshy_api_key') or MESHY_API_KEY env var —
same convention as scripts/rig_bakeoff/meshy_rig.py.

Usage:
    python meshy_image_to_3d.py <concept.png> <out_dir> [target_polycount=150000]
"""

from __future__ import annotations

import base64
import json
import mimetypes
import os
import sys
import time
import urllib.request
from pathlib import Path

API = "https://api.meshy.ai/openapi/v1/image-to-3d"


def _key() -> str:
    key = os.environ.get("MESHY_API_KEY")
    if not key:
        try:
            import keyring
            key = keyring.get_password("comfyui-toolchain", "meshy_api_key")
        except ImportError:
            key = None
    if not key:
        raise SystemExit("ERROR: no Meshy API key (keyring or MESHY_API_KEY)")
    return key


def _req(url: str, key: str, payload: dict | None = None) -> dict:
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(
        url, data=data,
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=300) as resp:
        return json.loads(resp.read().decode())


def _download(url: str, dest: Path) -> None:
    with urllib.request.urlopen(url, timeout=600) as resp:
        dest.write_bytes(resp.read())
    print(f"DOWNLOADED {dest} ({dest.stat().st_size // 1024} KB)")


def main() -> None:
    img = Path(sys.argv[1])
    out_dir = Path(sys.argv[2])
    polycount = int(sys.argv[3]) if len(sys.argv) > 3 else 150000
    out_dir.mkdir(parents=True, exist_ok=True)
    key = _key()

    mime = mimetypes.guess_type(img.name)[0] or "image/png"
    b64 = base64.b64encode(img.read_bytes()).decode()
    print(f"Submitting {img.name} ({img.stat().st_size // 1024} KB) ...")
    start = time.monotonic()
    created = _req(API, key, {
        "image_url": f"data:{mime};base64,{b64}",
        "ai_model": "latest",
        "should_texture": True,
        "enable_pbr": False,
        "should_remesh": True,
        "topology": "triangle",
        "target_polycount": polycount,
        "pose_mode": "t-pose",
        "target_formats": ["glb", "fbx"],
    })
    task_id = created["result"]
    print("TASK", task_id)

    while True:
        time.sleep(15)
        task = _req(f"{API}/{task_id}", key)
        status = task.get("status")
        print(f"  {status} {task.get('progress', '?')}% ({time.monotonic()-start:.0f}s)")
        if status in ("SUCCEEDED", "FAILED", "CANCELED"):
            break

    (out_dir / "img2threed_result.json").write_text(json.dumps(task, indent=2))
    if status != "SUCCEEDED":
        raise SystemExit(f"ERROR: task {status}: {task.get('task_error')}")

    wall = time.monotonic() - start
    print(f"SUCCEEDED in {wall:.0f}s, credits: {task.get('consumed_credits', '?')}")
    urls = task.get("model_urls") or {}
    for fmt in ("glb", "fbx"):
        if url := urls.get(fmt):
            _download(url, out_dir / f"berserkr_v3_meshy.{fmt}")
    for i, tex in enumerate(task.get("texture_urls") or []):
        if url := tex.get("base_color"):
            _download(url, out_dir / f"berserkr_v3_meshy_basecolor_{i}.png")
    print("DONE")


if __name__ == "__main__":
    main()
