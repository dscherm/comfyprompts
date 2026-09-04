# Spec — Multiview-Consistency LoRA (Hunyuan3D-friendly ortho T-pose)

*Crystallized: 2026-06-24. Interactive intake. Builds on the completed
train_lora harness PoC (see `.ralph/spec-berserkr-poc.md`).*

## Goal

Train a Flux LoRA (`mv_ortho`) that emits **clean, orthographic, Hunyuan3D-friendly
character art** — single neutral-pose (wide T-pose) subject, plain background, even
lighting, canonical front framing, consistent silhouette. Feeding this LoRA's output
into Hunyuan3D should produce **cleaner, more consistent meshes** than feeding base
Flux output. This is the documented "training lever for 3D characters" (see
`comfy-improve-model` skill, Path 3) and directly improves the `art-to-rig-ralph`
flagship pipeline upstream.

Reuses the existing `scripts/train_lora/` harness end-to-end — only the dataset
source and the eval (which now includes a 3D mesh comparison) differ.

## Locked decisions (interactive intake, 2026-06-24)

- **Objective:** clean ortho **single-image** T-pose (NOT a multi-angle sheet).
  Matches the proven pipeline: *wide T-pose → Hunyuan3D → cleanup → UniRig*.
- **Limb separation (HARD requirement):** the LoRA must produce art where every
  *movable* part is in clear negative space — **wide/exaggerated T-pose, arms fully
  horizontal, fingers spread, legs apart, visible gaps between arms↔torso,
  hands↔hips, and between the legs.** Rationale: when Hunyuan3D sees parts in
  contact (hands on hips, arms against the torso, legs together) it bakes them into
  *fused* geometry that cannot be rigged/posed (see project memory
  `project_mesh_intersection_fix` and the `mesh split` step of the proven pipeline).
  This drives BOTH dataset selection (only train on separated-limb meshes; cull
  relaxed/arms-down poses) AND the eval (the output mesh must have separable limbs).
- **Dataset source:** **Blender-rendered orthographic views of 3D assets we already
  own** — gives ground-truth-clean, view-consistent training images for free.
  - Source meshes: ~62 in `D:\Projects\ComfyUI\output\3D` + ~36 rigged humanoids in
    `pipelines/autorig-ralph/references/humanoid`.
  - Render via **blender-mcp** (`execute_blender_code`): orthographic camera,
    neutral/transparent background, even 3-point or studio lighting, framed front
    (primary) + a few canonical angles for volume.
  - Target ~100-150 images. Lives on `E:\ai-training\datasets\mv_ortho\` (off the
    full C:/D: drives).
- **Trigger:** `mv_ortho` (+ a view tag like "front view" derived from filename).
- **Eval:** **full rigor** — 2D base-vs-LoRA grid (judge cleanliness/orthographic
  framing) AND feed base-vs-LoRA front images through Hunyuan3D, then compare the
  resulting meshes (watertightness, silhouette fidelity, artifact count) via
  blender-mcp + viewport screenshots.
- **Base / trainer / hardware:** unchanged from the PoC — Flux `flux1-dev-fp8`,
  `ostris/ai-toolkit` in its own venv, train on the 3090 Ti (`CUDA_VISIBLE_DEVICES=1`),
  rank 16, 512-768px, ~1500 steps. Generation and training contend for the 24GB →
  run sequentially (stop ComfyUI before training, restart after).

## Reuse the existing tooling

- `prep_dataset.py`, `launch_train.py`, `lora_eval_grid.py` — unchanged, dataset-agnostic.
- `caption.py` — extended/post-processed to add a per-view tag from the filename.
- New: a Blender orthographic multi-view **renderer** script (the only genuinely new
  dataset-gen component).

## Deliverables

1. Blender ortho multi-view renderer (blender-mcp-driven) — dataset-agnostic, points
   at any folder of meshes.
2. ~100-150 captioned `mv_ortho` training images on `E:\`.
3. A trained `mv_ortho` Flux LoRA `.safetensors`.
4. Eval: 2D grid verdict + a base-vs-LoRA **Hunyuan3D mesh comparison** showing the
   LoRA yields cleaner/more-consistent meshes.
5. Winning LoRA deployed to `loras/style/` + sidecar; README + `art-to-rig-ralph`
   cross-link documenting how to use it as the Hunyuan3D front-end.

## Out of scope

- Multi-angle/multi-view *reconstruction* LoRA (chose single-image objective).
- Finetuning Hunyuan3D/TripoSR (frozen feed-forward — improve the input, not the model).
- Rigging/animation/retargeting (those are `autorig-ralph`/`animate-ralph` data problems).

## Definition of done

The `mv_ortho` LoRA measurably produces cleaner orthographic T-pose art than base
Flux at fixed seeds, with **limbs clearly separated (no hands/arms/legs in contact
with the body)**, AND a base-vs-LoRA Hunyuan3D comparison shows the LoRA's output
yields a cleaner mesh **whose hands/arms/legs are separable (not fused to the body)**.
Winner deployed; the renderer + README let a future run rebuild the dataset from any
mesh folder without code changes.
