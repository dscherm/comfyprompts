---
title: CUDA_VISIBLE_DEVICES=1 alone lands on the 3070 — also set CUDA_DEVICE_ORDER=PCI_BUS_ID for the 3090 Ti
severity: high
tags: [cuda, dual-gpu, training, ai-toolkit, 3090ti, 3070, gpu-selection]
source: hand-authored
created: 2026-07-20
project: comfyui-toolchain
---

## Symptom

A training launched with only `CUDA_VISIBLE_DEVICES=1` (intending the 24GB
3090 Ti) ran on the **8GB RTX 3070** instead: `nvidia-smi` showed GPU 0 (3070)
at 100% / GPU 1 (3090 Ti) idle, and the ai-toolkit config's `device: cuda:0`
mapped to the wrong physical card. On the 8GB 3070, a 24GB Kontext train would
OOM or crawl.

## Root cause

CUDA's **default device order is FASTEST_FIRST**, which enumerates the more
powerful 3090 Ti as `cuda:0` and the 3070 as `cuda:1`. So `CUDA_VISIBLE_DEVICES=1`
selects the *slower* card (3070). `nvidia-smi` uses PCI_BUS_ID order (3070=0,
3090 Ti=1), so the index that looks right in nvidia-smi is backwards under
CUDA's default order. `run_3090ti.ps1` sets **both** vars precisely to fix this;
a hand-rolled launch that sets only `CUDA_VISIBLE_DEVICES` inherits the trap.

## Mitigation

1. **Always set BOTH** when pinning the 3090 Ti:
   `CUDA_DEVICE_ORDER=PCI_BUS_ID` **and** `CUDA_VISIBLE_DEVICES=1`. With
   PCI_BUS_ID order, index 1 = 3090 Ti, matching nvidia-smi.
2. **Verify which physical GPU the job actually landed on** — don't trust the
   env alone. Map process→GPU:
   `nvidia-smi --query-compute-apps=pid,gpu_bus_id,used_memory --format=csv` and
   `nvidia-smi --query-gpu=index,gpu_bus_id,name --format=csv`; bus `:0B:` = 3070,
   `:0C:` = 3090 Ti on this box.
3. Prefer launching via `run_3090ti.ps1` (sets both) where possible; when
   launching ai-toolkit manually, set both in the same `Start-Process` env
   ([[detached-launch-survives-task-reaping]]).
