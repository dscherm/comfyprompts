# plan.md — Multiview-Consistency LoRA (Hunyuan3D-friendly ortho T-pose)

Task queue for Ralph Loop. JSON blocks in triple-backtick fences.
Only ONE task per iteration. Mark `"passes": true` when complete.
Spec: `.ralph/spec.md`. All training runs on GPU 1 (3090 Ti) via
`CUDA_VISIBLE_DEVICES=1`. Reuses the `scripts/train_lora/` harness.

---

## Task Format (template — not a real task)

<!-- Template for reference only. Do NOT pick this up as a task.
{
  "id": "M0",
  "category": "setup|feature|testing|bugfix",
  "priority": 1,
  "description": "One-line description",
  "files": ["path/one.py"],
  "acceptance_criteria": ["observable check 1"],
  "steps": ["Step 1"],
  "passes": true
}
-->

---

## Prior pipeline (Berserkr-style LoRA training harness PoC) — COMPLETE

All of T1-T8 shipped (see git through `b7c6658` and `scripts/train_lora/README.md`).
That pipeline proved the reusable harness; this one retrains it on a Blender-rendered
orthographic dataset to produce the `mv_ortho` LoRA. Spec archived at
`.ralph/spec-berserkr-poc.md`.

---

### Phase 1: Dataset generation (Blender ortho multi-view renderer)

```json
{
  "id": "M1",
  "category": "feature",
  "priority": 1,
  "description": "Build a Blender orthographic multi-view renderer (blender-mcp) — dataset-agnostic, renders any mesh folder to clean ortho views",
  "files": ["scripts/train_lora/render_multiview.py"],
  "acceptance_criteria": [
    "Takes a mesh source dir/glob + output dir + list of canonical angles (default front/back/left/right + front-3/4 L/R)",
    "Drives blender-mcp execute_blender_code: imports each mesh, frames it to fill the frame, sets an ORTHOGRAPHIC camera, neutral/transparent background, even studio lighting",
    "Renders each angle to <out>/<mesh>__<view>.png; view encoded in filename for downstream captioning",
    "Checks blender-mcp availability (get_external_app_status / get_scene_info) first; clear error if unreachable, no half-written set",
    "Dataset-agnostic: nothing mesh-specific hardcoded; runs on an arbitrary mesh folder"
  ],
  "steps": [
    "Confirm blender-mcp reachable (socket 9876) via get_scene_info",
    "Per mesh: clear scene, import, normalize scale/origin, frame, render N angles",
    "Neutral bg + even lighting; orthographic camera per angle",
    "Write <mesh>__<view>.png; log a count summary"
  ],
  "passes": true
}
```

```json
{
  "id": "M2",
  "category": "feature",
  "priority": 1,
  "description": "Generate the mv_ortho raw dataset: render ~100-150 ortho views across owned meshes",
  "files": ["scripts/train_lora/datasets/mv_ortho_manifest.md"],
  "acceptance_criteria": [
    "render_multiview.py run across D:/Projects/ComfyUI/output/3D + pipelines/autorig-ralph/references/humanoid",
    "~100-150 clean ortho PNGs on E:/ai-training/datasets/mv_ortho/ (front view weighted heaviest, since the objective is single-image front)",
    "LIMB SEPARATION: only meshes with clearly separated limbs are kept — wide/exaggerated T-pose, arms horizontal, fingers spread, legs apart, visible gaps between arms/hands and the torso/hips. Relaxed/arms-down/hands-on-hips meshes (e.g. player_textured, A-pose Quaternius) are CULLED, not trained on (see project_mesh_intersection_fix)",
    "Spot-checked via the rendered PNGs: subjects centered, neutral bg, even light, no clipping, AND no movable part touching the body",
    "A manifest lists which meshes contributed, the view distribution, and which were culled for fused/contacting limbs"
  ],
  "steps": [
    "Select meshes that are clean, full-body, humanoid-ish (skip broken/partial)",
    "render_multiview.py --src ... --out E:/ai-training/datasets/mv_ortho",
    "Review a sample; cull bad renders; write manifest"
  ],
  "passes": false
}
```

### Phase 2: Caption + train

