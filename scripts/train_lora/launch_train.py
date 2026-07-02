"""launch_train — generate an ai-toolkit Flux-LoRA config and launch it on GPU 1.

Stage 3 of the train_lora harness (see scripts/train_lora/README.md). Builds an
ai-toolkit JSON config (which it accepts alongside YAML) from CLI args, then runs
ai-toolkit's run.py in the ai-toolkit venv with the GPU/cache environment pinned:

    CUDA_VISIBLE_DEVICES=1   -> only the 3090 Ti is visible (appears as cuda:0)
    CUDA_DEVICE_ORDER=PCI_BUS_ID
    HF_HUB_CACHE=E:\\ai-training\\hf-cache  -> finds the pre-downloaded FLUX.1-dev

Dataset-agnostic: point --dataset at any captioned folder. To run the actual
(long) training, invoke this script itself in the background. Use --no-launch to
just generate/inspect the config (no GPU needed).

Stdlib only.

Usage:
    python scripts/train_lora/launch_train.py \\
        --dataset scripts/train_lora/datasets/berserkr_style \\
        --name berserkr_style --trigger brsk_style
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

# Defaults tuned for the 3090 Ti (24GB) — see CLAUDE.md GPU section.
AITK_DIR = Path(os.environ.get("AITK_DIR", r"D:\Projects\ai-toolkit"))
DEFAULT_OUTPUT = r"E:\ai-training\flux-output"
DEFAULT_HF_CACHE = r"E:\ai-training\hf-cache"
DEFAULT_BASE = "black-forest-labs/FLUX.1-dev"

# Generic, trigger-anchored sample prompts so progress images show the style on
# varied subjects. [trigger] is substituted by ai-toolkit with the trigger word.
DEFAULT_SAMPLE_PROMPTS = [
    "[trigger], a lone warrior standing on a cliff at dawn",
    "[trigger], a fierce horned beast in a snowy forest",
    "[trigger], an ornate battle axe resting on a stone altar",
    "[trigger], a ruined longhouse under a stormy sky",
]


def build_config(
    *,
    dataset: str,
    name: str,
    trigger: str,
    steps: int,
    rank: int,
    resolutions: list[int],
    output: str,
    base: str,
    device: str = "cuda:0",
    sample_prompts: list[str] | None = None,
    lr: float = 1e-4,
) -> dict:
    """Return an ai-toolkit config dict for a Flux LoRA. device is 'cuda:0'
    because CUDA_VISIBLE_DEVICES hides every card but the target one."""
    return {
        "job": "extension",
        "config": {
            "name": name,
            "process": [
                {
                    "type": "sd_trainer",
                    "training_folder": output,
                    "device": device,
                    "trigger_word": trigger,
                    "network": {"type": "lora", "linear": rank, "linear_alpha": rank},
                    "save": {
                        "dtype": "float16",
                        "save_every": 250,
                        "max_step_saves_to_keep": 4,
                        "push_to_hub": False,
                    },
                    "datasets": [
                        {
                            "folder_path": str(Path(dataset).resolve()),
                            "caption_ext": "txt",
                            "caption_dropout_rate": 0.05,
                            "shuffle_tokens": False,
                            "cache_latents_to_disk": True,
                            "resolution": resolutions,
                        }
                    ],
                    "train": {
                        "batch_size": 1,
                        "steps": steps,
                        "gradient_accumulation_steps": 1,
                        "train_unet": True,
                        "train_text_encoder": False,
                        "gradient_checkpointing": True,
                        "noise_scheduler": "flowmatch",
                        "optimizer": "adamw8bit",
                        "lr": lr,
                        "ema_config": {"use_ema": True, "ema_decay": 0.99},
                        "dtype": "bf16",
                    },
                    "model": {
                        "name_or_path": base,
                        "is_flux": True,
                        "quantize": True,
                    },
                    "sample": {
                        "sampler": "flowmatch",
                        "sample_every": 250,
                        "width": 1024,
                        "height": 1024,
                        "prompts": sample_prompts or DEFAULT_SAMPLE_PROMPTS,
                        "neg": "",
                        "seed": 42,
                        "walk_seed": True,
                        "guidance_scale": 4,
                        "sample_steps": 20,
                    },
                }
            ],
        },
        "meta": {"name": name, "version": "1.0"},
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Generate + launch an ai-toolkit Flux LoRA train.")
    ap.add_argument("--dataset", required=True, help="Captioned training folder.")
    ap.add_argument("--name", default="berserkr_style", help="LoRA/config name.")
    ap.add_argument("--trigger", default="brsk_style", help="Trigger word.")
    ap.add_argument("--steps", type=int, default=1500)
    ap.add_argument("--rank", type=int, default=16)
    ap.add_argument("--resolutions", default="512,768,1024",
                    help="Comma-separated training resolutions.")
    ap.add_argument("--output", default=DEFAULT_OUTPUT, help="ai-toolkit training_folder.")
    ap.add_argument("--base", default=DEFAULT_BASE, help="Base model (HF repo id or local path).")
    ap.add_argument("--hf-cache", default=DEFAULT_HF_CACHE, help="HF_HUB_CACHE for the base model.")
    ap.add_argument("--cuda-device", default="1", help="Physical GPU index (PCI order). 1 = 3090 Ti.")
    ap.add_argument("--sample-prompts", default=None,
                    help="Semicolon-separated in-training sample prompts (use [trigger]). "
                         "Pass DOMAIN-appropriate prompts for non-fantasy LoRAs — the default "
                         "prompts are GrimForge/fantasy and mislead progress previews otherwise.")
    ap.add_argument("--config-out", default=None,
                    help="Where to write the config json (default scripts/train_lora/configs/<name>.json).")
    ap.add_argument("--no-launch", action="store_true",
                    help="Only write the config; do not start training (no GPU needed).")
    args = ap.parse_args(argv)

    ds = Path(args.dataset)
    if not ds.is_dir():
        ap.error(f"--dataset is not a directory: {ds}")
    resolutions = [int(r) for r in args.resolutions.split(",")]

    sample_prompts = None
    if args.sample_prompts:
        sample_prompts = [p.strip() for p in args.sample_prompts.split(";") if p.strip()]

    cfg = build_config(
        dataset=args.dataset, name=args.name, trigger=args.trigger, steps=args.steps,
        rank=args.rank, resolutions=resolutions, output=args.output, base=args.base,
        sample_prompts=sample_prompts,
    )

    cfg_path = Path(args.config_out) if args.config_out else (
        Path(__file__).resolve().parent / "configs" / f"{args.name}.json")
    cfg_path.parent.mkdir(parents=True, exist_ok=True)
    cfg_path.write_text(json.dumps(cfg, indent=2), encoding="utf-8")
    print(f"config  -> {cfg_path}")

    run_py = AITK_DIR / "run.py"
    py = AITK_DIR / "venv" / "Scripts" / "python.exe"
    env = {
        **os.environ,
        "CUDA_VISIBLE_DEVICES": args.cuda_device,
        "CUDA_DEVICE_ORDER": "PCI_BUS_ID",
        "HF_HUB_CACHE": args.hf_cache,
    }
    cmd = [str(py), str(run_py), str(cfg_path)]
    print(f"command -> CUDA_VISIBLE_DEVICES={args.cuda_device} {' '.join(cmd)}")

    if args.no_launch:
        print("(--no-launch) config written; not starting training.")
        return 0

    if not py.exists():
        ap.error(f"ai-toolkit venv python not found: {py} (set AITK_DIR?)")
    print("Launching training on GPU 1 (3090 Ti). Verify with: nvidia-smi  (VRAM should climb on the 3090 Ti)")
    proc = subprocess.run(cmd, env=env, cwd=str(AITK_DIR))
    return proc.returncode


if __name__ == "__main__":
    sys.exit(main())
