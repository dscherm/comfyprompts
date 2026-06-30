---
title: Spread-finger T-pose art reconstructs as double-thumb/backwards hands in image-to-3D
severity: medium
tags: [hunyuan3d, image-to-3d, mv_ortho, lora, mesh]
source: hand-authored
created: 2026-06-30
project: comfyui-toolchain
---

## Symptom

Characters generated for image-to-3D (Hunyuan3D / Tripo / Rodin) come out with
malformed hands — extra/double thumbs, hands that look mirrored or "backwards"
(left hand on the right arm). The defect appears in EVERY image-to-3D tool tried
on the same art, and in any rig built on the resulting mesh.

## Root cause

It is a SOURCE-ART defect, not a rigging/reconstruction failure. The `mv_ortho`
LoRA prompt included "fingers spread" (added to keep limbs separated for clean
generation). Flat, open, spread-finger hands with an ambiguous thumb are the
single hardest case for image-to-3D: the depth/thumb ambiguity reconstructs as
doubled thumbs and flipped palm orientation. Because it's in the 2D art, it
propagates identically into every downstream mesh.

## Mitigation

1. Generate the T-pose with **closed fists** instead of spread fingers
   ("hands clenched into tight fists"). A fist at the end of an outstretched arm
   still gives full limb separation (separation comes from the arm being OUT, not
   the fingers splayed) AND reconstructs reliably — a fist is a simple blob with
   no thumbs to double.
2. Check the hands close-up before meshing; seed variance matters (one seed gives
   clean fists, another stays open) — pick a seed whose fists are actually closed.
3. If open hands are required, add a 2D hand-refiner (MeshGraphormer / hand
   ControlNet) pass before meshing — but fists are far more reliable.

## Notes (optional)

Fists also suit weapon-holding game characters. Diagnose by cropping/zooming the
hands of the SOURCE art: if both rig paths share the defect, it's the art, not the
rig. Related: project memory project_mv_ortho_fists.
