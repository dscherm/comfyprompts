# ComfyUI Toolchain Audit Report

**Date:** 2026-03-28
**Scope:** Conflicts, redundant code, redundant documents, dead code, overlapping functionality

---

## Executive Summary

The toolchain is well-organized with clear package boundaries, but has accumulated significant duplication across Blender addons, animation scripts, and utility modules. Documentation is comprehensive but contains conflicting counts and some stale references. Several standalone scripts and one utility module are dead code.

**Key findings:**
- ~830 lines of identical code between the two Blender addons (`animations.py`, `utils.py`)
- `RigBones` class duplicated in **6 separate files** (1 canonical + 5 copies, already flagged in prior audit, unfixed)
- `packages/mcp-server/utils/autotile.py` is an exact duplicate of `packages/comfyui-nodes/utils/autotile.py` and unused
- 2 redundant animation scripts (`apply_animation.py`, `run_animate.py`) — flagged in Feb 2026 audit, still present
- 3 workflow file mismatches (1 missing meta, 2 orphaned metas) + 6 undocumented workflows
- Tool count conflicts across 4 docs: CLAUDE.md/README/Research say "40+", tool-reference says "83+", actual = **75 explicit + N dynamic**
- `COMFYUI_RESEARCH_SUMMARY.md` largely duplicates info already in `CLAUDE.md` + `docs/tool-reference.md`
- Common script utility functions duplicated 7-11x across standalone scripts (`queue_prompt`, `download_image`, `check_comfyui`)
- Hunyuan3D documentation conflates two distinct paths: local ComfyUI workflows vs cloud Blender-MCP integration

---

## 1. Duplicate Code

### 1.1 Blender Addon Duplication (CRITICAL)

Both addons share nearly identical copies of two files:

| File | Lines | Diff |
|------|-------|------|
| `blender/comfyui_tools/animations.py` vs `blender/comfyui_mcp_tools/animations.py` | 595 each | Only docstring differs |
| `blender/comfyui_tools/utils.py` vs `blender/comfyui_mcp_tools/utils.py` | 237 each | 3 trivial diffs (docstring, import order, trailing comma) |

**Total: ~830 lines of duplicated code.**

**Recommendation:** Since Blender addons can't share pip dependencies, this duplication is somewhat inherent. However, a shared `_common/` directory could be copied into both at build time, or one addon could import from the other if they're always installed together. CLAUDE.md already notes they're "intentionally separate" but doesn't address the code duplication.

### 1.2 RigBones Class Duplication

`RigBones` (universal bone finder) exists in at least 3 places with diverging implementations:

| File | Implementation |
|------|---------------|
| `scripts/animation_library.py` | Most complete (1195 lines total, includes RigBones + 7 animation generators) |
| `scripts/apply_animation.py` | Simpler version (300 lines, walk-only RigBones) |
| `blender/comfyui_mcp_tools/utils.py` | Addon-embedded copy |

The prior audit (`packages/mcp-server/docs/audit_animation_rigging_pipeline.md`, 2026-02-06) already identified this and recommended consolidation. **Still unfixed 7 weeks later.**

Additionally, `RigBones` also exists in blender snippet files:

| File | Implementation |
|------|---------------|
| `scripts/blender_snippets/animate_walk.py` | Copy |
| `scripts/blender_snippets/animate_idle.py` | Copy |
| `scripts/blender_snippets/utils.py` | Copy (identical to animation_library.py) |

**Total: 6 copies of RigBones** (1 canonical in `animation_library.py` + 5 diverging copies).

### 1.3 autotile.py Duplication

`packages/mcp-server/utils/autotile.py` (220 lines) is a **byte-for-byte duplicate** of `packages/comfyui-nodes/utils/autotile.py`. The MCP server copy is imported nowhere.

**Recommendation:** Delete `packages/mcp-server/utils/autotile.py`.

---

## 2. Dead Code / Unused Files

### 2.1 Standalone Scripts (Not Imported by Main Codebase)

All 32 scripts in `packages/mcp-server/scripts/` are standalone (never imported). The `external_app_manager.py` only references 4 of them as subprocess targets:

