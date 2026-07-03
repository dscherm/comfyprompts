#!/usr/bin/env python3
"""batch_retarget.py — retarget the GS0 commercial clip set onto the barbarian.

Reads the GS0 manifest (output/intake/barbarian_clipset.md) for the authoritative
clip -> source -> root_motion -> loop mapping, applies a representative frame sub-range
per clip (the sources are 250-frame ROM takes), runs retarget_mocap.py for each, writes
output/export/barbarian/<clip>.fbx, and renders per-clip proof frames via
render_rootmotion.py. Travelling clips (walk, dodge) get a facing auto-calibration
(probe src_z=0 -> diag_facing -> solve); in-place clips use src_z=0.

CPU/Blender only — no GPU, no MDM. Library clips are already Character1_*, so they feed
retarget_mocap.py directly (no mdm_to_source step).

Usage:
    python batch_retarget.py [--rig <renamed_rig.glb>] [--only clip1,clip2]
"""
from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PIPE = HERE.parent                      # .../animate-ralph
REPO = HERE.parents[2]                  # .../comfyui-toolchain
REF = PIPE / "references" / "humanoid"
MANIFEST = PIPE / "output" / "intake" / "barbarian_clipset.md"
MAP = PIPE / "references" / "retarget_maps" / "mixamo_to_unirig.json"
OUTDIR = PIPE / "output" / "export" / "barbarian"
PROOFDIR = PIPE / "validation" / "retarget" / "gs1_barbarian"
REPORT = PIPE / "validation" / "gs1_retarget_report.md"

RETARGET_PY = HERE / "retarget_mocap.py"
RENDER_PY = HERE / "render_rootmotion.py"
DIAG_PY = HERE / "diag_facing.py"

BLENDER = os.environ.get("BLENDER_EXE", r"C:\Program Files\Blender Foundation\Blender 5.0\blender.exe")
DEFAULT_RIG = os.environ.get("BARBARIAN_RIG", r"E:\ai-training\_animtest\barbarian_renamed.glb")

# facing is now solved inside retarget_mocap.py (src_z="auto", bind-pose derived,
# label-safe) — the old probe/measure/FACE_SLOPE solve for TRAVEL_CLIPS is gone.

# Representative frame sub-ranges (0-indexed into the 250-frame source takes). Loops get a
# multi-cycle window; one-shots a window around the action. Loop-seam fine-tuning is a GS3
# / polish concern (Unity loop import), not required for the GS1 motion proof.
SUBRANGE = {
    "idle":      (30, 170),
    "walk":      (12, 132),
    "run":       (12, 132),
    "attack":    (20, 150),
    "hit":       (20, 150),
    "dodge":     (8, 110),
    "block":     (20, 170),
    "wave":      (20, 170),
    "celebrate": (20, 170),
}


def log(m: str) -> None:
    print(f"[batch_retarget] {m}", flush=True)


def run(cmd: list[str]) -> str:
    proc = subprocess.run([str(c) for c in cmd], capture_output=True, text=True)
    if proc.returncode != 0:
        sys.stderr.write(proc.stdout[-2000:] + "\n--- stderr ---\n" + proc.stderr[-1500:])
        raise SystemExit(f"step failed (exit {proc.returncode}): {Path(str(cmd[0])).name}")
    return proc.stdout


def blender(script: Path, args: list[str]) -> str:
    return run([BLENDER, "--background", "--python", str(script), "--", *args])


def parse_manifest() -> list[dict]:
    """Pull clip rows out of the GS0 markdown table."""
    clips = []
    for line in MANIFEST.read_text(encoding="utf-8").splitlines():
        if not line.startswith("| `"):
            continue
        cols = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cols) < 7 or ".fbx" not in cols[1]:
            continue
        clip = cols[0].strip("` ")
        src = cols[1].strip("` ")
        root = "transfer" if "transfer" in cols[5].lower() else "off"
        loop = "loop" in cols[6].lower()
        clips.append({"clip": clip, "src": src, "root": root, "loop": loop})
    return clips


