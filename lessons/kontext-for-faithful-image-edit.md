---
title: For a faithful image→image transform, train a FLUX.1 Kontext paired-edit LoRA — a style LoRA + img2img cannot
severity: medium
tags: [flux, kontext, lora, img2img, image-edit, ink-to-clay, training, technique]
source: hand-authored
created: 2026-07-20
project: comfyui-toolchain
---

## Symptom

Goal: convert an arbitrary drawing to a clean "clay" 3D-render, keeping the
subject/pose. **Approach A** (a Flux style LoRA applied via img2img) failed the
faithfulness test at every denoise: at ~0.6 it kept the input ink (barely
converted); at ~0.75-0.85 it converted but **drifted the design** (added/changed
gear, recolored); at ~0.95 it collapsed to a blob. No denoise both preserved the
specific drawing AND applied the target style.

## Root cause

A style LoRA only knows the *target look*, and img2img's single denoise dial
trades "how much of the source survives" against "how much new style is imposed"
— you cannot get both from one knob. The transform (input→output mapping) is
never learned, only a style is overlaid.

## Mitigation

1. **Train a FLUX.1-Kontext-dev paired-EDIT LoRA** on aligned pairs:
   `control_path` = the input images (ink), `folder_path` = the target images
   (clay) with a **fixed edit-instruction caption** (e.g. "convert to a clean 3d
   clay render, plain neutral-grey background"). ai-toolkit's
   `train_lora_flux_kontext_24gb.yaml` is the template; `arch: flux_kontext`,
   rank 16, res [512,768] (1024 OOMs at 24GB), ~2000 steps.
2. **Inference is single-pass, no denoise knob** — it learns the actual mapping.
   Verified on ink→clay: faithful on training subjects AND held-out drawings in
   an *unseen ink style* (kept character + pose, clean grey clay), where the
   style-LoRA+img2img route ([[img2img-clay-identity-vs-denoise]]) drifted.
3. **When you need faithful, don't reach for img2img** — reach for Kontext (or an
   analogous edit model). Cost: a gated ~24GB base download
   ([[hf-transfer-for-large-gated-downloads]]) + a paired dataset. Keep the style
   LoRA only for text2img generation of the target look.
