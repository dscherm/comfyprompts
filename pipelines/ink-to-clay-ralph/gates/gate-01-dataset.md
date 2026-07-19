# Gate 1 — DATASET

Advance only if ALL hold:

- [ ] `E:/ai-training/datasets/ink_to_clay_v1/ink/` and `.../clay/` each contain
      50–150 PNGs, and **every filename in `ink/` has an exact match in `clay/`**
      (aligned pairs — verify programmatically, not by eye).
- [ ] Each pair is the SAME subject at the SAME seed (spot-check ≥5 pairs).
- [ ] Clay images meet the target look: plain neutral-grey/white bg, even light,
      no cast shadow/ground, full subject, clear silhouette (`judge_image` coarse
      pass + montage).
- [ ] Ink images are flat high-contrast linework/cel (clearly the "before").
- [ ] `output/pairs_montage.png` exists and is **human-approved** (self-confirm ≠
      approval — feedback_exemplar_human_curation).
- [ ] Subject list includes non-character props/creatures (generalization) and at
      least one held-out subject reserved for eval.

Fail → fix generation (seeds, prompts, weights) and re-run Stage 1.
