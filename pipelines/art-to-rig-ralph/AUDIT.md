# Codebase Audit — art-to-rig-ralph Pipeline Rewrite

Date: 2026-03-28 | Triggered by: ralph-loop iteration 1 completion

---

## 1. Duplicate/Conflicting Tool Definitions

### MCP Server Tools (81 @mcp.tool() definitions across 18 files)

| File | Tool Count | Category |
|------|-----------|----------|
| external.py | 14 | External services (Tripo, UniRig, blender-mcp) |
| prompt_library_tools.py | 18 | Prompt templates, style presets |
| export.py | 7 | Asset export (FBX, GLB, STL, shared dir) |
| job.py | 5 | Job queue management |
| asset.py | 5 | Asset registry operations |
| webhook.py | 5 | Webhook notifications |
| configuration.py | 4 | Health check, defaults, models |
| style_presets.py | 5 | Style preset management |
| batch.py | 3 | Batch generation |
| workflow.py | 3 | Workflow list/run/validate |
| model_management.py | 4 | Model download/install |
| generation.py | 1 | Dynamic workflow tool registration |
| variations.py | 1 | Image variations |
| publish.py | 3 | Cross-server publishing |
| upscale.py | 1 | Image upscaling |
| tileset.py | 1 | Tileset generation |

**No conflicts found.** All tools are in separate files with distinct names. The `generation.py` dynamic registration creates tools from workflow .meta.json files — these are complementary to `workflow.py`'s `run_workflow`, not duplicates.

### Potential Overlap: Rigging Tools
- `external.py:auto_rig_model` — MCP tool wrapping UniRig/Tripo rigging
- `unirig_client.py:rig_model` — Direct UniRig client
- `tripo_client.py:rig_model` + `rig_and_animate` — Tripo cloud rigging
- `blender/comfyui_tools/operators_rig.py:COMFYUI_OT_auto_rig` — Blender UI operator
- `blender/comfyui_mcp_tools/operators.py:COMFY_OT_auto_rig` — Blender MCP UI operator

**Verdict:** Not duplicates — different layers of the same feature (API client, MCP tool, Blender UI). By design.

---

## 2. Redundant Workflow Files

**48 workflow JSONs, 49 meta JSONs.**

### Orphans Found

| File | Type | Action Needed |
|------|------|---------------|
| `hunyuan3d_v20_geometry_only.json` | Workflow without .meta.json | Needs meta file or is a WIP |
| `generate_terrain_transition.meta.json` | Meta without workflow JSON | Dead reference — workflow never created |
| `generate_tileset_coherent.meta.json` | Meta without workflow JSON | Dead reference — workflow never created |

### Berserkr Workflows
`workflows/berserkr/` directory exists but is **empty** (no files found). The berserkr workflows (`berserkr_chargen_card.json`, `berserkr_chargen_fullbody.json`, `berserkr_chargen_portrait.json`) are correctly in `workflows/mcp/` with meta files. **No duplication.**

---

## 3. Dead Code / Unused Scripts

### Old vs New Pipeline Scripts

| Script | Status | Notes |
|--------|--------|-------|
| `scripts/rig_kart.py` | **SUPERSEDED** | Old 17-bone armature approach. Replaced by mesh_split.py + kart_assembler.py |
| `scripts/mesh_prep.py` | **STILL NEEDED** | Mesh preparation (fill holes, decimate, scale) — used before split |
| `scripts/mesh_prep_light.py` | **CHECK** | Lighter version of mesh_prep — may be redundant with mesh_prep.py |
| `scripts/mesh_split.py` | **NEW** | Region-based mesh separator |
| `scripts/kart_assembler.py` | **NEW** | Hierarchy assembly + export |
| `scripts/kart_pipeline_interactive.py` | **NEW** | Interactive blender-mcp wrapper |
| `scripts/test_backpressure.py` | **NEW** | Back-pressure test suite (25 tests) |

**Action:** `rig_kart.py` should be archived or removed. `mesh_prep_light.py` should be checked for redundancy with `mesh_prep.py`.

### Batch Scripts in packages/mcp-server/scripts/

