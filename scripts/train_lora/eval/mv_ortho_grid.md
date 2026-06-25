# M5 — mv_ortho eval: 2D grid + Hunyuan3D mesh-separability verdict

**Date:** 2026-06-24
**LoRA:** `mv_ortho` (rank-16 Flux LoRA, 1500 steps; trained M4)
**Base model:** `flux1-dev-fp8` | **Trigger phrase:** `mv_ortho, front view, wide T-pose, arms outstretched, fingers spread, legs apart`
**Artifacts:** `eval/mv_ortho_assets/` (key cells + mesh renders), `eval/mv_ortho-grid/` (raw 2D grid)

## Part A — 2D grid (base vs LoRA × checkpoints × strengths)

Grid: base + checkpoints 1000/1250/1500 × strengths 0.6/0.8/1.0 on two character
prompts (plate-armor knight, sci-fi droid), seed 123456, 768px.

**Critical usage finding:** the LoRA ties the pose to the explicit pose tokens it
was captioned with, NOT to the bare trigger. Prompting only `mv_ortho` yields a
normal standing pose; the pose words must be in the prompt:

> `mv_ortho, front view, wide T-pose, arms outstretched, fingers spread, legs apart, <subject>`

**Result — the LoRA measurably corrects the pose:**
- **Base Flux** (even *with* the pose words): droid → arms droop **down by the hips**
  (fusion risk); knight → arms **raised ~45°** (welcoming pose). Inconsistent, not ortho.
- **mv_ortho** snaps both subjects to a clean **horizontal wide T-pose**, limbs clearly
  separated from the torso, tight orthographic front framing on a plain background.
- Effect strengthens with weight; pose consistency best at the **final (1500)** checkpoint.

**Strength:** knight cleanest at **0.8** (1.0 droops the wrists slightly); droid cleanest
at **1.0**. Both strong.

### 🏆 Winner: `mv_ortho.safetensors` (checkpoint 1500) @ strength 0.8
(default; use 1.0 for subjects that need stronger pose enforcement.)

## Part B — Hunyuan3D mesh-separability test (the core proof)

Fed a matched pair of droid front images through the **local** Hunyuan3D v2.0
geometry workflow (`hunyuan3d_v20_geometry_only`, octree 256), then rendered both
meshes ortho (`mesh_BASE_*` / `mesh_LORA_*`):

- **BASE mesh** (from base Flux's arms-down image): arms hang against the body, **hands
  pressed beside the hips/thighs** — limbs adjacent to the torso, no clean gap. This is
  the fused, hard-to-rig geometry the whole LoRA exists to avoid.
- **LoRA mesh** (from the clean T-pose image): arms extend **straight out with open gaps
  between arms and torso** — each limb a distinct, separable volume that rigs cleanly.

This closes the loop end-to-end: `mv_ortho` → separated-limb T-pose art → Hunyuan3D mesh
with **separable limbs**. The limb-separation requirement is satisfied not just in 2D but
in the resulting 3D geometry.

## Notes / gotchas (for M6 docs)

- **Prompt with the pose tokens**, not the bare trigger (see usage finding above).
- The geometry workflow's `Hy3DExportMesh` node does NOT report its output filename to
  ComfyUI history and uses a leftover `filename_prefix: "3D/ground_tile"`; the GLB lands
  at `output/3D/ground_tile_*.glb`. (A driver should locate the GLB on disk by mtime, not
  via /history outputs.)
- `render_multiview.py` hardened: data-API scene wipe (operator-free) so it works from any
  Blender context.

## Part C — Full-pipeline validation (mv_ortho → Hunyuan3D → UniRig)

Ran one character end-to-end through the real art-to-rig chain:
1. **mv_ortho** generated a barbarian wide-T-pose front image (strength 0.8).
2. **Hunyuan3D** (local geometry workflow) → 40K-vert mesh; prep = keep main mesh +
   merge doubles → clean GLB (`barbarian_clean.glb`).
3. **UniRig** (`C:\UniRig`, extract → skeleton → skin; ~3 min total on this box, not the
   ~30 min the older 3070 note assumed) → `barbarian_rigged.fbx`: a **28-bone humanoid
   skeleton** with symmetric 4-bone arm chains (shoulder→elbow→wrist→hand) and a vertex
   group per bone.
4. **Separability test:** rotated the right upper-arm bone 75° — **only that arm
   articulated; torso, legs, head, and the other arm stayed put** (`mv_ortho_assets/
   rig_rest.png` vs `rig_posed_arm_down.png`).

**Result:** the mv_ortho mesh rigs cleanly straight out of UniRig with **no manual
mesh-split / fusion fix** — the limb-separation requirement holds all the way through to
a posable rig. This is the production proof that mv_ortho earns its place as the
art-to-rig concept-art front-end.

_Judge: Claude (Opus 4.8), visual comparison of the rendered 2D grid, the two meshes, and the rest-vs-posed rig._
