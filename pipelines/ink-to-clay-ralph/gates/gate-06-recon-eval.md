# Gate 6 — RECON-EVAL (the one that matters)

Advance / declare complete only if ALL hold:

- [ ] Each held-out subject's A output AND B output were fed into
      `trellis2_image_to_3d`, plus the soapbox-baseline clay for comparison.
- [ ] Each mesh passed `scripts/mesh_product_check.py` (or its defects are
      documented) — clean, watertight-ish, good silhouette.
- [ ] The winning approach reconstructs **at least as cleanly as the baseline**,
      AND holds on the out-of-training subject (generalization proven, not
      assumed).
- [ ] `output/recon_report.json` records per-subject A/B/baseline mesh verdicts.
- [ ] Deliverables shipped: both LoRAs (E: + deployed), both workflow JSONs, a
      README/DELIVERABLES with recommended denoise/weights, and 3–5 before/after
      examples INCLUDING ≥1 TRELLIS reconstruction render.
- [ ] `pipeline-state.json` all stages `gate_passed: true`; promise
      **`INK TO CLAY COMPLETE`** emitted.

Fail → the image looking clay-ish is NOT enough. If the mesh is worse than
baseline, iterate the winning approach (denoise/weight, pair quality, or Kontext
instruction) until the reconstruction clears.