Many standalone batch scripts exist. These are NOT referenced by MCP tools — they're standalone CLI utilities:
- `generate_3d_ground_tiles.py`, `generate_berserkr_assets.py`, `generate_berserkr_characters.py`, etc.
- `batch_animate_unirig.py`, `batch_unirig.py` — batch rigging scripts
- `hunyuan3d_batch_convert.py`, `tripo_batch_convert.py` — batch 3D conversion

**Verdict:** These are intentional standalone scripts, not dead code. They use `urllib.request` directly (no SDK dependency).

---

## 4. Conflicting Documentation

### CLAUDE.md vs Actual State

| Claim in CLAUDE.md | Actual | Conflict? |
|---------------------|--------|-----------|
| "40+ tools" | 81 @mcp.tool() definitions | Outdated — should say 80+ |
| Tool reference doc says "83+ tools" | 81 counted | Close enough |
| "17-bone mechanical skeleton" in PRD | Now modular hierarchy | **PRD updated** in this iteration |
| art-to-rig-ralph plan.md had 8 tasks, all `"passes": false` | Now has 8 tasks with updated architecture | **Updated** in this iteration |

### Pipeline PROMPT.md Conflicts
- `art-to-rig-ralph/PROMPT.md` — needs updating to reference new scripts (mesh_split, kart_assembler) instead of old rig_kart.py
- `character-ralph/stages/05-rig-animate.md` — references UniRig and Blender Rigify for humanoid rigging. No conflict with kart pipeline (different body types).
- `animate-ralph/stages/01-intake.md` — references kart animation. Should be checked for compatibility with new modular hierarchy.

---

## 5. Overlapping Functionality Between Packages

### SDK vs MCP Server
- **No overlap found.** SDK provides client/assets/defaults/config. MCP server provides tools/managers/workflows. Clean separation.

### packages/mcp-server/utils/
- Directory exists but is **empty** (no files). No overlap possible.

### Blender Addons Overlap

| Feature | comfyui_tools (SDK) | comfyui_mcp_tools (MCP) |
|---------|---------------------|-------------------------|
| Auto-rig | `COMFYUI_OT_auto_rig` | `COMFY_OT_auto_rig` |
| Generate animation | `COMFYUI_OT_generate_animation` | `COMFY_OT_generate_animation` |
| Import mocap | `COMFYUI_OT_import_mocap` | `COMFY_OT_import_mocap` |
| Export model | `COMFYUI_OT_export_model` | `COMFY_OT_export_model` |
| Capture viewport | `COMFYUI_OT_capture_viewport` | `COMFY_OT_capture_viewport` |
| Use render result | `COMFYUI_OT_use_render_result` | `COMFY_OT_use_render_result` |

**6 overlapping operators** between the two Blender addons. They have different class prefixes and connect to different backends (Flask API vs MCP HTTP), but provide identical user-facing features. This is documented as intentional in CLAUDE.md ("Two separate addons — different backends").

---

## 6. Summary of Actions Needed

### Critical — ALL DONE
1. ~~**Archive `rig_kart.py`**~~ DONE — renamed to `rig_kart.py.archived`
2. ~~**Create meta for `hunyuan3d_v20_geometry_only.json`**~~ DONE — created `.meta.json`
3. ~~**Remove orphan metas**~~ DONE — already removed (were untracked)

### Recommended — ALL DONE
4. ~~**Update CLAUDE.md** tool count from "40+" to "80+"~~ DONE
5. ~~**Update `art-to-rig-ralph/PROMPT.md`**~~ DONE — added Mech/Vehicle row, updated stage 6 desc
6. ~~**Check `mesh_prep_light.py`**~~ KEPT — valid fallback script (scale+center only, for meshes that fail aggressive cleanup)
7. **`workflows/berserkr/`** — KEPT — contains prompt JSON files (character, creature, equipment, UI prompts), not empty
8. ~~**Check `animate-ralph`**~~ DONE — updated 01-intake.md bone count reference for karts

### Low Priority — DEFERRED
9. Document the 6 overlapping Blender addon operators as architectural decision
10. Consider consolidating `generate_*` batch scripts that share common patterns
