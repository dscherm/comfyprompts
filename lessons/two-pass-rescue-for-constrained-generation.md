---
title: When a mechanical constraint wrecks composition — generate free, then re-diffuse constrained
severity: medium
tags: [sdxl, seamless-tiling, lora, img2img, generation]
source: hand-authored
created: 2026-07-17
project: comfyui-toolchain
---

## Symptom

A generation-time mechanical constraint (ComfyUI-seamless-tiling's circular
Conv2d padding) degraded the *composition* at the LoRA strength whose look was
otherwise wanted. Observed 2026-07-17 on `mat_tile` wood planks: at strength
0.8 with tiling enabled, long directional planks broke into a stepped
patchwork; with tiling disabled the same seed/prompt/strength produced clean
continuous planks — the look the user chose — but it does not tile
(edge MAD 8.58% vs the <5% bar). Lowering strength to 0.6 tiled fine but lost
the wood aesthetic. The constraint and the aesthetic appeared mutually
exclusive.

## Root cause

Circular padding constrains every conv in the denoising path for the *whole*
trajectory, including the early steps that decide layout. Materials whose
identity lives in long directional structure (planks, boards, beams) have their
composition decided under a wrap constraint that fights the structure. The
constraint is only strictly needed at the *edges* — but it applies globally,
and it applies while composition is still forming.

## Mitigation

1. **Two-pass rescue.** Pass 1: generate with the constraint **disabled**, at
   whatever strength gives the right look — composition forms freely. Pass 2:
   img2img re-diffuse that image at **denoise ~0.35** with the constraint
   **enabled**, same prompt/LoRA/seed. Low denoise preserves layout; the
   constrained convs heal the wrap edges. Wood: 8.58% → **3.14% MAD**, clean
   2×2 mosaic, plank composition intact. Cost: one extra generation.
2. **Tune denoise as the dial**: too low leaves the seam, too high re-decides
   the composition you just paid a pass to protect. 0.35 worked first try on
   wood; sweep 0.25-0.45 if a material resists.
3. **Diagnose before reaching for it.** Compare constrained vs unconstrained at
   the same seed/strength. If unconstrained is *better composed* (not merely
   different), the constraint is the culprit and this applies. If both are
   equally good, just keep the constrained one.
4. Apply per-material, not globally — brick/cobble/sand tiled fine single-pass
   at 0.6. Record which materials need the second pass (see
   `scripts/train_lora/datasets/tile_loras_spec.md` §6c).

## Notes (optional)

Generalizes beyond tiling: any post-hoc mechanical constraint on the denoiser
(circular padding, region masks, forced symmetry) can be deferred to a
low-denoise second pass when it costs composition on the first. Does NOT fix a
LoRA that is simply wrong for the subject — that is a dataset problem (see
auto-bucketed-dataset-labels-cause-mode-bleed).
