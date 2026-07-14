"""Quadruped creature concept via ComfyUI — single sagaink STYLE LoRA (no T-pose
pose LoRA; that one is humanoid-only). One clean 3/4 full-body view for TRELLIS
(multiview corrupts). STYLE.md: grayscale ink + ONE small accent (red eyes)."""
import argparse, json, time, urllib.request, urllib.parse
from pathlib import Path

COMFY = "http://localhost:8188"
WF = Path("D:/Projects/comfyui-toolchain/workflows/mcp/generate_image_lora.json")
INPUT_DIR = Path("D:/Projects/ComfyUI/input")

CREATURES = {
    # subject phrase in the LoRA's native "a <subject> V1" caption slot
    "wolf": ("a fierce Norse dire wolf standing on all four legs, thick shaggy pelt, "
             "mouth closed, ears up, standing squarely and calmly on four straight "
             "legs in a neutral alert stance, head level, full body side profile, the "
             "whole animal in frame"),
}
POSE = ""       # the subject phrase already carries the pose
POSE_NEG = ("human, humanoid, biped, standing upright, two legs, person, rider, "
            "cropped, close-up, headshot, multiple animals, held weapon, text, "
            "watermark, busy background")


def style_block(accent):
    # EXACT sagaink trained caption structure (trigger vibrant_rpg_char). The LoRA
    # responds to this format — hand-rolled prompts blur out-of-distribution subjects.
    return (f"heavy black ink illustration, extreme high-contrast black and white, thick "
            f"aggressive ink brushstrokes, stark noir shadows, selective bold colour "
            f"accents of glowing {accent} eyes, Frank Miller Sin City graphic novel "
            f"style, Frank Frazetta dark fantasy, gritty noir atmosphere, not smooth, "
            f"not photorealistic",
            "smooth, photorealistic, photograph, 3d render, blurry, soft, low contrast, "
            "washed out, pale")


def http_json(path, payload=None):
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(COMFY + path, data,
                                 {"Content-Type": "application/json"} if data else {})
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.loads(r.read())


def build(pos, neg, seed, s_style):
    wf = json.loads(WF.read_text(encoding="utf-8-sig"))
    # single LoRA: put sagaink directly on node 2 (the workflow's LoRA loader)
    wf["2"]["inputs"].update(lora_name="vibrant_rpg_char_sagaink_v3.safetensors",
                             strength_model=s_style, strength_clip=s_style)
    wf["4"]["inputs"].update(clip=["2", 1], text=pos)
    wf["5"]["inputs"].update(clip=["2", 1], text=neg)
    wf["6"]["inputs"].update(model=["2", 0], seed=seed, steps=24, cfg=3.0,
                             sampler_name="euler", scheduler="simple", denoise=1.0)
    wf["3"]["inputs"].update(width=1024, height=768)  # landscape for a quadruped
    wf["8"]["inputs"]["filename_prefix"] = "creature_concept"
    return {k: v for k, v in wf.items() if not k.startswith("_")}


def run(wf, timeout=600):
    pid = http_json("/prompt", {"prompt": wf})["prompt_id"]
    print(f"queued {pid}", flush=True)
    deadline = time.time() + timeout
    while time.time() < deadline:
        time.sleep(2)
        hist = http_json(f"/history/{pid}")
        if pid not in hist:
            continue
        st = hist[pid].get("status", {})
        if st.get("status_str") == "error":
            raise RuntimeError(json.dumps(st)[:400])
        if st.get("completed"):
            imgs = []
            for out in hist[pid].get("outputs", {}).values():
                imgs += [i for i in out.get("images", []) if isinstance(i, dict)]
            return imgs
    raise RuntimeError("timeout")


def download(img, dst):
    qs = urllib.parse.urlencode({"filename": img["filename"],
                                 "subfolder": img.get("subfolder", ""), "type": "output"})
    with urllib.request.urlopen(f"{COMFY}/view?{qs}", timeout=120) as r:
        Path(dst).write_bytes(r.read())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--creature", default="wolf", choices=list(CREATURES))
    ap.add_argument("--accent", default="pale-red")
    ap.add_argument("--seed", type=int, default=7412)
    ap.add_argument("--s2", type=float, default=1.0)   # sagaink strength (STYLE.md: 1.0)
    ap.add_argument("--out", required=True)
    ap.add_argument("--stage", default="")
    args = ap.parse_args()

    style, style_neg = style_block(args.accent)
    # native caption: "vibrant_rpg_char, a <subject>, <trained style>, ..."
    pos = f"vibrant_rpg_char, {CREATURES[args.creature]}, {style}, plain white background"
    neg = f"{POSE_NEG}, {style_neg}"
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    imgs = run(build(pos, neg, args.seed, args.s2))
    if not imgs:
        raise SystemExit("no image")
    download(imgs[0], args.out)
    print(f"OUTPUT {args.out}", flush=True)
    if args.stage:
        download(imgs[0], str(INPUT_DIR / f"{args.stage}.png"))
        print(f"STAGED {INPUT_DIR / (args.stage + '.png')}", flush=True)


if __name__ == "__main__":
    main()
