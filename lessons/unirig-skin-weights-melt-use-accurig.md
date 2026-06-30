---
title: UniRig drops UVs and its skin weights melt the mesh under motion — AccuRIG for deformation
severity: high
tags: [rigging, unirig, accurig, skinning, animation, mesh]
source: hand-authored
created: 2026-06-30
project: comfyui-toolchain
---

## Symptom

A UniRig-rigged character looks fine in the static bind pose and the bone
ROTATIONS track the mocap faithfully, but once animated the MESH distorts
drastically: hands/forearms melt and stretch into points, the torso collapses/
hunches ~45° in side view, limbs look stubby. Separately, the rigged mesh exports
with NO UV layer (texture collapses to one flat color when re-applied).

## Root cause

Two independent UniRig limitations: (1) its auto-generated SKIN WEIGHTS are crude,
so the mesh deforms badly the moment bones rotate (joint collapse, candy-wrapper
limbs) — this is a weights problem, not a retarget-rotation problem. (2) The
UniRig skin step does not carry the input mesh's UVs through, so the output has no
UV layer.

## Mitigation

1. For SHIPPABLE/textured characters, rig with **AccuRIG 2** (free, Reallusion)
   instead of UniRig — its weights "mimic professional weight-painting" and deform
   cleanly (proven on the same mesh + same CMU clip: melting gone, knees defined,
   fists hold). UniRig stays fine for throwaway/previz rigs and full headless
   automation where deformation quality doesn't matter.
2. AccuRIG drops the MATERIAL but PRESERVES UVs → re-apply the original texture
   image to its rigged mesh afterward (assign to the existing UV layer; aligns
   perfectly). Re-texturing after rigging is a mandatory pipeline step for ANY
   local rigger.
3. If you must use UniRig and need texture, transfer UVs from the original
   textured mesh onto the rigged mesh via Blender's Data Transfer modifier
   (`loop_mapping='POLYINTERP_NEAREST'`, `data_types_loops={'UV'}`, then apply) —
   proximity transfer aligns the texture acceptably (minor seam smear).

## Notes (optional)

Diagnose deformation by rendering mid-motion frames from front AND side at bent
joints — static poses hide weight problems. Distinct from the arms-up bind bug
(retarget-arms-up-bind-direction-mismatch), which is about bone rotation; this is
about mesh deformation quality.
