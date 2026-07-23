"""infer_kontext — Approach-B inference for ink-to-clay-ralph (stage 5).

Converts an ink/comic drawing into a clean 3D-clay render via FLUX.1-Kontext, the
single-pass instruction editor. Two modes:

- DEFAULT (trained LoRA): applies the pipeline's trained Kontext-edit LoRA
  (ink_to_clay_v1_b, stage 4) through the proper Kontext reference-latent graph
  (UNET -> LoraLoaderModelOnly -> FluxKontextImageScale -> ReferenceLatent). This
  is the faithful transform, verified on held-out drawings.
- --base: the zero-shot base-model baseline (no LoRA) via the shipped
  edit_image_kontext.json img2img graph — the bar the LoRA must beat.

Drives ComfyUI over HTTP. ComfyUI must be UP on the 3090 Ti; generation only.

Usage:
  python infer_kontext.py <ink.png> <out.png>                       # trained LoRA (default)
  python infer_kontext.py <ink.png> <out.png> --base --denoise 0.85 # base baseline
  python infer_kontext.py <ink.png> <out.png> --lora-strength 0.9 --guidance 2.5
"""
import argparse
import json
import shutil
import sys
from pathlib import Path

# reuse the berserkr _work ComfyUI helpers (run/download/INPUT_DIR/COMFY)
sys.path.insert(0, str(Path("D:/Projects/comfyui-toolchain/products/berserkr_v2_chars_v1/_work")))
import gen_concept_v2 as g

WF = Path("D:/Projects/comfyui-toolchain/workflows/mcp/edit_image_kontext.json")

# The pipeline's canonical ink->clay instruction (pipeline-state.json:kontext_instruction),
# expanded with the clay target cues from the PRD (matte, soft even light, no ground/shadow).
DEFAULT_INSTRUCTION = (
    "Convert this drawing into a clean smooth matte 3D clay render of the exact same character. "
    "Keep the same design, pose, and proportions. Plain flat neutral-grey background, soft even "
    "studio lighting, no cast shadow, no ground plane, the whole subject in frame, clear silhouette."
)
DEFAULT_NEG = ("cast shadow, drop shadow, ground shadow, floor, ground plane, pedestal, base, "
               "reflection, heavy black ink, bold outlines, comic linework, flat 2d, cropped, "
               "close-up, text, watermark, extra limbs, deformed")

# Trained LoRA (default mode). It learned the SHORT fixed instruction it was trained
# on — use that, not the long baseline instruction, for the faithful mapping.
DEFAULT_LORA = "style\\ink_to_clay_v1_b.safetensors"
LORA_INSTRUCTION = "convert to a clean 3d clay render, plain neutral-grey background"
KONTEXT_UNET = "flux1-dev-kontext_fp8_scaled.safetensors"
KONTEXT_CLIP = ("t5xxl_fp8_e4m3fn_scaled.safetensors", "clip_l.safetensors")
KONTEXT_VAE = "ae.safetensors"


