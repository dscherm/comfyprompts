"""SX3 eval — soapbox_style base-vs-LoRA grid on NEW kart-mascot subjects.

Drives ComfyUI directly over HTTP (MCP disconnected). Tests whether the LoRA
reproduces the gritty cartoon-kart-mascot look on characters it never trained on
(training set = skeletons + a few animals). Strengths 0.6 / 0.8 / 1.0 + base ctrl.

    D:/Projects/ComfyUI/venv/Scripts/python.exe soapbox_eval_gen.py   # (any py3 ok; urllib only)
"""
import json
import os
import time
import urllib.request
import urllib.error

COMFY = "http://localhost:8188"
OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "soapbox_style_assets")
os.makedirs(OUT_DIR, exist_ok=True)
LORA = "style\\soapbox_style.safetensors"  # ComfyUI lists loras with OS separator (Windows backslash)

# NEW mascot subjects — none of these were in the training set (skeletons/animals).
SUBJECTS = [
    ("robot", "a chunky robot mascot driving a soapbox go-kart, arms outstretched, dark background"),
    ("frog", "a cartoon frog mascot driving a go-kart, big grin, dark background"),
    ("wizard", "a wizard mascot in a pointed hat driving a soapbox racer, dark background"),
    ("shark", "a cartoon shark mascot driving a go-kart, sharp teeth, dark background"),
]
TRIGGER = "soapbox_style"
STRENGTHS = [0.6, 0.8, 1.0]
SEED = 70707  # fixed seed so strength rows are directly comparable

WORKFLOW = json.load(open(os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "..", "..",
    "workflows", "mcp", "generate_image_lora.json")))


def build(prompt, strength, seed):
    wf = json.loads(json.dumps(WORKFLOW))
    wf["2"]["inputs"]["lora_name"] = LORA
    wf["2"]["inputs"]["strength_model"] = strength
    wf["2"]["inputs"]["strength_clip"] = strength
    wf["3"]["inputs"]["width"] = 1024
    wf["3"]["inputs"]["height"] = 1024
    wf["4"]["inputs"]["text"] = prompt
    wf["5"]["inputs"]["text"] = "blurry, photo, realistic, watermark, text"
    wf["6"]["inputs"]["seed"] = seed
    wf["6"]["inputs"]["steps"] = 22
    wf["6"]["inputs"]["cfg"] = 1.0
    wf["6"]["inputs"]["sampler_name"] = "euler"
    wf["6"]["inputs"]["scheduler"] = "beta"
    wf["6"]["inputs"]["denoise"] = 1.0
    return wf


def queue(wf):
    data = json.dumps({"prompt": wf}).encode()
    req = urllib.request.Request(f"{COMFY}/prompt", data=data,
                                 headers={"Content-Type": "application/json"})
    return json.loads(urllib.request.urlopen(req, timeout=30).read())["prompt_id"]


def wait(pid, timeout=240):
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


def gen(tag, prompt, strength, seed):
    pid = queue(build(prompt, strength, seed))
    img = wait(pid)
    if not img:
        print(f"FAIL  {tag}")
        return
    dest = os.path.join(OUT_DIR, f"{tag}.png")
    fetch(img, dest)
    print(f"OK    {tag} -> {dest}")


def main():
    n = 0
    for key, prompt in SUBJECTS:
        full = f"{TRIGGER}, {prompt}"
        # base control (no trigger language influence; LoRA at 0 == effectively base)
        gen(f"base_{key}", prompt, 0.0, SEED)
        n += 1
        for s in STRENGTHS:
            gen(f"lora_{key}_s{int(s*10):02d}", full, s, SEED)
            n += 1
    print(f"DONE — {n} images in {OUT_DIR}")


if __name__ == "__main__":
    main()
