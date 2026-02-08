# Getting Started

## Prerequisites

- Python 3.10 or later
- ComfyUI installed and running at `http://localhost:8188`
- (Optional) Ollama for AI-powered workflow recommendation
- (Optional) Blender 4.0+ for 3D pipeline integration

## Installation

### Automated Setup

The setup wizard handles everything:

```bash
python setup_wizard.py
```

It will:
1. Verify your Python version
2. Check for ComfyUI and Ollama
3. Install all packages in development mode
4. Configure environment variables
5. Set up API credentials (HuggingFace, CivitAI)
6. Run smoke tests

### Manual Setup

```bash
# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
.venv\Scripts\activate     # Windows

# Install packages
pip install -e packages/sdk/
pip install -e packages/mcp-server/
pip install -e packages/prompter/
pip install -e ".[dev]"

# Copy and edit environment config
cp .env.example .env
```

## Configuration

See `.env.example` for all available settings. Key variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `COMFYUI_URL` | `http://localhost:8188` | ComfyUI server URL |
| `OLLAMA_URL` | `http://localhost:11434` | Ollama server URL |
| `COMFY_MCP_WORKFLOW_DIR` | `workflows/mcp` | Parametric workflow directory |

## Next Steps

- [Architecture Overview](architecture-overview.md) - Understand the codebase structure
- Start the MCP server: `comfyui-mcp`
- Launch the GUI: `comfyui-gui`
