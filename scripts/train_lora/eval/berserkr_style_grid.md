# T7 — Berserkr-style LoRA eval grid + judge verdict

**Date:** 2026-06-23
**LoRA:** `berserkr_style` (rank-16 Flux LoRA, trained T6 — 1500 steps @ 512px)
**Trigger word:** `brsk_style`
**Base model:** `flux1-dev-fp8`
**Driver:** `scripts/lora_eval_grid.py --only berserkr --strengths 0.6 0.8 1.0`
**Raw artifacts:** `scripts/train_lora/eval/grid-run/` (`results.json`, `report.md`)
**Render settings:** fixed seed 123456, 512×512, 12 steps, euler/simple, CFG 1.0 — identical across every cell, so any visual delta is attributable to the LoRA, not sampling noise.

## Grid

20 cells = 2 prompts × (1 base + **3 checkpoints** × **3 strengths**).

Checkpoints evaluated (the strongest tail of the run):

| label | file | steps |
|---|---|---|
| ckpt-1000 | `_eval_berserkr/berserkr_style_000001000.safetensors` | 1000 |
| ckpt-1250 | `_eval_berserkr/berserkr_style_000001250.safetensors` | 1250 |
| ckpt-1500 (final) | `_eval_berserkr/berserkr_style.safetensors` | 1500 |

Two neutral, deliberately *non*-Berserkr prompts were used so the measured shift
is the LoRA imposing its aesthetic, not the prompt doing the work:

- **portrait** — "portrait of a woman with long red hair, forest background"
- **scene** — "a small wooden cabin by a lake at sunset"

## Does the LoRA measurably shift output toward the Berserkr aesthetic? — YES

The effect is unambiguous on the **scene** prompt and consistent on the portrait:

- **Baseline scene** (`ComfyUI_00181_.png`): a soft, naturalistic **photograph** —
  muted warm light, photoreal water and foliage, shallow tonal range.
- **Every LoRA scene cell** (`ComfyUI_LoRA_00012/00015/00018_.png`): converts to a
  **painterly fantasy concept-art / game-environment render** — bold dramatic sky
  with vivid orange→pink cloud banding, elevated contrast, stylized bare silhouette
  trees, glowing window interiors, a "matte-painting" surface quality. This is the
  look of the Berserkr asset renders the LoRA was trained on.
- **Portrait**: subtler (the base is already a forest redhead) but directional and
  monotonic in strength — hair saturation, rim contrast and an illustrative,
  rendered-3D quality all increase from baseline → 0.6 → 0.8 → 1.0.

Florence-2 captions are near-identical baseline-vs-LoRA — expected, because the
captioner describes *content* (a redhead in woods / a cabin at sunset), which the
LoRA preserves, not *style*, which is what shifted. The verdict is therefore made
on the pixels, not the captions.

## Strength behavior

- **0.6** — gentle. Clear style nudge while staying close to photoreal. Good when
  you want subject fidelity with only a hint of the house look.
- **0.8** — the sweet spot. Strong, obvious Berserkr style transfer with no
  coherence loss or oversaturation artifacts.
- **1.0** — maximum style. Best for environment/scene work where the painterly
  look is the point; on portraits it begins to push hair toward an over-saturated,
  near-neon cast.

## Checkpoint ranking

Differences between 1000/1250/1500 are modest at these settings; style completeness
increases with steps and the final checkpoint reads as the most fully-formed:

1. **ckpt-1500 (final)** — strongest, most complete style; cleanest painterly scene.
2. **ckpt-1250** — very close; marginally more restrained.
3. **ckpt-1000** — already strong but the most naturalistic of the three.

No checkpoint showed degradation/overfitting at 1500, so the final checkpoint is the
keeper.

## 🏆 Winner

**`berserkr_style.safetensors` (checkpoint 1500) @ strength 0.8**

- Strongest, most coherent style transfer without the strength-1.0 oversaturation
  creep seen on portraits.
- It is also the canonical final checkpoint, so deployment (T8) is a straight copy.

**Recommended usage:** trigger `brsk_style`, default strength **0.8**; drop to **0.6**
for portrait/character fidelity, push to **1.0** for environment/scene renders.

## Best cells (for reference)

| prompt | cell | checkpoint | strength | image |
|---|---|---|---|---|
| scene | best overall | 1500 | 1.0 | `ComfyUI_LoRA_00012_.png` |
| scene | balanced | 1500 | 0.8 | `ComfyUI_LoRA_00011_.png` |
| portrait | balanced | 1500 | 0.8 | `ComfyUI_LoRA_00002_.png` |

_Judge: Claude (Opus 4.8), visual comparison of the rendered grid against the base cells._
