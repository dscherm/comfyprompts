# MV3D — Multi-View 2D→3D Reconstruction (implementation plan)

**Goal:** eliminate **webbed hands** and **loose-clothing limb-fusion** at the source
by reconstructing the mesh from **multiple views** instead of a single front image —
no prompt workarounds (closed fists / fitted clothing), no LoRA retrain.

## Why this is the right lever (recap)

Webbing and fusion are **topology failures of single-image reconstruction**: from one
front view, Hunyuan3D 2.0 can't resolve the thin gaps between fingers or the occluded
arm↔torso gap behind a cape, so it fills them. The 2D image is already fine (M5 eval:
"fingers render separated fine"). Multiple views resolve exactly that ambiguity — the
geometry hidden in the front view is visible from the side/back. This is the dominant
2026 pattern (Hunyuan3D-MV, TRELLIS.2, InstantMesh) precisely because it yields the
cleanest topology.

## Grounding (verified on this box)

- **Current stage:** mv_ortho front image → `hunyuan3d_v20_geometry_only` (Hunyuan3D
  **2.0, single front image**, octree 256) → mesh. This is where webbing/fusion enter.
- **Installed:** `ComfyUI-Hunyuan3DWrapper` with a **code-ready multi-view geometry
  node** — `Hy3DGenerateMeshMultiView` (inputs: `front`, `left`, `right`, `back` →
  mesh latent). Also `ComfyUI-Flowty-TripoSR`, `ComfyUI-TripoSG` (both single-view).
  **TRELLIS is NOT installed.**
- **Checkpoints on disk:** only Hunyuan3D **v2-0** (dit-v2-0 / -fast / -turbo, all
  single-view). The **multi-view checkpoint (Hunyuan3D-2mv) is NOT downloaded** — this
  is the gating dependency.
- **Multi-view INPUT source is the hard part — we DON'T have a good one (tested):**
  the `multiview_full_body_ipadapter` tool uses **SD_XL_base** (not Flux/mv_ortho),
  so it enforces **no wide-T-pose** and IPAdapter gives weak *geometric* consistency —
  a test gen with mv_ortho pose tokens produced garbage. **No novel-view synthesis is
  installed** (no Zero123/SV3D/MV-Adapter/Wonder3D; the wrapper's `Hy3DSampleMultiView`
  is for texture baking, not input views). So `Hy3DGenerateMeshMultiView` has no
  consistent front/left/right/back to feed. (`render_multiview.py` renders EXISTING
  meshes — not usable pre-reconstruction.)

## STRATEGY REVISION — try higher-fidelity SINGLE-view first

Because the multi-view path has a real unmet dependency (consistent T-pose view
synthesis), the **lower-risk first move is a better single-view model**: **TRELLIS.2**
(SOTA "field-free" O-Voxel — best at thin structures / open surfaces = fingers) or
**Hunyuan3D 2.5** may fix webbed hands **from the single front image via topology
alone**, with NO view-synthesis to build. Test that FIRST. Only pursue full multi-view
(which needs a novel-view synthesizer installed + evaluated) if single-view isn't enough.
- **Storage:** route the new model to `E:\ai-training\` if C:/D: are tight
  (`project_training_storage`).

## Primary path: Hunyuan3D-2mv (low risk — reuses installed wrapper)

The wrapper node already exists; we need the model + the back view + a workflow.

## Stretch path: TRELLIS.2-4B (higher topology ceiling for hands)

SOTA "field-free" O-Voxel — best at thin structures/open surfaces (fingers). Needs
installing `ComfyUI-Trellis2` + the 4B model (bigger VRAM/disk). Only pursue if
Hunyuan3D-2mv's hands aren't clean enough in the MV4 eval.

## Task breakdown (→ plan.md, phase MV3D)

- **MV1 — Acquire + verify the multi-view model.** Inspect `Hy3DModelLoader` /
  `DownloadAndLoadHy3DModel` to find how it loads the mv checkpoint; download
  **Hunyuan3D-2mv** to `models/` (route to E:\ if needed). Verify
  `Hy3DGenerateMeshMultiView` loads it and runs on a dummy 4-view input. Gate: node
  produces a mesh latent without error.
- **MV2 — Produce + validate the 4 consistent character views.** Use the existing
  `multiview_full_body_ipadapter` tool to generate front/left/right/back of one
  character (IPAdapter identity). Validate they're consistent enough for
  reconstruction AND hold the wide-T-pose across angles (drive with mv_ortho pose
  tokens). Gate: 4 aligned views, same character, separated limbs in every view. If
  IPAdapter consistency is too weak, fall back to a novel-view-synthesis step (e.g.
  Hunyuan3D's own mv sampler / Zero123) — decided here.
- **MV3 — Build + register the MV reconstruction workflow.** New `workflows/mcp/`
  JSON: load front/left/right/back → Hy3DModelLoader(2mv) → Hy3DGenerateMeshMultiView
  → VAE decode/export → GLB. Register an MCP tool (e.g. `hunyuan3d_2mv_image_to_3d`).
  Gate: `validate_workflow` passes + a smoke-test mesh exports. (workflow-architect.)
- **MV4 — A/B eval: hands + limb separation (the correctness gate).** Reuse the
  mv_ortho eval harness (`scripts/lora_eval_grid.py` + Hunyuan3D separability). Run the
  SAME character(s) — incl. spread-finger + caped test cases — through: (a) current
  single-front Hunyuan3D 2.0, (b) MV Hunyuan3D-2mv. Score **finger separation (no
  webbing)**, **arm↔torso gap**, **cape non-fusion** on the MESH, AI-judged. Gate:
  MV measurably beats single-front on webbing + fusion, topology no worse elsewhere.
- **MV5 — Wire into the pipeline.** If MV4 wins, replace the single-front
  reconstruction stage in art-to-rig-ralph (and animate-ralph's 3D step) with the MV
  tool; update stage docs. Gate: one character runs end-to-end gen→mesh with clean
  hands/limbs.
- **MV6 (stretch) — TRELLIS.2 track.** Install `ComfyUI-Trellis2` + TRELLIS.2-4B,
  build a parallel MV workflow, compare against Hunyuan3D-2mv in the MV4 eval. Only if
  2mv hands are insufficient. Gate: documented winner.

## Guardrail

Success = **cleaner hands + separated limbs on the reconstructed MESH**, verified by
the MV4 eval — not by eyeballing the 2D. Multi-view must not regress overall topology
or limb separation vs the current path.
