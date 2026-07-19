# Stage 4 — TRAIN-B (FLUX.1 Kontext paired-edit LoRA) · GPU-GATED

**Goal:** train the faithful, single-pass ink→clay edit LoRA on the aligned pairs.
This is the real prize — a learned mapping, not a style overlay.

## ⚠️ GPU gate
Same rule as Stage 2: **human GPU-free confirmation required**; stop ComfyUI +
`ollama stop`, train, restart after.

## Do

1. Assemble the Kontext training set from the aligned pairs:
   `(input = ink/<id>.png, target = clay/<id>.png)` with the fixed edit
   instruction `convert to a clean 3D clay render, plain grey background`.
2. Train a **FLUX.1 Kontext [dev]** edit LoRA (ai-toolkit Kontext mode): rank
   16–32, LR 1e-4, 1500–3000 steps, 1024px, save every 250, `CUDA_VISIBLE_DEVICES=1`.
   Fresh output `E:/ai-training/flux-output/ink_to_clay_v1_b`.
3. If ai-toolkit's Kontext path needs a manifest/format different from the FLUX
   dev path, write the config explicitly (do not assume launch_train.py covers
   Kontext — verify, extend if needed).

## Output artifacts
- `E:/ai-training/flux-output/ink_to_clay_v1_b/*.safetensors`
- Kontext training config recorded in stage `4-train-b`.

→ Gate: `gates/gate-04-train-b.md`.
