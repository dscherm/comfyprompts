---
title: Evaluation lanes ran on a test subject the user hadn't approved
severity: medium
tags: [eval, bake-off, human-in-the-loop, inputs]
source: hand-authored
created: 2026-07-16
project: comfyui-toolchain
---

## Symptom

A full evaluation lane (rig + diagnostic renders) ran against a test subject
chosen by the agent, and the user then rejected the subject itself: the
berserkr's fused fists and fur silhouette made rig deformation illegible,
and a candidate textured variant had pre-deformed hands. The user supplied
a better mesh (exemplar.obj: clean spread-finger hands, legible cloth) and
the lane was re-staged, re-rigged, and re-rendered. Rework observed in the
2026-07-16 rig bake-off (RB1/RB3).

## Root cause

For evaluation work, the input subject IS part of the ground truth — a
subject that hides or pre-contains the failure mode being judged
invalidates every lane run on it. Subject choice is a curation call, and
(per perceptual-ground-truth-needs-human-signoff) curation calls belong to
the human. The agent optimized for "already pipeline-proven" assets, which
selects for provenance, not legibility.

## Mitigation

1. Before running any evaluation lane, render a quick preview of each
   proposed test subject (one full-body still is enough) and get the
   user's explicit approval of the subject list.
2. Select subjects for LEGIBILITY of the property under test (visible
   joints, distinct limbs, no pre-existing artifacts in the judged
   regions), not for convenience or provenance.
3. When the user swaps a subject mid-run, re-run all affected lanes on the
   new subject rather than mixing subjects across lanes; keep old-lane
   outputs as secondary data, clearly labeled.

## Notes (optional)

Related: perceptual-ground-truth-needs-human-signoff (same principle,
applied to outputs), curate-before-benchmark (same principle, applied to
corpora).