```json
{
  "id": "M3",
  "category": "feature",
  "priority": 2,
  "description": "Caption the mv_ortho set with trigger + per-view tag (reuse caption.py, add view tag from filename)",
  "files": ["scripts/train_lora/caption.py", "scripts/train_lora/datasets/mv_ortho_manifest.md"],
  "acceptance_criteria": [
    "Every image has a .txt caption prefixed with trigger mv_ortho, a view tag derived from the filename (e.g. 'front view'/'side view'/'back view'), AND pose tags reinforcing limb separation ('wide T-pose, arms outstretched, fingers spread, legs apart')",
    "Florence2 content caption appended after the tags; idempotent (skips existing .txt)",
    "Captions describe the subject neutrally; the ortho/clean framing is implicit in the consistent dataset",
    "Existing caption.py tests still pass; any new view-tag logic is covered"
  ],
  "steps": [
    "Add a --view-from-filename option (or a thin post-pass) mapping __front/__side/__back to view tags",
    "caption.py --dir E:/ai-training/datasets/mv_ortho --trigger mv_ortho",
    "Run prep_dataset.py to normalize into the ai-toolkit layout if needed"
  ],
  "passes": false
}
```

```json
{
  "id": "M4",
  "category": "feature",
  "priority": 2,
  "description": "Train the mv_ortho Flux LoRA via launch_train.py (stop ComfyUI first to free the 24GB)",
  "files": ["scripts/train_lora/output/mv_ortho/"],
  "acceptance_criteria": [
    "ComfyUI stopped before launch; training confirmed on GPU 1 via nvidia-smi",
    "launch_train.py --dataset E:/ai-training/datasets/mv_ortho --name mv_ortho (rank 16, ~1500 steps, save per epoch)",
    "Per-epoch checkpoints + a final mv_ortho.safetensors on E:/ai-training/flux-output/mv_ortho/",
    "No OOM; sample images during training trend toward clean ortho framing"
  ],
  "steps": [
    "Stop ComfyUI (free 24GB)",
    "launch_train.py ... ; monitor in background, verify device 1",
    "Collect checkpoints"
  ],
  "passes": false
}
```

### Phase 3: Eval (2D grid + Hunyuan3D mesh comparison) + deploy

```json
{
  "id": "M5",
  "category": "testing",
  "priority": 3,
  "description": "Eval: 2D grid (base vs LoRA) AND base-vs-LoRA Hunyuan3D mesh comparison",
  "files": ["scripts/train_lora/eval/mv_ortho_grid.md"],
  "acceptance_criteria": [
    "Restart ComfyUI on the 3090 Ti; lora_eval_grid.py --only mv_ortho across strengths 0.6/0.8/1.0 on character prompts",
    "2D judge verdict: LoRA produces cleaner/more-orthographic T-pose framing vs base at fixed seeds",
    "3D test: feed the best base front image AND the best LoRA front image through Hunyuan3D; import both meshes via blender-mcp; compare watertightness/silhouette/artifacts with viewport screenshots",
    "LIMB SEPARATION check: confirm the LoRA's mesh has separable hands/arms/legs (no fusion to torso/hips/each other) — the core reason for this LoRA; base will typically fuse them",
    "Verdict names a winning (checkpoint, strength) AND states whether the LoRA's mesh is measurably cleaner AND more separable than base"
  ],
  "steps": [
    "Restart ComfyUI; run the 2D grid; pick the winning cell",
    "Generate matched base + LoRA front images at a fixed seed",
    "Run both through Hunyuan3D (comfyui-mcp or blender-mcp); import + screenshot both meshes",
    "Record the combined 2D+3D verdict in eval/mv_ortho_grid.md"
  ],
  "passes": false
}
```

```json
{
  "id": "M6",
  "category": "feature",
  "priority": 4,
  "description": "Deploy winning mv_ortho LoRA + document the Hunyuan3D front-end use in README + art-to-rig-ralph",
  "files": ["scripts/train_lora/README.md", "D:/Projects/ComfyUI/models/loras/style/"],
  "acceptance_criteria": [
    "Winning mv_ortho.safetensors copied to ComfyUI/models/loras/style/ with a sidecar note (trigger mv_ortho + recommended strength)",
    "Smoke-tested: generate a clean front T-pose via generate_image_lora, confirm Hunyuan3D ingests it well",
    "README documents the renderer + how to rebuild the dataset from any mesh folder, and how to use mv_ortho as the art-to-rig Hunyuan3D front-end",
    "Cross-link added in pipelines/art-to-rig-ralph (point its concept-art step at this LoRA)"
  ],
  "steps": [
    "Copy + sidecar-note the winner",
    "Smoke-test through generate_image_lora -> Hunyuan3D",
    "Update README + art-to-rig-ralph cross-link"
  ],
  "passes": false
}
```
