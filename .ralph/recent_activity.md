# Recent Activity (auto-generated)

## 2026-03-26 - Task 2: Audit Current Codebase State

**Goal:** Run existing tests, check package installations, identify broken/missing pieces

**Changes Made:**
- No code changes — audit only

**Findings:**

1. **Packages:** All three packages installed correctly as editable:
   - `comfyui-agent-sdk` v0.1.0 (packages/sdk)
   - `comfyui-mcp-server` v1.0.0 (packages/mcp-server)
   - `comfyui-prompter` v0.1.0 (packages/prompter)

2. **Test Suite:** 194 passed, 9 failed, 6 skipped (72.93s)
   - All 9 failures are in `packages/mcp-server/tests/test_workflows.py`
   - Root cause: `WorkflowManager` defaults to `packages/mcp-server/workflows` but parametric workflows live at `workflows/mcp/`
   - Known issue (mem-20260326-001): `COMFY_MCP_WORKFLOW_DIR` env var can override

3. **Failed tests (all workflow path related):**
   - `TestWorkflowDiscovery::test_workflows_directory_exists`
   - `TestWorkflowDiscovery::test_workflows_discovered`
   - `TestWorkflowDiscovery::test_core_workflows_present`
   - `TestWorkflowParameters::test_generate_image_params`
   - `TestWorkflowParameters::test_generate_video_params`
   - `TestWorkflowParameters::test_generate_song_params`
   - `TestWorkflowOutputTypes::test_image_workflow_output`
   - `TestWorkflowOutputTypes::test_video_workflow_output`
   - `TestWorkflowOutputTypes::test_audio_workflow_output`

4. **ComfyUI:** Not reachable at http://localhost:8188 (not running)

5. **Blender addons:** Both compile successfully
   - `blender/comfyui_tools/` — Flask-based addon
   - `blender/comfyui_mcp_tools/` — MCP-based addon

6. **Workflows:** Present at `workflows/mcp/` with 10+ parametric workflows and meta sidecars

**Verification:**
- `pytest --tb=no -q` -- 194 passed, 9 failed, 6 skipped

**Status:** COMPLETE
