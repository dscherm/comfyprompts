"""sl8_gen_sword_concepts — Flux concepts for clean low-poly swords (Task SL8).

Stage 1 of the SL8 sword regen: generate clean low-poly sword concept images to
feed image->3D (TRELLIS/Hunyuan3D). The arsenal sword/greatsword share one blade
mesh whose baked dark-fuller stripe + spade tip read as a split blade; SL8
replaces them with cleaner meshes. This produces the concept art; a person picks
the best before the (uncertain, thin-blade) 3D step.

Flux1-dev-fp8 via ComfyUI (3090 Ti). Stdlib urllib only.

Usage:
  python scripts/train_lora/sl8_gen_sword_concepts.py [--size 1024] [--out <dir>]
"""
from __future__ import annotations
import argparse, json, shutil, time, urllib.request
from pathlib import Path

COMFY = "http://127.0.0.1:8188"
COMFY_OUT = Path("D:/Projects/ComfyUI/output")
NEG = ("blurry, low quality, multiple objects, busy or cluttered background, text, "
       "watermark, ornate engraving, fuller groove, blood groove, split blade, "
       "two-tone blade, dark stripe down the blade, photograph, realistic metal")

# Clean, simple, low-poly game swords — solid flat colours, clean tapering blade,
# NO fuller (the exact defect we're replacing), plain background, front view.
SWORDS = {
    "arming_sword": "low-poly 3D game asset, a single arming sword, straight double-edged blade "
        "tapering smoothly to a clean sharp point, simple straight crossguard, wrapped leather grip, "
        "round pommel, solid flat matte colors, steel-grey blade with NO groove, brown grip, "
        "centered single object, plain white background, orthographic front view",
    "broadsword": "low-poly 3D game asset, a single broad medieval sword, wide straight blade "
        "tapering to a clean point, thick simple crossguard, wrapped grip, heavy pommel, solid flat "
        "matte colors, clean uniform steel-grey blade, centered single object, plain white background, "
        "orthographic front view",
    "saber": "low-poly 3D game asset, a single curved saber, smoothly curved single-edged blade with a "
        "clean point, simple guard, wrapped grip, solid flat matte colors, uniform steel-grey blade, "
        "centered single object, plain white background, orthographic front view",
    "dagger": "low-poly 3D game asset, a single dagger, short straight blade tapering to a clean point, "
        "small crossguard, wrapped grip, small pommel, solid flat matte colors, uniform steel-grey blade "
        "with NO groove, centered single object, plain white background, orthographic front view",
}


def workflow(prompt: str, seed: int, prefix: str, size: int) -> dict:
    return {
        "1": {"inputs": {"ckpt_name": "flux1-dev-fp8.safetensors"}, "class_type": "CheckpointLoaderSimple"},
        "2": {"inputs": {"width": size, "height": size, "batch_size": 1}, "class_type": "EmptySD3LatentImage"},
        "3": {"inputs": {"text": prompt, "clip": ["1", 1]}, "class_type": "CLIPTextEncode"},
        "4": {"inputs": {"text": NEG, "clip": ["1", 1]}, "class_type": "CLIPTextEncode"},
        "5": {"inputs": {"seed": seed, "steps": 28, "cfg": 1.0, "sampler_name": "euler",
                         "scheduler": "simple", "denoise": 1.0, "model": ["1", 0],
                         "positive": ["3", 0], "negative": ["4", 0], "latent_image": ["2", 0]},
              "class_type": "KSampler"},
        "6": {"inputs": {"samples": ["5", 0], "vae": ["1", 2]}, "class_type": "VAEDecode"},
        "7": {"inputs": {"filename_prefix": prefix, "images": ["6", 0]}, "class_type": "SaveImage"},
    }


def _post(path: str, payload: dict) -> dict:
    req = urllib.request.Request(COMFY + path, json.dumps(payload).encode(),
                                 {"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read())


def _get(path: str) -> dict:
    with urllib.request.urlopen(COMFY + path, timeout=60) as r:
        return json.loads(r.read())


def generate(name: str, prompt: str, seed: int, out: Path, size: int) -> Path | None:
    pid = _post("/prompt", {"prompt": workflow(prompt, seed, f"sl8_{name}", size)})["prompt_id"]
    print(f"  {name}: queued {pid}", flush=True)
    for _ in range(120):  # up to ~10 min (offload is slow at 1024)
        time.sleep(5)
        hist = _get(f"/history/{pid}")
        if pid in hist:
            outs = hist[pid].get("outputs", {})
            for node in outs.values():
                for img in node.get("images", []):
                    src = COMFY_OUT / img.get("subfolder", "") / img["filename"]
                    dst = out / f"{name}.png"
                    shutil.copy2(src, dst)
                    print(f"  {name}: -> {dst}", flush=True)
                    return dst
            print(f"  {name}: FINISHED but no image", flush=True)
            return None
    print(f"  {name}: TIMEOUT", flush=True)
    return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--size", type=int, default=1024)
    ap.add_argument("--out", default="E:/ai-training/_raw/lowpoly_flat_swords/concepts")
    ap.add_argument("--seed", type=int, default=7)
    args = ap.parse_args()
    out = Path(args.out); out.mkdir(parents=True, exist_ok=True)
    got = []
    for i, (name, prompt) in enumerate(SWORDS.items()):
        p = generate(name, prompt, args.seed + i * 101, out, args.size)
        if p:
            got.append(p)
    print(f"DONE: {len(got)}/{len(SWORDS)} concepts -> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
