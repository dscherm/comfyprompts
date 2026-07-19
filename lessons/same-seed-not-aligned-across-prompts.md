---
title: Same subject + same seed in two different prompts does NOT give an aligned image pair
severity: medium
tags: [flux, comfyui, dataset, image-translation, paired-data, lora]
source: hand-authored
created: 2026-07-19
project: comfyui-toolchain
---

## Symptom

Bootstrapping paired `(input, target)` data for an image→image translator by
rendering "the same subject at the same seed" in two *different* prompt / LoRA-
stack configs produced **misaligned** pairs. On the ink-to-clay-ralph Stage-1
smoke, the clay half and the ink half of the same seed drifted in costume and
pose: the barbarian grew a phantom hood + shoulder armor, the wizard lost his
pointed hat, the knight swapped a spear for a sword. The pairs shared a seed but
not a composition — useless for a paired-edit (Kontext) LoRA, which would learn
the wrong ink→clay mapping.

## Root cause

A diffusion seed only fixes the *initial noise*, not the *output composition*.
Composition is driven by the conditioning (prompt tokens + LoRA stack + weights).
When the two renders differ substantially in conditioning — one adds pose/pose-
LoRA tokens the other lacks — the same seed lands in a different region of the
distribution, so subject, costume, and pose diverge. "Same seed ⇒ aligned pair"
is a false assumption whenever the two prompts aren't near-identical.

## Mitigation

1. **Share the invariant framing tokens across BOTH prompts** — view, full-body,
   and pose (e.g. `front view, full body, A/T-pose`) go in the input prompt AND
   the target prompt, so the shared seed tracks composition. Only the
   style-defining tokens (linework vs. matte-render, background) should differ.
2. **Verify alignment on a 3-subject smoke before scaling** — render a montage of
   the pairs side by side and check subject/pose/silhouette track. Do not
   generate the full 50–150 set until the smoke pairs align.
3. **If prompt-sharing still drifts, derive one half from the other's latent**
   (img2img from the target latent) so the pair is guaranteed to share pose —
   the tighter but costlier route. See the ink-to-clay-ralph Stage 1 doc.
4. Remember the asymmetry: a style set (Approach A, target images only) tolerates
   drift; a **paired-edit** set (Approach B) does not — align before training B.
