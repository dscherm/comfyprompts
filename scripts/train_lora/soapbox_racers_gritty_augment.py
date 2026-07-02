"""soapbox_racers (gritty retrain) — augment the curated gritty base (~26 images:
the character_variations + bones) to ~70 via img2img at LOW denoise with a
gritty-comic prompt (heavy ink, crosshatching — NEVER cartoon/anime). Low denoise
preserves the real comic art while adding render/detail variety.
    python soapbox_racers_gritty_augment.py
"""
import io
import json
import os
import time
import urllib.request

import requests
from PIL import Image

BASE = "http://localhost:8188"
WF = json.load(open(r"D:\Projects\comfyui-toolchain\workflows\mcp\img2img.json"))
D = r"E:/ai-training/datasets/soapbox_racers_gritty"

PROMPT = ("gritty comic book illustration, heavy black ink, dense crosshatching, bold black "
          "outlines, detailed line art, post-apocalyptic wasteland racer, full body, dramatic "
          "shading, R. Crumb, Katsuhiro Otomo, Jack Davis, muted desert palette")
NEG = "cartoon, anime, chibi, cute, smooth, 3d render, glossy, plastic"
DENOISE = [0.35, 0.45]
SEEDS = [7, 19, 31]


def http_json(path, payload):
    req = urllib.request.Request(BASE + path, data=json.dumps(payload).encode(),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode())


def upload(src_path, upname):
    im = Image.open(src_path).convert("RGB")
    w, h = im.size
    scale = min(896 / max(w, h), 1.0)
    w, h = int(w * scale), int(h * scale)
    w -= w % 64; h -= h % 64
    im = im.resize((max(512, w), max(512, h)), Image.LANCZOS)
    buf = io.BytesIO(); im.save(buf, "PNG"); buf.seek(0)
    requests.post(f"{BASE}/upload/image", files={"image": (upname, buf, "image/png")},
                  data={"overwrite": "true"})
    return upname


def build(imgname, denoise, seed, tag):
    wf = json.loads(json.dumps(WF))
    wf["2"]["inputs"]["image"] = imgname
    wf["4"]["inputs"]["text"] = PROMPT
    wf["5"]["inputs"]["text"] = NEG
    wf["6"]["inputs"].update(seed=seed, steps=24, cfg=1.0, sampler_name="euler",
                             scheduler="beta", denoise=denoise)
    wf["8"]["inputs"]["filename_prefix"] = f"gritty_{tag}"
    return wf


def main():
    # only augment the REAL gritty base (var_* and orig_bones); skip prior augments/outputs
    base = [f for f in sorted(os.listdir(D))
            if f.endswith(".png") and (f.startswith("var_") or f.startswith("orig_"))]
    pending = {}
    for f in base:
        stem = f[:-4].replace("var_", "").replace("orig_", "").replace("_fullbody", "")
        upname = upload(f"{D}/{f}", f"grittysrc_{stem}.png")
        for dn in DENOISE:
            for sd in SEEDS:
                tag = f"{stem}_d{int(dn*100)}_s{sd}"
                try:
                    pid = http_json("/prompt", {"prompt": build(upname, dn, sd, tag)})["prompt_id"]
                    pending[pid] = tag
                except Exception as e:
                    print(f"  FAIL {tag}: {e}", flush=True)
        print(f"queued {stem}", flush=True)
    print(f"\n{len(pending)} jobs queued. Polling...\n", flush=True)
    done = 0
    deadline = time.time() + 6000
    while pending and time.time() < deadline:
        time.sleep(6)
        for pid in list(pending):
            try:
                hist = json.loads(urllib.request.urlopen(f"{BASE}/history/{pid}", timeout=30).read().decode())
            except Exception:
                continue
            if pid in hist:
                pending.pop(pid)
                for n in hist[pid].get("outputs", {}).values():
                    for im in n.get("images", []):
                        try:
                            data = urllib.request.urlopen(
                                f"{BASE}/view?filename={im['filename']}&type=output", timeout=30).read()
                            open(f"{D}/{im['filename']}", "wb").write(data)
                        except Exception:
                            pass
                done += 1
                if done % 10 == 0:
                    print(f"  {done} done", flush=True)
    n = len([f for f in os.listdir(D) if f.endswith('.png')])
    print(f"\n==== GRITTY AUGMENT DONE: {n} images -> {D} ====", flush=True)


if __name__ == "__main__":
    main()