def retarget(rig: str, src_fbx: str, out_glb: str, f0: int, f1: int,
             src_z: float | str, root: str) -> tuple[str, int]:
    out = blender(RETARGET_PY, [rig, src_fbx, str(MAP), out_glb,
                                str(f0), str(f1), str(src_z), root])
    m = re.search(r"MATCHED (\d+)/\d+", out)
    if "RETARGET_DONE" not in out:
        raise SystemExit("retarget did not finish:\n" + out[-800:])
    return out_glb.rsplit(".", 1)[0] + ".fbx", (int(m.group(1)) if m else 0)


def measure(fbx: str) -> float:
    out = blender(DIAG_PY, [fbx])
    m = re.search(r"MISALIGN_DEG\s+(-?\d+\.?\d*)", out)
    return float(m.group(1)) if m else float("nan")


def proof(fbx: str, clip: str, length: int) -> None:
    # 4 frames spread across the retargeted clip (0 .. length-1)
    fs = sorted({0, length // 3, (2 * length) // 3, length - 1})
    frames = ",".join(str(f) for f in fs)
    blender(RENDER_PY, [fbx, str(PROOFDIR), frames, "ortho34"])


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--rig", default=DEFAULT_RIG)
    ap.add_argument("--only", help="comma-separated subset of clip names")
    args = ap.parse_args()

    OUTDIR.mkdir(parents=True, exist_ok=True)
    PROOFDIR.mkdir(parents=True, exist_ok=True)
    only = set(args.only.split(",")) if args.only else None

    rows = parse_manifest()
    if only:
        rows = [r for r in rows if r["clip"] in only]
    log(f"{len(rows)} clips from manifest: {', '.join(r['clip'] for r in rows)}")

    results = []
    for r in rows:
        clip, root = r["clip"], r["root"]
        src_fbx = str(REF / r["src"])
        if not os.path.isfile(src_fbx):
            log(f"!! {clip}: source missing {src_fbx} — skipping")
            results.append({**r, "ok": False, "note": "source missing"})
            continue
        f0, f1 = SUBRANGE.get(clip, (0, 249))
        length = f1 - f0 + 1
        out_glb = str(OUTDIR / f"{clip}.glb")

        # facing: retarget_mocap.py derives the yaw from the bind poses ("auto")
        src_z = "auto"

        out_fbx, matched = retarget(args.rig, src_fbx, out_glb, f0, f1, src_z, root)
        mis = measure(out_fbx)
        proof(out_fbx, clip, length)
        log(f"{clip}: {matched}/20 bones, frames {f0}-{f1} ({length}), root={root}, "
            f"src_z={src_z}, misalign={mis:.1f}")
        results.append({**r, "ok": matched >= 18, "matched": matched,
                        "frames": length, "win": f"{f0}-{f1}", "src_z": src_z, "misalign": mis})

    # clean probes
    for p in OUTDIR.glob("_probe_*"):
        p.unlink()

    # report
    lines = ["# GS1 — barbarian batch-retarget report", "",
             "| clip | bones | window (src f) | frames | root motion | src_z | misalign | ok |",
             "|------|:-----:|:--------------:|:------:|-------------|:-----:|:--------:|:--:|"]
    for r in results:
        if "matched" in r:
            lines.append(f"| {r['clip']} | {r['matched']}/20 | {r['win']} | {r['frames']} | "
                         f"{r['root']} | {r['src_z']} | {r['misalign']:.1f} | "
                         f"{'YES' if r['ok'] else 'NO'} |")
        else:
            lines.append(f"| {r['clip']} | — | — | — | {r['root']} | — | — | NO ({r.get('note','')}) |")
    lines += ["", f"Output FBX: `output/export/barbarian/<clip>.fbx`  ·  "
              f"Proof frames: `validation/retarget/gs1_barbarian/`", ""]
    REPORT.write_text("\n".join(lines), encoding="utf-8")
    log(f"report -> {REPORT}")
    log("DONE " + "  ".join(f"{r['clip']}={r.get('matched','x')}" for r in results))


if __name__ == "__main__":
    main()
