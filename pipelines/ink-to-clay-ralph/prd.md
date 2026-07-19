# Ink→Clay Image Translator — Requirements

## Overview

ink-to-clay-ralph trains a FLUX **image→image** translator that re-renders any
2D drawing (ink/comic, sprite, concept art) as a clean "3D-clay" image: smooth
matte 3D forms, soft even lighting, plain neutral-grey/white background, no cast
shadow or ground plane, full subject in frame, clear silhouette. The clay look
is the one that reconstructs cleanly in **TRELLIS image-to-3D**, so this pipeline
generalizes the character pipeline: *any* drawing can enter the 3D-model path,
not only LoRA-triggered subjects.

Source brief: `D:/Projects/soapbox-sabotage/docs/lora-ink-to-clay-spec.md`.
Target-look reference: `products/soapbox_characters_v1/concepts/*.png`.

## Target State

Given an input drawing, the pipeline produces a clay-style render that (a) keeps
the subject/pose/proportions of the drawing and (b) restyles surface + lighting +
background to the clay target — and, fed straight into TRELLIS, yields a clean
mesh. Two trained artifacts: an **Approach-A style LoRA** (img2img @ denoise ~0.6)
and an **Approach-B Kontext edit LoRA** (single-pass), with the better one wired
as default.

## Acceptance Criteria

1. **Paired dataset** `E:/ai-training/datasets/ink_to_clay_v1/{ink,clay}/<id>.png`
   exists with matched filenames, ~50–150 aligned pairs, produced by the
   same-subject/same-seed bootstrap; a curation montage is human-approved.
2. **Clay halves** form a coherent Approach-A style set (consistent bg, lighting,
   framing) — verified by `judge_image` + montage.
3. **Approach-A style LoRA** trained (`E:/ai-training/flux-output/ink_to_clay_v1_a*`,
   trigger `clay3d`, rank 16–32, LR 1e-4, 1500–3000 steps, 1024px); checkpoints
   saved every 250–500.
4. **Approach-A img2img workflow** (ComfyUI JSON) restyles an input drawing to
   clay at denoise 0.55–0.70 while preserving composition; optional lineart
   ControlNet locks the silhouette.
5. **Approach-B Kontext edit LoRA** trained on the pairs; single-pass edit maps
   ink→clay faithfully without a denoise knob.
6. **Composition preserved** — output subject, pose, and proportions match the
   input drawing (not a hallucinated new subject).
7. **Clay look achieved** — smooth matte surfaces, soft even light, plain grey/
   white bg, no cast shadow/ground, whole subject in frame, clear silhouette.
8. **Reconstruction test (the one that matters)** — the output feeds into
   `trellis2_image_to_3d` and yields a clean, watertight-ish mesh with a good
   silhouette; it reconstructs at least as well as a clay image made the current
   (soapbox_char_final_v1) way.
9. **Generalizes** — a held-out ink drawing (subject NOT in the training set)
   still converts to a usable clay render + reconstructs.
10. **Deliverables shipped:** the two LoRAs, both ComfyUI inference workflow JSONs,
    a README (recommended denoise/weights per approach), and 3–5 before/after
    examples including at least one TRELLIS reconstruction.
11. Pipeline completes within `max_iterations` (20); training stages only run
    after explicit human GPU-free confirmation.

## Out of scope / non-goals

- Not a text→image generator — this is strictly an image→image transform.
- Not a rigging/animation pipeline (hand off the clean mesh to art-to-rig-ralph /
  photo-to-3d downstream).
- Does not fine-tune TRELLIS itself; it feeds TRELLIS better inputs.

## Dependencies

- `soapbox_char_final_v1` + `mv_ortho` LoRAs (dataset bootstrap) — deployed in
  `ComfyUI/models/loras/`.
- ai-toolkit (FLUX dev + Kontext LoRA training), FLUX.1 [dev] + FLUX.1 Kontext
  [dev] base weights, optional FLUX lineart/canny ControlNet.
- ComfyUI-Trellis2 + TRELLIS.2-4B (installed) for the Stage-6 acceptance test.
