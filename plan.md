# plan.md — ComfyPrompts + Blender MCP Integration

Task queue for Ralph Loop. JSON blocks in triple-backtick fences.
Only ONE task per iteration. Mark `"passes": true` when complete.

---

## Task Format (template — not a real task)

<!-- Template for reference only. Do NOT pick this up as a task.
{
  "category": "setup|feature|testing|bugfix",
  "priority": 1,
  "description": "One-line description of what this task accomplishes",
  "steps": ["Step 1", "Step 2"],
  "passes": true
}
-->

---

### Phase 1: Project Assessment & Integration Setup

```json
{
  "category": "setup",
  "priority": 1,
  "description": "Audit current codebase state — run existing tests, check package installations, identify broken/missing pieces",
  "steps": [
    "Read CLAUDE.md and README.md to understand the project structure",
    "Check if all three packages (sdk, mcp-server, prompter) are installed correctly",
    "Run the existing test suite (pytest from repo root) and record baseline pass/fail counts",
    "Check if ComfyUI is reachable at http://localhost:8188 (the configured default)",
    "Check if the Blender MCP addon is installed and what version it is",
    "Document findings in activity.md with exact test counts and any errors"
  ],
  "passes": true
}
```

```json
{
  "category": "setup",
  "priority": 1,
  "description": "Verify Blender MCP integration — confirm blender MCP server is installed and can communicate with ComfyUI",
  "steps": [
    "Check blender/comfyui_mcp_tools/ addon structure and version",
    "Check blender/comfyui_tools/ addon structure and version",
    "Verify the MCP server entry point (comfyui-mcp) works",
    "Check if Blender is installed and accessible from command line",
    "Test that the Blender addon can reach the Flask API at port 5050",
    "Document the integration state: what works, what's broken, what's missing"
  ],
  "passes": true
}
```

```json
{
  "category": "setup",
  "priority": 2,
  "description": "Map ComfyUI installation at C:\\Users\\Teacher\\ComfyUI — verify models, custom nodes, and output paths",
  "steps": [
    "Check C:\\Users\\Teacher\\ComfyUI exists and identify the version",
    "List installed models in ComfyUI/models/ (checkpoints, loras, controlnets)",
    "List installed custom nodes in ComfyUI/custom_nodes/",
    "Check if ComfyUI output directory matches COMFYUI_OUTPUT_ROOT env var",
    "Verify parametric workflows in workflows/mcp/ reference available models",
    "Document any missing models or custom nodes that workflows depend on"
  ],
  "passes": true
}
```

### Phase 2: Blender-ComfyUI Pipeline Integration

```json
{
  "category": "feature",
  "priority": 2,
  "description": "Create end-to-end Blender-to-ComfyUI generation pipeline — render Blender scene, send to ComfyUI for AI processing",
  "steps": [
    "Read blender/comfyui_mcp_tools/ to understand existing MCP-based operators",
    "Read blender/comfyui_tools/ to understand existing Flask-based operators",
    "Identify the gap: what pipeline steps are missing between Blender render and ComfyUI ingest",
    "Implement or wire up the missing pipeline: Blender render -> image upload -> ComfyUI workflow -> result download",
    "Test the pipeline with a simple scene (e.g., render a cube, apply img2img)",
    "Write tests for the pipeline components",
    "Run targeted tests to verify"
  ],
  "passes": true
}
```

```json
{
  "category": "feature",
  "priority": 2,
  "description": "Wire MCP server tools into Blender addon — expose ComfyUI generation capabilities as Blender operators via MCP",
  "steps": [
    "Read packages/mcp-server/server.py to understand available MCP tools",
    "Read blender/comfyui_mcp_tools/ to see which tools are already exposed",
    "Identify high-value MCP tools not yet accessible from Blender (e.g., generate_image, apply_controlnet)",
    "Add Blender operators that call these MCP tools via HTTP",
    "Add UI panels in Blender for the new operators",
    "Test each new operator manually and document in activity.md"
  ],
  "passes": true
}
```

### Phase 3: Workflow Enhancement

```json
{
  "category": "feature",
  "priority": 3,
  "description": "Add Blender-specific parametric workflows — depth-guided generation, normal-map-based texturing, pose-to-render",
  "steps": [
    "Analyze existing workflows in workflows/mcp/ to understand the pattern",
    "Create a depth-guided img2img workflow (Blender depth pass -> ComfyUI ControlNet)",
    "Create a normal-map texturing workflow (Blender normal pass -> ComfyUI texture generation)",
    "Write .meta.json sidecars for each new workflow",
    "Register new workflows with the MCP server's workflow manager",
    "Test workflows with sample Blender scenes"
  ],
  "passes": true
}
```

```json
{
  "category": "testing",
  "priority": 3,
  "description": "Establish integration test suite for Blender-ComfyUI pipeline with mocked and live test modes",
  "steps": [
    "Create tests/integration/ directory with conftest.py",
    "Write mocked tests for the Blender-ComfyUI pipeline (no running services needed)",
    "Write live integration tests (marked @pytest.mark.integration) that require ComfyUI",
    "Add test fixtures for sample Blender scenes and expected outputs",
    "Run the full test suite and baseline the count",
    "Update CLAUDE.md with test commands"
  ],
  "passes": true
}
```
