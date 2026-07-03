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
import math
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
DIAG_HIP_PY = HERE / "diag_hip_travel.py"
MESH_GATE_PY = HERE / "validate_animation_mesh.py"

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
             src_z: float | str, root: str) -> tuple[str, int, tuple[float, float, float]]:
    out = blender(RETARGET_PY, [rig, src_fbx, str(MAP), out_glb,
                                str(f0), str(f1), str(src_z), root])
    m = re.search(r"MATCHED (\d+)/\d+", out)
    if "RETARGET_DONE" not in out:
        raise SystemExit("retarget did not finish:\n" + out[-800:])
    e = re.search(r"EXPECTED_TRAVEL\s+(-?[\d.]+)\s+(-?[\d.]+)\s+(-?[\d.]+)", out)
    expected = (float(e.group(1)), float(e.group(2)), float(e.group(3))) if e else (0.0, 0.0, 0.0)
    return out_glb.rsplit(".", 1)[0] + ".fbx", (int(m.group(1)) if m else 0), expected


def fidelity(fbx: str, expected: tuple[float, float, float]) -> tuple[float, float, str]:
    """Transfer fidelity: exported hip travel vs the transfer's own expectation.

    Returns (dir_err_deg, mag_ratio, verdict). For in-place clips (expected ~0)
    the check is simply that the export doesn't drift. Replaces the old
    diag_facing 'misalign', which was noise for in-place clips.
    """
    out = blender(DIAG_HIP_PY, [fbx])
    a = re.search(r"ACTUAL_TRAVEL\s+(-?[\d.]+)\s+(-?[\d.]+)\s+(-?[\d.]+)", out)
    if not a:
        return float("nan"), float("nan"), "NO_MEASURE"
    ax, ay, _ = (float(a.group(i)) for i in (1, 2, 3))
    ex, ey, _ = expected
    e_len = math.hypot(ex, ey)
    a_len = math.hypot(ax, ay)
    if e_len < 0.05:                      # in-place clip
        return 0.0, 1.0, ("OK_INPLACE" if a_len < 0.1 else f"DRIFT({a_len:.2f})")
    err = math.degrees(math.atan2(ay, ax) - math.atan2(ey, ex))
    err = (err + 180.0) % 360.0 - 180.0
    ratio = a_len / e_len
    ok = abs(err) <= 15.0 and 0.7 <= ratio <= 1.4
    return err, ratio, ("OK" if ok else "MISMATCH")


def mesh_gate(fbx: str) -> tuple[str, float]:
    """Mesh-integrity under motion (validate_animation_mesh.py): catches weight
    melting and scramble that travel/bone metrics miss. Calibrated 2026-07-03:
    AccuRIG walk p99=1.80 (OK) vs UniRig walk 2.76 / crossed-skin 18.6 (MELT)."""
    out = blender(MESH_GATE_PY, [fbx])
    m = re.search(r"MESH_VERDICT\s+(\w+)\s+p99_worst=([\d.]+)", out)
    return (m.group(1), float(m.group(2))) if m else ("NO_MEASURE", float("nan"))


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

        # facing: travelling clips align the CLIP'S TRAVEL to the target's forward
        # (straight game-forward locomotion); in-place clips align bind facings.
        src_z = "auto_travel" if root == "transfer" else "auto"

        out_fbx, matched, expected = retarget(args.rig, src_fbx, out_glb, f0, f1, src_z, root)
        err, ratio, verdict = fidelity(out_fbx, expected)
        mesh_v, p99 = mesh_gate(out_fbx)
        proof(out_fbx, clip, length)
        ok = matched >= 18 and verdict.startswith("OK") and mesh_v == "OK"
        log(f"{clip}: {matched}/20 bones, frames {f0}-{f1} ({length}), root={root}, "
            f"src_z={src_z}, fidelity={verdict} (dir_err={err:.1f} deg, mag={ratio:.2f}), "
            f"mesh={mesh_v} (p99={p99:.2f})")
        results.append({**r, "ok": ok, "matched": matched,
                        "frames": length, "win": f"{f0}-{f1}", "src_z": src_z,
                        "err": err, "ratio": ratio, "verdict": verdict,
                        "mesh": mesh_v, "p99": p99})

    # clean probes
    for p in OUTDIR.glob("_probe_*"):
        p.unlink()

    # report
    lines = ["# GS1 — barbarian batch-retarget report", "",
             "| clip | bones | window (src f) | frames | root motion | src_z | fidelity | dir err | mag | mesh | p99 | ok |",
             "|------|:-----:|:--------------:|:------:|-------------|:-----:|:--------:|:-------:|:---:|:----:|:---:|:--:|"]
    for r in results:
        if "matched" in r:
            lines.append(f"| {r['clip']} | {r['matched']}/20 | {r['win']} | {r['frames']} | "
                         f"{r['root']} | {r['src_z']} | {r['verdict']} | {r['err']:.1f} | "
                         f"{r['ratio']:.2f} | {r['mesh']} | {r['p99']:.2f} | "
                         f"{'YES' if r['ok'] else 'NO'} |")
        else:
            lines.append(f"| {r['clip']} | — | — | — | {r['root']} | — | — | NO ({r.get('note','')}) |")
    lines += ["", f"Output FBX: `output/export/barbarian/<clip>.fbx`  ·  "
              f"Proof frames: `validation/retarget/gs1_barbarian/`", "",
              "GATE (all three required): bones >= 18; `fidelity` (exported hip",
              "travel vs the transfer's EXPECTED_TRAVEL: dir err <= 15 deg, mag",
              "0.7-1.4; in-place clips must not drift); `mesh` (integrity under",
              "motion: p99 edge stretch <= 2.0 and bounds within [0.5, 1.8] of",
              "rest — catches weight melting/scramble; calibrated: AccuRIG walk",
              "1.80 OK vs UniRig walk 2.76 MELT vs crossed-skin 18.6 MELT).",
              "Proof frames remain a REQUIRED human check for pose naturalness",
              "(limb plane) — no numeric gate covers it.", ""]
    REPORT.write_text("\n".join(lines), encoding="utf-8")
    log(f"report -> {REPORT}")
    log("DONE " + "  ".join(f"{r['clip']}={r.get('matched','x')}" for r in results))


if __name__ == "__main__":
    main()