| Script | Referenced By | Status |
|--------|--------------|--------|
| `blender_import.py` | `external_app_manager.py:234` | **Active** |
| `blender_convert.py` | `external_app_manager.py:401` | **Active** |
| `blender_autorig.py` | `external_app_manager.py:530` | **Active** |
| `blender_animate.py` | `external_app_manager.py:685` | **Active** |
| `apply_animation.py` | Nowhere | **Dead** (redundant with blender_animate.py) |
| `run_animate.py` | Nowhere | **Dead** (prototype, hardcoded bone_N refs) |
| `animation_library.py` | Nowhere | **Potential dead** (comprehensive but unused by main code) |
| `create_test_model.py` | Nowhere | **Test utility** |
| `process_triposg.py` | Nowhere | **Dead** |
| `hot_reload_watcher.py` | Nowhere | **Dead** (hot-reload-ralph pipeline exists) |

The remaining ~18 scripts (`generate_berserkr_*`, `regen_*`, `batch_*`, `generate_*_tiles`, etc.) are **user-invoked batch tools** for the Berserkr game project. They're not dead code but are project-specific and arguably belong outside the MCP server package.

### 2.2 Unused Utils Directory

`packages/mcp-server/utils/` contains only `autotile.py` (duplicate, unused) and `__init__.py`. The entire directory can be removed.

---

## 3. Workflow File Issues

### 3.1 Count Mismatch

| Source | Count |
|--------|-------|
| Actual `.json` files (excluding `.meta.json`) | **44-48** (agent counts vary by inclusion criteria) |
| `COMFYUI_RESEARCH_SUMMARY.md` claims | **45** |
| `docs/tool-reference.md` header claims | Not specified per-workflow |

### 3.1a Undocumented Workflows (Not in Research Summary)

6 workflows exist in code but are NOT listed in `COMFYUI_RESEARCH_SUMMARY.md`:

1. `blender_depth_guided.json` — Depth-guided rendering from Blender
2. `blender_normal_texturing.json` — Normal texture projection from Blender
3. `blender_pose_to_render.json` — Pose-based rendering from Blender
4. `edit_image_kontext.json` — Image editing via Kontext
5. `face_id_portrait.json` — Face ID-based portrait generation
6. `hunyuan3d_v20_geometry_only.json` — Hunyuan3D v2.0 geometry-only export

### 3.2 Missing Meta Sidecar

| Workflow | Issue |
|----------|-------|
| `hunyuan3d_v20_geometry_only.json` | **No `.meta.json`** — won't register as dynamic MCP tool |

### 3.3 Orphaned Meta Files

| Meta File | Issue |
|-----------|-------|
| `generate_terrain_transition.meta.json` | **No matching workflow JSON** |
| `generate_tileset_coherent.meta.json` | **No matching workflow JSON** |

These orphaned metas will cause errors or silent failures during workflow registration.

### 3.4 Potentially Redundant Workflows

Multiple image-to-3D workflows with overlapping capabilities:

| Workflow | Purpose | Overlap |
|----------|---------|---------|
| `image_to_3d.json` | Generic image-to-3D | Superset? |
| `image_to_3d_simple.json` | Simplified | Subset of above |
| `image_to_3d_triposg.json` | TripoSG backend | Specific backend |
| `hunyuan3d_mini_image_to_3d.json` | Hunyuan Mini | Different model |
| `hunyuan3d_turbo_image_to_3d.json` | Hunyuan Turbo | Different model |
| `hunyuan3d_v20_image_to_3d.json` | Hunyuan v2.0 full | Full pipeline |
| `hunyuan3d_v20_geometry_only.json` | Hunyuan v2.0 geometry | Subset of above |
| `hunyuan3d_v25_image_to_3d_pbr.json` | Hunyuan v2.5 PBR | Latest |

While each serves a distinct purpose (different models, quality levels), the naming is inconsistent and `image_to_3d.json` vs `image_to_3d_simple.json` could potentially be merged with a parameter toggle.

---

