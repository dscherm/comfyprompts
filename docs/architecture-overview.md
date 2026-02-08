# Architecture Overview

*Detailed architecture documentation — to be expanded during Phase B migration.*

## Package Structure

```
comfyui-toolchain/
├── packages/
│   ├── sdk/          → comfyui-agent-sdk (shared library)
│   ├── mcp-server/   → comfyui-mcp-server (MCP protocol server)
│   └── prompter/     → comfyui-prompter (GUI + REST API)
├── blender/          → Two Blender 4.0+ addons
├── workflows/mcp/    → Parametric workflow templates
└── docs/             → Documentation
```

## Dependency Graph

```
comfyui-mcp-server ──depends-on──→ comfyui-agent-sdk
comfyui-prompter   ──depends-on──→ comfyui-agent-sdk

blender/comfyui_tools     ──HTTP──→ Flask API (prompter)
blender/comfyui_mcp_tools ──HTTP──→ MCP Server
```

## Key Design Decisions

1. **Three separate packages** rather than one monolithic package — different deployment targets (library vs server vs GUI app)
2. **Two workflow managers** — MCP server's is a parametric template engine; Prompter's is a UI format converter. Different purposes.
3. **Two Blender addons** — Different class prefixes, different backends, different feature sets. Both are stdlib-only (no pip deps).
4. **Workflows in repo** — MCP server's parametric workflows ship with the repo. Prompter reads user's local ComfyUI workflows.
