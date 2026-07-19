"""Finish the raw kart-part geometry into game-ready GLBs for soapbox-sabotage.
Phase 1: decimate all parts (grey shapes -> game right away).
Phase 2: texture (TRELLIS) + bake albedo @512 -> colored -> game (overwrite).
Resumable: every stage skips if its output exists. Concepts are already staged
in ComfyUI/input from the geometry pass.

    python finish_kart_parts.py
"""
import glob, os, shutil, subprocess, sys

ROOT = "D:/Projects/comfyui-toolchain"
KP = ROOT + "/products/soapbox_kart_parts_v1"
GAME = "D:/Projects/soapbox-sabotage/assets/kart_parts"
LOWPOLY = ROOT + "/tools/asset_generators/lowpoly"
TRELLIS_Q = ROOT + "/pipelines/art-to-rig-ralph/scripts/trellis_queue.py"
PY = "D:/Projects/ComfyUI/venv/Scripts/python.exe"
BL = r"C:/Program Files/Blender Foundation/Blender 5.0/blender.exe"
OUT = "D:/Projects/ComfyUI/output"

PARTS = ["chassis_crate", "wheel_knobby", "engine_steam", "seat_bucket", "wpn_flamethrower"]
TRIS = {"chassis_crate": 6000, "wheel_knobby": 3000}  # else 4000
os.makedirs(GAME, exist_ok=True)


def log(m): print(m, flush=True)


def find_tex(p):
    c = sorted(glob.glob(f"{OUT}/{p}_tex*.glb"), key=os.path.getmtime, reverse=True)
    return c[0] if c else None


# Phase 1 — decimate (grey shapes into the game immediately)
for p in PARTS:
    geo = f"{KP}/models_glb/{p}.glb"
    low = f"{KP}/_work/{p}_lowpoly.glb"
    if not os.path.exists(geo):
        log(f"SKIP {p} (no geometry)"); continue
    if not os.path.exists(low):
        log(f"DECIMATE {p}")
        subprocess.run([BL, "-b", "--python", f"{LOWPOLY}/decimate_lowpoly.py", "--",
                        geo, low, str(TRIS.get(p, 4000))], check=True, timeout=900)
    shutil.copy2(low, f"{GAME}/{p}.glb")   # grey shape usable now
    log(f"GREY_READY {p}")
log("PHASE1_DONE")

# Phase 2 — texture + bake @512 (color)
for p in PARTS:
    geo = f"{KP}/models_glb/{p}.glb"
    low = f"{KP}/_work/{p}_lowpoly.glb"
    final = f"{KP}/_work/{p}_final.glb"
    if not (os.path.exists(geo) and os.path.exists(low)):
        continue
    if os.path.exists(final):
        shutil.copy2(final, f"{GAME}/{p}.glb"); log(f"COLOR_READY {p} (cached)"); continue
    tex = find_tex(p)
    if not tex:
        if not os.path.exists(f"D:/Projects/ComfyUI/input/{p}.png"):
            log(f"NO_CONCEPT {p} — leaving grey"); continue
        log(f"TEXTURE {p}")
        subprocess.run([PY, TRELLIS_Q, "--workflow", "MeshTexturing", "--front", f"{p}.png",
                        "--mesh", geo, "--prefix", f"{p}_tex", "--seed", "12345"],
                       cwd=ROOT, check=True, timeout=2700)
        tex = find_tex(p)
    if not tex:
        log(f"TEXTURE_FAIL {p} — leaving grey"); continue
    log(f"BAKE {p}")
    subprocess.run([BL, "-b", "--python", f"{LOWPOLY}/bake_lowpoly.py", "--",
                    low, tex, final, "512"], check=True, timeout=600)
    shutil.copy2(final, f"{GAME}/{p}.glb")
    log(f"COLOR_READY {p}")
log("ALL_DONE")
