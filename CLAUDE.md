# ComfyUI Toolchain

## Project Goal

This project is built on **two primary MCP servers** that Claude uses directly:

- **comfyui-mcp** — AI generation backend (image, video, audio, 3D mesh generation) via ComfyUI at `http://localhost:8188`
- **blender-mcp** — Live Blender control via socket (port 9876). Provides `execute_blender_code`, `get_viewport_screenshot`, `get_scene_info`, Poly Haven, Sketchfab, and Hunyuan3D tools

Additionally:
- **coplay-mcp** — Unity editor control for game integration (Meshy 3D, rigging, animations)
- **ComfyUI** — local installation at `D:\Projects\ComfyUI`

The goal is a seamless AI-powered creative pipeline for 3D modeling and game design:
ComfyUI (AI generation) -> Blender (3D assembly/rigging/animation) -> Unity (game integration)

### MCP Server Priority for 3D/Game Pipelines

Any pipeline involving Blender operations (rigging, animation, scene assembly, mesh operations, export) **MUST use blender-mcp as the primary tool**. This means:
1. **Always try blender-mcp first** — `execute_blender_code` for arbitrary Blender Python, `get_viewport_screenshot` for visual validation
2. **comfyui-mcp for generation** — image generation, 3D mesh generation (Hunyuan3D), background removal, style transfer
3. **coplay-mcp for Unity** — auto-rigging (Meshy), animations, Unity scene setup
4. **Headless Blender (`--background`) is the fallback**, not the default — only use when blender-mcp is unreachable
5. Check blender-mcp availability via `get_external_app_status` → `blender_mcp.available` at the start of any Blender-related stage

## Key Commands

```bash
# Run all tests
pytest

# Run one package's tests
pytest packages/mcp-server/tests/

# Start MCP server
comfyui-mcp

# Start Flask API (for Blender addon)
comfyui-api

# Check ComfyUI is running
curl http://localhost:8188/system_stats
```

## Rules

- ONE task per ralph loop iteration
- No stubs or placeholders — full implementations only
- Always run tests after implementing
- Update plan.md after every loop
- Commit after each completed task
- Blender addons: NO pip dependencies, urllib only, Blender 4.0+ API

## Architecture

