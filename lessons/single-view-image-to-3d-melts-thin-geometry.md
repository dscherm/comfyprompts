---
title: Single-view image-to-3D melts thin geometry (blades, poles, spread hands) — render + look, or go multi-view
severity: medium
tags: [3d, trellis, hunyuan3d, image-to-3d, mesh, low-poly, multiview]
source: hand-authored
created: 2026-07-18
project: comfyui-toolchain
---

## Symptom

Thin, flat features reconstruct badly from a SINGLE view. The original arsenal
sword shipped with a "split blade" look (a baked dark fuller stripe + spade tip);
the SL8 regen — clean Flux concept → TRELLIS.2 → mesh — still needed weld+decimate
cleanup and came out serviceable but not crisp on the blade. Same failure class as
the known TRELLIS spread-open-hand MELT (rounded to mitts) on the berserkr.

## Root cause

Single-view image-to-3D must hallucinate every unseen surface. A **thin flat part
(a blade, a pole, splayed fingers) offers almost no volume or parallax cue in one
image**, so the model produces melted / frayed / ambiguous geometry exactly there —
while thick, rounded subjects reconstruct fine. A clean concept image does NOT
guarantee clean 3D; the failure is in the reconstruction, not the prompt.

## Mitigation

1. **Always RENDER the reconstructed mesh** (flat-shaded, a couple of 3/4 angles)
   and LOOK before trusting or shipping it. "TRELLIS returned a GLB" is not "the
   mesh is good." (See [[verify-asset-pack-pixels-before-dataset]].)
2. **Prefer MULTI-VIEW for thin / prop subjects.** Hunyuan3D-2mv (front/left/right/
   back → `Hy3DGenerateMeshMultiView`) is installed (MV1) precisely to give the
   reconstructor the side/edge cues a single view lacks.
3. **Weld first, then simplify.** TRELLIS ships unwelded (coincident-vertex
   fragments); merge-by-distance BEFORE decimate/smooth or cracks open up
   (see [[project_trellis_unwelded_mesh_weld_before_smooth]]).
4. Prompt the concept for a solid uniform blade ("no fuller/groove") to remove one
   failure source, but budget for a cleanup/recolor pass regardless.
