# Stage 6 — RECON-EVAL (the TRELLIS acceptance test + ship)

**Goal:** the gate that matters — prove the clay outputs reconstruct into clean
meshes, pick A vs B, and ship the deliverables. ComfyUI UP (TRELLIS.2 installed).

## Do

1. For each held-out subject, feed BOTH the A output and the B output into
   `trellis2_image_to_3d` (`workflows/mcp/trellis2_image_to_3d.json`). TRELLIS.2
   blocks the HTTP server 10+ min per recon — trust the job's own DONE, do not
   kill a busy ComfyUI (project_trellis_reconstruction_blocks_server).
2. Also reconstruct a **baseline**: a clay image made the current way
   (soapbox_char_final_v1 + mv_ortho) for the same subject.
3. Run each mesh through `scripts/mesh_product_check.py` (weld/manifold/watertight
   /silhouette). Compare: does A and/or B reconstruct **at least as cleanly** as
   the baseline? Does it hold on the out-of-training subject (generalization)?
4. Pick the winner (usually B); wire it as the pipeline default in the README.
5. **Ship deliverables:**
   - both LoRAs on `E:/ai-training/flux-output/ink_to_clay_v1_{a,b}*` (+ deployed
     copies in `ComfyUI/models/loras/`),
   - `output/workflow_infer_a.json` + `output/workflow_infer_b.json`,
   - a `DELIVERABLES.md` / update this pipeline's README with recommended
     denoise/weights per approach,
   - 3–5 before/after examples INCLUDING at least one TRELLIS reconstruction
     render (`output/recon/*.png`).
6. Emit the completion promise **`INK TO CLAY COMPLETE`**.

## Output artifacts
- `output/recon/*.glb` + render PNGs, `output/recon_report.json`
  (per-subject: A/B/baseline mesh pass + silhouette note),
- `DELIVERABLES.md`, updated README, `pipeline-state.json` fully `gate_passed`.

→ Gate: `gates/gate-06-recon-eval.md`.
