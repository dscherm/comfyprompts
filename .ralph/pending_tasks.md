# Pending Tasks (auto-generated)

2 pending task(s), sorted by priority:

### Task 3 [MEDIUM] (feature)
**Add Blender-specific parametric workflows — depth-guided generation, normal-map-based texturing, pose-to-render**

1. Analyze existing workflows in workflows/mcp/ to understand the pattern
2. Create a depth-guided img2img workflow (Blender depth pass -> ComfyUI ControlNet)
3. Create a normal-map texturing workflow (Blender normal pass -> ComfyUI texture generation)
4. Write .meta.json sidecars for each new workflow
5. Register new workflows with the MCP server's workflow manager
6. Test workflows with sample Blender scenes

### Task 4 [MEDIUM] (testing)
**Establish integration test suite for Blender-ComfyUI pipeline with mocked and live test modes**

1. Create tests/integration/ directory with conftest.py
2. Write mocked tests for the Blender-ComfyUI pipeline (no running services needed)
3. Write live integration tests (marked @pytest.mark.integration) that require ComfyUI
4. Add test fixtures for sample Blender scenes and expected outputs
5. Run the full test suite and baseline the count
6. Update CLAUDE.md with test commands
