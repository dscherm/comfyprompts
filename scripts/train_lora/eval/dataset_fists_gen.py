"""dataset_fists_gen — regenerate a LoRA's training characters with EMPTY CLOSED
FISTS and no weapons, from their own captions.

Reads a dataset dir's caption .txt files (each already carries the LoRA trigger +
style), dedupes to unique characters, appends a strong closed-fist / no-weapon
clause, and regenerates one clean version per character with the given LoRA. The
caption owns the trigger + style, so this works for any character LoRA (sagaink
grayscale-ink, soapbox full-color, ...). Closed fists in the positive; claws /
spread fingers / fake signatures in the negative (project_mv_ortho_fists).

ComfyUI HTTP (3090 Ti), stdlib urllib only. ComfyUI must be UP.

  python dataset_fists_gen.py --dataset E:/ai-training/datasets/vibrant_rpg_char_sagaink \
      --lora vibrant_rpg_char_sagaink_v3.safetensors [--limit 3] [--size 1024]
  python dataset_fists_gen.py --dataset E:/ai-training/datasets/soapbox_char_final_v1 \
      --lora "style\\soapbox_char_final_v1.safetensors"
"""
from __future__ import annotations

import argparse
import json
import time
import urllib.error
import urllib.request
from pathlib import Path

COMFY = "http://localhost:8188"
WF = json.loads((Path(__file__).resolve().parents[3] / "workflows" / "mcp"
                 / "generate_image_lora.json").read_text())

FISTS = ("both arms hanging straight down at the sides, both hands tightly clenched "
         "into closed fists, human-like fists, fingers fully curled into the palm, "
         "knuckles facing forward, holding nothing, no weapon")
NEG = ("weapon, sword, axe, staff, spear, shield, holding an object, claws, talons, "
       "clawed hands, long fingers, spread fingers, splayed fingers, open hands, "
       "pointing finger, extra fingers, extra thumb, signature, artist name, logo, "
       "watermark, text, blurry, low quality")


def unique_chars(dataset: Path) -> list[tuple[str, str]]:
    """Dedupe caption files by content → [(output_stem, caption), ...] in file order."""
    seen: dict[str, str] = {}
    for t in sorted(dataset.glob("*.txt")):
        cap = t.read_text(encoding="utf-8").strip()
        if cap and cap not in seen:
            seen[cap] = t.stem
    return [(stem, cap) for cap, stem in seen.items()]


def build(lora: str, pos: str, seed: int, size: int) -> dict:
    wf = json.loads(json.dumps(WF))
    wf["2"]["inputs"].update(lora_name=lora, strength_model=1.0, strength_clip=1.0)
    wf["3"]["inputs"].update(width=size, height=size)
    wf["4"]["inputs"]["text"] = pos
    wf["5"]["inputs"]["text"] = NEG
    wf["6"]["inputs"].update(seed=seed, steps=24, cfg=1.0, sampler_name="euler",
                             scheduler="beta", denoise=1.0)
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
    ap.add_argument("--lora", required=True, help="LoRA name as ComfyUI lists it.")
    ap.add_argument("--out", default=None, help="default E:/ai-training/_raw/<name>_fists")
    ap.add_argument("--size", type=int, default=1024)
    ap.add_argument("--start-seed", type=int, default=51715)
    ap.add_argument("--limit", type=int, default=0, help="first N unique chars (0=all).")
    a = ap.parse_args()

    chars = unique_chars(a.dataset)
    if a.limit:
        chars = chars[:a.limit]
    out = Path(a.out) if a.out else Path("E:/ai-training/_raw") / f"{a.dataset.name}_fists"

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
        pos = f"{cap}, {FISTS}"
        pid = queue(build(a.lora, pos, a.start_seed + i * 101, a.size))
        img = wait(pid)
        if not img:
            print(f"  [{i + 1}/{len(chars)}] FAIL {stem}")
            continue
        fetch(img, dest)
        ok += 1
        print(f"  [{i + 1}/{len(chars)}] OK {stem}", flush=True)
    print(f"DONE: {ok}/{len(chars)} -> {out}  (LoRA {a.lora})")
    return 0 if ok == len(chars) else 1


if __name__ == "__main__":
    raise SystemExit(main())
