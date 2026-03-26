# Pending Tasks (auto-generated)

6 pending task(s), sorted by priority:

### ~~Task 1 [DONE]~~ — placeholder, skipped
### ~~Task 2 [DONE]~~ — Audit codebase state (194 passed, 9 failed, 6 skipped)

### Task 3 [CRITICAL] (setup)
**Verify Blender MCP integration — confirm blender MCP server is installed and can communicate with ComfyUI**

1. Check blender/comfyui_mcp_tools/ addon structure and version
2. Check blender/comfyui_tools/ addon structure and version
3. Verify the MCP server entry point (comfyui-mcp) works
4. Check if Blender is installed and accessible from command line
5. Test that the Blender addon can reach the Flask API at port 5050
6. Document the integration state: what works, what's broken, what's missing

### Task 4 [HIGH] (setup)
**Map ComfyUI installation at C:\Users\Teacher\ComfyUI — verify models, custom nodes, and output paths**

1. Check C:\Users\Teacher\ComfyUI exists and identify the version
2. List installed models in ComfyUI/models/ (checkpoints, loras, controlnets)
3. List installed custom nodes in ComfyUI/custom_nodes/
4. Check if ComfyUI output directory matches COMFYUI_OUTPUT_ROOT env var
5. Verify parametric workflows in workflows/mcp/ reference available models
6. Document any missing models or custom nodes that workflows depend on

### Task 5 [HIGH] (feature)
**Create end-to-end Blender-to-ComfyUI generation pipeline — render Blender scene, send to ComfyUI for AI processing**

1. Read blender/comfyui_mcp_tools/ to understand existing MCP-based operators
2. Read blender/comfyui_tools/ to understand existing Flask-based operators
3. Identify the gap: what pipeline steps are missing between Blender render and ComfyUI ingest
4. Implement or wire up the missing pipeline: Blender render -> image upload -> ComfyUI workflow -> result download
5. Test the pipeline with a simple scene (e.g., render a cube, apply img2img)
6. Write tests for the pipeline components
7. Run targeted tests to verify

### Task 6 [HIGH] (feature)
**Wire MCP server tools into Blender addon — expose ComfyUI generation capabilities as Blender operators via MCP**

1. Read packages/mcp-server/server.py to understand available MCP tools
2. Read blender/comfyui_mcp_tools/ to see which tools are already exposed
3. Identify high-value MCP tools not yet accessible from Blender (e.g., generate_image, apply_controlnet)
4. Add Blender operators that call these MCP tools via HTTP
5. Add UI panels in Blender for the new operators
6. Test each new operator manually and document in activity.md

### Task 7 [MEDIUM] (feature)
**Add Blender-specific parametric workflows — depth-guided generation, normal-map-based texturing, pose-to-render**

1. Analyze existing workflows in workflows/mcp/ to understand the pattern
2. Create a depth-guided img2img workflow (Blender depth pass -> ComfyUI ControlNet)
3. Create a normal-map texturing workflow (Blender normal pass -> ComfyUI texture generation)
4. Write .meta.json sidecars for each new workflow
5. Register new workflows with the MCP server's workflow manager
6. Test workflows with sample Blender scenes

### Task 8 [MEDIUM] (testing)
**Establish integration test suite for Blender-ComfyUI pipeline with mocked and live test modes**

1. Create tests/integration/ directory with conftest.py
2. Write mocked tests for the Blender-ComfyUI pipeline (no running services needed)
3. Write live integration tests (marked @pytest.mark.integration) that require ComfyUI
4. Add test fixtures for sample Blender scenes and expected outputs
5. Run the full test suite and baseline the count
6. Update CLAUDE.md with test commands

