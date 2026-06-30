---
title: Hand-rolled mocap retarget mishandles limb plane — use the rigger's retarget ecosystem for shippable motion
severity: high
tags: [rigging, retarget, animation, accurig, unity, mixamo]
source: hand-authored
created: 2026-06-30
project: comfyui-toolchain
---

## Symptom

A hand-rolled rest-relative quaternion retarget gives *faithful bone rotations*
(numerically matches the source) yet the LIMB PLANE is wrong on the target
character: arms splay outward with bind-direction alignment ON, pull inward
toward the body with it OFF; legs sit too narrow (inner-thigh overlap). Trying to
fix it with a world-axis abduction post-process makes the legs windmill and
adducts the wrong way.

## Root cause

A hand-rolled transfer does not normalize BOTH skeletons through a canonical
T-pose "muscle space." Bind-direction alignment corrects a bone's swing but not
its twist/roll, so the forearm/shin plane drifts. World-axis post-corrections
fight the bone's per-frame orientation (hence the windmill). This is the exact
problem professional retargeters (Unity Humanoid, Mixamo, AccuRIG/ActorCore)
exist to solve — and a script won't match them without reimplementing muscle-space.

## Mitigation

1. For SHIPPABLE animation, retarget through the rigger's own ecosystem, NOT a
   hand-rolled script:
   - **Unity Humanoid** (muscle-space) — import the rig as Humanoid, feed it
     Humanoid clips (free Mixamo clips work); Unity retargets cleanly. KEEPS your
     AccuRIG rig + weights. Recommended (native to a Unity game).
   - **Mixamo** — upload the mesh, auto-rig + auto-animate (re-rigs with Mixamo's
     skeleton).
   - **AccuRIG 2 / ActorCore** — apply built-in motions in AccuRIG (no manual
     retarget).
2. Keep the hand-rolled `retarget_mocap.py` for PREVIZ / headless throwaway only.
   It is faithful in rotation but not production-clean in limb plane.
3. Don't chase limb-plane fixes with world-axis post-rotations — they windmill.
   If you must correct in-script, do it in the bone's LOCAL/parent space, but
   prefer not to.

## Notes (optional)

Pairs with unirig-skin-weights-melt-use-accurig (that's deformation/weights; this
is limb-plane/retarget). The through-line of the whole rig/animate investigation:
use proven tools for rig + animate; reserve custom code for art (the LoRA) and
glue. Related: project memory project_tripo_strategy.
