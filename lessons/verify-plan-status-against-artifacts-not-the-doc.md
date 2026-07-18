---
title: When acting on a plan/status doc, verify against the actual artifacts — docs drift
severity: medium
tags: [planning, process, verification, docs, review]
source: hand-authored
created: 2026-07-18
project: comfyui-toolchain
---

## Symptom

Asked to review the business plan for gaps, the plan's §4.6 `ANIM-PRODUCT` said the
animation chain was the "weakest link — only a single locomotion clip survives."
The actual state (git log + `pipelines/animate-ralph/validation/VALIDATION.md` +
the berserkr work dir) was a **9-clip barbarian Humanoid set validated live in
Unity** plus a **23-clip berserkr Meshy set** — two working multi-clip routes.
Acting on the doc's status would have mis-scoped the work (re-hardening a chain
that already clears) and mis-reported readiness.

## Root cause

Status/plan docs are written at a point in time and **drift** as the work advances;
the doc is a claim, not the ground truth. A months-old "❌ / weakest link" line
survives long after the capability lands, especially for the parts of a project
that moved fastest.

## Mitigation

1. **Before acting on a status doc, verify the claim against artifacts:** `git log`
   for the relevant commits, the pipeline's own validation/VALIDATION.md, the product
   dirs on disk, a passing/failing gate test. Trust the artifacts over the prose.
2. **When you find drift, fix the doc as part of the task** (mark the real status,
   note the date + evidence) — an updated plan is a deliverable, not a side quest.
3. Same discipline as [[log-text-read-as-live-verification]]: a status line is
   "read", not "verified" — re-establish it from something that could only be true now.
