"""Re-texture an existing Meshy model (Text-to-Texture), preserving mesh + UV.

Retextures the mesh from a prior image-to-3d task (input_task_id) with a style
prompt, keeping the original UVs so the new base-colour can be swapped straight
onto the already-rigged/animated GLB. Same auth as the other meshy_*.py drivers.

Usage:
  python meshy_retexture.py <input_task_id> <out_dir> "<style prompt>"
"""

from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

API = "https://api.meshy.ai/openapi/v1/retexture"


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
    try:
        with urllib.request.urlopen(req, timeout=300) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors="replace")
        raise SystemExit(f"HTTP {e.code} from {url}\nrequest={json.dumps(payload)}\nresponse={body}")


def _download(url: str, dest: Path) -> None:
    with urllib.request.urlopen(url, timeout=600) as resp:
        dest.write_bytes(resp.read())
    print(f"DOWNLOADED {dest} ({dest.stat().st_size // 1024} KB)")


def main() -> None:
    input_task_id = sys.argv[1]
    out_dir = Path(sys.argv[2])
    prompt = sys.argv[3]
    out_dir.mkdir(parents=True, exist_ok=True)
    key = _key()

    print(f"Retexturing task {input_task_id} ...")
    start = time.monotonic()
    created = _req(API, key, {
        "input_task_id": input_task_id,
        "text_style_prompt": prompt,
        "enable_original_uv": True,
        "enable_pbr": False,
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

    (out_dir / "retexture_result.json").write_text(json.dumps(task, indent=2))
    if status != "SUCCEEDED":
        raise SystemExit(f"ERROR: task {status}: {task.get('task_error')}")
    print(f"SUCCEEDED in {time.monotonic()-start:.0f}s, credits: {task.get('consumed_credits', '?')}")

    urls = task.get("model_urls") or {}
    if url := urls.get("glb"):
        _download(url, out_dir / "berserkr_retex.glb")
    for i, tex in enumerate(task.get("texture_urls") or []):
        if url := tex.get("base_color"):
            _download(url, out_dir / f"berserkr_retex_basecolor_{i}.png")
    print("DONE")


if __name__ == "__main__":
    main()
