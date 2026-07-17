---
title: When a generalization regresses a working case, revert immediately — don't push deeper
severity: high
tags: [process, refactor, regression, git, discipline]
source: hand-authored
created: 2026-07-17
project: comfyui-toolchain
---

## Symptom

A change meant to GENERALIZE working code (handle one more case) breaks the
cases that already worked, and instead of reverting, the fix gets edited further
to chase the regression — each edit deepening the hole. Observed 2026-07-17: the
rig scanner's `up` axis was hardcoded `(0,0,1)`, correct for the two shipping
rigs (glTF, Z-up). Trying to generalize it (measure `up` from geometry, to also
support AccuRIG's axis-swapped FBX) made the up-detector grab the ARMS instead of
the legs, so BOTH working rigs produced garbage frames. Several more edits
followed before stopping and `git checkout`-ing back to the last-good commit.

## Root cause

A regression in a previously-passing case is qualitatively different from a
normal bug: it means the new approach is wrong for the general population, not
just incomplete. Continuing to edit treats it as a debugging opportunity when it
is actually a STOP signal. Sunk-cost on the in-progress generalization ("I'm
almost there") keeps the edits coming.

## Mitigation

1. **The moment a generalization makes a green case fail, revert to green.**
   `git checkout <file>` / `git stash` back to the last-good commit, then
   reattempt with a smaller scope.
2. **Commit working states frequently** so revert is one command and costs
   nothing — the whole strategy depends on green being cheap to return to.
3. **Re-scope instead of re-generalizing.** If the working cases share a
   property the new case lacks (here: Z-up vs axis-swapped), keep the working
   assumption and record its validity (`valid_for: z-up rigs`) rather than
   forcing one code path to cover both. A narrow, honest limitation beats a
   broad, broken generalization.
4. **A regression test is a full stop, not a warning.** Verify the previously
   working cases after any "make it more general" change, before committing.

## Notes (optional)

The reverted work is not wasted — the failed attempt is evidence about WHY the
general case is hard, worth a one-line note. Related:
curate-before-benchmark and log-text-read-as-live-verification (other
"stop and check before proceeding" disciplines).
