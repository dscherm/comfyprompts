#!/usr/bin/env python3
"""generate_motion.py — text prompt + rig -> animated FBX (MDM previz path).

One-command orchestrator for the text-to-motion chain proven in Phase MT:

    [MDM generate (GPU)]  ->  mdm_to_source  ->  retarget_mocap  ->  animated FBX
    prompt -> results.npy     22-joint xyz       Character1_* bones    faces its travel
                              -> mdm_clip.fbx     onto the renamed rig  (root motion)

=== LICENSE / POSTURE — PREVIZ ONLY ===
MDM and its AMASS / HumanML3D training weights are **research / non-commercial**.
Anything produced here is **previsualization, not shippable game content**. Use it to
block out motion and validate the pipeline; do not ship the resulting clips.

=== GPU GATE ===
The generation step runs MDM on the 3090 Ti and needs ComfyUI **idle** (its 24GB free).
It is OFF by default. To run it pass `--generate`; the orchestrator refuses while ComfyUI
is listening on :8188 (pass `--force-gpu` to override once you've stopped it). Restart
ComfyUI afterwards with `run_3090ti.ps1`. Without `--generate`, supply an existing
`--results results.npy` and the chain runs **CPU/Blender only** (source -> retarget).

Examples:
    # CPU-only: reuse an existing MDM results.npy, retarget onto the barbarian
    python generate_motion.py --results .../results.npy \
        --rig E:/ai-training/_animtest/barbarian_renamed.glb --out out/walkwave.fbx

    # Full chain incl. GPU generation (ComfyUI must be stopped first)
    python generate_motion.py --generate --prompt "a person walks forward and waves" \
        --rig E:/ai-training/_animtest/barbarian_renamed.glb --out out/walkwave.fbx
"""
from __future__ import annotations

import argparse
import glob
import os
import re
import socket
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]  # .../comfyui-toolchain

SOURCE_PY = HERE / "mdm_to_source.py"
RETARGET_PY = HERE / "retarget_mocap.py"
DIAG_PY = HERE / "diag_facing.py"
DEFAULT_MAP = HERE.parent / "references" / "retarget_maps" / "mixamo_to_unirig.json"

# Machine-specific defaults (this previz spike lives on E:); all overridable via env/CLI.
BLENDER = os.environ.get("BLENDER_EXE", r"C:\Program Files\Blender Foundation\Blender 5.0\blender.exe")
MDM_DIR = os.environ.get("MDM_DIR", r"E:\ai-training\_motiongen\motion-diffusion-model")
MDM_PY = os.environ.get("MDM_PYTHON", r"E:\ai-training\_motiongen\venv\Scripts\python.exe")
MDM_MODEL = os.environ.get("MDM_MODEL", "save/humanml_enc_512_50steps/model000750000.pt")
MDM_TMP = os.environ.get("MDM_TMP", r"E:\ai-training\_motiongen\tmp")

# facing(src_z) response measured in Phase MT: misalign(src_z) ~= misalign0 + K*src_z,
# K ~= +1.08 deg/deg (src_z rotates facing; travel is invariant). Used by --auto-face.
FACE_SLOPE = 1.08
DEFAULT_SRC_Z = -36.0  # calibrated for the barbarian + "walk forward and waves" clip


def log(msg: str) -> None:
    print(f"[generate_motion] {msg}", flush=True)


def port_listening(port: int, host: str = "127.0.0.1") -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.5)
        return s.connect_ex((host, port)) == 0


def run(cmd: list[str], cwd: str | None = None, env: dict | None = None) -> str:
    """Run a subprocess, echo + capture stdout, raise on non-zero with stderr tail."""
    log("$ " + " ".join(str(c) for c in cmd))
    proc = subprocess.run(cmd, cwd=cwd, env=env, capture_output=True, text=True)
    if proc.returncode != 0:
        sys.stderr.write(proc.stdout[-2000:])
        sys.stderr.write("\n--- stderr ---\n")
        sys.stderr.write(proc.stderr[-2000:])
        raise SystemExit(f"step failed (exit {proc.returncode}): {cmd[0]}")
    return proc.stdout


def blender(script: Path, args: list[str]) -> str:
    return run([BLENDER, "--background", "--python", str(script), "--", *args])


# ----------------------------------------------------------------------------- stages
def generate_mdm(prompt: str, force_gpu: bool) -> str:
    """Run MDM on the GPU; return the produced results.npy path."""
    if port_listening(8188) and not force_gpu:
        raise SystemExit(
            "GPU GATE: ComfyUI is listening on :8188 — the 3090 Ti is occupied.\n"
            "Stop ComfyUI to free its 24GB, then re-run with --generate "
            "(or pass --force-gpu to override). Restart it afterwards via run_3090ti.ps1."
        )
    env = dict(os.environ)
    env.update(CUDA_VISIBLE_DEVICES="1", TMP=MDM_TMP, TEMP=MDM_TMP)
    log(f"MDM generate (GPU 1): {prompt!r}")
    run([MDM_PY, "-m", "sample.generate", "--model_path", MDM_MODEL,
         "--text_prompt", prompt, "--num_repetitions", "1"], cwd=MDM_DIR, env=env)
    # sample.generate writes save/<model_dir>/samples_*<slug>/results.npy
    model_dir = str(Path(MDM_DIR) / Path(MDM_MODEL).parent)
    hits = glob.glob(os.path.join(model_dir, "samples_*", "results.npy"))
    if not hits:
        raise SystemExit("MDM finished but no results.npy was found under " + model_dir)
    npy = max(hits, key=os.path.getmtime)
    log(f"MDM -> {npy}")
    return npy


