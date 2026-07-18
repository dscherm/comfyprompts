---
title: Caption named assets from their filenames, not a vision model
severity: low
tags: [dataset, captions, lora, gpu, florence2, determinism]
source: hand-authored
created: 2026-07-17
project: comfyui-toolchain
---

## Symptom

The train_lora captioner (`caption.py`) runs Florence-2 via ComfyUI — which loads
the 3090 Ti. For the lowpoly_flat dataset (SL5) that was both unavailable (a "no
3090 Ti" constraint was in force) and unnecessary: the subjects were named kit
meshes (`anvil.glb`, `guard_tower.glb`, `wizard_staff.glb`) rendered at known
angles.

## Root cause

Vision captioning is the right tool only when the image content is *unknown*
(photos, generated art). For a render of a mesh you own, the subject is already
encoded in the mesh filename and the view in the render's `__<view>` suffix — a
VLM would (at best) re-derive that, and can hallucinate objects/scene detail on a
plain flat-shaded prop.

## Mitigation

1. **When the asset filename already names the subject, derive the caption from it**
   instead of running a vision model:
   `f"{trigger}, {subject}, low-poly, flat shading, {view_phrase}, neutral background, even lighting"`
   where `subject = stem.replace('_',' ')` and `view_phrase` comes from the
   `render_multiview.py` `__<view>` suffix.
2. This is **deterministic, IP-clean, and dependency-free** — no ComfyUI, no GPU,
   no Florence-2 hallucinations — the same short-tag discipline the tile LoRAs use.
3. Reserve Florence-2 (`caption.py`) for datasets whose image content is genuinely
   unknown. For named renders/kits, filename-derived tags are both cheaper and more
   accurate.
