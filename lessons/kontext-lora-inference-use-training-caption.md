---
title: Drive a trained Kontext-edit LoRA with its EXACT short training caption, not a long descriptive instruction
severity: medium
tags: [flux, kontext, lora, image-edit, inference, ink-to-clay, technique]
source: hand-authored
created: 2026-07-25
project: comfyui-toolchain
---

## Symptom

The trained ink→clay Kontext-edit LoRA (`ink_to_clay_v1_b`) transforms faithfully
when driven by the short instruction it was trained on
(`"convert to a clean 3d clay render, plain neutral-grey background"`), but
faithfulness degrades when fed the long, descriptive instruction that was tuned
for the BASE model (the multi-clause "clean smooth matte 3D clay render… soft
even studio lighting, no cast shadow…" prompt).

## Root cause

A paired-edit LoRA learns the mapping conditioned on ONE fixed caption seen at
every training step. At inference the caption is not a free-text prompt to
elaborate — it is the key that selects the learned transform. A different
(longer, differently-worded) instruction pushes the conditioning off the
distribution the LoRA was fit to, so the mapping weakens even though the words
mean the same thing to a human. The long instruction only helps the BASE model,
which has no learned mapping and genuinely needs the extra descriptive cues.

## Mitigation

1. **Match the inference instruction to the training caption verbatim.** In
   `infer_kontext.py`, LoRA mode defaults to `LORA_INSTRUCTION` (the exact short
   training caption); the long `DEFAULT_INSTRUCTION` is reserved for `--base`.
2. **General rule for any edit-LoRA:** store the training caption alongside the
   LoRA and use it as the inference default — don't let a caller pass a "nicer"
   longer prompt and assume it's an upgrade. Expose an override, but default to
   the trained caption.
3. If you WANT prompt flexibility at inference, that's a training-data decision:
   vary the caption during training. A fixed-caption LoRA is a fixed-caption
   tool. Related: [[kontext-for-faithful-image-edit]] (train the paired-edit LoRA
   in the first place).
