---
title: "Node class not installed" + the workflow-validation gate = ComfyUI launched with the WRONG Python
severity: high
tags: [comfyui, custom-nodes, venv, gate, hunyuan3d, environment]
source: hand-authored
created: 2026-07-18
project: comfyui-toolchain
---

## Symptom

For many sessions, `tests/test_workflow_validation.py::test_workflows_against_live_object_info`
FAILED with every hunyuan3d workflow reporting `node class not installed on this
ComfyUI (check custom_nodes or fix the class name)` for `Hy3DModelLoader`,
`Hy3DGenerateMesh`, etc. (it's in the handoff/precompact of every session). The
custom-node files were present in `custom_nodes/ComfyUI-Hunyuan3DWrapper`, so it
looked installed — but its nodes never appeared in `/object_info`.

## Root cause

**ComfyUI was launched with the wrong Python interpreter.** The running process on
`:8188` was the global `C:\Users\...\Programs\Python\Python311\python.exe`
(torch 2.11.0+cu128), NOT the documented venv `D:\Projects\ComfyUI\venv`
(torch 2.9.1+cu126, which `run_3090ti.ps1` uses). The global env was **missing the
wrapper's deps** (`accelerate`, then `trimesh`, …). A custom node whose top-level
import raises `ModuleNotFoundError` at ComfyUI startup is **silently skipped** — its
`NODE_CLASS_MAPPINGS` never register — so any workflow referencing those classes
fails live validation. The venv had all the deps; the global env didn't.

## Mitigation

1. **Always launch ComfyUI via `run_3090ti.ps1`** (it pins the 3090 Ti AND uses the
   venv with the full custom-node dep set). Do not `python main.py` with the global
   interpreter.
2. **Diagnose "node not installed" by checking the RUNNING interpreter**, not the
   files: `netstat -ano | grep :8188` → PID → `Get-Process -Id <pid> | Select Path`.
   If Path isn't the venv, that's the bug — restart via `run_3090ti.ps1`.
3. **Get the real import error** by importing the node package in the target env:
   `python -c "import sys; sys.path.insert(0,'custom_nodes'); import ComfyUI-Hunyuan3DWrapper"`
   — it prints the exact missing module. Fix with `pip install --no-deps <pkg>` (the
   `--no-deps` keeps torch's CUDA-ext ABI safe; see [[project_comfyui_torch_xformers_pin]]).
4. **Confirm the fix live**: `/object_info/<NodeClass>` lists the node AND rerun the
   gate test — don't trust the file's presence as "installed."
