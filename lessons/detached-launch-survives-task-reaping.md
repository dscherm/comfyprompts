---
title: Long GPU jobs launched as a run_in_background bash task get reaped mid-run — launch them detached via Start-Process
severity: high
tags: [training, ai-toolkit, background, process, windows, gpu, harness]
source: hand-authored
created: 2026-07-20
project: comfyui-toolchain
---

## Symptom

A FLUX Kontext training (ai-toolkit `run.py`) launched with the Bash tool's
`run_in_background: true` was **killed three times**, each within minutes of
starting — status `killed`, not `completed`, with NO error in the log. Every
time it had loaded the model cleanly and was about to step. The monitoring
watchers (also `run_in_background` bash) were killed too. It was not an OOM, not
a crash, and not a stop I issued.

## Root cause

The long-running child process (a heavy, hours-long GPU job) tied to a
`run_in_background` bash task gets reaped when the harness manages/cleans up that
task's process tree. Short background tasks finish before this bites; a
multi-hour trainer does not. The training itself is healthy — the *wrapper* is
the problem.

## Mitigation

1. **Launch long GPU jobs DETACHED, not via `run_in_background`.** On Windows use
   PowerShell `Start-Process` with the env set inline and output redirected to
   files:
   ```powershell
   $env:CUDA_DEVICE_ORDER="PCI_BUS_ID"; $env:CUDA_VISIBLE_DEVICES="1"
   Start-Process -FilePath <venv-python> -ArgumentList <run.py>,<config> `
     -WorkingDirectory <dir> -RedirectStandardOutput out.log `
     -RedirectStandardError out.err -WindowStyle Minimized -PassThru
   ```
   The `-PassThru` PID is your handle. This process is decoupled from the task
   manager and survives.
2. **Monitor with FOREGROUND checks**, not background watchers (they get reaped
   too): poll the redirected log + `nvidia-smi` + a `Get-Process -Id <pid>`
   liveness check on demand. A dead PID + released GPU = finished (or crashed —
   check the .err).
3. There is **no completion notification** for a detached process — check back
   explicitly. See also [[cuda-device-order-pci-bus-id]] (set the GPU env in the
   same Start-Process) and [[hf-transfer-for-large-gated-downloads]].
