# Stage 2 — TRAIN-A (FLUX style LoRA on the clay set) · GPU-GATED

**Goal:** train the Approach-A style LoRA on the **clay halves** of the dataset so
img2img can repaint any drawing into the clay look.

## ⚠️ GPU gate
Training and generation share the 3090 Ti and run SEQUENTIALLY. **Do not start
until the human confirms the GPU is free.** Then: stop ComfyUI (free 24 GB) and
`ollama stop`; train; restart ComfyUI via `run_3090ti.ps1` after.

## Do

1. Point the trainer at the **clay** dir only:
   `E:/ai-training/datasets/ink_to_clay_v1/clay/` (flat dir — subfolders deadlock
   ai-toolkit latent caching; see project_aitk_training_gotchas).
2. Caption minimally/consistently with the trigger `clay3d` (the clean framing is
   implicit in the consistent set — do not over-caption).
3. Train via `scripts/train_lora/launch_train.py` (ai-toolkit, FLUX dev):
   rank 24 (16–32 ok), LR 1e-4, ~2000 steps (1500–3000), 1024px, save every 250,
   `CUDA_VISIBLE_DEVICES=1`. Use a **fresh** output name
   `E:/ai-training/flux-output/ink_to_clay_v1_a` (reused folders resume + exit
   in ~7 min without training).
4. Collect checkpoints; note which steps to eval in Stage 3.

## Output artifacts
- `E:/ai-training/flux-output/ink_to_clay_v1_a/*.safetensors` (checkpoints)
- training config + step log recorded in stage `2-train-a`.

→ Gate: `gates/gate-02-train-a.md`.
