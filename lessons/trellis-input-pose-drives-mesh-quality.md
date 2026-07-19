---
title: TRELLIS 3D mesh quality is gated by the INPUT pose/detail — arms-at-sides isolated subjects reconstruct clean; spread-arm poses go spindly; wispy hair/tendrils go noisy
severity: medium
tags: [trellis, image-to-3d, mesh, pose, character, reconstruction]
source: hand-authored
created: 2026-07-19
project: comfyui-toolchain
---

## Symptom

Reconstructing 5 isolated character clay images through TRELLIS.2 (`trellis2_
image_to_3d`, ~6-14 min each) gave a clear quality split that tracked the INPUT,
not the pipeline:

- **Clean, solid meshes** — crank, valkyrie, huldra: all **isolated, full-body,
  arms-at-sides** subjects → correct silhouette, complete geometry.
- **Spindly / fragile** — sparks: her **wide spread-arm + spread-leg pose**
  reconstructed into thin spidery limbs.
- **Noisy** — barrow_wight: **spiky hair + trailing tendrils** in the source
  became a chaotic spiky mesh at the top; body fine.

## Root cause

TRELLIS infers volume from a single view. A compact, closed silhouette (limbs
near the body) gives it solid mass to reconstruct; **limbs stretched far from the
torso reconstruct as thin, unsupported geometry**, and **high-frequency wispy
detail (hair strands, tendrils, fringe) has no coherent volume** so it comes out
as noise. Isolation cleanliness is necessary but not sufficient — pose and
detail-density dominate the result.

## Mitigation

1. **Feed TRELLIS an A/T-pose, arms-down (or arms-near-body), full-body,
   isolated subject.** This is the same reason the fist/clay generators enforce
   "full body from head to feet, arms at the sides".
2. **Avoid wide spread-arm / dynamic action poses as 3D inputs** — they read
   great in 2D but reconstruct spindly. If a specific art has a spread pose you
   must keep in 2D, generate a separate arms-down variant for the 3D path.
3. **Expect hair/fur/tendril-heavy characters to need mesh cleanup** (decimate +
   remove floaters/spikes) post-reconstruction; budget for it or simplify the
   source silhouette first.
4. Judge the mesh, don't assume: import the GLB and render front/¾/side/back —
   a good front view can hide spindly limbs only visible in profile.
