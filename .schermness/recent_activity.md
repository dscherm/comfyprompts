# Recent Activity (auto-generated)

## 2026-03-26 - Task 4: Integration Test Suite for Blender-ComfyUI Pipeline

**Goal:** Establish integration test suite with mocked and live test modes for the Blender-to-ComfyUI pipeline.

**Changes Made:**
- `tests/integration/__init__.py`: Created integration test package
- `tests/integration/conftest.py`: Shared fixtures — MockComfyUI server (full HTTP mock), MockMCP server (streamable-http mock), client factories, sample PNG fixtures, live ComfyUI/SDK client fixtures with auto-skip
- `tests/integration/test_pipeline_mocked.py`: 23 mocked tests — full direct pipeline (upload→build→submit→poll→download), MCP pipeline (health check, generate, Blender workflows), session management, custom responses, multi-job sequencing, error handling
- `tests/integration/test_pipeline_live.py`: 9 live tests (skip if ComfyUI unavailable) — connection, checkpoints, upload, txt2img generation, img2img generation, SDK client, workflow manager
- `tests/integration/test_workflow_validation.py`: 20 tests — file integrity, meta/JSON consistency, ControlNet model matching, PARAM_* placeholder coverage, node graph connectivity, workflow rendering with full/partial params, cross-pipeline consistency
- `CLAUDE.md`: Added integration test commands to Testing section

**Verification:**
- `pytest tests/integration/ -v` — 45 passed, 9 skipped (live tests, ComfyUI not running)
- `pytest --tb=line -q` — 353 passed, 9 failed (pre-existing test_workflows.py bug), 15 skipped

**Status:** COMPLETE