def build_lora(image_name, instruction, lora, strength, guidance, seed, steps):
    """Proper FLUX Kontext + LoRA reference-latent graph (validated on held-out inks).
    Single-pass edit: the ink is the reference; instruction drives the clay conversion."""
    return {
        "1": {"inputs": {"unet_name": KONTEXT_UNET, "weight_dtype": "default"},
              "class_type": "UNETLoader"},
        "2": {"inputs": {"lora_name": lora, "strength_model": strength, "model": ["1", 0]},
              "class_type": "LoraLoaderModelOnly"},
        "3": {"inputs": {"clip_name1": KONTEXT_CLIP[0], "clip_name2": KONTEXT_CLIP[1],
                         "type": "flux"}, "class_type": "DualCLIPLoader"},
        "4": {"inputs": {"vae_name": KONTEXT_VAE}, "class_type": "VAELoader"},
        "5": {"inputs": {"text": instruction, "clip": ["3", 0]}, "class_type": "CLIPTextEncode"},
        "6": {"inputs": {"conditioning": ["5", 0], "guidance": guidance},
              "class_type": "FluxGuidance"},
        "10": {"inputs": {"image": image_name, "upload": "image"}, "class_type": "LoadImage"},
        "11": {"inputs": {"image": ["10", 0]}, "class_type": "FluxKontextImageScale"},
        "12": {"inputs": {"pixels": ["11", 0], "vae": ["4", 0]}, "class_type": "VAEEncode"},
        "13": {"inputs": {"conditioning": ["6", 0], "latent": ["12", 0]},
               "class_type": "ReferenceLatent"},
        "14": {"inputs": {"conditioning": ["5", 0]}, "class_type": "ConditioningZeroOut"},
        "8": {"inputs": {"seed": seed, "steps": steps, "cfg": 1.0, "sampler_name": "euler",
                         "scheduler": "simple", "denoise": 1.0, "model": ["2", 0],
                         "positive": ["13", 0], "negative": ["14", 0], "latent_image": ["12", 0]},
              "class_type": "KSampler"},
        "9": {"inputs": {"samples": ["8", 0], "vae": ["4", 0]}, "class_type": "VAEDecode"},
        "15": {"inputs": {"filename_prefix": "ink2clay_kontext_lora", "images": ["9", 0]},
               "class_type": "SaveImage"},
    }


def build(image_name, instruction, neg, seed, steps, cfg, sampler, scheduler, denoise):
    wf = json.loads(WF.read_text(encoding="utf-8-sig"))
    wf["4"]["inputs"]["image"] = image_name
    wf["6"]["inputs"]["text"] = instruction
    wf["7"]["inputs"]["text"] = neg
    wf["8"]["inputs"].update(seed=seed, steps=steps, cfg=cfg,
                             sampler_name=sampler, scheduler=scheduler, denoise=denoise)
    wf["10"]["inputs"]["filename_prefix"] = "ink2clay_kontext"
    return {k: v for k, v in wf.items() if not k.startswith("_")}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("ink")
    ap.add_argument("out")
    ap.add_argument("--instruction", default=None, help="override the edit instruction")
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--steps", type=int, default=25)
    ap.add_argument("--base", action="store_true",
                    help="use the base-model baseline (no LoRA) instead of the trained LoRA")
    ap.add_argument("--lora", default=DEFAULT_LORA, help="Kontext-edit LoRA (default mode)")
    ap.add_argument("--lora-strength", type=float, default=1.0)
    ap.add_argument("--guidance", type=float, default=2.5, help="FluxGuidance (LoRA mode)")
    # base-mode-only img2img knobs
    ap.add_argument("--neg", default=DEFAULT_NEG)
    ap.add_argument("--cfg", type=float, default=3.5)
    ap.add_argument("--sampler", default="euler")
    ap.add_argument("--scheduler", default="simple")
    ap.add_argument("--denoise", type=float, default=0.85)
    args = ap.parse_args()

    ink = Path(args.ink)
    if not ink.exists():
        print("MISSING", ink); sys.exit(1)
    # LoadImage reads from ComfyUI/input — stage the ink there with a stable name.
    staged = "ink2clay_src_" + ink.stem + ink.suffix
    shutil.copyfile(ink, g.INPUT_DIR / staged)

    if args.base:
        instr = args.instruction or DEFAULT_INSTRUCTION
        print(f"[kontext:base] {ink.name} denoise={args.denoise} seed={args.seed} ...", flush=True)
        wf = build(staged, instr, args.neg, args.seed, args.steps,
                   args.cfg, args.sampler, args.scheduler, args.denoise)
    else:
        instr = args.instruction or LORA_INSTRUCTION
        print(f"[kontext:lora] {ink.name} lora={args.lora} strength={args.lora_strength} "
              f"guidance={args.guidance} seed={args.seed} ...", flush=True)
        wf = build_lora(staged, instr, args.lora, args.lora_strength, args.guidance,
                        args.seed, args.steps)
    imgs = g.run(wf)
    if imgs:
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        g.download(imgs[0], str(out))
        print(f"[kontext] OK -> {out}", flush=True)
    else:
        print("[kontext] FAILED (no image)"); sys.exit(2)


if __name__ == "__main__":
    main()
