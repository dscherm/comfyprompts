---
title: Blender QuadriFlow cancels in headless retopo — use voxel remesh + decimate
severity: low
tags: [blender, retopo, mesh, headless]
source: hand-authored
created: 2026-06-30
project: comfyui-toolchain
---

## Symptom

Headless auto-retopology of a noisy AI-generated mesh via
`bpy.ops.object.quadriflow_remesh(mode='FACES', target_faces=N)` returns
`{'CANCELLED'}` with "QuadriFlow: The mesh needs to be manifold and have face
normals that point in a consistent direction" — even after a voxel remesh and
recalculating normals. The output face count is unchanged (no-op).

## Root cause

Blender's built-in QuadriFlow is unreliable headlessly; it rejects meshes that
look manifold and refuses to run. There is no robust, scriptable way to force it.
(`bpy.ops.object.datatransfer_refresh` also does not exist in Blender 5.0 — the
Data Transfer modifier computes on apply, not via a refresh op.)

## Mitigation

1. For a reliable HEADLESS cleanup of a noisy mesh, use **Voxel Remesh**
   (`obj.data.remesh_voxel_size = H/200; bpy.ops.object.voxel_remesh()`) to make
   it watertight + manifold + quad-dominant, then a **Decimate (COLLAPSE)**
   modifier to hit a game-friendly face count. This always works.
2. If you genuinely need clean even QUAD flow, use **Exoside Quad Remesher**
   (paid addon, reliable) or take the quad mesh from an image-to-3D tool that
   outputs quads directly (Rodin/Tripo) — don't fight built-in QuadriFlow.
3. Always set `mode='FACES'` if you do call quadriflow_remesh (default mode
   ignores `target_faces`), but expect it to still cancel headlessly.

## Notes (optional)

Voxel remesh increases vertex count (it re-tessellates), so follow with Decimate
to control polycount. Voxel + Decimate drops UVs — re-UV or transfer UVs after
(see unirig-skin-weights-melt-use-accurig step 3).
