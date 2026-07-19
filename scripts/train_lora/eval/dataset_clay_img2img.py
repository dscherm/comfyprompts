"""dataset_clay_img2img — clay version of a character by IMG2IMG through mv_ortho.

For LoRAs whose identity lives in the rendered image, not a reusable text
description (e.g. sagaink: caption is only "sagaink, <name>, ... ink style"), the
text2img clay bootstrap loses the character. This restyles the character's own
ink render into clay: upload the ink PNG -> VAEEncode -> KSampler(mv_ortho,
denoise ~0.6) -> a clean-ish clay render that KEEPS the costume/silhouette.

Source ink renders must already exist (run dataset_fists_gen.py first). Output
-> <ink_dir>/clay/<stem>.png. ComfyUI HTTP (3090 Ti), urllib only, ComfyUI UP.

  python dataset_clay_img2img.py --ink-dir E:/ai-training/_raw/vibrant_rpg_char_sagaink_fists \
      [--denoise 0.6] [--strength 1.0] [--limit 1]
"""
from __future__ import annotations

import argparse
import json
import time
import urllib.error
import urllib.request
import uuid
from pathlib import Path

COMFY = "http://localhost:8188"
CKPT = "flux1-dev-fp8.safetensors"
MV_ORTHO = "style\\mv_ortho.safetensors"

POS = ("mv_ortho, front view, full body from head to feet, the entire figure centered "
       "with the feet visible, smooth matte 3d clay render, isolated on a plain flat "
       "neutral-grey background, orthographic, soft even studio lighting, no cast "
       "shadow, no weapon, hands at sides")
NEG = ("cropped, close-up, portrait, bust shot, cut off, out of frame, feet cut off, "
       "weapon, sword, axe, staff, holding an object, cast shadow, drop shadow, ground, "
       "floor, scenery, background objects, architecture, signature, logo, watermark, "
       "text, blurry, low quality")


def upload(path: Path) -> str:
    boundary = "----comfy" + uuid.uuid4().hex
    body = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="image"; filename="{path.name}"\r\n'
        "Content-Type: image/png\r\n\r\n"
    ).encode() + path.read_bytes() + f"\r\n--{boundary}--\r\n".encode()
    hdr = {"Content-Type": f"multipart/form-data; boundary={boundary}"}
    req = urllib.request.Request(f"{COMFY}/upload/image", data=body, headers=hdr)
    r = json.loads(urllib.request.urlopen(req, timeout=60).read())
    return f"{r['subfolder']}/{r['name']}" if r.get("subfolder") else r["name"]


def build(image_ref: str, denoise: float, strength: float, seed: int) -> dict:
    return {
        "1": {"inputs": {"ckpt_name": CKPT}, "class_type": "CheckpointLoaderSimple"},
        "2": {"inputs": {"lora_name": MV_ORTHO, "strength_model": strength,
                         "strength_clip": strength, "model": ["1", 0], "clip": ["1", 1]},
              "class_type": "LoraLoader"},
        "10": {"inputs": {"image": image_ref}, "class_type": "LoadImage"},
        "11": {"inputs": {"pixels": ["10", 0], "vae": ["1", 2]}, "class_type": "VAEEncode"},
        "4": {"inputs": {"text": POS, "clip": ["2", 1]}, "class_type": "CLIPTextEncode"},
        "5": {"inputs": {"text": NEG, "clip": ["2", 1]}, "class_type": "CLIPTextEncode"},
        "6": {"inputs": {"seed": seed, "steps": 24, "cfg": 1.0, "sampler_name": "euler",
                         "scheduler": "beta", "denoise": denoise, "model": ["2", 0],
                         "positive": ["4", 0], "negative": ["5", 0], "latent_image": ["11", 0]},
              "class_type": "KSampler"},
        "7": {"inputs": {"samples": ["6", 0], "vae": ["1", 2]}, "class_type": "VAEDecode"},
        "8": {"inputs": {"filename_prefix": "clay_i2i", "images": ["7", 0]},
              "class_type": "SaveImage"},
    }


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
    ap.add_argument("--ink-dir", required=True, type=Path, help="dir of source ink renders.")
    ap.add_argument("--denoise", type=float, default=0.6)
    ap.add_argument("--strength", type=float, default=1.0)
    ap.add_argument("--seed", type=int, default=51715)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--rembg", action="store_true",
                    help="isolate the clay subject on transparency (TRELLIS-ready) via rembg.")
    a = ap.parse_args()

    inks = sorted(p for p in a.ink_dir.glob("*.png"))
    if a.limit:
        inks = inks[:a.limit]
    if not inks:
        print(f"no ink PNGs in {a.ink_dir} (run dataset_fists_gen.py first)")
        return 1
    out = a.ink_dir / "clay"
    try:
        urllib.request.urlopen(f"{COMFY}/system_stats", timeout=5).read()
    except (urllib.error.URLError, OSError):
        print(f"ComfyUI not reachable at {COMFY}.")
        return 1
    out.mkdir(parents=True, exist_ok=True)
    ok = 0
    for i, ink in enumerate(inks):
        dest = out / ink.name
        ref = upload(ink)
        img = wait(queue(build(ref, a.denoise, a.strength, a.seed + i * 101)))
        if not img:
            print(f"  [{i + 1}/{len(inks)}] FAIL {ink.stem}")
            continue
        fetch(img, dest)
        if a.rembg:
            from PIL import Image
            from rembg import remove
            remove(Image.open(dest).convert("RGBA")).save(dest)
        ok += 1
        print(f"  [{i + 1}/{len(inks)}] OK {ink.stem}", flush=True)
    print(f"DONE: {ok}/{len(inks)} clay (img2img d={a.denoise}) -> {out}")
    return 0 if ok == len(inks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
