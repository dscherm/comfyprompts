# Gate 5 — INFER-B

- [ ] `output/workflow_infer_b.json` loads + runs: single-pass Kontext edit
      (reference = ink, fixed instruction, + Kontext LoRA), no denoise knob.
- [ ] Run on the SAME 3–5 held-out drawings as Stage 3 (so A vs B is comparable).
- [ ] Output preserves composition AND achieves the clay look (`judge_image` +
      montage); at least as faithful as Approach A on the same inputs.
- [ ] `output/before_after_b/` + `output/infer_b_montage.png` exist.

Fail → adjust the instruction/checkpoint or revisit the pair data quality.
