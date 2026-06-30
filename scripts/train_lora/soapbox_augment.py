"""Soapbox LoRA — dataset AUGMENTATION pipeline (SX0).

The source sprites are 64x64 (too small/few for Flux). Pilot proved that
upscale->img2img at LOW denoise (~0.5-0.55) UPGRADES each sprite to a clean 512px
bold-outline cartoon while PRESERVING the character (skeleton, punk-king mohawk,
etc.); denoise >=0.7 drifts to generic Flux cartoon. So we augment at d0.5/0.55,
several seeds per character + both front + 3/4 source angles, to build a faithful
~70-image cartoon-kart-mascot dataset. Run with ComfyUI venv (PIL+requests).
    python soapbox_augment.py
"""
import json, time, io, os, urllib.request
import requests
from PIL import Image

BASE = "http://localhost:8188"
WF = json.load(open(r"D:\Projects\comfyui-toolchain\workflows\mcp\img2img.json"))
SPR = r"D:/Projects/soapboxsabatoge/assets/sprites/characters"
OUT_COLLECT = r"E:/ai-training/datasets/soapbox_raw"
PROMPT = ("a cute cartoon mascot character driving a soapbox derby racer kart, bold black "
          "outlines, vibrant saturated flat colors, clean cartoon illustration, white background")
CHARS = ["bones", "crank", "grit", "pip", "player", "punk_king", "rust", "smog", "sparks"]
ANGLES = ["front_normal", "front_quarter_normal"]   # 2 source compositions for variety
DENOISE = [0.50, 0.55]
SEEDS = [11, 22, 33]                                 # 9 chars x 2 angles x 2 denoise x 3 seeds = up to 108


def http_json(path, payload):
    req = urllib.request.Request(BASE + path, data=json.dumps(payload).encode(),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode())


def upscale_upload(char, angle):
    src = f"{SPR}/{char}_{angle}.png"
    if not os.path.exists(src):
        return None
    im = Image.open(src).convert("RGB").resize((512, 512), Image.LANCZOS)
    buf = io.BytesIO(); im.save(buf, "PNG"); buf.seek(0)
    fn = f"soapsrc_{char}_{angle}.png"
    requests.post(f"{BASE}/upload/image", files={"image": (fn, buf, "image/png")},
                  data={"overwrite": "true"})
    return fn


def build(imgname, denoise, seed, tag):
    wf = json.loads(json.dumps(WF))
    wf["2"]["inputs"]["image"] = imgname
    wf["4"]["inputs"]["text"] = PROMPT
    wf["5"]["inputs"]["text"] = ""
    wf["6"]["inputs"].update(seed=seed, steps=20, cfg=1.0, sampler_name="euler",
                             scheduler="simple", denoise=denoise)
    wf["8"]["inputs"]["filename_prefix"] = f"sx_{tag}"
    return wf


def main():
    os.makedirs(OUT_COLLECT, exist_ok=True)
    pending = {}
    for char in CHARS:
        for angle in ANGLES:
            name = upscale_upload(char, angle)
            if not name:
                continue
            for dn in DENOISE:
                for sd in SEEDS:
                    tag = f"{char}_{angle.split('_')[0]}{angle.count('quarter') and 'q' or ''}_d{int(dn*100)}_s{sd}"
                    try:
                        pid = http_json("/prompt", {"prompt": build(name, dn, sd, tag)})["prompt_id"]
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
                            open(f"{OUT_COLLECT}/{im['filename']}", "wb").write(data)
                        except Exception:
                            pass
                done += 1
                if done % 10 == 0:
                    print(f"  {done} done", flush=True)
    n = len([f for f in os.listdir(OUT_COLLECT) if f.endswith('.png')])
    print(f"\n==== AUGMENT DONE: {n} images collected -> {OUT_COLLECT} ====", flush=True)
    print("Next: curate (drop drifted/duplicate) -> prep_dataset.py -> caption.py --trigger soapbox_style -> train", flush=True)


if __name__ == "__main__":
    main()
