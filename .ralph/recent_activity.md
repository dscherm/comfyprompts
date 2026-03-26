# Recent Activity (auto-generated)

## 2026-03-26 - Task 1: End-to-end Blender-to-ComfyUI generation pipeline

**Goal:** Create a complete render-to-AI pipeline in the comfyui_mcp_tools Blender addon

**Changes Made:**
- `blender/comfyui_mcp_tools/comfyui_client.py`: New file — lightweight ComfyUI HTTP client (urllib only) with upload_image (multipart), queue_prompt, get_history, get_job_status, download_image, get_checkpoints, extract_output_images
- `blender/comfyui_mcp_tools/workflows.py`: New file — img2img and txt2img workflow builders targeting SD 1.5 (v1-5-pruned-emaonly.ckpt default)
- `blender/comfyui_mcp_tools/operators_pipeline.py`: New file — 8 operators: check_comfyui, capture_viewport_mcp, use_render_result_mcp, run_pipeline, monitor_pipeline (modal timer), cancel_pipeline, apply_as_texture, open_output
- `blender/comfyui_mcp_tools/properties.py`: Added ComfyMCPPipelineProps (mode, prompts, generation params, capture settings, job state) and comfyui_url to preferences
- `blender/comfyui_mcp_tools/panels.py`: Added COMFY_PT_pipeline_panel with full UI for connection, mode selection, input capture, prompts, generation settings, status, and output actions
- `blender/comfyui_mcp_tools/__init__.py`: Registered all new classes, bumped version to 1.4.0
- `tests/test_blender_pipeline.py`: New file — 38 tests covering workflow builders, HTTP client (mock server), output extraction, singleton, and full pipeline round-trip
- `pyproject.toml`: Added `tests` to testpaths

**Verification:**
- `python -c "import py_compile; ..."` — all 5 addon files compile OK
- `pytest tests/test_blender_pipeline.py -v` — 38 passed, 0 failures
- `pytest -x --tb=short -q` — 190 passed, 6 skipped, 1 pre-existing failure (mem-20260326-001)

**Status:** COMPLETE
