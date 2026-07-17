---
title: A whole-frame pixel metric cannot separate subject from background — it fails on composition
severity: high
tags: [eval, metrics, visual-qa, vlm, false-negatives]
source: hand-authored
created: 2026-07-16
project: comfyui-toolchain
---

## Symptom

A numeric image metric reports a batch as a near-total failure while the batch is
almost entirely correct. Observed on the occult_providence accent pilots
(2026-07-16): a chroma-coverage metric (`% of frame carrying saturated colour`)
scored pilot v3 **3/10** when the batch was **~10/10 by eye**. Every "failure" was
a false negative — the *characters* were exactly on-spec (a gold crucifix, a green
charm-bottle, crimson blood at the mouth), and the metric was scoring the flat
cyan **background** behind them. The single worst case: a stark monochrome
mortician with no accent at all, sitting on a flat red field, scored "39.1% red
FAIL" — the metric graded the field and never saw the figure.

Worse, the metric's numbers were persuasive enough that the agent trusted them over
its own eyes for a full pilot cycle, and only caught the error after rendering a
montage and looking.

## Root cause

A whole-frame statistic integrates over every pixel and has no notion of figure vs
ground. "Subject is monochrome with one small accent, on a coloured field" and
"subject is flooded with colour" are the same number. The metric is not measuring
the property the spec is about; it is measuring a correlate that decouples the
moment the background stops being neutral.

This is not a threshold-tuning problem. No band on a whole-frame chroma statistic
separates those two images, because the statistic does not contain the information.

## Mitigation

1. **Whole-frame metrics screen for PRESENCE, never for COMPOSITION.** "Is there any
   colour here at all" is a fair question to ask a histogram. "Is the colour in the
   right place, on the right object, and nowhere else" is not.
2. **Use `judge_image` (`packages/mcp-server/tools/vlm_judge.py`) for composition
   claims** — a VLM can be instructed what to ignore ("ignoring the background
   entirely, is the character monochrome with exactly one accent colour?"). On a
   hand-labelled 9-image probe qwen3-vl:8b scored 92% and got the red-field
   mortician 7/7, the exact case the metric failed.
3. **When a metric and a montage disagree, the montage wins.** Render the batch and
   look before acting on a score. A metric that disagrees with your eyes is a
   hypothesis about the metric, not about the images.
4. **State the metric's blind spot in its own docstring**, next to the number it
   returns, so the next reader cannot take the score at face value.

## Notes (optional)

The metric was still worth building: it correctly separated a flooded image (36%)
from a duotone reference (0.11%) where a naive "any chroma" test would have flagged
both. Presence-screening is its real job. The failure was promoting a screen to a
verdict. Related: `perceptual-ground-truth-needs-human-signoff` (agent
self-confirmation of visual claims), `curate-before-benchmark`.