## 4. Documentation Conflicts

### 4.1 Tool Count Conflicts (CRITICAL)

| Document | Claim |
|----------|-------|
| `CLAUDE.md` | "40+ tools" |
| `COMFYUI_RESEARCH_SUMMARY.md` | "40+ MCP tools" |
| `README.md` | "40+ tools" |
| `docs/tool-reference.md` | "83+ tools" |
| Actual `@mcp.tool()` decorators | **83** (grep count) |
| Actual distinct tool functions (agent audit) | **75 explicit** + N dynamic (per workflow) |

The discrepancy between 83 decorators and 75 functions may be due to counting methodology (some decorators may be on inner functions or conditional registrations). **All three "40+" references are severely stale** — the actual count is 75-83 explicit tools plus dynamic workflow tools.

### 4.1a Hunyuan3D Path Confusion

Documentation conflates two distinct Hunyuan3D integration paths:

| Path | Backend | Description |
|------|---------|-------------|
| **Local** (ComfyUI workflows) | `hunyuan3d_v20_image_to_3d.json`, `v25_pbr` | Runs on local GPU via ComfyUI nodes |
| **Cloud** (Blender-MCP) | `generate_hunyuan3d_model`, `poll_hunyuan_job_status` | Cloud API via blender-mcp addon |

CLAUDE.md mentions both without clearly distinguishing them. `COMFYUI_RESEARCH_SUMMARY.md` describes only the local path. `docs/tool-reference.md` documents both but in separate sections. Users may not understand these are different systems.

### 4.2 Redundant Documentation

`COMFYUI_RESEARCH_SUMMARY.md` (436 lines) largely duplicates content already covered by:
- `CLAUDE.md` — Architecture, SDK API, configuration, conventions
- `docs/tool-reference.md` — Complete tool catalog with parameters
- `pipelines/RALPH-MANIFEST.md` — Pipeline details

**Sections of COMFYUI_RESEARCH_SUMMARY.md that are redundant:**
- Section 3 (SDK Capabilities) — duplicates CLAUDE.md "SDK Public API"
- Section 4 (MCP Server Tools) — duplicates `tool-reference.md` but with less detail
- Section 7 (Agent Definitions) — duplicates CLAUDE.md "Agent Team"
- Section 9 (Workflow File Structure) — duplicates CLAUDE.md "Workflow Conventions"
- Section 10 (Limitations) — duplicates CLAUDE.md "Common Pitfalls"

**Unique content in COMFYUI_RESEARCH_SUMMARY.md worth preserving:**
- Section 2 (Hunyuan3D deep-dive with VRAM requirements per stage)
- Section 6 (Texture & Material Capabilities detail)
- Section 8 (Key Technical Insights — model comparison)
- Section 12 (Missing Features)

### 4.3 Stale Path References

