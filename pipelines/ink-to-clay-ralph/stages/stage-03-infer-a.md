# Stage 3 — INFER-A (img2img workflow + before/after)

**Goal:** a ComfyUI img2img workflow that restyles an input drawing into clay
using the Stage-2 LoRA, preserving composition. No training — ComfyUI UP.

## Do

1. Deploy the winning Stage-2 checkpoint to `ComfyUI/models/loras/style/`
   (`clay3d` trigger sidecar). Confirm `list_loras` sees it.
2. Build the img2img graph (save JSON to `workflows/mcp/` or the pipeline
   `output/`):
   `LoadImage(ink) → VAEEncode → KSampler(denoise 0.55–0.70, clay LoRA @ weight)
   → VAEDecode → SaveImage`.
3. Add an **optional lineart/canny ControlNet** branch from the ink input to lock
   the silhouette at higher denoise; expose it as a toggle.
4. Sweep denoise {0.55, 0.6, 0.65, 0.70} × LoRA weight on 3–5 held-out drawings
   (incl. at least one subject NOT in training). Judge with `judge_image`
   (coarse clay-look call) + a montage; pick the recommended denoise/weight.
5. Record the recommended settings for the README.

## Output artifacts
- `output/workflow_infer_a.json` (+ ControlNet variant)
- `output/before_after_a/*.png` (3–5 pairs) + `output/infer_a_montage.png`
- recommended `denoise_a` + weight written to `pipeline-state.json`.

→ Gate: `gates/gate-03-infer-a.md`.
