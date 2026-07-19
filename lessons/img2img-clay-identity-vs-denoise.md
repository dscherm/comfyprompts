---
title: Making a clean "clay"/3D-render from a character LoRA — identity survival depends on where identity lives, and denoise trades identity vs clean-clay
severity: medium
tags: [flux, comfyui, img2img, lora, clay, trellis, character, mv_ortho]
source: hand-authored
created: 2026-07-19
project: comfyui-toolchain
---

## Symptom

Turning a character LoRA's art into a clean isolated "clay" 3D-render (for
TRELLIS) gave opposite results on two datasets from the same session:

- **soapbox_char_final_v1** (captions describe the character — "a hulking bald
  East Asian man in tan overalls"): the text2img bootstrap `mv_ortho@0.85 +
  char@0.65` produced a clean, isolated, full-body clay with **identity intact**.
- **vibrant_rpg_char_sagaink** (caption is only `sagaink, <name>, a figure, <ink
  style>` — identity carried by the LoRA, not described): the same bootstrap
  rendered a **generic grey mannequin** ("astrid" lost her hood/cape entirely).

Switching sagaink to img2img from the character's own render then hit a second
wall: **denoise ~0.55 kept the character but stayed comic/ink (barely clay);
denoise ~0.85 clay-ified but drifted generic/mech-armored** (lost the specific
costume). No single denoise gave both.

## Root cause

Identity has to come from *somewhere the generator can read*. A text prompt can
only reconstruct a character it can describe; when the identity lives only in the
LoRA weights + a bare name token, text2img + a competing style LoRA (mv_ortho)
washes it out. img2img reads identity from the source *pixels*, but the denoise
knob is a single dial trading "how much of the source survives" against "how much
new clay style is imposed" — and mv_ortho at high denoise re-authors the figure
toward a generic armored body.

## Mitigation

1. **Choose the clay method by where identity lives.** Caption *describes* the
   character (soapbox) → text2img bootstrap `mv_ortho@0.85 + char@0.65` (clean +
   identity). Identity only in the *image* (sagaink) → **img2img** from the
   character's own render.
2. **For img2img, tune denoise to the source, ~0.85 as a start**: high enough to
   read as clay, low enough to keep the costume. Expect a per-dataset sweet spot;
   ~0.85 balanced clay-vs-identity for sagaink, but generic-ized fine detail.
3. **Accept the trade-off explicitly** — there is no denoise that gives both
   perfect identity and pure clay via a single-LoRA img2img. If identity must be
   exact, isolate the original art instead of restyling (see
   [[birefnet-not-u2net-for-thin-limbs]]).
4. Isolate on transparency for TRELLIS (rembg); feed the mesh through the
   MESH-PRODUCT gate afterward. Pose matters downstream too:
   [[trellis-input-pose-drives-mesh-quality]].
