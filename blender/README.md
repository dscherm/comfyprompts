# Blender Addons

Two Blender 4.0+ addons for ComfyUI integration.

## comfyui_tools (v2.0.0)

Full-featured addon connecting to the Prompter's Flask API:
- Image/video generation from Blender viewport
- Auto-rigging for imported 3D models
- Animation and motion capture
- Export to multiple formats

**Backend:** Flask REST API at `http://localhost:5050`

## comfyui_mcp_tools (v1.3.0)

Lightweight addon connecting to the MCP server:
- Rigging and animation
- MCP protocol integration

**Backend:** MCP HTTP server

## Installation

1. Open Blender → Edit → Preferences → Add-ons
2. Click "Install from Disk"
3. Navigate to the addon folder and select `__init__.py`
4. Enable the addon in the list

## Important Notes

- Both addons use **urllib only** (no pip-installed dependencies)
- Requires **Blender 4.0+**
- Different class prefixes: `COMFYUI_OT_` vs `COMFY_OT_` (can be installed simultaneously)
