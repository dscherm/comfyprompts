# Stage 5 — INFER-B (Kontext single-pass edit workflow)

**Goal:** a ComfyUI FLUX Kontext workflow that converts an ink drawing to clay in
one pass with the Stage-4 LoRA — no denoise knob.

## Do

1. Deploy the winning Stage-4 checkpoint; confirm `list_loras`.
2. Build the Kontext graph (save JSON):
   reference image = ink, prompt = `convert to a clean 3D clay render, plain grey
   background`, + Kontext LoRA → single-pass output.
3. Run the SAME 3–5 held-out drawings used in Stage 3 (incl. the out-of-training
   subject) so A and B are directly comparable at Stage 6.
4. Judge (`judge_image` + montage): composition preserved AND clay look achieved,
   no denoise fiddling.

## Output artifacts
- `output/workflow_infer_b.json`
- `output/before_after_b/*.png` (same subjects as A) + `output/infer_b_montage.png`.

→ Gate: `gates/gate-05-infer-b.md`.