def to_source(npy: str, sample_idx: int, out_fbx: str) -> int:
    """Build the Character1_* animated source FBX; return frame count."""
    out = blender(SOURCE_PY, [npy, out_fbx, str(sample_idx)])
    m = re.search(r"MDM_SOURCE_DONE frames=(\d+)", out)
    if not m:
        raise SystemExit("mdm_to_source.py did not report MDM_SOURCE_DONE:\n" + out[-1000:])
    return int(m.group(1))


def retarget(rig: str, mocap_fbx: str, out_glb: str, f0: int, f1: int,
             src_z: float, root_motion: str, mapping: str) -> tuple[str, int]:
    """Retarget the source clip onto the rig; return (out_fbx, matched_bones)."""
    out = blender(RETARGET_PY, [rig, mocap_fbx, mapping, out_glb,
                                str(f0), str(f1), str(src_z), root_motion])
    matched = 0
    m = re.search(r"MATCHED (\d+)/\d+", out)
    if m:
        matched = int(m.group(1))
    if "RETARGET_DONE" not in out:
        raise SystemExit("retarget_mocap.py did not report RETARGET_DONE:\n" + out[-1000:])
    return out_glb.rsplit(".", 1)[0] + ".fbx", matched


def measure_facing(fbx: str) -> tuple[float, float, float]:
    """Return (facing_deg, travel_deg, misalign_deg) for a retargeted FBX."""
    out = blender(DIAG_PY, [fbx])
    def grab(tag):
        m = re.search(tag + r"\s+(-?\d+\.?\d*)", out)
        return float(m.group(1)) if m else float("nan")
    return grab("FACING_DEG"), grab("TRAVEL_DEG"), grab("MISALIGN_DEG")


# ------------------------------------------------------------------------------- main
def main() -> None:
    ap = argparse.ArgumentParser(
        description="text prompt + rig -> animated FBX (MDM previz path)",
        formatter_class=argparse.RawDescriptionHelpFormatter, epilog=__doc__)
    ap.add_argument("--prompt", help="text prompt (required with --generate)")
    ap.add_argument("--rig", required=True, help="renamed UniRig rig (.glb) — retarget target")
    ap.add_argument("--out", required=True, help="final animated FBX path")
    ap.add_argument("--results", help="existing MDM results.npy (skips generation)")
    ap.add_argument("--generate", action="store_true",
                    help="run MDM generation on the GPU (ComfyUI must be idle)")
    ap.add_argument("--force-gpu", action="store_true",
                    help="generate even if ComfyUI is listening on :8188")
    ap.add_argument("--sample-idx", type=int, default=0, help="MDM sample index (default 0)")
    ap.add_argument("--src-z", type=float, default=DEFAULT_SRC_Z,
                    help=f"facing offset deg for retarget (default {DEFAULT_SRC_Z})")
    ap.add_argument("--auto-face", action="store_true",
                    help="measure facing and auto-solve src_z so the body faces its travel")
    ap.add_argument("--root-motion", default="transfer",
                    help="transfer (default) | off | <float speed/frame>")
    ap.add_argument("--map", default=str(DEFAULT_MAP), help="retarget bone map json")
    ap.add_argument("--workdir", help="scratch dir for intermediates (default: out's dir)")
    args = ap.parse_args()

    out = Path(args.out).resolve()
    workdir = Path(args.workdir).resolve() if args.workdir else out.parent
    workdir.mkdir(parents=True, exist_ok=True)
    mdm_clip = str(workdir / "mdm_clip.fbx")

    # 1) obtain results.npy (generate on GPU, or reuse)
    if args.generate:
        if not args.prompt:
            raise SystemExit("--generate requires --prompt")
        npy = generate_mdm(args.prompt, args.force_gpu)
    elif args.results:
        npy = args.results
        if not os.path.isfile(npy):
            raise SystemExit(f"--results not found: {npy}")
        log(f"reusing results.npy: {npy}")
    else:
        raise SystemExit("provide --generate (GPU) or --results <existing results.npy>")

    # 2) source FBX
    frames = to_source(npy, args.sample_idx, mdm_clip)
    f0, f1 = 0, frames - 1
    log(f"source clip: {frames} frames")

    # 3) retarget (optionally auto-calibrate facing)
    src_z = args.src_z
    if args.auto_face:
        out_glb = str(workdir / "_probe.glb")
        probe_fbx, _ = retarget(args.rig, mdm_clip, out_glb, f0, f1, 0.0,
                                args.root_motion, args.map)
        _, _, mis0 = measure_facing(probe_fbx)
        src_z = round(-mis0 / FACE_SLOPE, 1)
        log(f"auto-face: misalign@0={mis0:.1f} deg -> src_z={src_z}")

    out_glb = str(out.with_suffix(".glb"))
    out_fbx, matched = retarget(args.rig, mdm_clip, out_glb, f0, f1, src_z,
                                args.root_motion, args.map)

    # 4) report
    facing, travel, misalign = measure_facing(out_fbx)
    log("=" * 60)
    log(f"DONE -> {out_fbx}")
    log(f"  bones matched : {matched}/20")
    log(f"  src_z         : {src_z} deg")
    log(f"  facing/travel : {facing:.1f} / {travel:.1f} deg  (misalign {misalign:.1f})")
    log(f"  root motion   : {args.root_motion}")
    log("  NOTE: research-license weights -> PREVIZ ONLY, not shippable.")


if __name__ == "__main__":
    main()
