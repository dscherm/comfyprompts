"""Apply Meshy library animations to an already-rigged character.

POST /openapi/v1/animations with a rig_task_id + action_id (0=Idle, 4=Attack,
...), poll, download the resulting GLB (rigged mesh + that one clip). Same auth
convention as meshy_rig.py.

Usage:
  python meshy_animate.py <rig_task_id> <out_dir> <action_id>[:name] [more...]
  e.g. python meshy_animate.py 019f70f9-... rig_v3/meshy_anims 0:idle 4:attack
"""

from __future__ import annotations

import json
import os
import sys
import time
import urllib.request
from pathlib import Path

API = "https://api.meshy.ai/openapi/v1/animations"


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


def run_one(rig_task_id: str, out_dir: Path, action_id: int, name: str, key: str) -> None:
    print(f"Applying action {action_id} ({name}) to {rig_task_id} ...")
    start = time.monotonic()
    created = _req(API, key, {
        "rig_task_id": rig_task_id,
        "action_id": action_id,
        "post_process": {"target_formats": ["glb"]},
    })
    task_id = created["result"]
    print("  TASK", task_id)
    while True:
        time.sleep(10)
        task = _req(f"{API}/{task_id}", key)
        status = task.get("status")
        print(f"  {status} {task.get('progress', '?')}% ({time.monotonic()-start:.0f}s)")
        if status in ("SUCCEEDED", "FAILED", "CANCELED"):
            break
    (out_dir / f"anim_{name}_result.json").write_text(json.dumps(task, indent=2))
    if status != "SUCCEEDED":
        raise SystemExit(f"ERROR: action {name} {status}: {task.get('task_error')}")
    res = task.get("result") or {}
    urls = res.get("model_urls") or res
    url = urls.get("glb") if isinstance(urls, dict) else None
    if not url:
        # some payloads nest under 'animation_glb_url' or similar
        for k, v in (res.items() if isinstance(res, dict) else []):
            if isinstance(v, str) and v.startswith("http") and "glb" in v:
                url = v
                break
    if not url:
        raise SystemExit(f"ERROR: no glb url in result: {json.dumps(res)[:400]}")
    _download(url, out_dir / f"anim_{name}.glb")
    print(f"  credits: {task.get('consumed_credits', '?')}")


def main() -> None:
    rig_task_id = sys.argv[1]
    out_dir = Path(sys.argv[2])
    out_dir.mkdir(parents=True, exist_ok=True)
    key = _key()
    for spec in sys.argv[3:]:
        aid, _, nm = spec.partition(":")
        run_one(rig_task_id, out_dir, int(aid), nm or aid, key)
    print("DONE")


if __name__ == "__main__":
    main()
