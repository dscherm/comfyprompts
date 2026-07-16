---
title: Agent self-confirmation of perceptual ground truth is self-marking
severity: high
tags: [eval, exemplars, human-in-the-loop, visual-qa]
source: hand-authored
created: 2026-07-16
project: comfyui-toolchain
---

## Symptom

A task producing visual/perceptual ground truth (exemplar pairs, labeled
eval images) is committed and marked `passes: true` on the agent's own
"visually confirmed" check — then the human reviews the images and rejects
them. Observed on VL4 (2026-07-16): the berserkr knee_bend pair shipped
with an unattached left foot in BOTH twins (a pre-existing artifact that
violates the pair's one-variable contract), and the joint crops were too
tight for the human to verify or refute region claims made about them
(a claimed neck bulge with no neck in frame). Churn-after-done: the task
had to be reopened as a new curation task (VL9) and the downstream probe
verdict downgraded.

## Root cause

The agent confirming its own generated ground truth is self-marking — the
same eyes that missed the artifact during generation miss it during
confirmation. And tight "detail" framing optimizes for showing the intended
delta while making every OTHER claim about the image unadjudicable, so
flaws and confounds outside the crop are structurally invisible to review.

## Mitigation

1. Any task whose deliverable is perceptual ground truth (exemplars,
   labeled renders) gets a human per-item approval step BEFORE
   `passes: true` — present the items in a gallery, collect
   approve/reject/unadjudicated per item, and record verdicts in the
   artifact's manifest (`curation` block: status, by, date, reason).
2. Render candidates wide enough that every region a claim could cite is
   in frame: full-body view PLUS joint/detail view, never detail-only.
3. Treat "agent visually confirmed" as a pre-filter only — it can reject
   candidates, it can never approve them into the corpus.

## Notes (optional)

Does NOT apply to deterministic artifacts a test can verify (file exists,
schema valid, pixel-diff nonzero) — those stay agent-gated. Related:
curate-before-benchmark (verdicts from uncurated corpora), VL9 in plan.md
for the concrete curation schema.
