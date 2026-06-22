# plan.md — Reusable Flux LoRA Training Harness (Berserkr-style PoC)

Task queue for Ralph Loop. JSON blocks in triple-backtick fences.
Only ONE task per iteration. Mark `"passes": true` when complete.
Spec: `.ralph/spec.md`. All training runs on GPU 1 (3090 Ti) via
`CUDA_VISIBLE_DEVICES=1`.

---

## Task Format (template — not a real task)

<!-- Template for reference only. Do NOT pick this up as a task.
{
  "id": "T0",
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

## Prior pipeline (ComfyPrompts + Blender MCP integration) — COMPLETE

All earlier setup/integration/workflow-drift tasks shipped (see git history
through `bf00a3e` and the fully-checked `fix_plan.md`). This plan supersedes
them with the LoRA-training PoC.

---

### Phase 1: Trainer + harness scaffolding

```json
{
  "id": "T1",
  "category": "setup",
  "priority": 1,
  "description": "Install ostris/ai-toolkit in its own venv and confirm it runs on GPU 1 (3090 Ti)",
  "files": ["scripts/train_lora/README.md"],
  "acceptance_criteria": [
    "ai-toolkit cloned to a dedicated dir with its OWN venv (Python 3.11, its pinned torch — NOT the ComfyUI venv)",
    "CUDA_VISIBLE_DEVICES=1 python -c 'import torch; print(torch.cuda.get_device_name(0))' prints 'NVIDIA GeForce RTX 3090 Ti'",
    "ai-toolkit's run script imports without error in that venv",
    "scripts/train_lora/README.md records the install path, venv path, and the CUDA_VISIBLE_DEVICES=1 contract"
  ],
  "steps": [
    "Clone github.com/ostris/ai-toolkit to a dedicated dir (e.g. D:\\Projects\\ai-toolkit)",
    "Create its own venv, install per its requirements (do not reuse ComfyUI venv)",
    "Verify torch sees the 3090 Ti as device 0 under CUDA_VISIBLE_DEVICES=1",
    "Note install/venv paths in scripts/train_lora/README.md"
  ],
  "passes": true
}
```

```json
{
  "id": "T2",
  "category": "feature",
  "priority": 1,
  "description": "Build scripts/train_lora/prep_dataset.py — curate any image set into an ai-toolkit training folder",
  "files": ["scripts/train_lora/prep_dataset.py"],
  "acceptance_criteria": [
    "Takes a source dir/glob (or a list file) + an output training dir + image count cap",
    "Copies/normalizes images (RGB, strips alpha, optional max-edge resize), skips dupes/corrupt files",
    "Writes the ai-toolkit-expected folder layout",
    "Dataset-agnostic: nothing Berserkr-specific hardcoded; runs on an arbitrary dir",
    "Has a unit test under packages/.../tests or tests/ that runs on a tiny fixture set"
  ],
  "steps": [
    "Implement CLI with argparse: --src, --out, --max-images, --max-edge",
    "Image normalization + dedupe + manifest",
    "Add a pytest covering the prep on a 3-image fixture"
  ],
  "passes": true
}
```

```json
{
  "id": "T3",
  "category": "feature",
  "priority": 1,
  "description": "Build scripts/train_lora/caption.py — Florence2 auto-caption with trigger-word prefix",
  "files": ["scripts/train_lora/caption.py"],
  "acceptance_criteria": [
    "For each image in a training dir, calls the caption_image (Florence2) workflow via ComfyUI REST",
    "Writes a sibling .txt caption per image, prefixed with a configurable trigger word (e.g. brsk_style)",
    "Idempotent: skips images that already have a .txt",
    "Graceful failure if ComfyUI (localhost:8188) is unreachable — clear error, no half-written files"
  ],
  "steps": [
    "Reuse the existing caption_image workflow + REST pattern (see scripts/ for the API helper)",
    "CLI: --dir, --trigger, --prepend/--append",
    "Write .txt sidecars, log a count summary"
  ],
  "passes": true
}
```

### Phase 2: Curate the PoC dataset

```json
{
  "id": "T4",
  "category": "feature",
  "priority": 2,
  "description": "Curate ~100-150 best Berserkr renders into a captioned training set (trigger brsk_style)",
  "files": ["scripts/train_lora/datasets/berserkr_style/"],
  "acceptance_criteria": [
    "~100-150 images selected across Creature/Character/Equipment from D:\\Projects\\ComfyUI\\output (Berserkr_*)",
    "Run through prep_dataset.py (T2) then caption.py (T3)",
    "Every image has a brsk_style-prefixed .txt caption; a few spot-checked captions are hand-corrected",
    "A short manifest lists what was included and why (category balance)"
  ],
  "steps": [
    "Select the cleanest renders, balanced across categories",
    "prep_dataset.py --src ... --out datasets/berserkr_style",
    "caption.py --dir datasets/berserkr_style --trigger brsk_style",
    "Spot-check + hand-fix ~10 captions"
  ],
  "passes": false
}
```

### Phase 3: Train + evaluate

```json
{
  "id": "T5",
  "category": "feature",
  "priority": 2,
  "description": "Build scripts/train_lora/launch_train.py — generate ai-toolkit Flux config + launch on GPU 1",
  "files": ["scripts/train_lora/launch_train.py"],
  "acceptance_criteria": [
    "Generates an ai-toolkit Flux-LoRA config (rank 16, 512-768px, batch 1, grad-checkpoint, ~1500 steps, save per epoch) from CLI args",
    "Launches training with CUDA_VISIBLE_DEVICES=1, base = flux1-dev-fp8",
    "Dataset dir and output LoRA name are parameters (reusable for any dataset)",
    "Prints the resolved config path + a tail-the-log hint; safe to run in background"
  ],
  "steps": [
    "Template the ai-toolkit YAML/JSON config from args (--dataset, --name, --steps, --rank)",
    "Subprocess-launch ai-toolkit's run script under CUDA_VISIBLE_DEVICES=1",
    "Document background-run + nvidia-smi verification in README"
  ],
  "passes": true
}
```

```json
{
  "id": "T6",
  "category": "feature",
  "priority": 3,
  "description": "Run the Berserkr-style PoC training to produce a Flux LoRA",
  "files": ["scripts/train_lora/output/berserkr_style/"],
  "acceptance_criteria": [
    "Training launched via launch_train.py on the berserkr_style dataset, confirmed on GPU 1 via nvidia-smi",
    "Per-epoch checkpoints written; at least one final berserkr_style .safetensors produced",
    "No OOM; system stayed responsive (ComfyUI on GPU 0 untouched)"
  ],
  "steps": [
    "launch_train.py --dataset datasets/berserkr_style --name berserkr_style",
    "Monitor in background, verify device 1 placement",
    "Collect checkpoints"
  ],
  "passes": false
}
```

```json
{
  "id": "T7",
  "category": "testing",
  "priority": 3,
  "description": "Eval-grid base Flux vs +brsk_style LoRA; AI judge picks winning checkpoint/strength",
  "files": ["scripts/train_lora/eval/berserkr_style_grid.md"],
  "acceptance_criteria": [
    "Uses scripts/lora_eval_grid.py to render fixed prompt+seed cells: base vs LoRA at strengths 0.6/0.8/1.0 across the best 2-3 checkpoints",
    "AI-judge verdict ranks cells and names a winning (checkpoint, strength)",
    "Verdict shows the LoRA measurably shifts output toward the Berserkr aesthetic vs base"
  ],
  "steps": [
    "Pick 3-4 representative prompts + fixed seeds",
    "Run lora_eval_grid.py across checkpoints x strengths",
    "Record judge verdict + winner in eval/berserkr_style_grid.md"
  ],
  "passes": false
}
```

```json
{
  "id": "T8",
  "category": "feature",
  "priority": 4,
  "description": "Deploy winning LoRA + finalize reusable-harness README",
  "files": ["scripts/train_lora/README.md", "D:/Projects/ComfyUI/models/loras/style/"],
  "acceptance_criteria": [
    "Winning .safetensors copied to ComfyUI/models/loras/style/ with a sidecar note (trigger brsk_style + recommended strength)",
    "Smoke-tested through the generate_image_lora workflow (one good sample)",
    "README documents the full reusable loop end-to-end: how to point prep/caption/train/eval at ANY new dataset dir with no code changes",
    "README cross-links comfy-improve-model Path 3 and the multiview-consistency 3D use case"
  ],
  "steps": [
    "Copy + sidecar-note the winner",
    "Smoke-test via generate_image_lora",
    "Write the reusable-harness README"
  ],
  "passes": false
}
```
