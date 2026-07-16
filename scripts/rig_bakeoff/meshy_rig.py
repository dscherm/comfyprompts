"""Drive Meshy's rigging API directly for the rig bake-off (RB4).

Submits a GLB as a base64 Data URI (no hosting needed), polls to completion,
and downloads the rigged GLB/FBX plus the basic walk/run animations Meshy
returns. Key comes from keyring ('comfyui-toolchain'/'meshy_api_key') or the
MESHY_API_KEY env var.

Usage:
    python scripts/rig_bakeoff/meshy_rig.py <model.glb> <out_dir> [height_m]
"""

from __future__ import annotations

import base64
import json
import os
import sys
import time
import urllib.request
from pathlib import Path

API = "https://api.meshy.ai/openapi/v1/rigging"


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
    model = Path(sys.argv[1])
    out_dir = Path(sys.argv[2])
    height = float(sys.argv[3]) if len(sys.argv) > 3 else 1.8
    out_dir.mkdir(parents=True, exist_ok=True)
    key = _key()

    b64 = base64.b64encode(model.read_bytes()).decode()
    print(f"Submitting {model.name} ({model.stat().st_size // 1024**2} MB) ...")
    start = time.monotonic()
    created = _req(API, key, {
        "model_url": f"data:model/gltf-binary;base64,{b64}",
        "height_meters": height,
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

    (out_dir / "task_result.json").write_text(json.dumps(task, indent=2))
    if status != "SUCCEEDED":
        raise SystemExit(f"ERROR: task {status}: {task.get('task_error')}")

    result = task["result"]
    wall = time.monotonic() - start
    print(f"SUCCEEDED in {wall:.0f}s, credits: {task.get('consumed_credits', '?')}")
    if url := result.get("rigged_character_glb_url"):
        _download(url, out_dir / "exemplar_meshy_rigged.glb")
    if url := result.get("rigged_character_fbx_url"):
        _download(url, out_dir / "exemplar_meshy_rigged.fbx")
    for name, anim in (result.get("basic_animations") or {}).items():
        if isinstance(anim, str) and anim.startswith("http") and "glb" in anim:
            _download(anim, out_dir / f"anim_{name}.glb")
        elif isinstance(anim, dict):
            for fmt, u in anim.items():
                if isinstance(u, str) and u.startswith("http") and "glb" in fmt:
                    _download(u, out_dir / f"anim_{name}.glb")
    print("DONE")


if __name__ == "__main__":
    main()
