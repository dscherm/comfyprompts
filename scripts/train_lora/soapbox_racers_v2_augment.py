"""soapbox_racers v2 — targeted augmentation to strengthen under-represented / weak
characters (player, sparks, pip) and add the MUTANT character. Reads illustrative
source art from _v2_augsrc, img2img at LOW denoise (preserves the bold-ink look),
writes character-named augments into the flat v2 dataset.
    python soapbox_racers_v2_augment.py
"""
import io, json, os, time, urllib.request
import requests
from PIL import Image

BASE = "http://localhost:8188"
WF = json.load(open(r"D:\Projects\comfyui-toolchain\workflows\mcp\img2img.json"))
SRC = r"E:/ai-training/datasets/_v2_augsrc"
OUT = r"E:/ai-training/datasets/soapbox_racers_v2"

STYLE = ("flat ink comic book illustration, bold black outlines, heavy ink, crosshatching, "
         "gritty, full body, white background")
# source-filename substring -> (character key, description)
MAP = [
    ("wide_tpose_rookie", "player", "the rookie racer in an orange racing jacket with black stripes, goggles on his forehead, messy brown hair"),
    ("sparks", "sparks", "an electric livewire in a black leather jacket covered in yellow lightning bolts over a blue suit, goggles, wild light-blue hair"),
    ("pip", "pip", "a scrappy scavenger teenager in a green patched vest, scrap backpack, messy red hair"),
    ("mutant", "mutant", "a pink-skinned mutant brawler with a blue mohawk, bulging muscles, spiked blue armor pads, riding boots"),
]
NEG = "photo, realistic 3d render, blurry, cartoon, anime, chibi, superhero, marvel comics, clean vector"
DENOISE = [0.40, 0.50]


def char_of(fname):
    for sub, key, desc in MAP:
        if sub in fname:
            return key, desc
    return None, None


def http_json(path, payload):
    req = urllib.request.Request(BASE + path, data=json.dumps(payload).encode(),
                                 headers={"Content-Type": "application/json"})
    return json.loads(urllib.request.urlopen(req, timeout=30).read().decode())


def upload(src_path, upname):
    im = Image.open(src_path).convert("RGB")
    w, h = im.size
    scale = min(896 / max(w, h), 1.0)
    w, h = int(w * scale) - int(w * scale) % 64, int(h * scale) - int(h * scale) % 64
    im = im.resize((max(512, w), max(512, h)), Image.LANCZOS)
    buf = io.BytesIO(); im.save(buf, "PNG"); buf.seek(0)
    requests.post(f"{BASE}/upload/image", files={"image": (upname, buf, "image/png")}, data={"overwrite": "true"})
    return upname


def build(imgname, desc, dn, seed, tag):
    wf = json.loads(json.dumps(WF))
    wf["2"]["inputs"]["image"] = imgname
    wf["4"]["inputs"]["text"] = f"soapbox_racers, {STYLE}, {desc}"
    wf["5"]["inputs"]["text"] = NEG
    wf["6"]["inputs"].update(seed=seed, steps=24, cfg=1.0, sampler_name="euler", scheduler="beta", denoise=dn)
    wf["8"]["inputs"]["filename_prefix"] = f"v2_{tag}"
    return wf


def main():
    srcs = sorted(f for f in os.listdir(SRC) if f.endswith(".png"))
    pending = {}
    for f in srcs:
        key, desc = char_of(f)
        if not key:
            continue
        up = upload(f"{SRC}/{f}", f"v2src_{f}")
        # pip has few sources -> 2 denoise; others 1 (denoise 0.40) to control counts
        dns = DENOISE if key == "pip" else [0.40]
        for dn in dns:
            tag = f"{key}_{os.path.splitext(f)[0][:10]}_d{int(dn*100)}"
            try:
                pid = http_json("/prompt", {"prompt": build(up, desc, dn, 700 + len(pending), tag)})["prompt_id"]
                pending[pid] = (key, tag)
            except Exception as e:
                print("FAIL", tag, e, flush=True)
    print(f"{len(pending)} augment jobs queued. Polling…", flush=True)
    done = 0
    deadline = time.time() + 3000
    while pending and time.time() < deadline:
        time.sleep(6)
        for pid in list(pending):
            try:
                hist = json.loads(urllib.request.urlopen(f"{BASE}/history/{pid}", timeout=30).read().decode())
            except Exception:
                continue
            if pid in hist:
                key, tag = pending.pop(pid)
                for n in hist[pid].get("outputs", {}).values():
                    for im in n.get("images", []):
                        try:
                            data = urllib.request.urlopen(f"{BASE}/view?filename={im['filename']}&type=output", timeout=30).read()
                            # rename so caption keys off the character name
                            open(f"{OUT}/{key}_{im['filename']}", "wb").write(data)
                        except Exception:
                            pass
                done += 1
                if done % 5 == 0:
                    print(f"  {done} done", flush=True)
    print(f"V2 AUGMENT DONE — dataset now {len([f for f in os.listdir(OUT) if f.endswith('.png')])} images", flush=True)


if __name__ == "__main__":
    main()
