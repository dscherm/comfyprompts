# ComfyUI Toolchain

## Architecture

Three packages in `packages/` directory:
- **packages/sdk/** (`comfyui-agent-sdk`) - Shared Python SDK providing ComfyUIClient, AssetRegistry, DefaultsManager, and credential management
- **packages/mcp-server/** (`comfyui-mcp-server`) - FastMCP server with 40+ tools for AI image/video/audio/3D generation
- **packages/prompter/** (`comfyui-prompter`) - Tkinter GUI + Flask REST API for workflow recommendation and generation

Dependency graph: `prompter → SDK ← mcp-server` (both prompter and mcp-server depend on the SDK)

Two Blender addons in `blender/`:
- `blender/comfyui_tools/` - Full-featured addon (generation, rigging, animation, motion capture, export) - connects via Flask API
- `blender/comfyui_mcp_tools/` - Lightweight addon (rigging, animation, MCP integration) - connects via MCP HTTP

Parametric workflows in `workflows/mcp/` - JSON files with PARAM_* placeholders and .meta.json sidecars.

## SDK Public API

The SDK (`packages/sdk/src/comfyui_agent_sdk/`) exports:

### Client (`client/`)
- `ComfyUIClient` - Main client for ComfyUI API interaction (queue prompts, upload images, get history)
- Error types: `ComfyUIError`, `ConnectionError`, `MissingModelError`, `MissingNodeError`, `TimeoutError`, `VRAMError`, `WorkflowValidationError`
- `WebSocketMonitor` - Real-time progress tracking via WebSocket
- `parse_comfyui_error()` - Structured error parsing

### Assets (`assets/`)
- `AssetRegistry` - Track and manage generated assets with TTL-based cleanup
- `AssetRecord` - Individual asset metadata
- `EncodedImage` - Base64-encoded image wrapper
- `encode_preview_for_mcp()` - Encode images for MCP transport
- `get_image_metadata()` - Extract image metadata

### Defaults (`defaults/`)
- `DefaultsManager` - Manage default models, parameters, and presets per media type

### Configuration
- `config.py` - `ComfyUIConfig` class, environment variable loading
- `credentials.py` - Keyring-based credential storage (HuggingFace, CivitAI tokens)

## Entry Points

| Command | Module | Description |
|---------|--------|-------------|
| `comfyui-mcp` | `packages/mcp-server/server.py:main` | Start MCP server |
| `comfyui-gui` | `packages/prompter/main.py` | Launch Tkinter GUI |
| `comfyui-api` | `packages/prompter/api_server.py` | Start Flask REST API (port 5050) |
| `comfyui-setup` | `setup_wizard.py:main` | Interactive setup wizard |

## Code Conventions

- Python >=3.10 (uses modern syntax: `dict[str, str]`, `X | None`, match/case)
- Formatter/linter: `ruff` with 100-character line length
- Type hints on all public API functions
- Build system: hatchling for all packages
- Import order: stdlib, third-party, local (enforced by ruff isort)

## Configuration Strategy

### Environment Variables
- `COMFYUI_URL` - ComfyUI server URL (default: `http://localhost:8188`)
- `OLLAMA_URL` - Ollama server URL (default: `http://localhost:11434`)
- `COMFY_MCP_WORKFLOW_DIR` - Parametric workflow directory (default: `workflows/mcp`)
- `COMFY_MCP_ASSET_TTL_HOURS` - Asset cleanup TTL (default: 24)
- `COMFY_MCP_GENERATION_TIMEOUT` - Generation timeout in seconds (default: 300)
- `COMFYUI_OUTPUT_ROOT` - Override ComfyUI output directory

### Credentials
Stored via `keyring` (system credential store):
- `huggingface_token` - HuggingFace API token for model downloads
- `civitai_api_key` - CivitAI API key for model downloads

## Workflow Conventions

Parametric workflows use `PARAM_*` placeholder strings in JSON values:
- `PARAM_POSITIVE_PROMPT`, `PARAM_NEGATIVE_PROMPT` - Text prompts
- `PARAM_WIDTH`, `PARAM_HEIGHT` - Dimensions
- `PARAM_SEED` - Random seed
- `PARAM_STEPS` - Sampling steps
- `PARAM_CFG` - CFG scale
- `PARAM_CHECKPOINT` - Model checkpoint name

Each workflow JSON has a companion `.meta.json` sidecar defining:
- `WorkflowParameter` entries (name, type, default, description, constraints)
- `WorkflowToolDefinition` (tool name, description, category)

## Blender Addon Rules

Both Blender addons follow strict constraints:
- **No pip-installed dependencies** - Only stdlib and Blender's bundled Python
- **HTTP via urllib only** - No `requests` library
- **Blender 4.0+ required** - Uses modern Blender API
- **Two separate addons** - Different `bl_info`, different class prefixes:
  - `comfyui_tools`: prefix `COMFYUI_OT_`, `COMFYUI_PT_`
  - `comfyui_mcp_tools`: prefix `COMFY_OT_`, `COMFY_PT_`
- **Different backends**: comfyui_tools connects to Flask API (port 5050), comfyui_mcp_tools connects to MCP server via HTTP

## Testing

- Framework: pytest
- Test paths: `packages/sdk/tests/`, `packages/mcp-server/tests/`, `packages/prompter/tests/`
- Markers: `@pytest.mark.integration` (requires running ComfyUI), `@pytest.mark.slow`
- Async tests: `pytest-asyncio` for MCP server tests
- Run all: `pytest` from repo root
- Run one package: `pytest packages/mcp-server/tests/`

## Common Pitfalls

1. **Two `workflow_manager` modules** - MCP server's (`packages/mcp-server/managers/workflow_manager.py`, ~495 LOC) is a parametric template engine that substitutes PARAM_* placeholders. Prompter's (`packages/prompter/workflow_manager.py`, ~916 LOC) is a UI<>API format converter. They serve completely different purposes and should NOT be merged.

2. **Two Blender addons** - `blender/comfyui_tools/` (SDK, v2.0.0) and `blender/comfyui_mcp_tools/` (MCP, v1.3.0) have different class prefixes, different backends, and different feature sets. They are intentionally separate.

3. **Hardcoded paths** - Watch for hardcoded Windows paths (e.g., `D:\` prefixed paths). Use `os.path.join()` and environment variables instead.

4. **SDK imports** - MCP server and Prompter both import from `comfyui_agent_sdk`. In dev mode, install SDK as editable: `pip install -e packages/sdk/`

5. **MCP version** - SDK requires `mcp>=1.0.0`. MCP server previously pinned `mcp>=0.9.0` but should use `>=1.0.0` in the monorepo.

## Agent Team

Seven specialized agents in `.claude/agents/`:

| Agent | Scope | Use When |
|-------|-------|----------|
| `sdk-developer` | `packages/sdk/` | Modifying SDK client, assets, defaults, config, credentials |
| `mcp-tools-dev` | `packages/mcp-server/` | Adding/modifying MCP tools, managers, server config |
| `prompter-dev` | `packages/prompter/` | GUI changes, Flask API, Ollama recommender, model registry |
| `workflow-engineer` | `workflows/` | Creating/modifying parametric workflows and meta files |
| `test-engineer` | All `tests/` dirs | Writing tests, fixtures, CI test configuration |
| `blender-addon-dev` | `blender/` | Blender operators, panels, properties, addon packaging |
| `setup-engineer` | Root configs, setup, docs | pyproject.toml, setup wizard, CI/CD, documentation |