The prior animation audit (`packages/mcp-server/docs/audit_animation_rigging_pipeline.md`) references paths like `D:\Projects\comfyui-mcp-server\scripts\` — this was the old standalone repo path before monorepo restructuring. The paths should be `packages/mcp-server/scripts/`.

### 4.4 Version Discrepancy

| Reference | Blender Version |
|-----------|----------------|
| CLAUDE.md | Blender 5.0 |
| RALPH-MANIFEST.md | Blender 5.0 |
| Agent defs (.claude/agents/) | Blender 4.0+ (compatibility) |
| Prior audit doc | Blender 4.0+ |

This is consistent (addons are 4.0+ compatible, runtime is 5.0).

---

## 5. Overlapping Functionality

### 5.1 Two Workflow Managers (Intentional)

| File | Purpose | Lines |
|------|---------|-------|
| `packages/mcp-server/managers/workflow_manager.py` | Parametric template engine (PARAM_* substitution) | ~495 |
| `packages/prompter/workflow_manager.py` | UI <> API format converter | ~916 |

CLAUDE.md explicitly documents these as intentionally separate. **No action needed.**

### 5.2 Two Blender Addons (Intentional, but with excessive duplication)

Both addons are architecturally distinct (different backends, different class prefixes) but share ~830 lines of identical animation/utility code. See Section 1.1.

### 5.3 comfyui-nodes vs tileset.py

| Component | Type | Purpose |
|-----------|------|---------|
| `packages/comfyui-nodes/` | ComfyUI custom nodes (runs inside ComfyUI) | Non-manifold diffusion tileset sampler |
| `packages/mcp-server/tools/tileset.py` | MCP tool (API client) | Builds tileset workflows via REST API |

These are complementary (one runs inside ComfyUI, the other is an API client), but the MCP tool may not be using the custom nodes. Worth verifying the integration path.

### 5.4 Script Utility Function Duplication

Standalone scripts in `packages/mcp-server/scripts/` duplicate common functions extensively:

| Function | Copies | Purpose |
|----------|--------|---------|
| `queue_prompt()` | 11 | Queue a workflow on ComfyUI |
| `check_comfyui()` | 10 | Health check server |
| `download_image()` | 7 | Download generated image |
| `poll_history()` | 3+ | Poll job completion |

These are acceptable for standalone scripts (avoiding cross-script dependencies), but if scripts grow more interdependent, extraction to a shared `scripts/common.py` module would reduce maintenance burden.

### 5.5 Berserkr Prompt Libraries

`workflows/berserkr/` contains 4 prompt JSON files (`character_prompts.json`, `creature_prompts.json`, `equipment_prompts.json`, `ui_prompts.json`). These overlap with the prompt library MCP tools that manage prompts in `data/prompt_library.json`. The Berserkr prompts are hardcoded in scripts rather than managed through the library.

---

## 6. Recommended Actions

### Priority 1 (Quick wins)
1. Delete `packages/mcp-server/utils/autotile.py` (dead duplicate)
2. Delete `packages/mcp-server/scripts/apply_animation.py` (dead, redundant)
3. Delete `packages/mcp-server/scripts/run_animate.py` (dead prototype)
4. Create `hunyuan3d_v20_geometry_only.meta.json` (missing sidecar)
5. Delete orphaned `generate_terrain_transition.meta.json` and `generate_tileset_coherent.meta.json` (or create their workflow JSONs)
6. Update CLAUDE.md tool count from "40+" to "83+"

### Priority 2 (Cleanup)
7. Consolidate `RigBones` class into one canonical location
8. Move Berserkr batch scripts to `scripts/berserkr/` subdirectory
9. Delete `packages/mcp-server/scripts/process_triposg.py` (dead)
10. Update stale paths in `audit_animation_rigging_pipeline.md`

### Priority 3 (Architecture)
11. Evaluate `COMFYUI_RESEARCH_SUMMARY.md` — consider slimming to only unique content (Hunyuan3D deep-dive, missing features) and removing sections duplicated in CLAUDE.md
12. Address Blender addon code duplication (build-time copy from shared source, or accept as cost of addon independence)
13. Verify `comfyui-nodes` custom nodes are actually used by `tileset.py` MCP tool

---

## Appendix: File Inventory

### Static MCP Tool Count by File

| File | Tools |
|------|-------|
| `tools/prompt_library_tools.py` | 18 |
| `tools/external.py` | 14 |
| `tools/export.py` | 7 |
| `tools/model_management.py` | 7 |
| `tools/asset.py` | 5 |
| `tools/job.py` | 5 |
| `tools/style_presets.py` | 5 |
| `tools/webhook.py` | 5 |
| `tools/configuration.py` | 4 |
| `tools/batch.py` | 3 |
| `tools/publish.py` | 3 |
| `tools/workflow.py` | 3 |
| `tools/generation.py` | 1 (+ N dynamic) |
| `tools/tileset.py` | 1 |
| `tools/upscale.py` | 1 |
| `tools/variations.py` | 1 |
| **Total** | **75-83 explicit** (depending on count method) |

### Workflow Count: 48 JSONs, 49 metas (1 missing, 2 orphaned)
### Pipeline Count: 15 (12 production + 3 daemon)
### Script Count: 32 standalone scripts (4 active, 3+ dead, rest are batch tools)
