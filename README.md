# ComfyUI Toolchain

Unified toolkit for AI media generation via ComfyUI. Three integrated packages — a shared SDK, an MCP server with 40+ tools, and a GUI/API — plus Blender addons for 3D pipeline integration.

## Quick Start

```bash
git clone https://github.com/YOUR_USERNAME/comfyui-toolchain.git
cd comfyui-toolchain
python setup_wizard.py
```

## Architecture

```
┌─────────────────────────────────────────────────┐
│                comfyui-toolchain                 │
├──────────┬──────────────┬───────────────────────┤
│          │              │                       │
│  SDK     │  MCP Server  │  Prompter             │
│          │              │                       │
│  Client  │  40+ Tools   │  Tkinter GUI          │
│  Assets  │  Managers    │  Flask API (:5050)    │
│  Config  │  Workflows   │  Ollama Recommender   │
│  Creds   │              │  Model Registry       │
│          │              │                       │
├──────────┴──────┬───────┴───────────────────────┤
│                 │                               │
│  Blender Addons │  Parametric Workflows         │
│                 │                               │
│  comfyui_tools  │  PARAM_* templates            │
│  comfyui_mcp    │  .meta.json sidecars          │
│                 │                               │
└─────────────────┴───────────────────────────────┘

Dependencies:  MCP Server ──→ SDK ←── Prompter
               Blender (comfyui_tools) ──→ Flask API
               Blender (comfyui_mcp)   ──→ MCP HTTP
```

## Packages

### SDK (`packages/sdk/`)
Shared Python SDK providing the foundation for all ComfyUI interactions:
- **ComfyUIClient** - Queue workflows, upload images, poll results
- **AssetRegistry** - Track generated assets with TTL-based cleanup
- **DefaultsManager** - Per-media-type model and parameter defaults
- **Credentials** - Keyring-based secret storage (HuggingFace, CivitAI)

### MCP Server (`packages/mcp-server/`)
[Model Context Protocol](https://modelcontextprotocol.io/) server exposing 40+ tools for AI-powered generation:
- Image generation (Stable Diffusion, FLUX, SDXL)
- Video generation (AnimateDiff, SVD, Wan)
- Audio generation
- 3D model generation (TripoSG, Hunyuan3D)
- Style transfer, upscaling, batch processing
- Asset and model management

### Prompter (`packages/prompter/`)
Desktop GUI and REST API for interactive workflow management:
- Tkinter-based GUI with workflow browser and parameter editor
- Flask REST API (port 5050) for Blender addon integration
- Ollama-powered workflow recommendation
- Generation history and model registry

## Blender Addons

Two Blender 4.0+ addons in `blender/`:

| Addon | Prefix | Backend | Features |
|-------|--------|---------|----------|
| `comfyui_tools` | `COMFYUI_OT_` | Flask API | Generation, rigging, animation, mocap, export |
| `comfyui_mcp_tools` | `COMFY_OT_` | MCP HTTP | Rigging, animation, MCP integration |

## Entry Points

| Command | Description |
|---------|-------------|
| `comfyui-mcp` | Start MCP server |
| `comfyui-gui` | Launch desktop GUI |
| `comfyui-api` | Start Flask REST API (port 5050) |
| `comfyui-setup` | Run interactive setup wizard |

## Development

### Setup
```bash
python setup_wizard.py          # Full interactive setup
# or manually:
pip install -e packages/sdk/
pip install -e packages/mcp-server/
pip install -e packages/prompter/
pip install -e ".[dev]"
```

### Testing
```bash
pytest                                    # All tests
pytest packages/mcp-server/tests/        # MCP server tests only
pytest -m "not integration"              # Skip integration tests
```

### Linting
```bash
ruff check .
ruff format .
```

### Claude Code Agents

This repo includes 7 specialized Claude Code agents for development:

| Agent | Scope |
|-------|-------|
| `/sdk-developer` | SDK client, assets, defaults, config |
| `/mcp-tools-dev` | MCP tools, managers, server |
| `/prompter-dev` | GUI, Flask API, recommender |
| `/workflow-engineer` | Parametric workflows |
| `/test-engineer` | Tests and CI |
| `/blender-addon-dev` | Blender addons |
| `/setup-engineer` | Setup, packaging, docs |

## Requirements

- Python >=3.10
- ComfyUI running at localhost:8188 (for generation features)
- Ollama (optional, for workflow recommendation)
- Blender 4.0+ (optional, for 3D pipeline)

## License

Apache-2.0