Three packages in `packages/` directory:
- **packages/sdk/** (`comfyui-agent-sdk`) - Shared Python SDK providing ComfyUIClient, AssetRegistry, DefaultsManager, and credential management
- **packages/mcp-server/** (`comfyui-mcp-server`) - FastMCP server with 80+ tools for AI image/video/audio/3D generation
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
- `BLENDER_HOST` - Blender MCP socket host (default: `localhost`)
- `BLENDER_PORT` - Blender MCP socket port (default: `9876`)
- `COMFY_MCP_SHARED_DIR` - Shared directory for cross-server asset handoff (default: `output/shared`)

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
- Test paths: `packages/sdk/tests/`, `packages/mcp-server/tests/`, `packages/prompter/tests/`, `tests/`
- Markers: `@pytest.mark.integration` (requires running ComfyUI), `@pytest.mark.slow`
- Async tests: `pytest-asyncio` for MCP server tests
- Run all: `pytest` from repo root
- Run one package: `pytest packages/mcp-server/tests/`
- Integration tests (mocked, no services): `pytest tests/integration/ -v`
- Integration tests (live, requires ComfyUI): `pytest tests/integration/ -m integration -v`
- Integration tests (live + slow generation): `pytest tests/integration/ -m "integration and slow" -v`

## ComfyUI Runtime Environment

- **ComfyUI version**: 0.10.0 at `D:\Projects\ComfyUI\`
- **Venv**: `D:\Projects\ComfyUI\venv\` — **Python 3.11.9** (NOT system Python 3.13)
- **PyTorch**: 2.9.1+cu126 (CUDA 12.6 runtime)
- **CUDA toolkit**: 12.4 (system install at `C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v12.4`)
- **GPU**: NVIDIA GeForce RTX 3070 8GB VRAM
- **System RAM**: ~16GB
- **Blender**: 5.0 at `C:\Program Files\Blender Foundation\Blender 5.0\blender.exe`
- **Blender MCP**: addon.py (v1.4.0) installed in Blender addons, socket server on port 9876. MCP server configured in `.claude.json` from `C:\Users\scher\Downloads\blender-mcp-main\blender-mcp-main`. Provides `execute_blender_code`, `get_viewport_screenshot`, `get_scene_info`, Poly Haven asset search/download, Sketchfab search/download, and Hunyuan3D cloud generation tools. **This is the primary interface for all Blender operations in pipelines.**
- **UniRig**: `C:\UniRig` (.venv Python 3.11, CUDA)

### Version Compatibility Notes

- **Python version mismatch**: System Python is 3.13, ComfyUI venv is 3.11. CUDA extensions (.pyd) compiled for 3.11 will NOT work with system Python. Always use `D:/Projects/ComfyUI/venv/Scripts/python.exe` for anything that imports torch/CUDA.
- **Batch scripts** (`hunyuan3d_batch_convert.py`, `generate_props.py`, etc.) use `urllib.request` to talk to ComfyUI's REST API and do NOT need the venv Python — they work with any Python 3.10+.
- **Hunyuan3D textured pipeline DLL fix**: The `custom_rasterizer_kernel` CUDA extension requires torch and CUDA DLL directories in the DLL search path on Windows. Fixed via `os.add_dll_directory()` in `ComfyUI-Hunyuan3DWrapper/hy3dgen/texgen/custom_rasterizer/custom_rasterizer/__init__.py`. Without this, nodes 12-24 (texture baking) fail with "DLL load failed".

## Common Pitfalls

1. **Two `workflow_manager` modules** - MCP server's (`packages/mcp-server/managers/workflow_manager.py`, ~495 LOC) is a parametric template engine that substitutes PARAM_* placeholders. Prompter's (`packages/prompter/workflow_manager.py`, ~916 LOC) is a UI<>API format converter. They serve completely different purposes and should NOT be merged.

2. **Two Blender addons** - `blender/comfyui_tools/` (SDK, v2.0.0) and `blender/comfyui_mcp_tools/` (MCP, v1.3.0) have different class prefixes, different backends, and different feature sets. They are intentionally separate.

3. **Hardcoded paths** - Watch for hardcoded Windows paths (e.g., `D:\` prefixed paths). Use `os.path.join()` and environment variables instead.

4. **SDK imports** - MCP server and Prompter both import from `comfyui_agent_sdk`. In dev mode, install SDK as editable: `pip install -e packages/sdk/`

5. **MCP version** - SDK requires `mcp>=1.0.0`. MCP server previously pinned `mcp>=0.9.0` but should use `>=1.0.0` in the monorepo.

6. **Blender-MCP is the primary Blender interface** - For all pipeline stages that touch Blender (rigging, animation, mesh prep, scene assembly, export), use `blender-mcp` tools (`execute_blender_code`, `get_viewport_screenshot`, `get_scene_info`) as the **first choice**. The `publish_for_blender` comfyui-mcp tool copies assets to `output/shared/` for cross-server handoff. Headless Blender (`--background --python`) is the fallback path only when blender-mcp is unreachable. Legacy addon paths: (a) `comfyui_tools` addon → Flask API port 5050, (b) `comfyui_mcp_tools` addon → MCP HTTP — these are secondary to blender-mcp for pipeline work.

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

## Ralph Loop

This project uses the Universal Ralph Loop at `~/ralph-universal/` (GitHub: dscherm/ralph-universal).

```bash
~/ralph-universal/ralph.sh 20           # Run 20 iterations
~/ralph-universal/ralph.sh --dry-run    # Validate setup
~/ralph-universal/ralph-plan.sh         # Discover work (read-only analysis)
python ~/ralph-universal/tools/bootstrap.py  # Bootstrap a new project
```

Tasks go in `plan.md` (JSON blocks) or `fix_plan.md` (checkbox format). Configuration in `ralph.config.json`.

<!-- unpossible-ralph: auto-injected context -->
@.claude/.ralph-lessons.md
@.claude/.ralph-spec.md
@.claude/.ralph-pending-reviews.md
@.claude/.ralph-handoff.md
@.claude/.ralph-bridge-resume.md
@.claude/.ralph-bootstrap-needed.md


<!-- unpossible-ralph: auto-injected context -->
@.claude/.ralph-precompact.md
@.claude/.ralph-human-requests.md
@.claude/.ralph-scope.md

---

## Lesson tagging discipline

<!-- ralph-discipline: lesson_applied_tagging -->

This project is enrolled in ralph-universal's cross-project learning
system. The dashboard's `applied_count` metric depends on accurate
`<lesson_applied>` tags in commit bodies. A Day-1 audit (2026-06-02)
across enrolled projects found that ~70% of tags didn't reflect the
actual diff — agents were defaulting to familiar stem names rather
than tagging what the diff actually applied. This section sets the
rule going forward.

### When to emit `<lesson_applied>`

Emit `<lesson_applied stem='X' note='...'/>` in commit bodies **only
when the diff actually contains the pattern, fix, or behavior the
lesson documents**. The test:

> Would this commit's code be measurably different if the lesson
> didn't exist?

If yes → tag it. If no → do not tag.

### When NOT to tag

- **Read but didn't apply** — that is consultation, not application.
  Do not emit `<lesson_applied>`. The day-30 audit explicitly filters
  "consulted but not applicable" out as noise.
- **Familiar-stem default** — never emit a tag just because the stem
  is the one you remember from a prior session. Re-check
  `.claude/.ralph-lessons.md` for the currently-injected set and
  cross-reference against the diff.
- **Stale stems** — only stems with both `lessons/<stem>.md` present
  AND a recent injection record for this project should be tagged.
- **Same tag-block on every commit** — if two consecutive unrelated
  commits emit the same tag set, the second one is almost certainly
  ritual stamping. Stop.

### Optional: track consultations in the audit channel

If you want a paper trail for "I read this lesson and decided it
didn't apply", use the dedicated verb instead of polluting the
application metric:

```bash
python $RALPH_HOME/tools/tag_lesson.py consulted <stem> \
  --source preflight \
  --reason "<one-line reason>"
```

This appends a `consulted` event to `.ralph/lesson-events.jsonl` —
honest audit signal that doesn't inflate the application count.

### Short version

- Diff reflects the lesson → `<lesson_applied stem='X' note='...'/>` ✓
- Read but didn't apply → say nothing, OR use `tag_lesson consulted` ✓
- Same tag-block on every commit → ✗ (ritual stamping; stop)
- "Consulted, decided not applicable" as a `<lesson_applied>` note → ✗

When in doubt, skip the tag. Under-tagging is correctable (the
auto-stamp mechanism catches some real applications via keyword
matching); over-tagging is harder to clean up after.

### Process lessons are NOT default tags

<!-- ralph-discipline: anti-ritual -->

Day-2 (2026-06-03) audit found that the original discipline rule (above)
compressed ritual stamping from a 5-tag block to a 1-tag default —
agents started tagging the same process lesson on every commit
regardless of whether the commit body discussed the procedure. This
addendum closes that hole.

The following lessons describe procedure-failure modes and are
particularly prone to ritual stamping:

- `mark-phase-skipped` — about agents forgetting to set `passes: true`
  or skipping the bridge_state lifecycle
- `harvest-skip` — meta-marker that no lessons applied this task
- `check-existing-before-authoring` — about authoring code without
  reading the existing module first
- `template-task-infinite-loop` — about getting stuck on dummy tasks

**Do NOT tag any of these by default.** Tag them only when BOTH of:

1. The commit body explicitly discusses the procedure the lesson
   documents (e.g., a `mark-phase-skipped` tag requires the commit
   body to mention plan.md, mark-phase, passes:true, or the bridge
   lifecycle by name).
2. The diff would have been wrong without the lesson's guidance.
   "Following standard protocol" is not application — it's
   compliance, and compliance is the expected default.

If you followed the procedure but the commit body doesn't reference
it, that's good engineering, not lesson application. No tag.

If you want to record that you followed the procedure for audit
purposes (without inflating the application count), use the consulted
audit channel:

```bash
python $RALPH_HOME/tools/tag_lesson.py consulted mark-phase-skipped \
  --source preflight \
  --reason "followed procedure as expected"
```

### Sanity check before any tag

Before emitting `<lesson_applied stem='X' />`, ask:

> Could a reviewer reading the commit body alone trace the X lesson's
> guidance to a specific change in this diff?

If yes → tag.
If no → it's ritual or compliance, not application. Don't tag.
