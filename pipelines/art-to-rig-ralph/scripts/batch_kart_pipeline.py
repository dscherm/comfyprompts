"""Batch process all 10 karts: split → assemble → export.

Runs mesh_split.py and kart_assembler.py sequentially for each kart.
Uses subprocess to call Blender headless for each step (each step needs a clean scene).

Usage:
    python batch_kart_pipeline.py
"""

import subprocess
import sys
import os
import json
import time
from pathlib import Path

BLENDER = r"C:\Program Files\Blender Foundation\Blender 5.0\blender.exe"
SCRIPTS_DIR = Path(__file__).parent
PREPARED_DIR = SCRIPTS_DIR.parent / "output" / "prepared"
SPLIT_DIR = SCRIPTS_DIR.parent / "output" / "split"
FINAL_DIR = SCRIPTS_DIR.parent / "output" / "final"

KARTS = [
    "bones_kart",
    "crank_kart",
    "grit_kart",
    "pip_kart",
    "player_kart",
    "punk_king_kart",
    "rust_kart",
    "smog_kart",
    "soup_box_kart",
    "sparks_kart",
]


def run_blender(script: str, args: list[str], label: str) -> bool:
    """Run a Blender headless script. Returns True on success."""
    cmd = [BLENDER, "--background", "--python", script, "--"] + args
    print(f"  [{label}] Running...", flush=True)
    start = time.time()
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    elapsed = time.time() - start

    if result.returncode != 0:
        print(f"  [{label}] FAILED ({elapsed:.1f}s)")
        # Print last 10 lines of stderr/stdout for debugging
        output = (result.stdout + result.stderr).strip().split("\n")
        for line in output[-10:]:
            print(f"    {line}")
        return False

    print(f"  [{label}] OK ({elapsed:.1f}s)")
    return True


def process_kart(kart_id: str) -> dict:
    """Process a single kart through split → assemble → export."""
    prepared = PREPARED_DIR / f"{kart_id}_v1_prepared.glb"
    if not prepared.exists():
        return {"kart_id": kart_id, "success": False, "error": f"Not found: {prepared}"}

    # Output paths
    split_glb = SPLIT_DIR / f"{kart_id}_split.glb"
    split_report = SPLIT_DIR / f"{kart_id}_split_report.json"
    final_dir = FINAL_DIR / kart_id
    unity_fbx = final_dir / f"{kart_id}_unity.fbx"
    blender_glb = final_dir / f"{kart_id}_blender.glb"
    assembly_report = final_dir / f"{kart_id}_assembly_report.json"

    # Create output dirs
    SPLIT_DIR.mkdir(parents=True, exist_ok=True)
    final_dir.mkdir(parents=True, exist_ok=True)

    # Step 1: Split
    ok = run_blender(
        str(SCRIPTS_DIR / "mesh_split.py"),
        ["--input", str(prepared), "--output", str(split_glb), "--report", str(split_report)],
        f"{kart_id}/split",
    )
    if not ok:
        return {"kart_id": kart_id, "success": False, "error": "mesh_split failed", "stage": "split"}

    # Step 2: Assemble + Export
    ok = run_blender(
        str(SCRIPTS_DIR / "kart_assembler.py"),
        [
            "--input", str(split_glb),
            "--output-fbx", str(unity_fbx),
            "--output-glb", str(blender_glb),
            "--report", str(assembly_report),
        ],
        f"{kart_id}/assemble",
    )
    if not ok:
        return {"kart_id": kart_id, "success": False, "error": "kart_assembler failed", "stage": "assemble"}

    # Read assembly report for summary
    report_data = {}
    if assembly_report.exists():
        with open(assembly_report) as f:
            report_data = json.load(f)

    return {
        "kart_id": kart_id,
        "success": True,
        "outputs": {
            "split_glb": str(split_glb),
            "unity_fbx": str(unity_fbx),
            "blender_glb": str(blender_glb),
            "assembly_report": str(assembly_report),
        },
        "mesh_count": report_data.get("mesh_count", 0),
        "empty_count": report_data.get("empty_count", 0),
        "total_faces": report_data.get("total_faces", 0),
    }


def main():
    print(f"=== Batch Kart Pipeline: {len(KARTS)} karts ===\n")
    start_all = time.time()

    results = []
    for i, kart_id in enumerate(KARTS, 1):
        print(f"[{i}/{len(KARTS)}] {kart_id}")
        result = process_kart(kart_id)
        results.append(result)
        status = "OK" if result["success"] else f"FAILED: {result.get('error', '?')}"
        print(f"  → {status}\n")

    elapsed_all = time.time() - start_all

    # Summary
    succeeded = [r for r in results if r["success"]]
    failed = [r for r in results if not r["success"]]

    print(f"=== BATCH COMPLETE: {len(succeeded)}/{len(KARTS)} succeeded in {elapsed_all:.1f}s ===")
    if failed:
        print(f"FAILED: {[r['kart_id'] for r in failed]}")

    for r in succeeded:
        print(f"  {r['kart_id']}: {r['mesh_count']} meshes, {r['empty_count']} empties, {r['total_faces']} faces")

    # Write manifest
    manifest_path = FINAL_DIR / "BATCH-MANIFEST.json"
    manifest = {
        "total_karts": len(KARTS),
        "succeeded": len(succeeded),
        "failed": len(failed),
        "elapsed_seconds": round(elapsed_all, 1),
        "results": results,
    }
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)
    print(f"\nManifest: {manifest_path}")


if __name__ == "__main__":
    main()
