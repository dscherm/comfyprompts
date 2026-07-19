# Gate 2 — TRAIN-A · GPU-GATED

- [ ] **Human GPU-free confirmation was obtained BEFORE training started** (record
      it in the stage log). No confirmation → gate fails regardless of output.
- [ ] `E:/ai-training/flux-output/ink_to_clay_v1_a/` holds real checkpoints
      (multiple steps, non-trivial size) — not a ~7-min no-op resume.
- [ ] Trained on the **clay** dir only, flat layout, trigger `clay3d`.
- [ ] A quick base-vs-LoRA text2img smoke at `clay3d` shows the clay look emerging
      (sanity only; real eval is Stage 3).
- [ ] ComfyUI restarted (`run_3090ti.ps1`) and `generate_image` works again.

Fail → adjust caps/steps/dataset and retrain to a fresh output name.
