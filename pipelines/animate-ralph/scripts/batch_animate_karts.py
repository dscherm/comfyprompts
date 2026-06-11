"""Batch animate all 10 karts with MK-reference animation clips.

Usage:
    python batch_animate_karts.py
"""

import subprocess
import sys
import os
import json
import time
from pathlib import Path

BLENDER = r"C:\Program Files\Blender Foundation\Blender 5.0\blender.exe"
SCRIPTS_DIR = Path(__file__).parent
KART_FINAL_DIR = Path(__file__).parent.parent.parent / "art-to-rig-ralph" / "output" / "final"
ANIM_OUTPUT_DIR = SCRIPTS_DIR.parent / "output" / "export"

ALL_CLIPS = "idle,engine_vibrate,steer_left,steer_right,boost,drift_hop,hit_left,hit_right,banana_spin,shell_tumble"

KARTS = [
    "bones_kart", "crank_kart", "grit_kart", "pip_kart", "player_kart",
    "punk_king_kart", "rust_kart", "smog_kart", "soup_box_kart", "sparks_kart",
]


def animate_kart(kart_id: str) -> dict:
    input_glb = KART_FINAL_DIR / kart_id / f"{kart_id}_blender.glb"
    output_dir = ANIM_OUTPUT_DIR / kart_id

    if not input_glb.exists():
        return {"kart_id": kart_id, "success": False, "error": f"Not found: {input_glb}"}

    output_dir.mkdir(parents=True, exist_ok=True)

    cmd = [
        BLENDER, "--background", "--python", str(SCRIPTS_DIR / "animate_kart.py"), "--",
        "--input", str(input_glb),
        "--output-dir", str(output_dir),
        "--kart-id", kart_id,
        "--clips", ALL_CLIPS,
    ]

    start = time.time()
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    elapsed = time.time() - start

    if result.returncode != 0:
        output = (result.stdout + result.stderr).strip().split("\n")
        return {
            "kart_id": kart_id, "success": False,
            "error": "\n".join(output[-5:]), "elapsed": round(elapsed, 1),
        }

    # Read report
    report_path = output_dir / f"{kart_id}_animation_report.json"
    report = {}
    if report_path.exists():
        with open(report_path) as f:
            report = json.load(f)

    return {
        "kart_id": kart_id, "success": True,
        "clips": report.get("total_clips", 0),
        "elapsed": round(elapsed, 1),
    }


def main():
    print(f"=== Batch Kart Animation: {len(KARTS)} karts, {len(ALL_CLIPS.split(','))} clips each ===\n")
    start_all = time.time()

    results = []
    for i, kart_id in enumerate(KARTS, 1):
        print(f"[{i}/{len(KARTS)}] {kart_id}...", end=" ", flush=True)
        r = animate_kart(kart_id)
        results.append(r)
        if r["success"]:
            print(f"OK ({r['clips']} clips, {r['elapsed']}s)")
        else:
            print(f"FAILED: {r.get('error', '?')[:80]}")

    elapsed_all = time.time() - start_all
    succeeded = [r for r in results if r["success"]]
    failed = [r for r in results if not r["success"]]

    print(f"\n=== BATCH COMPLETE: {len(succeeded)}/{len(KARTS)} in {elapsed_all:.1f}s ===")
    if failed:
        for r in failed:
            print(f"  FAILED: {r['kart_id']}: {r.get('error', '?')[:100]}")

    manifest = {
        "total_karts": len(KARTS),
        "clips_per_kart": len(ALL_CLIPS.split(",")),
        "succeeded": len(succeeded),
        "failed": len(failed),
        "elapsed_seconds": round(elapsed_all, 1),
        "results": results,
    }
    manifest_path = ANIM_OUTPUT_DIR / "ANIMATION-MANIFEST.json"
    ANIM_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)
    print(f"Manifest: {manifest_path}")


if __name__ == "__main__":
    main()
