"""Soapbox Kart Kit — concept + mascot source generation (soapbox_style LoRA @0.8).

Generates the 5 mascot-racer source images that feed Hunyuan3D (character seated
in a soapbox go-kart, full vehicle visible, 3/4 front — clean silhouette for
image->3D; the Hunyuan workflow removes the dark bg itself), plus a hero concept
that locks the kit's cartoon palette. Winning eval settings: strength 0.8.

    D:/Projects/ComfyUI/venv/Scripts/python.exe gen_concepts.py
"""
import json
import os
import time
import urllib.request
import urllib.error

COMFY = "http://localhost:8188"
ROOT = r"D:/Projects/comfyui-toolchain/products/soapbox_kart_kit_v1"
OUT = os.path.join(ROOT, "refs")
os.makedirs(OUT, exist_ok=True)
LORA = "style\\soapbox_style.safetensors"
TRIGGER = "soapbox_style"
STRENGTH = 0.8

WORKFLOW = json.load(open(r"D:/Projects/comfyui-toolchain/workflows/mcp/generate_image_lora.json"))

# 5 mascot racers — full vehicle, centered, 3/4 front for clean image->3D
MASCOTS = {
    "robot": "a chunky robot mascot sitting in a soapbox go-kart racer",
    "frog": "a cartoon frog mascot sitting in a soapbox go-kart racer",
    "wizard": "a wizard mascot in a pointed hat sitting in a soapbox go-kart racer",
    "shark": "a cartoon shark mascot sitting in a soapbox go-kart racer",
    "skeleton": "a skeleton mascot sitting in a soapbox go-kart racer",
}
MASCOT_TAIL = "full vehicle visible, centered, three-quarter front view, dark background"

# hero concept for the kit palette / look-lock (not for 3D)
HERO = ("soapbox_style, a cartoon soapbox go-kart racing scene, karts on a race track "
        "with ramps and cones, dynamic, dark background")


def build(prompt, seed, w=1024, h=1024):
    wf = json.loads(json.dumps(WORKFLOW))
    wf["2"]["inputs"]["lora_name"] = LORA
    wf["2"]["inputs"]["strength_model"] = STRENGTH
    wf["2"]["inputs"]["strength_clip"] = STRENGTH
    wf["3"]["inputs"]["width"] = w
    wf["3"]["inputs"]["height"] = h
    wf["4"]["inputs"]["text"] = prompt
    wf["5"]["inputs"]["text"] = "blurry, photo, realistic, watermark, text, cropped, cut off"
    wf["6"]["inputs"]["seed"] = seed
    wf["6"]["inputs"]["steps"] = 24
    wf["6"]["inputs"]["cfg"] = 1.0
    wf["6"]["inputs"]["sampler_name"] = "euler"
    wf["6"]["inputs"]["scheduler"] = "beta"
    wf["6"]["inputs"]["denoise"] = 1.0
    return wf


def queue(wf):
    data = json.dumps({"prompt": wf}).encode()
    req = urllib.request.Request(f"{COMFY}/prompt", data=data, headers={"Content-Type": "application/json"})
    return json.loads(urllib.request.urlopen(req, timeout=30).read())["prompt_id"]


def wait(pid, timeout=300):
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


def fetch(img, dest):
    url = f"{COMFY}/view?filename={img['filename']}&subfolder={img.get('subfolder','')}&type={img.get('type','output')}"
    with urllib.request.urlopen(url, timeout=30) as r, open(dest, "wb") as f:
        f.write(r.read())


def gen(tag, prompt, seed):
    pid = queue(build(prompt, seed))
    img = wait(pid)
    if not img:
        print("FAIL", tag)
        return
    dest = os.path.join(OUT, f"{tag}.png")
    fetch(img, dest)
    print("OK  ", tag, "->", dest)


def main():
    gen("hero_concept", HERO, 4242)
    for i, (key, body) in enumerate(MASCOTS.items()):
        gen(f"mascot_{key}", f"{TRIGGER}, {body}, {MASCOT_TAIL}", 1000 + i * 111)
    print("DONE — refs in", OUT)


if __name__ == "__main__":
    main()
