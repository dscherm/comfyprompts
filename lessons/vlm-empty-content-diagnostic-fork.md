---
title: Empty content from a thinking-enabled local VLM is a diagnostic fork, not a score
severity: medium
tags: [ollama, vlm, qwen3-vl, num_ctx, thinking, dual-gpu]
source: hand-authored
created: 2026-07-16
project: comfyui-toolchain
---

## Symptom

An ollama vision model with `think: true` returns an empty `content` field
(with a large `thinking` field) on some inputs. Scored naively, this counts
as a model failure — but it is ambiguous between (a) context exhaustion
(num_ctx too small for images + prompt + thinking) and (b) genuine
non-convergence (runaway thinking that never terminates in an answer).
Observed on the VL7 probe (2026-07-16): qwen3-vl:8b returned empty content
on 3/6 pairs at num_ctx 8192; only a re-run at 20480 disambiguated — it was
non-convergence (80k+ chars of circular thinking, still no answer).

**THIRD BRANCH (added 2026-07-16): cold model load, with thinking OFF.**
Empty content is NOT always a thinking/num_ctx problem. On the accent-judge
probe — `think: false`, num_ctx 4096 — the FIRST call after a cold model load
returned empty content on both qwen3-vl:8b (33s, loading 6GB) and
qwen3-vl:32b (113s, loading 20GB): in each run, image 1 of 9 came back empty
and every subsequent call parsed cleanly. Neither branch above applies —
there is no thinking stream to exhaust the context.

Critically it is **INTERMITTENT**: a later cold 8b run did NOT reproduce it
(image 1 scored 6/6 at 13.4s). So you cannot predict which batch silently
loses its first image, and a single clean run does not prove the harness is
sound.

## Root cause

With thinking enabled, the thinking stream competes with the answer for the
same context budget. Truncation-by-ctx and never-converging loops produce
the identical observable (empty content), so a single run at a single ctx
cannot attribute the failure. Separately, ollama defaults some models to
large contexts with heavy VRAM cost: qwen3-vl:32b at its 32768 default is
~29GB — it spills past the 3090 Ti's 24GB onto the 3070 and CPU (>600s per
image); capped at 8192 it runs 23GB, 100% GPU, 60-127s per pair.

## Mitigation

1. Always record `thinking` length and the num_ctx used alongside each
   verdict record, so empty-content cases are auditable.
2. On empty content, re-run that input once at a materially larger num_ctx
   (2.5x) before scoring: still-empty with much longer thinking =
   non-convergence (score as model failure); non-empty = your ctx was too
   small (fix the harness, don't score the model).
3. Cap num_ctx explicitly per model and GPU — never trust the ollama
   default. Verify residency with `ollama ps` (want "100% GPU") or
   /api/ps size_vram/size immediately after the first call, and record it.
4. **Retry once on empty content, unconditionally — even with thinking off.**
   The cold-load branch is intermittent, so a warmup call does not reliably
   prevent it and a clean run does not prove it is absent; only a retry
   covers it. `judge_image`
   (`packages/mcp-server/tools/vlm_judge.py`) does this automatically —
   hand-rolled ollama callers must implement it themselves or they will
   silently drop the first image of some batches.
5. Disambiguate the three branches by what you already logged: thinking
   length > 0 → branch (a)/(b), use the 2.5x re-run above. Thinking empty or
   disabled AND it was the first call after a load (latency dominated by
   model load — 33s/6GB, 113s/20GB) → cold-load branch; just retry.

## Notes (optional)

Disabling thinking avoids the fork but under-elicits the model (VL2
finding) — for capability probes, keep thinking on and pay the
disambiguation cost. GPU numbers above are for the dual-GPU box (3090 Ti
24GB primary, 3070 8GB secondary); recompute for other hardware.
