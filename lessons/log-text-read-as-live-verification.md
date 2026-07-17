---
title: Log text read as live probe output — a "verified" claim that never ran
severity: high
tags: [verification, bash, install, false-positive, gate]
source: hand-authored
created: 2026-07-17
project: comfyui-toolchain
---

## Symptom

A prerequisite task (TX0b: "SDXL trainer installed and GPU-verified") was
closed as **done and verified** when the thing did not exist at all. The
2026-07-17 sequence:

```bash
tail -20 /e/ai-training/sd_scripts_install.log | head -12
ls /e/ai-training/sd-scripts/venv/Scripts/python.exe 2>/dev/null && \
  /e/ai-training/sd-scripts/venv/Scripts/python.exe -c "import torch; print('torch', ...)"
```

Output included `torch 2.4.0+cu124 cuda True NVIDIA GeForce RTX 3090 Ti` — read
as the live probe succeeding. It was not: the `ls` failed (no venv), `&&`
short-circuited, the probe **never ran**, and that line was text *inside the
install log* from a June run. The venv had been deleted since. The error
surfaced only at training launch ("system cannot find the file specified"),
after the task was already marked passed and committed.

## Root cause

A log of a past successful verification contains, verbatim, the text a present
verification would print. Mixing log-reading and live-probing in one command
makes those two indistinguishable in the combined output — and `&&`
short-circuits print nothing, so a skipped probe looks identical to a probe
that produced no line of its own. Confirmation bias does the rest: the expected
string appeared, so the check "passed."

## Mitigation

1. **Never mix log-reading and live-probing in the same command.** Read logs
   for history; probe for state; separate invocations.
2. **Make probe output self-labeling** so it cannot be confused with anything
   else: `echo "LIVE_PROBE: $(python -c '...')"` — a marker string the log
   cannot contain.
3. **Assert the artifact before believing the claim.** For an install:
   `test -f "$VENV/Scripts/python.exe" || { echo "MISSING VENV"; exit 1; }` as
   its own statement, not an `&&` prefix whose failure is silent.
4. **A "verified" gate needs output that could only come from this run.** If
   the evidence could plausibly be a replay (log text, cached file, prior
   screenshot), it is not verification — re-run and watch it happen.
5. When a task's status derives from a document rather than an execution, say
   so in the close-out ("closed on the strength of the install log") — that
   phrasing alone would have caught this.

## Notes (optional)

Related: curate-before-benchmark (evidence quality gates the verdict),
perceptual-ground-truth-needs-human-signoff. The install itself had a real
second bug this masked (numpy 2.x breaks torch 2.4 imports) — now pinned in
`E:/ai-training/install_sd_scripts.sh` step 4b; that script is idempotent, so
recovery from a vanished venv is one command.
