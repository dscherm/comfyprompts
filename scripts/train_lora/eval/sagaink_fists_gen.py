"""sagaink_fists_gen — redo the vibrant_rpg_char (sagaink) showcase chars with EMPTY
CLOSED FISTS and no weapons.

Same 6 Norse dark-fantasy characters + dominant colors as the shipped eval
(vibrant_rpg_char_grid.md), regenerated with the sagaink_v3 LoRA and a prompt that
forces both hands into tight closed fists holding nothing. Applies the closed-fist
rule (spread/open fingers -> double-thumb/backwards hands; project_mv_ortho_fists):
open/spread fingers go in the NEGATIVE, closed fists in the positive.

ComfyUI HTTP (3090 Ti), stdlib urllib only. ComfyUI must be UP.

  python scripts/train_lora/eval/sagaink_fists_gen.py [--lora v3|v2] [--size 1024]
"""
from __future__ import annotations

import argparse
import json
import time
import urllib.error
import urllib.request
from pathlib import Path

COMFY = "http://localhost:8188"
OUT = Path(__file__).resolve().parent / "vibrant_rpg_char_fists"
WF = json.loads((Path(__file__).resolve().parents[3] / "workflows" / "mcp"
                 / "generate_image_lora.json").read_text())

# (slug, character, dominant color) — matches vibrant_rpg_char_grid.md.
CHARS = [
    ("berserker", "a viking berserker", "green"),
    ("frostgiant", "a frost giant", "blue"),
    ("huldra", "a forest huldra", "green"),
    ("draugr", "an undead draugr", "teal"),
    ("runecaster", "a rune caster", "purple"),
    ("shieldmaiden", "a shield maiden", "red"),
]
SEED = 51715  # v2 of the fist redo — new seed to escape the loose/clawed hands

# Force empty closed fists, no weapon. Strong fist language in the positive; claws,
# spread fingers, and the LoRA's fake signatures in the negative.
FISTS = ("full body character, standing straight, both arms hanging straight down at "
         "the sides, both hands tightly clenched into closed fists, human-like fists, "
         "fingers fully curled into the palm, knuckles facing forward, holding nothing, "
         "no weapon")
NEG = ("weapon, sword, axe, staff, spear, shield, holding an object, claws, talons, "
       "clawed hands, long fingers, spread fingers, splayed fingers, open hands, "
       "pointing finger, extra fingers, extra thumb, signature, artist name, logo, "
       "watermark, text, blurry, low quality")


def prompt(char: str, color: str) -> str:
    return (f"vibrant_rpg_char, {char}, {color} monochromatic, high-contrast "
            f"graphic-novel illustration, Sin City comic-noir style, {FISTS}")


def build(lora: str, pos: str, seed: int, size: int) -> dict:
    wf = json.loads(json.dumps(WF))
    wf["2"]["inputs"]["lora_name"] = lora
    wf["2"]["inputs"]["strength_model"] = 1.0
    wf["2"]["inputs"]["strength_clip"] = 1.0
    wf["3"]["inputs"]["width"] = size
    wf["3"]["inputs"]["height"] = size
    wf["4"]["inputs"]["text"] = pos
    wf["5"]["inputs"]["text"] = NEG
    wf["6"]["inputs"].update(seed=seed, steps=24, cfg=1.0, sampler_name="euler",
                             scheduler="beta", denoise=1.0)
    return wf


def queue(wf: dict) -> str:
    data = json.dumps({"prompt": wf}).encode()
    req = urllib.request.Request(f"{COMFY}/prompt", data=data,
                                 headers={"Content-Type": "application/json"})
    return json.loads(urllib.request.urlopen(req, timeout=30).read())["prompt_id"]


def wait(pid: str, timeout: int = 240) -> dict | None:
    t0 = time.time()
    while time.time() - t0 < timeout:
        try:
            h = json.loads(urllib.request.urlopen(f"{COMFY}/history/{pid}", timeout=15).read())
            if pid in h and h[pid].get("outputs"):
                imgs = h[pid]["outputs"].get("8", {}).get("images", [])
                if imgs:
                    return imgs[0]
        except urllib.error.URLError:
            pass
        time.sleep(2)
    return None


def fetch(img: dict, dest: Path) -> None:
    url = (f"{COMFY}/view?filename={img['filename']}"
           f"&subfolder={img.get('subfolder', '')}&type={img.get('type', 'output')}")
    dest.parent.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(url, timeout=60) as r, open(dest, "wb") as f:
        f.write(r.read())


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--lora", default="v3", choices=["v2", "v3"])
    ap.add_argument("--size", type=int, default=1024)
    a = ap.parse_args()
    lora = f"vibrant_rpg_char_sagaink_{a.lora}.safetensors"
    try:
        urllib.request.urlopen(f"{COMFY}/system_stats", timeout=5).read()
    except (urllib.error.URLError, OSError):
        print(f"ComfyUI not reachable at {COMFY}. Start it and retry.")
        return 1
    OUT.mkdir(parents=True, exist_ok=True)
    ok = 0
    for slug, char, color in CHARS:
        pid = queue(build(lora, prompt(char, color), SEED, a.size))
        img = wait(pid)
        if not img:
            print(f"  FAIL {slug}")
            continue
        dest = OUT / f"{slug}.png"
        fetch(img, dest)
        ok += 1
        print(f"  OK   {slug} ({color}) -> {dest.name}")
    print(f"DONE: {ok}/{len(CHARS)} -> {OUT}  (LoRA {lora})")
    return 0 if ok == len(CHARS) else 1


if __name__ == "__main__":
    raise SystemExit(main())
