# Blender-MCP Audit Report

**Date**: 2026-03-28
**Scope**: All blender-mcp references across comfyui-toolchain
**Finding**: blender-mcp was extensively documented and referenced but **never configured as an MCP server** in `.claude.json`. Added to config this session.

## Summary

| Metric | Count |
|--------|-------|
| Total files with blender-mcp references | 22 |
| Pipeline stages referencing blender-mcp | 9 |
| Pipelines that **require** blender-mcp | 1 (scene-ralph) |
| Pipelines that **prefer** blender-mcp (with headless fallback) | 2 (art-to-rig-ralph, animate-ralph) |
| Pipelines with **zero** blender-mcp refs | character-ralph, tileset-ralph, video-ralph, audio-ralph, style-transfer-ralph, upscale-ralph, inpaint-ralph, fusion-ralph, skeuomorph-ralph, asset-forge-ralph |
| Agent definitions with blender-mcp refs | 0 |

## Root Cause

CLAUDE.md line 184 states: *"For agent-driven pipelines, prefer blender-mcp"* — this is the directive that causes every pipeline with Blender operations to check for blender-mcp first. However:
1. blender-mcp was never added to `.claude.json` `mcpServers`
2. No agent definitions reference it
3. The `get_external_app_status` MCP tool checks blender-mcp availability at runtime but always finds it unreachable

## Detailed Reference Map

### Tier 1: Core Documentation (sets the expectation)

| File | Line(s) | Type | Content |
|------|---------|------|---------|
| `CLAUDE.md` | 6, 12 | Doc | "Blender MCP — installed as a Claude Code MCP server" |
| `CLAUDE.md` | 108-109 | Config | `BLENDER_HOST`, `BLENDER_PORT` env vars |
| `CLAUDE.md` | 163 | Doc | "addon.py (v1.4.0) installed... Provides execute_blender_code, get_viewport_screenshot, get_scene_info" |
| `CLAUDE.md` | 184 | **Directive** | "For agent-driven pipelines, prefer blender-mcp" |
| `docs/tool-reference.md` | 10, 342-497 | Doc | Full blender-mcp tool catalog (19 tools), workflow examples, pipeline integration table |

### Tier 2: Pipeline Stages (direct tool calls)

| Pipeline | Stage/File | Mode | blender-mcp Usage |
|----------|-----------|------|-------------------|
| **art-to-rig-ralph** | `stages/06-rig.md` | Interactive (Path A) | `execute_blender_code` for import, rig, export; `get_viewport_screenshot` for validation |
| **art-to-rig-ralph** | `prd.md` | Doc | "kart_pipeline_interactive.py via blender-mcp" |
| **art-to-rig-ralph** | `plan.md` | Doc | "Mesh prep + modular split via Blender (headless or blender-mcp)" |
| **art-to-rig-ralph** | `scripts/kart_pipeline_interactive.py` | Interactive | BLENDER-MCP SNIPPETS section at bottom |
| **art-to-rig-ralph** | `scripts/mesh_split.py` | Interactive | Usage note for execute_blender_code |
| **animate-ralph** | `PROMPT.md` | Interactive (Path A) | Full 5-step blender-mcp workflow |
| **animate-ralph** | `stages/02-block-out.md` | Interactive | Import, keyframe, screenshot, export |
| **animate-ralph** | `stages/03-refine.md` | Interactive | Breakdown poses, screenshot validation |
| **animate-ralph** | `stages/04-polish.md` | Interactive | Final polish, visual validation |
| **scene-ralph** | `PROMPT.md` | **Required** | Cross-server pipeline: comfyui-mcp + blender-mcp |
| **scene-ralph** | `stages/03-scene-build.md` | **Required** | All scene assembly via execute_blender_code |
| **scene-ralph** | `stages/04-materials.md` | **Required** | Poly Haven, HDRI, material application |

### Tier 3: MCP Server Code (runtime checks)

| File | Function | Purpose |
|------|----------|---------|
| `packages/mcp-server/managers/external_app_manager.py` | `check_blender_mcp_available()` | Socket probe on port 9876 |
| `packages/mcp-server/tools/external.py` | `publish_for_blender()` | Copy asset to shared dir for blender-mcp import |
| `packages/mcp-server/tools/external.py` | `get_external_app_status()` | Reports blender_mcp availability |

### Tier 4: Support Files

| File | Context |
|------|---------|
| `pipelines/RALPH-MANIFEST.md` | scene-ralph listed as "comfyui-mcp + blender-mcp" |
| `pipelines/art-to-rig-ralph/AUDIT.md` | external.py listed with 14 tools including blender-mcp |
| `docs/toolchain-audit-2026-03-28.md` | Cloud Blender-MCP Hunyuan3D path documented |
| `ralph.sh` | scene pipeline help text mentions blender-mcp |

## Pipeline Dependency Analysis

| Pipeline | Blender-MCP Required? | Headless Fallback? | Status |
|----------|----------------------|-------------------|--------|
| **scene-ralph** | YES - no fallback | No | **BLOCKED without blender-mcp** |
| **art-to-rig-ralph** | Preferred (Path A) | Yes (Path B: headless scripts) | Works headless |
| **animate-ralph** | Preferred (Path A) | Yes (Path B: headless Blender) | Works headless |
| **character-ralph** | No references | N/A - uses headless Blender + CoPlay Meshy | Works independently |
| All other pipelines | No references | N/A | No Blender dependency |

## Actions Taken

### 1. CLAUDE.md Rewritten
- blender-mcp and comfyui-mcp established as the **two primary MCP servers** in Project Goal
- Added "MCP Server Priority for 3D/Game Pipelines" section with explicit ordering
- blender-mcp is now the **required first choice** for all Blender operations
- Headless Blender demoted to fallback-only status
- Common Pitfalls #6 rewritten to reflect blender-mcp as primary interface

### 2. character-ralph Pipeline Updated
- `PROMPT.md`: Added full "MCP Tool Priority" section listing blender-mcp, comfyui-mcp, coplay-mcp with explicit ordering
- `stages/04-3d-convert.md`: Added blender-mcp visual validation (import + screenshot) before script validation
- `stages/05-rig-animate.md`: Complete rewrite — blender-mcp (Path A) is now primary, with Rigify code snippets for execute_blender_code. Meshy (Path B) and headless (Path C) are fallbacks
- `stages/06-package.md`: Added "Final Visual Validation (blender-mcp)" section

### 3. RALPH-MANIFEST.md Updated
- Added "MCP Servers (Claude Code)" table to Environment Requirements
- Explicit tool priority: blender-mcp > coplay-mcp > headless Blender
- Listed which pipelines require which MCP servers

### 4. Configuration
- blender-mcp added to `.claude.json` mcpServers (done this session)
- Requires Claude Code restart to take effect
- Requires Blender 5.0 open with blender-mcp addon enabled on port 9876

## Config Added This Session

```json
"blender-mcp": {
  "type": "stdio",
  "command": "uv",
  "args": [
    "run",
    "--directory",
    "C:\\Users\\scher\\Downloads\\blender-mcp-main\\blender-mcp-main",
    "blender-mcp"
  ],
  "env": {
    "BLENDER_HOST": "localhost",
    "BLENDER_PORT": "9876"
  }
}
```
