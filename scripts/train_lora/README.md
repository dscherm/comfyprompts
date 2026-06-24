# train_lora — reusable LoRA training harness

A thin, dataset-agnostic wrapper around [ostris/ai-toolkit](https://github.com/ostris/ai-toolkit)
for training Flux LoRAs on this workstation. The pipeline:

```
prep_dataset.py  ->  caption.py  ->  launch_train.py  ->  (lora_eval_grid.py)  ->  deploy
```

Point it at any folder of images and it produces a LoRA. The Berserkr-style LoRA
is just the first proof-of-concept (see `.ralph/spec.md`).

## Reusable loop — train a LoRA on ANY dataset (no code changes)

The four scripts are fully dataset-agnostic; only the paths and the trigger word
change. To train `<name>` from a folder of images in `<SRC>`:

```bash
# 1. Curate: normalize/dedupe/resize into an ai-toolkit training folder.
python scripts/train_lora/prep_dataset.py \
    --src "<SRC>" --out "E:/ai-training/datasets/<name>" \
    --max-images 150 --max-edge 1024

# 2. Caption: Florence2 over ComfyUI REST, every .txt prefixed with the trigger.
#    (ComfyUI must be running on the 3090 Ti — see hardware contract below.)
python scripts/train_lora/caption.py \
    --dir "E:/ai-training/datasets/<name>" --trigger <name>_trig

# 3. Train: generate the ai-toolkit Flux config + launch on GPU 1.
#    STOP ComfyUI first to free the 24GB (training and generation are sequential).
python scripts/train_lora/launch_train.py \
    --dataset "E:/ai-training/datasets/<name>" --name <name> --steps 1500 --rank 16

# 4. Eval: restart ComfyUI, grid base-vs-LoRA across this model's checkpoints.
#    --only filters the LoraLoader list to just this model.
python scripts/lora_eval_grid.py --only <name> --strengths 0.6 0.8 1.0 \
    --out-dir scripts/train_lora/eval/<name>-grid
# then judge the rendered cells and record a winner.

# 5. Deploy: copy the winning checkpoint to ComfyUI and write a trigger sidecar.
cp "E:/ai-training/flux-output/<name>/<name>.safetensors" \
   "D:/Projects/ComfyUI/models/loras/style/<name>.safetensors"
```

Nothing in the scripts is Berserkr-specific — the trigger word, dataset dir, and
output name are all CLI args. The Berserkr run below is just the worked example.

### Where this loop plugs in

- **`comfy-improve-model` Path 3 (train a style/character LoRA)** — this harness is
  the concrete implementation of that path. When a user asks to "improve the model"
  by training a LoRA on their own outputs/reference images, drive these four scripts.
- **Multiview-consistency for 3D** — train a LoRA on multi-angle renders of one
  subject, then generate consistent novel views to feed Hunyuan3D / the
  art-to-rig pipeline, tightening identity across the turntable used for meshing.

## Install (T1)

- **ai-toolkit repo:** `D:\Projects\ai-toolkit` (cloned with submodules)
- **Its own venv:** `D:\Projects\ai-toolkit\venv` — **Python 3.11.9**, torch
  `2.9.1+cu128`. This is a SEPARATE venv from ComfyUI's
  (`D:\Projects\ComfyUI\venv`, torch 2.9.1+cu126) — do NOT cross the two.
- Install command of record (from ai-toolkit's README):
  ```bash
  cd /d/Projects/ai-toolkit
  ./venv/Scripts/python.exe -m pip install --no-cache-dir \
      torch==2.9.1 torchvision==0.24.1 torchaudio==2.9.1 \
      --index-url https://download.pytorch.org/whl/cu128
  ./venv/Scripts/python.exe -m pip install -r requirements.txt
  ```

## Hardware contract — the 3090 Ti does both generation AND training

This is a dual-GPU box (see CLAUDE.md). The **RTX 3090 Ti (24GB)** is the primary
card for both ComfyUI generation and LoRA training; the **RTX 3070 (8GB)** is
secondary.

- **ComfyUI** runs on the 3090 Ti via `D:\Projects\ComfyUI\run_3090ti.ps1`
  (`CUDA_DEVICE_ORDER=PCI_BUS_ID` + `CUDA_VISIBLE_DEVICES=1`).
- **Training** also runs on the 3090 Ti: **every** trainer invocation is prefixed
  with `CUDA_VISIBLE_DEVICES=1`, so ai-toolkit sees only the 3090 Ti (as `cuda:0`).

Because both want the same 24GB, they run **sequentially, not concurrently**:

1. **Caption (T4)** — ComfyUI up on the 3090 Ti, Florence2 captions the dataset.
2. **Train (T6)** — **stop ComfyUI first** to free the 24GB, then launch training.
3. **Eval (T7)** — restart ComfyUI on the 3090 Ti (Flux eval is comfortable at
   24GB) and run the grid.

Verify with `nvidia-smi` that VRAM is climbing on the 3090 Ti before walking away.
System RAM is ~64GB (comfortable) — latent/text-encoder caching to disk is
optional, not forced. `launch_train.py` still caches to E: by default to keep
the dataset and activations off the nearly-full C:/D: drives.

### GPU verification

```bash
cd /d/Projects/ai-toolkit
CUDA_VISIBLE_DEVICES=1 ./venv/Scripts/python.exe -c \
  "import torch; print(torch.cuda.get_device_name(0))"
# expected: NVIDIA GeForce RTX 3090 Ti
```

_Verified 2026-06-21:_ `torch 2.9.1+cu128`, `cuda avail True`, device under
`CUDA_VISIBLE_DEVICES=1` = **NVIDIA GeForce RTX 3090 Ti** (25.8 GB). `run.py
--help` runs clean (entry point imports OK).

## Avoid the 24GB re-download

ai-toolkit defaults to pulling `black-forest-labs/FLUX.1-dev` (~24GB bf16) from
HuggingFace. This box has only ~36GB free on D: and already has
`D:\Projects\ComfyUI\models\checkpoints\flux1-dev-fp8.safetensors`. `launch_train.py`
(T5) must point the training config at the **local fp8 checkpoint**, not let
ai-toolkit download the full model.

## Status

- [x] T1 — ai-toolkit installed in own venv, GPU-1 contract verified
- [x] T2 — `prep_dataset.py` (Pillow normalize/dedupe/resize; 4 tests pass)
- [x] T3 — `caption.py` (Florence2 REST, trigger prefix, idempotent; 4 tests pass; live round-trip exercised in T4)
- [x] T4 — Berserkr dataset curated + captioned: **148 images** on `E:\ai-training\datasets\berserkr_style\` (balanced Creature/Portrait/Fullbody/Equipment/Prop; UI/tiles excluded), Florence2 captions cleaned + `brsk_style`-prefixed. Dataset lives on E: (not the repo) to avoid bloat.
- [x] T5 — `launch_train.py` (generates ai-toolkit JSON config, pins GPU 1 + E: cache; 3 tests pass, --no-launch smoke OK)
- [x] T6 — trained `berserkr_style.safetensors` (164 MB, rank-16 Flux LoRA, 1500 steps @ 512). Checkpoints at 500/750/1000/1250/1500 on `E:\ai-training\flux-output\berserkr_style\`. A transient external-GPU `cudaErrorUnknown` at step 499 was recovered by resuming from the step-500 checkpoint — the save_every=250 setting made it a non-event. Step-1500 samples show strong style transfer vs baseline.
- [x] T7 — eval grid + AI-judge verdict (`eval/berserkr_style_grid.md`). Base vs LoRA across checkpoints 1000/1250/1500 × strengths 0.6/0.8/1.0 on 2 neutral prompts (seed 123456, 512px, 12 steps). LoRA measurably shifts output toward the Berserkr painterly concept-art aesthetic (dramatic on the scene prompt). **Winner: `berserkr_style.safetensors` (ckpt 1500) @ strength 0.8** (trigger `brsk_style`; 0.6 portraits / 1.0 scenes). Driver gained a `--only` substring filter to target one model's checkpoints.
- [x] T8 — deployed winner to `D:\Projects\ComfyUI\models\loras\style\berserkr_style.safetensors` + `berserkr_style.txt` sidecar (trigger `brsk_style`, strength 0.8). Smoke-tested through `generate_image_lora` @ 768px/strength 0.8 → on-aesthetic dark-fantasy warrior (`eval/deploy_smoke_brsk_style.png`). Reusable end-to-end loop + `comfy-improve-model` Path 3 / multiview-3D cross-links documented above.
