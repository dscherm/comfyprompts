# train_lora — reusable LoRA training harness

A thin, dataset-agnostic wrapper around [ostris/ai-toolkit](https://github.com/ostris/ai-toolkit)
for training Flux LoRAs on this workstation. The pipeline:

```
prep_dataset.py  ->  caption.py  ->  launch_train.py  ->  (lora_eval_grid.py)  ->  deploy
```

Point it at any folder of images and it produces a LoRA. The Berserkr-style LoRA
is just the first proof-of-concept (see `.ralph/spec.md`).

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

## Hardware contract — ALWAYS train on GPU 1

This is a dual-GPU box (see CLAUDE.md):

- **GPU 0** — RTX 3070, 8GB — ComfyUI's card. Leave it alone during training.
- **GPU 1** — RTX 3090 Ti, 24GB — the training card.

**Every** trainer invocation must be prefixed with `CUDA_VISIBLE_DEVICES=1` so
ai-toolkit only ever sees the 3090 Ti (which then appears to it as `cuda:0`).
Verify with `nvidia-smi` that VRAM is climbing on device 1, not device 0, before
walking away. 16GB system RAM is the tighter constraint — cache latents and
text-encoder outputs to disk in the training config.

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
- [ ] T2 — `prep_dataset.py`
- [ ] T3 — `caption.py`
- [ ] T4 — curate Berserkr dataset
- [ ] T5 — `launch_train.py`
- [ ] T6 — run PoC training
- [ ] T7 — eval grid
- [ ] T8 — deploy + finalize this README
