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

RESOLVED 2026-07-25. The working recipe (`ink_to_3d.py` stage 2.5 → stage 3):

1. **Heal with `mesh_to_solid --voxel-remesh <size>`, NOT `--watertight`.** The
   `--watertight` (holes_fill) path can't close TRELLIS soup; the OpenVDB voxel
   remesh resamples the volume into a GUARANTEED closed manifold (verified:
   `boundary=0 watertight=True`). `0.005` (~200 voxels tall) preserves a
   character silhouette + limbs; finer (`0.003`) barely helps and just adds tris
   the reducer discards.
2. **Recalc face normals AFTER the voxel remesh** — OpenVDB output is manifold
   but QuadriFlow refuses inconsistent winding, so recalc before handing off.
3. **In `mesh_product_check.fix()`, recalc normals as the LAST op** (after
   origin_set / smart-UV / transform_apply — those desync stored winding from
   geometry; observed 8 faces reading "flipped" otherwise), and
   `dissolve_degenerate` first to clear collapse slivers. Without the final
   recalc the gate fails `normals` on the very mesh it just fixed.
4. **Assert `watertight=True` from the heal report** before the gate — trust the
   geometry, not the flag name. `ink_to_3d` prints it and warns if False.

Residual (NOT a remesh bug): if TRELLIS reconstructs a part as fragmented soup
(e.g. spiky gauntlets on arms held away from the body — 12k+ non-manifold edges,
32 loose parts), the voxel remesh faithfully closes it into blobby/shredded
geometry. The gate still PASSES (watertight/manifold/budget/normals) but the
arms look bad. That's an UPSTREAM input-pose problem
([[trellis-input-pose-drives-mesh-quality]]), fix it at the clay stage, not here.
Related: [[trellis-decimate-splits-solid-vs-round]] (voxel remesh blobs round
parts), [[project_trellis_unwelded_mesh_weld_before_smooth]] (weld before remesh).
