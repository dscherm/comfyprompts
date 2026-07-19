# Gate 3 — INFER-A

- [ ] `output/workflow_infer_a.json` loads in ComfyUI and runs end-to-end on a
      fresh drawing (img2img: LoadImage → VAEEncode → KSampler(+clay LoRA) →
      VAEDecode).
- [ ] On 3–5 held-out drawings (incl. ≥1 out-of-training subject): output
      **preserves composition** (same subject/pose/proportions) AND achieves the
      clay look (`judge_image` + montage).
- [ ] The recommended `denoise_a` + LoRA weight are chosen from the sweep and
      recorded in `pipeline-state.json`.
- [ ] If silhouettes drift at higher denoise, the lineart/canny ControlNet toggle
      demonstrably fixes it.
- [ ] `output/before_after_a/` + `output/infer_a_montage.png` exist.

Fail → adjust denoise/weight/ControlNet or pick a different Stage-2 checkpoint.
