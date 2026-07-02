"""soapbox_racers LoRA — dataset augmentation from the 10 curated hero characters.

Source = D:/.../to3d/*.png (512x768, the definitive gritty-wasteland-racer art).
10 unique heroes is thin, so we img2img each at LOW denoise (0.40/0.50) x 3 seeds to
add render/detail variety while PRESERVING the character + the wasteland aesthetic
(higher denoise would drift to generic Flux). Result: 10 originals + ~60 variations
-> ~70-image dataset in the exact target style. Run with ComfyUI venv (PIL+requests).
    python soapbox_racers_augment.py
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
SRC = r"D:/Projects/soapbox-unity/Assets/Sprites/Characters/to3d"
OUT = r"E:/ai-training/datasets/soapbox_racers"

PROMPT = ("gritty post-apocalyptic wasteland kart racer character, full body, bold black "
          "outlines, dense comic-book detail, big expressive face, dramatic, retro cartoon "
          "illustration, Mad Max desert palette, R. Crumb crosshatching, Otomo mechanical detail")
DENOISE = [0.40, 0.50]
SEEDS = [11, 22, 33]


def http_json(path, payload):
    req = urllib.request.Request(BASE + path, data=json.dumps(payload).encode(),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode())


def upload(src_path, upname):
    im = Image.open(src_path).convert("RGB")
    # keep portrait aspect, snap to /64 (Flux-friendly); cap long side at 896
    w, h = im.size
    scale = min(896 / max(w, h), 1.0)
    w, h = int(w * scale), int(h * scale)
    w -= w % 64; h -= h % 64
    im = im.resize((max(512, w), max(512, h)), Image.LANCZOS)
    buf = io.BytesIO(); im.save(buf, "PNG"); buf.seek(0)
    requests.post(f"{BASE}/upload/image", files={"image": (upname, buf, "image/png")},
                  data={"overwrite": "true"})
    return upname, im


def build(imgname, denoise, seed, tag):
    wf = json.loads(json.dumps(WF))
    wf["2"]["inputs"]["image"] = imgname
    wf["4"]["inputs"]["text"] = PROMPT
    wf["5"]["inputs"]["text"] = ""
    wf["6"]["inputs"].update(seed=seed, steps=22, cfg=1.0, sampler_name="euler",
                             scheduler="beta", denoise=denoise)
    wf["8"]["inputs"]["filename_prefix"] = f"racer_{tag}"
    return wf


def main():
    os.makedirs(OUT, exist_ok=True)
    heroes = sorted(f for f in os.listdir(SRC) if f.endswith(".png"))
    pending = {}
    for f in heroes:
        char = f.split("_")[0]
        upname, im = upload(f"{SRC}/{f}", f"racersrc_{char}.png")
        im.save(f"{OUT}/orig_{char}.png")  # keep the pristine original in the dataset
        for dn in DENOISE:
            for sd in SEEDS:
                tag = f"{char}_d{int(dn*100)}_s{sd}"
                try:
                    pid = http_json("/prompt", {"prompt": build(upname, dn, sd, tag)})["prompt_id"]
                    pending[pid] = tag
                except Exception as e:
                    print(f"  FAIL {tag}: {e}", flush=True)
        print(f"queued {char}", flush=True)
    print(f"\n{len(pending)} jobs queued. Polling...\n", flush=True)
    done = 0
    deadline = time.time() + 5400
    while pending and time.time() < deadline:
        time.sleep(6)
        for pid in list(pending):
            try:
                hist = json.loads(urllib.request.urlopen(f"{BASE}/history/{pid}", timeout=30).read().decode())
            except Exception:
                continue
            if pid in hist:
                tag = pending.pop(pid)
                for n in hist[pid].get("outputs", {}).values():
                    for im in n.get("images", []):
                        try:
                            data = urllib.request.urlopen(
                                f"{BASE}/view?filename={im['filename']}&type=output", timeout=30).read()
                            open(f"{OUT}/{im['filename']}", "wb").write(data)
                        except Exception:
                            pass
                done += 1
                if done % 10 == 0:
                    print(f"  {done} done", flush=True)
    n = len([f for f in os.listdir(OUT) if f.endswith('.png')])
    print(f"\n==== RACERS AUGMENT DONE: {n} images -> {OUT} ====", flush=True)


if __name__ == "__main__":
    main()
