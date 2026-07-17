---
title: Keyword-bucketed dataset labels mislabel ~30% — and it resurfaces as mode bleed
severity: medium
tags: [lora, dataset, captions, sdxl, training]
source: hand-authored
created: 2026-07-17
project: comfyui-toolchain
---

## Symptom

Two failures, one cause.

**At build time (2026-07-16, TX1):** bucketing Poly Haven textures into
material families by keyword-matching slug/tags/categories mislabeled **16 of
55 (~29%)** — tree bark filed under `wood`, plaster walls under `concrete`,
coastal rocks under `sand` and `grass`. Every mislabel would have become a
caption (`mat_tile, <family>, seamless texture, ...`) teaching the trigger the
wrong noun for the pixels.

**At inference time (2026-07-17, TX3):** the trained LoRA regressed on
`mossy cobblestone` at strength ≥0.8 — base SDXL renders grey stones with moss;
the LoRA replaced stone structure entirely with **moss islands on a flat lilac
field**. That lilac matches the `blue_plaster_wall` / `blue_floor_tiles`
dataset entries: an off-family mode dominating as strength rises.

## Root cause

Keyword matchers score on text that describes *provenance*, not *appearance*:
"bark_brown_01" contains no token distinguishing tree bark from planks, and a
coastal rock scan is tagged with both "sand" and "rock". Wrong family → wrong
caption → the trigger token is bound to a mixture. At low strength the dominant
correct modes win; as strength rises the minority off-family modes assert
themselves, which is what "bleed" looks like from the outside.

## Mitigation

1. **Hand-audit auto-derived labels against the actual images before
   captioning** — one contact sheet with family labels burned in takes a minute
   to scan and is the whole fix at build time. Correct by slug, rename files,
   rewrite the selection metadata, THEN caption.
2. **Get the user's approval on the labeled contact sheet** before training
   (perceptual-ground-truth-needs-human-signoff — training data is ground
   truth).
3. **When a LoRA regresses at high strength into an off-family look, suspect
   the dataset first**, not the sampler or the prompt: find the training
   entries whose palette/structure matches the intruding look. The lilac field
   named its own source.
4. Fix options in order of cost: cap deployment strength below the bleed
   threshold (free, TX3 shipped 0.6); drop or rebalance the offending entries
   and retrain (~45 min here); rebuild the family taxonomy if bleed is
   widespread.
5. Record per-material strength limits in the deploy sidecar/receipt so the
   next caller does not rediscover the cliff.

## Notes (optional)

The audit is cheap precisely because the *sources* are CC0 and named — the slug
is enough to correct by hand once you have seen the image. Related:
two-pass-rescue-for-constrained-generation (a different failure that also shows
up at high strength — distinguish: bleed changes the MATERIAL, the constraint
changes the COMPOSITION).
