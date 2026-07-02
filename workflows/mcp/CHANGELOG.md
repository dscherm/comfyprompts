# Workflow Changelog

Provenance log for parametric MCP workflows in `workflows/mcp/`. Newest first.

## 2026-07-02 — `trellis2_image_to_3d` (added)

- **Tool:** `trellis2_image_to_3d` (category: 3d) — single-view image -> 3D mesh (geometry-only, GLB).
- **Model:** `microsoft/TRELLIS.2-4B` (auto-downloaded to `D:/Projects/ComfyUI/models/microsoft/TRELLIS.2-4B`, ~16GB). Custom node: `ComfyUI-Trellis2` (71 Trellis2* classes).
- **Source:** ported to API format from `ComfyUI-Trellis2/example_workflows/MeshOnly_HighQuality.json` (vendor "HighQuality" cascade: ImageCond -> Sparse -> Shape@1024 -> ShapeCascade@1536 -> Decode -> FillHoles -> QuadRemesh -> Simplify x2 -> Trimesh -> Export GLB). Helper Primitive nodes inlined; Preview3D dropped.
- **Params:** `PARAM_STR_IMAGE_PATH` (default `trellis_test.png`), `PARAM_INT_SEED` (default 12345). Everything else hardcoded to the proven preset. Output: `3D/trellis_test_*.glb`.
- **Validation:** `workflow_validator.py` PASS against live `/object_info` (2283 classes cached this session). Input names/order taken from `/object_info`, not the UI widget order.
- **Bugs fixed during authoring:**
  1. `Trellis2PreProcessImage` unconditionally indexes an alpha channel (`nodes.py:2656`); its rembg fallback is commented out. On an RGB (no-alpha) input it raised `index 3 is out of bounds for axis 2 with size 3`. Fix: set `remove_background=true` so the node runs rembg (v2.0.67, present) to create the alpha. Now works on arbitrary single-view images.
  2. API input ordering restored from `/object_info` (UI widget order differs); the seed `control_after_generate` widget value was dropped from `Trellis2SparseGenerator`.
- **Smoke test:** BLOCKED (not a workflow defect). prompt_id `e6481034-350e-41a1-a4a7-c73e66094bb5` reached node 5 `Trellis2SparseGenerator` then failed: `No module named 'flash_attn'`. Root cause: the sparse windowed-attention transformer (`trellis2/modules/sparse/attention/windowed_attn.py`) hard-requires `xformers` OR `flash_attn` and has NO torch-SDPA fallback (unlike `full_attn.py`). Neither library is installed in `D:/Projects/ComfyUI/venv` or in the system-Python311 process currently serving :8188. No workflow/parameter workaround exists.
- **Environment notes:** the ComfyUI serving :8188 (PID 146196) is running under **system Python 3.11** (`C:\Users\scher\...\Python311\python.exe`), launched as `main.py --port 8188` (no `CUDA_VISIBLE_DEVICES` pin) with CWD `D:\Projects\ComfyUI` — not the venv, not GPU-pinned per `run_3090ti.ps1`. A duplicate venv launch this session failed on the :8188 port collision (harmless).
- **Remediation to unblock:** install `xformers` (or `flash_attn`) matching torch 2.9.1+cu126 into `D:/Projects/ComfyUI/venv`, then relaunch ComfyUI from the venv via `run_3090ti.ps1 --listen 127.0.0.1 --port 8188`. Model is already downloaded, so re-running the smoke test should complete in ~2-4 min. Coordinate the install with the environment owner — a mismatched xformers can rebuild torch and break the verified Trellis2/Hunyuan3D CUDA extensions.
- **Known limits:** geometry-only (no texture SLAT decode); shape cascade at 1536 + ~1M-face simplify is heavy but comfortable on 24GB. Purpose: A/B the finger/webbing topology vs single-view Hunyuan3D 2.0 on the staged spread-finger T-pose (`input/trellis_test.png`).
