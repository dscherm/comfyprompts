---
title: Commercial AI-3D tool outputs (Tripo) are a benchmark, not training data — ToS forbids distillation
severity: medium
tags: [licensing, strategy, tripo, 3d, business]
source: hand-authored
created: 2026-06-30
project: comfyui-toolchain
---

## Symptom

Tempting to use a cloud AI-3D service's clean rigged/textured outputs (Tripo,
Meshy, Rodin) to "bootstrap our own model" so we eventually don't need the
service, or to ship its assets in a product.

## Root cause

Two separate constraints people conflate. (1) Most such services' ToS prohibit
using outputs "to create models OR services that directly compete" — i.e. you may
NOT use the meshes/rigs as TRAINING DATA for a competing model. Tripo's terms
state exactly this (verified). (2) Commercial SHIPPING of the outputs often
requires a paid tier (Tripo free tier = personal/non-commercial only). Separately,
training your own image-to-3D/rigging foundation model is infeasible at small
scale anyway (data + compute) and underperforms free open models.

## Mitigation

1. Use the tool's output as a **private quality BENCHMARK**: tune your OWN local
   open tools' parameters/process (Hunyuan3D settings, retopo, rig config, the art
   LoRA prompt) by comparison. Tuning knobs by eyeballing the gap is NOT
   distillation. Never put the outputs into a training set.
2. Build the OWNED pipeline from local open tools (Hunyuan3D/TRELLIS + a free
   rigger like AccuRIG/UniRig) and keep training only where it's the moat and is
   cheap: the 2D art LoRA, trained on YOUR OWN rendered/sourced art — never the
   tool's output.
3. If shipping the tool's assets, use the paid/commercial tier and read the
   license. If selling tools/assets (not a competing pipeline-service), the
   "compete" clause does not apply to you.

## Notes (optional)

Cleanest of all: benchmark against OPEN references (Mixamo / AccuRIG / CMU / open
assets) instead of the paid tool, to avoid the "compete" clause entirely. Related:
project memory project_tripo_strategy.
