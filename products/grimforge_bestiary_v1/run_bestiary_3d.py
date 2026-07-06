"""Bestiary 3D driver — takes each concept PNG through the proven low-poly 3D
stages and lands a textured low-poly GLB in models_glb/. Resumable: skips any
creature whose final models_glb/<name>.glb already exists. One bad creature is
logged and skipped, never aborts the batch.

Per creature (proven flow, two TRELLIS passes):
  Stage 2  geometry : trellis2_image_to_3d  -> _mesh/<name>.glb     (decimate source)
  Stage 3  texture  : MeshWithTexturing     -> _mesh/<name>_tex.glb (bake source)
  Stage 4a decimate : decimate_lowpoly.py (voxel-remesh dense path) -> _mesh/<name>_lp.glb
  Stage 4b bake     : bake_lowpoly.py (albedo bake)                 -> models_glb/<name>.glb

    python run_bestiary_3d.py [roster.json]   (default roster_remaining.json here)

Prints STAGE/DONE/FAIL/SKIP lines (flushed) so a Monitor can track it, and a
final SUMMARY line. urllib-only stages run under any Python; Blender stages shell
the Blender 5.0 exe.
"""
import json
import os
import shutil
import subprocess
import sys

ROOT = "D:/Projects/comfyui-toolchain"
KIT = f"{ROOT}/products/grimforge_bestiary_v1"
CONCEPTS = f"{KIT}/_concepts"
MESH = f"{KIT}/_mesh"
FINAL = f"{KIT}/models_glb"
COMFY_INPUT = "D:/Projects/ComfyUI/input"
LP = f"{ROOT}/tools/asset_generators/lowpoly"
TRELLIS_Q = f"{ROOT}/pipelines/art-to-rig-ralph/scripts/trellis_queue.py"
GEO_WF = f"{ROOT}/workflows/mcp/trellis2_image_to_3d.json"
BLENDER = r"C:/Program Files/Blender Foundation/Blender 5.0/blender.exe"
PY = sys.executable


def log(msg):
    print(msg, flush=True)


def sh_stream(cmd):
    """Run inheriting stdout (heartbeats flow to Monitor). Return exit code."""
    return subprocess.run(cmd).returncode


def sh_cap(cmd, timeout=2000):
    """Run capturing stdout+stderr. Return (code, text)."""
    p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    return p.returncode, (p.stdout or "") + (p.stderr or "")


def stage_geometry(name, seed):
    geo = f"{MESH}/{name}.glb"
    if os.path.exists(geo) and os.path.getsize(geo) > 0:
        log(f"  STAGE2 geometry cached -> {geo}")
        return geo
    log(f"  STAGE2 geometry (trellis2_image_to_3d) seed={seed} ...")
    code = sh_stream([PY, f"{LP}/fire_3d.py", GEO_WF, f"{name}.png", str(seed), MESH])
    if code != 0 or not os.path.exists(geo):
        return None
    return geo


def stage_texture(name, seed):
    tex = f"{MESH}/{name}_tex.glb"
    if os.path.exists(tex) and os.path.getsize(tex) > 0:
        log(f"  STAGE3 texture cached -> {tex}")
        return tex
    log(f"  STAGE3 texture (MeshWithTexturing) seed={seed} ...")
    code, out = sh_cap([PY, TRELLIS_Q, "--workflow", "MeshWithTexturing",
                        "--front", f"{name}.png", "--prefix", f"{name}_tex",
                        "--seed", str(seed), "--timeout", "2400"], timeout=2600)
    src = None
    for line in out.splitlines():
        if line.startswith("OUTPUT "):
            src = line[len("OUTPUT "):].strip()
    if code != 0 or not src or not os.path.exists(src):
        log("    " + " | ".join(l for l in out.splitlines()
                                 if l.startswith(("NODE_ERRORS", "ERROR", "TIMEOUT", "STATUS")))[:400])
        return None
    shutil.copy2(src, tex)
    return tex


def stage_decimate(name, geo, tris):
    lp = f"{MESH}/{name}_lp.glb"
    log(f"  STAGE4a decimate -> {tris} tris ...")
    code, out = sh_cap([BLENDER, "-b", "--python", f"{LP}/decimate_lowpoly.py",
                        "--", geo, lp, str(tris)], timeout=1200)
    ok = next((l for l in out.splitlines() if l.startswith("DECIMATE_OK")), None)
    if code != 0 or not ok or not os.path.exists(lp):
        log("    decimate FAILED: " + (out.strip().splitlines() or ["<no output>"])[-1][:300])
        return None
    log("    " + ok)
    return lp


def stage_bake(name, lp, tex):
    final = f"{FINAL}/{name}.glb"
    log("  STAGE4b bake albedo ...")
    code, out = sh_cap([BLENDER, "-b", "--python", f"{LP}/bake_lowpoly.py",
                        "--", lp, tex, final, "2048"], timeout=1200)
    ok = next((l for l in out.splitlines() if l.startswith("BAKE_OK")), None)
    if code != 0 or not ok or not os.path.exists(final):
        log("    bake FAILED: " + (out.strip().splitlines() or ["<no output>"])[-1][:300])
        return None
    log("    " + ok)
    return final


def main():
    roster_path = sys.argv[1] if len(sys.argv) > 1 else f"{KIT}/roster_remaining.json"
    R = json.load(open(roster_path, encoding="utf-8"))
    pieces = R["pieces"]
    for d in (MESH, FINAL, CONCEPTS):
        os.makedirs(d, exist_ok=True)

    done, failed, skipped = [], [], []
    n = len(pieces)
    log(f"BESTIARY_3D_START {n} creatures")
    for i, p in enumerate(pieces, 1):
        name = p["name"]
        tris = p.get("tris", 3000)
        seed = 1234 + i * 7
        final = f"{FINAL}/{name}.glb"
        log(f"==[{i}/{n}] {name}==")
        if os.path.exists(final) and os.path.getsize(final) > 0:
            log(f"  SKIP already done -> {final}")
            skipped.append(name)
            continue
        concept = f"{CONCEPTS}/{name}.png"
        if not os.path.exists(concept):
            log(f"  FAIL {name} concept-missing ({concept})")
            failed.append((name, "concept-missing"))
            continue
        shutil.copy2(concept, f"{COMFY_INPUT}/{name}.png")

        geo = stage_geometry(name, seed)
        if not geo:
            log(f"  FAIL {name} geometry")
            failed.append((name, "geometry"))
            continue
        tex = stage_texture(name, seed)
        if not tex:
            log(f"  FAIL {name} texture")
            failed.append((name, "texture"))
            continue
        lp = stage_decimate(name, geo, tris)
        if not lp:
            log(f"  FAIL {name} decimate")
            failed.append((name, "decimate"))
            continue
        fin = stage_bake(name, lp, tex)
        if not fin:
            log(f"  FAIL {name} bake")
            failed.append((name, "bake"))
            continue
        log(f"  DONE {name} -> {fin}")
        done.append(name)

    log(f"SUMMARY done={len(done)} skipped={len(skipped)} failed={len(failed)}")
    if failed:
        log("FAILED: " + ", ".join(f"{n}({s})" for n, s in failed))
    log("BESTIARY_3D_COMPLETE")


if __name__ == "__main__":
    main()
