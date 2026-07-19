---
title: rembg u2net ghosts thin/spread limbs (and largest-component cleanup then deletes them) — use birefnet-general
severity: medium
tags: [rembg, background-removal, matting, birefnet, u2net, alpha, comfyui]
source: hand-authored
created: 2026-07-19
project: comfyui-toolchain
---

## Symptom

Isolating a character with **wide-spread arms + gloves + trailing chains**
(soapbox "sparks") via `rembg` left the arms/hands **semi-transparent / ghosted**
across every img2img denoise (0.55 / 0.65 / 0.72). Worse: a well-intentioned
"keep the largest connected alpha component" cleanup then **deleted the arms
entirely** — because the ghosted arms were disconnected islands, so the cleanup
removed them as "specks". The user reported "sparks doesn't have any arms".

## Root cause

rembg's **default u2net** salient-object model treats thin, far-reaching
structures (spread arms, capes, chains, fringe) as low-confidence / background and
mattes them semi-transparent. Any "keep largest component" alpha pass then treats
those faint, disconnected limb islands as noise and zeroes them.

## Mitigation

1. **Use birefnet, not u2net, for thin/spread structure:**
   ```python
   from rembg import remove, new_session
   sess = new_session("birefnet-general")   # ~1GB first-use download; CPU fallback OK
   remove(img.convert("RGBA"), session=sess)
   ```
   birefnet held sparks' spread arms **solid, no halos** where u2net ghosted them.
2. **Never "keep only the largest connected component"** on a figure that can have
   spread limbs — you will delete arms/props. If you must despeckle, drop only
   islands below a tiny area fraction (e.g. `< 0.3-0.5% of total mask`), which
   removes stray pixels but keeps limbs.
3. **When a source already has complete limbs in a hard pose, isolate the
   original with birefnet** rather than restyling it — an img2img clay pass will
   mangle a wide-arm pose anyway ([[img2img-clay-identity-vs-denoise]],
   [[trellis-input-pose-drives-mesh-quality]]).
4. The `onnxruntime` cudnn CUDA-provider warning on birefnet load is harmless
   (falls back to CPU).
