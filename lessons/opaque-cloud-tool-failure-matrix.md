---
title: Opaque cloud-tool failures — vary one input dimension per attempt, cap, escalate
severity: medium
tags: [mcp, cloud, meshy, coplay, debugging]
source: hand-authored
created: 2026-07-16
project: comfyui-toolchain
---

## Symptom

A third-party cloud tool fails with a generic error and no diagnostics
(coplay's auto_rig_3d_model: "Error: Failed to auto-rig 3D model", nothing
in Unity's console). Blind retries with the same input burn attempts (and
potentially credits) without producing information.

## Root cause

The error surface hides which input constraint (size, format, content
requirement) or service condition (auth, credits, outage) failed. Retrying
unchanged inputs cannot distinguish these; unbounded retry loops are the
documented rabbit-hole failure mode.

## Mitigation

1. Never retry an opaque failure with an identical input. Each attempt
   changes exactly ONE dimension, chosen from the tool's documented
   requirements (2026-07-16 Meshy matrix: 34MB untextured → 4.6MB draco →
   5.9MB +UVs/texture).
2. Check the host application's own logs between attempts (Unity console
   via get_unity_logs; empty = failure is server-side, stop varying
   inputs).
3. Cap at 3-4 attempts. Then stop, record the attempt matrix in the lane/
   task record, and escalate to the user with the specific things only
   they can check (account credits, service dashboards, auth).

## Notes (optional)

If every one-variable change fails identically, the failure is almost
certainly NOT the input — that conclusion is the matrix's value. Related:
the browser-automation rabbit-hole rule (2-3 attempts then ask) in the
harness guidance.
