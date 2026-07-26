---
title: A raw TRELLIS mesh fails the game-ready gate, and mesh_to_solid --watertight does not actually close it
severity: medium
tags: [trellis, watertight, mesh-cleanup, game-ready, quadriflow, blender, ink-to-3d]
source: hand-authored
created: 2026-07-25
project: comfyui-toolchain
---

## Symptom

The `ink_to_3d` chain's stage 3 (strict MESH-PRODUCT gate) FAILs on the raw
TRELLIS reconstruction. The mesh is non-manifold — ~1M tris with thousands of
boundary edges — so:

- `mesh_to_solid.py --watertight` only PARTIALLY closes it. On the valkyrie run:
  welded verts=311160 faces=616096 boundary=8719 → after remesh FINAL
  boundary=6284, `watertight=False`. The flag ran without error but did not
  produce a closed manifold.
- QuadriFlow (`mesh_product_check --quad-remesh`) REFUSES the still-open input.
- The gate fails on `nonmanifold` + `normals`, and collapse-decimate floors at
  ~30–40k tris (well over the 8k budget).

## Root cause

TRELLIS single-view reconstruction emits organic triangle soup with many
boundary/non-manifold edges. `mesh_to_solid --watertight` does a weld +
voxel-remesh pass, but at its current voxel resolution the remesh leaves
thousands of boundary edges rather than a single closed shell — "watertight" as
a flag name overpromises what that pass delivers. Everything downstream that
assumes a closed manifold (QuadriFlow, the strict gate) then rejects the mesh.

## Mitigation

1. **Keep stage 3 NON-FATAL** in `ink_to_3d.py` (via `sh_soft`) until a TRUE
   voxel-remesh-to-watertight step exists — the chain still delivers clay + raw
   GLB + healed solid, and reports `mesh-gate: FAIL` honestly rather than
   aborting.
2. **The real fix is a dedicated remesh-to-closed-manifold step** before the
   reducer: a voxel/manifold remesh whose output is verified `watertight=True`
   (0 boundary edges, 0 non-manifold edges) — assert it, don't trust the flag.
   Only then hand off to QuadriFlow or collapse-decimate to the tri budget.
3. **Never report a healed mesh as game-ready on the flag alone.** Read back the
   boundary-edge and non-manifold-edge counts; `watertight=False` in the heal log
   is the tell that the gate will fail. Related:
   [[trellis-decimate-splits-solid-vs-round]] (voxel remesh blobs round parts —
   raising resolution to close boundaries trades against that),
   [[project_trellis_unwelded_mesh_weld_before_smooth]] (weld before any remesh).
