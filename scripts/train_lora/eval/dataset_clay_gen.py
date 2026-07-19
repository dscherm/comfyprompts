"""dataset_clay_gen — clay (3D-render) version of a LoRA's characters for TRELLIS.

The clay half of the ink->clay bootstrap, applied to a character dataset: for each
unique character it renders an ISOLATED full-body ortho A/T-pose "clay" image on a
plain neutral-grey background (no ground/shadow), empty closed fists, via
mv_ortho@0.85 + <char LoRA>@0.65 (chained). Same seed policy as dataset_fists_gen
so the ink (native-style) and clay renders line up per character.

ComfyUI HTTP (3090 Ti), stdlib urllib only. ComfyUI must be UP.

  python dataset_clay_gen.py --dataset E:/ai-training/datasets/vibrant_rpg_char_sagaink \
      --char-lora vibrant_rpg_char_sagaink_v3.safetensors [--limit 1] [--size 1024]
"""
from __future__ import annotations

import argparse
import json
import time
import urllib.error
import urllib.request
from pathlib import Path

COMFY = "http://localhost:8188"
CKPT = "flux1-dev-fp8.safetensors"
MV_ORTHO = "style\\mv_ortho.safetensors"

CLAY = ("smooth matte 3d clay render, isolated on a plain flat neutral-grey background, "
        "floating, no ground, orthographic, soft even studio lighting, no cast shadow")
FISTS = ("both arms straight down at the sides, both hands tightly clenched into closed "
         "fists, fingers fully curled into the palm, holding nothing, no weapon")
NEG = ("weapon, sword, axe, staff, spear, shield, holding an object, claws, talons, "
       "long fingers, spread fingers, open hands, cast shadow, drop shadow, ground, "
       "floor, pedestal, scenery, background objects, signature, logo, watermark, "
       "text, blurry, low quality")


def unique_chars(dataset: Path) -> list[tuple[str, str]]:
    seen: dict[str, str] = {}
    for t in sorted(dataset.glob("*.txt")):
        cap = t.read_text(encoding="utf-8").strip()
        if cap and cap not in seen:
            seen[cap] = t.stem
    return [(stem, cap) for cap, stem in seen.items()]


def identity(caption: str) -> str:
    """trigger + subject fields (drop the native-style clause)."""
    parts = [p.strip() for p in caption.split(",")]
    return ", ".join(parts[:2]) if len(parts) >= 2 else caption


def build(char_lora: str, pos: str, seed: int, size: int) -> dict:
    """checkpoint -> mv_ortho@0.85 -> char@0.65 -> CLIP/KSampler -> save."""
    wf: dict = {"1": {"inputs": {"ckpt_name": CKPT}, "class_type": "CheckpointLoaderSimple"}}
    src = "1"
    for nid, (name, strg) in {"10": (MV_ORTHO, 0.85), "11": (char_lora, 0.65)}.items():
        wf[nid] = {"inputs": {"lora_name": name, "strength_model": strg, "strength_clip": strg,
                              "model": [src, 0], "clip": [src, 1]}, "class_type": "LoraLoader"}
        src = nid
    wf["3"] = {"inputs": {"width": size, "height": size, "batch_size": 1},
               "class_type": "EmptySD3LatentImage"}
    wf["4"] = {"inputs": {"text": pos, "clip": [src, 1]}, "class_type": "CLIPTextEncode"}
    wf["5"] = {"inputs": {"text": NEG, "clip": [src, 1]}, "class_type": "CLIPTextEncode"}
    wf["6"] = {"inputs": {"seed": seed, "steps": 24, "cfg": 1.0, "sampler_name": "euler",
                          "scheduler": "beta", "denoise": 1.0, "model": [src, 0],
                          "positive": ["4", 0], "negative": ["5", 0], "latent_image": ["3", 0]},
               "class_type": "KSampler"}
    wf["7"] = {"inputs": {"samples": ["6", 0], "vae": ["1", 2]}, "class_type": "VAEDecode"}
    wf["8"] = {"inputs": {"filename_prefix": "clay", "images": ["7", 0]}, "class_type": "SaveImage"}
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
    ap.add_argument("--dataset", required=True, type=Path)
    ap.add_argument("--char-lora", required=True)
    ap.add_argument("--out", default=None, help="default E:/ai-training/_raw/<name>_fists/clay")
    ap.add_argument("--size", type=int, default=1024)
    ap.add_argument("--start-seed", type=int, default=51715)
    ap.add_argument("--limit", type=int, default=0)
    a = ap.parse_args()

    chars = unique_chars(a.dataset)
    if a.limit:
        chars = chars[:a.limit]
    out = Path(a.out) if a.out else Path("E:/ai-training/_raw") / f"{a.dataset.name}_fists" / "clay"
    try:
        urllib.request.urlopen(f"{COMFY}/system_stats", timeout=5).read()
    except (urllib.error.URLError, OSError):
        print(f"ComfyUI not reachable at {COMFY}. Start it and retry.")
        return 1
    out.mkdir(parents=True, exist_ok=True)
    ok = 0
    for i, (stem, cap) in enumerate(chars):
        dest = out / f"{stem}.png"
        if dest.exists():
            ok += 1
            continue
        pos = f"mv_ortho, front view, full body, A/T-pose, {identity(cap)}, {CLAY}, {FISTS}"
        img = wait(queue(build(a.char_lora, pos, a.start_seed + i * 101, a.size)))
        if not img:
            print(f"  [{i + 1}/{len(chars)}] FAIL {stem}")
            continue
        fetch(img, dest)
        ok += 1
        print(f"  [{i + 1}/{len(chars)}] OK {stem}", flush=True)
    print(f"DONE: {ok}/{len(chars)} clay -> {out}")
    return 0 if ok == len(chars) else 1


if __name__ == "__main__":
    raise SystemExit(main())
