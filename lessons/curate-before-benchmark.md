---
title: Benchmarking on an uncurated corpus yields verdicts that don't survive review
severity: medium
tags: [eval, benchmark, ground-truth, ordering]
source: hand-authored
created: 2026-07-16
project: comfyui-toolchain
---

## Symptom

A benchmark/probe runs on ground truth that hasn't been human-reviewed and
produces a decisive verdict — then the corpus fails review and the verdict
must be retracted or downgraded. Observed on VL7 (2026-07-16): a NO-GO on
local VLM rig-deformation judging was issued from the VL4 corpus; hours
later the human rejected parts of that corpus (shared artifact in both
twins, unadjudicable crops) and the NO-GO had to be downgraded to
provisional in the findings doc and plan.

## Root cause

A verdict is only as strong as its ground truth. Running the cheap
benchmark before the (also cheap) human curation pass feels faster, but
inverts the dependency: flaws in the corpus become confounds in the result
(a judge failing on a pair whose "good" twin contains a defect is not
evidence about the judge), and any decision keyed to the verdict inherits
the retraction.

## Mitigation

1. Order the pipeline: generate candidates → human curates (per-item
   approve/reject) → benchmark runs ONLY on approved items. Never the
   reverse.
2. If a benchmark has already run on uncurated data, label its verdict
   PROVISIONAL in the findings doc and in plan.md at the moment of
   writing, not retroactively.
3. Re-run the benchmark whenever the curated set changes; the findings doc
   records which corpus revision (commit) the verdict was computed on.

## Notes (optional)

The probe-before-invest pattern (VL7's "cheap falsifier first") is still
right — this lesson only fixes WHERE curation sits relative to it.
Related: perceptual-ground-truth-needs-human-signoff.
