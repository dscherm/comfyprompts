"""soapbox_style — 10-image showcase (winning settings: strength 0.8).
Diverse mascots + actions to show the LoRA's range. Direct ComfyUI HTTP.
    D:/Projects/ComfyUI/venv/Scripts/python.exe soapbox_showcase_gen.py
"""
import json
import os
import time
import urllib.request
import urllib.error

COMFY = "http://localhost:8188"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "soapbox_showcase")
os.makedirs(OUT, exist_ok=True)
LORA = "style\\soapbox_style.safetensors"
TRIGGER = "soapbox_style"
STRENGTH = 0.8

WORKFLOW = json.load(open(r"D:/Projects/comfyui-toolchain/workflows/mcp/generate_image_lora.json"))

PROMPTS = [
    ("cat", "a cool cat mascot driving a soapbox go-kart, sunglasses, dark background"),
    ("dragon", "a small dragon mascot driving a soapbox go-kart, breathing a puff of fire, dark background"),
    ("panda", "a panda mascot driving a soapbox go-kart, dark background"),
    ("robot_wheelie", "a robot mascot popping a wheelie in a soapbox go-kart, dynamic, dark background"),
    ("viking", "a viking mascot with a horned helmet driving a soapbox go-kart, dark background"),
    ("ghost", "a friendly ghost mascot floating in a soapbox go-kart, dark background"),
    ("tiger_finish", "a tiger racer mascot crossing the checkered finish line in a go-kart, dark background"),
    ("raccoon_wrench", "a raccoon mechanic mascot holding a wrench beside a soapbox go-kart, dark background"),
    ("chicken_dust", "a chicken mascot speeding in a soapbox go-kart, dust cloud, dark background"),
    ("shark_drift", "a shark mascot drifting a soapbox go-kart around a corner, dark background"),
]


def build(prompt, seed):
    wf = json.loads(json.dumps(WORKFLOW))
    wf["2"]["inputs"]["lora_name"] = LORA
    wf["2"]["inputs"]["strength_model"] = STRENGTH
    wf["2"]["inputs"]["strength_clip"] = STRENGTH
    wf["3"]["inputs"]["width"] = 1024
    wf["3"]["inputs"]["height"] = 1024
    wf["4"]["inputs"]["text"] = f"{TRIGGER}, {prompt}"
    wf["5"]["inputs"]["text"] = "blurry, photo, realistic, watermark, text"
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


def main():
    for i, (key, prompt) in enumerate(PROMPTS):
        pid = queue(build(prompt, 800 + i * 137))
        img = wait(pid)
        if not img:
            print("FAIL", key); continue
        dest = os.path.join(OUT, f"{i+1:02d}_{key}.png")
        fetch(img, dest)
        print("OK  ", dest)
    print("DONE — 10 showcase images in", OUT)


if __name__ == "__main__":
    main()
