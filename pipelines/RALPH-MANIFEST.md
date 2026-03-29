# Ralph Pipeline Manifest

Master registry of all autonomous ralph loops in the ComfyUI Toolchain. Each pipeline is a self-contained, iterative generation system with quality gates and back-pressure mechanisms.

## Architecture

```
pipelines/
├── RALPH-MANIFEST.md          ← You are here
├── animate-ralph/             ← Rigged 3D → game-ready animation clips (Blender)
├── art-to-rig-ralph/          ← 2D illustration → rigged 3D (batch, multi-style)
├── fusion-ralph/              ← 3D print-ready model generation
├── asset-forge-ralph/         ← Text → animated 3D game asset
├── character-ralph/           ← Character art + 3D pipeline
├── video-ralph/               ← Script → video production
├── audio-ralph/               ← Script → dialogue + SFX + music
├── tileset-ralph/             ← Game tileset generation
├── style-transfer-ralph/      ← Batch style application
├── upscale-ralph/             ← Batch upscale + multi-format export
├── inpaint-ralph/             ← Self-correcting image refinement
├── scene-ralph/               ← Text → rendered 3D scene (cross-server: comfyui-mcp + blender-mcp)
├── autorig-ralph/             ← ML auto-rigging: unrigged mesh → skeleton → weights → IK → export
├── skeuomorph-ralph/          ← Real-world imagery → PBR-textured 3D (material-faithful)
├── validate-ralph/            ← Continuous validation daemon
├── cleanup-ralph/             ← Periodic cleanup daemon
└── hot-reload-ralph/          ← File watcher + rebuild trigger
```

## Pipeline Categories

### Production Pipelines (Multi-Stage, Goal-Oriented)

These run to completion. Each has a defined end state and outputs a `<promise>` tag when done.

| Pipeline | Purpose | Stages | Completion Promise | Typical Runtime |
|----------|---------|--------|--------------------|-----------------|
| **animate-ralph** | Rigged 3D → game-ready animation clips via Blender | 6 | `ANIMATE COMPLETE` | 15-45 min |
| **art-to-rig-ralph** | PRD → 2D art → 3D → rigged for Blender/Unity/Unreal (batch), rigging via autorig-ralph | 8 | `ART TO RIG COMPLETE` | 20-60 min |
| **fusion-ralph** | Text/CAD → 3D print-ready STL for Fusion 360 | 6 | `PIPELINE COMPLETE` | 5-15 min |
| **asset-forge-ralph** | Text → rigged, animated 3D game asset | 6 | `ASSET FORGE COMPLETE` | 15-30 min |
| **character-ralph** | Description → full character package (art + 3D), rigging via autorig-ralph | 7 | `CHARACTER COMPLETE` | 20-40 min |
| **video-ralph** | Script → keyframes → video → audio → composite | 5 | `VIDEO COMPLETE` | 30-60 min |
| **audio-ralph** | Script → TTS → voice clone → SFX → mix | 5 | `AUDIO COMPLETE` | 10-20 min |
| **tileset-ralph** | Spec → tiles → transitions → atlas → export | 5 | `TILESET COMPLETE` | 15-30 min |
| **style-transfer-ralph** | Reference + targets → batch styled output | 4 | `STYLE TRANSFER COMPLETE` | 10-25 min |
| **upscale-ralph** | Images → analyze → upscale → enhance → export | 4 | `UPSCALE COMPLETE` | 5-15 min |
| **inpaint-ralph** | Generate → evaluate → fix → loop until quality | 4 | `INPAINT COMPLETE` | 5-20 min |
| **scene-ralph** | Text → 3D scene via comfyui-mcp + blender-mcp | 6 | `SCENE COMPLETE` | 15-45 min |
| **autorig-ralph** | Unrigged mesh → ML skeleton + weights + IK + hard-surface attach | 8 | `AUTORIG COMPLETE` | 20-45 min |
| **skeuomorph-ralph** | Real-world imagery → PBR-textured 3D with faithful materials | 8 | `SKEUOMORPH COMPLETE` | 25-60 min |

### Daemon Pipelines (Continuous, No End State)

These run indefinitely until cancelled with `/cancel-ralph`. They monitor and maintain.

| Pipeline | Purpose | Interval | Cancel Command |
|----------|---------|----------|----------------|
| **validate-ralph** | Scan all pipeline outputs, validate integrity | Per iteration | `/cancel-ralph` |
| **cleanup-ralph** | TTL-based cleanup, material dedup, disk reporting | Per iteration | `/cancel-ralph` |
| **hot-reload-ralph** | Watch source files, trigger rebuilds on changes | Per iteration | `/cancel-ralph` |

---

## Quality Gate System

Every production pipeline enforces quality gates between stages. No artifact advances without passing its gate.

### Gate Result Levels

| Level | Meaning | Action |
|-------|---------|--------|
| **PASS** | All criteria met | Advance to next stage |
| **WARN** | Non-blocking issues found | Advance, but log warnings for downstream stages |
| **FAIL** | Blocking issues found | Re-run current stage with adjusted parameters |

### Back-Pressure Mechanism

Back-pressure prevents infinite loops and resource waste:

```
┌─────────────────────────────────────────────────────┐
│                  BACK-PRESSURE RULES                │
├─────────────────────────────────────────────────────┤
│                                                     │
│  1. MAX ITERATIONS                                  │
│     Each pipeline has max_iterations (default 30).  │
│     If exceeded → ABORT with partial results.       │
│                                                     │
│  2. STAGE RETRY LIMIT                               │
│     A single stage can fail its gate at most 3      │
│     times before escalating to ABORT.               │
│                                                     │
│  3. DIMINISHING RETURNS                             │
│     If a gate score doesn't improve after 2         │
│     consecutive retries → try a different approach  │
│     (different model, different parameters) OR      │
│     accept WARN level and advance.                  │
│                                                     │
│  4. RESOURCE AWARENESS                              │
│     Before starting a GPU-intensive stage:          │
│     - Check ComfyUI queue depth (< 3 pending jobs)  │
│     - Verify VRAM availability (RTX 3070 = 8GB)    │
│     - If overloaded → wait or use lighter model     │
│                                                     │
│  5. COST TRACKING (Cloud APIs)                      │
│     For Meshy/Tripo cloud calls:                    │
│     - Track API credits consumed per pipeline run   │
│     - Abort if estimated cost exceeds budget        │
│     - Prefer local ComfyUI over cloud when possible │
│                                                     │
│  6. CASCADING FAILURE DETECTION                     │
│     If Stage N fails 3x AND Stage N-1's gate was    │
│     WARN → re-run Stage N-1 first, then retry N.   │
│     Root cause is often upstream quality.            │
│                                                     │
└─────────────────────────────────────────────────────┘
```

### Gate Validation Tools

| Validation Type | Tool | Used By |
|----------------|------|---------|
| GLB integrity | `packages/mcp-server/scripts/validate_glb.py` | fusion, asset-forge, character, tileset |
| Image quality | `caption_image` workflow (Florence-2) | All image-producing pipelines |
| Semantic match | Caption vs intent similarity scoring | inpaint, character, style-transfer |
| Mesh manifold | Blender bmesh non-manifold edge check | fusion, asset-forge |
| Audio validity | File size + duration + silence detection | audio, video |
| JSON schema | Python json.load + required field check | All pipelines (state files) |
| STL print-ready | Watertight + dimensions + wall thickness | fusion |
| Seamless tiling | Edge pixel comparison (<5% deviation) | tileset |
| Style consistency | Cross-image caption similarity (>80%) | style-transfer, character |
| Rig quality | Bone count + weight paint coverage | asset-forge, character |

---

## Pipeline Interactions

Some pipelines can chain together or feed into each other:

```
                    ┌──────────────┐
                    │ inpaint-ralph│ (self-correcting image gen)
                    └──────┬───────┘
                           │ cleaned image
                           ▼
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│character-ralph│───▶│asset-forge-  │───▶│ fusion-ralph │
│ (art + views) │    │ralph (3D)   │    │ (STL export) │
└──────┬───────┘    └──────┬───────┘    └──────────────┘
       │                   │ 3D model
       │                   ▼
       │            ┌──────────────┐
       │            │ video-ralph  │ (animated scenes)
       │            └──────┬───────┘
       │                   │ video clips
       │                   ▼
       │            ┌──────────────┐
       │            │ audio-ralph  │ (dialogue + SFX)
       │            └──────────────┘
       │
       │  SUB-PIPELINE DELEGATION (rigging)
       │
       ▼            ┌──────────────────┐
┌──────────────┐    │                  │    ┌──────────────────┐
│autorig-ralph │◀───│ character-ralph  │───▶│kart-assembly-    │
│ (ML rigging) │    │ (Stage 5 RIG)   │    │ralph (kart mount)│
│              │◀───│                  │    └──────────────────┘
│ UniRig >     │    │ art-to-rig-ralph │
│ Rigify >     │    │ (Stage 6 RIG)   │
│ Meshy >      │    │                  │
│ autorig      │    └──────────────────┘
│ 50 ref meshes│
└──────────────┘

┌──────────────┐    ┌──────────────────┐
│ tileset-ralph│───▶│style-transfer-   │ (apply consistent style)
│ (base tiles) │    │ralph             │
└──────────────┘    └──────────────────┘

┌──────────────┐
│upscale-ralph │ (can post-process ANY image output)
└──────────────┘

        DAEMONS (always running)
┌──────────────┐ ┌──────────────┐ ┌──────────────────┐
│validate-ralph│ │cleanup-ralph │ │hot-reload-ralph  │
│ (QA sweep)   │ │ (TTL + dedup)│ │ (watch + rebuild)│
└──────────────┘ └──────────────┘ └──────────────────┘
```

### Sub-Pipeline Delegation

**autorig-ralph** serves as the canonical rigging engine for the pipeline ecosystem. Other pipelines delegate their rigging stages to autorig-ralph via an `invocation.json` contract:

| Caller Pipeline | Rigging Stage | Body Types | Output |
|---|---|---|---|
| **character-ralph** | Stage 5 (RIG) | humanoid only | split-mesh rigged GLB for kart-assembly |
| **art-to-rig-ralph** | Stage 6 (RIG) | all types (humanoid, quadruped, creature, mech, serpentine) | rigged GLB with Blender bone names |

autorig-ralph also runs standalone via `bash ralph.sh --preset autorig` for ad-hoc rigging tasks.

### Pipeline Chaining (autorig → animate)

autorig-ralph can chain to animate-ralph after rigging completes. When `chain_to_animate: true` is set in the invocation contract, autorig-ralph writes a `rig-handoff.json` to animate-ralph's intake directory, passing skeleton details (IK chains, twist bones, reference template, quality score). animate-ralph uses this to select and retarget reference animations from its own library (Mixamo, Quaternius, CMU mocap -- 2,700+ reference animations).

Chain usage: `bash ralph.sh --chain autorig animate`

---

## How to Run a Pipeline

### Start a production pipeline:
```
/ralph-loop "Read pipelines/asset-forge-ralph/PROMPT.md and execute for: [DESCRIPTION]. Output <promise>ASSET FORGE COMPLETE</promise> when done." --completion-promise "ASSET FORGE COMPLETE" --max-iterations 30
```

### Start a daemon pipeline:
```
/ralph-loop "Read pipelines/validate-ralph/PROMPT.md and execute continuous validation sweeps." --max-iterations 999
```

### Chain pipelines (manual):
```
# 1. Generate character art
/ralph-loop "Read pipelines/character-ralph/PROMPT.md..." --completion-promise "CHARACTER COMPLETE"

# 2. Feed character into asset-forge for 3D
/ralph-loop "Read pipelines/asset-forge-ralph/PROMPT.md, use character art from pipelines/character-ralph/output/..." --completion-promise "ASSET FORGE COMPLETE"
```

---

## Pipeline State Convention

Every pipeline tracks state in `output/pipeline-state.json` with this structure:

```json
{
  "project_name": "string — user-provided project identifier",
  "description": "string — what this run is producing",
  "current_stage": 0,
  "stages": {
    "N-name": {
      "status": "pending|in_progress|complete|failed|skipped",
      "artifacts": ["list of output file paths"],
      "gate_passed": false,
      "gate_result": "PASS|WARN|FAIL",
      "retries": 0
    }
  },
  "iteration": 0,
  "max_iterations": 30
}
```

### Status Transitions
```
pending → in_progress → complete (gate PASS/WARN)
                      → failed   (gate FAIL, retry < 3)
                      → pending  (retry: reset for re-run)
failed (retry >= 3)  → ABORT pipeline
```

---

## Environment Requirements

### MCP Servers (Claude Code)

These MCP servers are the **primary tools** for all pipeline operations. Pipelines should always use MCP tools before falling back to headless scripts.

| MCP Server | Purpose | Required By | Config |
|------------|---------|-------------|--------|
| **comfyui-mcp** | AI generation (image, 3D, video, audio), workflow execution | All generation pipelines | `comfyui-mcp` in `.claude.json` |
| **blender-mcp** | Live Blender control: rigging, animation, scene assembly, mesh ops, visual validation | All Blender-related pipelines (art-to-rig, character, animate, scene, asset-forge, fusion, skeuomorph) | `blender-mcp` in `.claude.json`, requires Blender open with addon on port 9876 |
| **coplay-mcp** | Unity editor control, Meshy cloud 3D/rigging/animation | Unity integration pipelines | `coplay-mcp` in `.claude.json` |

**Tool priority for Blender operations**: blender-mcp (`execute_blender_code`, `get_viewport_screenshot`) > coplay-mcp (Meshy cloud) > headless Blender (`--background --python`).

### Local Services

| Resource | Path/URL | Used By |
|----------|----------|---------|
| ComfyUI | `http://localhost:8188` | All generation pipelines (via comfyui-mcp) |
| Blender 5.0 | `C:/Program Files/Blender Foundation/Blender 5.0/blender.exe` | All 3D pipelines (via blender-mcp primary, headless fallback) |
| UniRig | `C:/UniRig` | autorig, asset-forge, character (ML skeleton + skin prediction) |
| Ollama | `http://localhost:11434` | Prompt recommendation (optional) |
| Python | System Python 3.13 (scripts), ComfyUI venv 3.11 (torch) | All |
| GPU | RTX 3070 8GB | All generation (VRAM-constrained) |

### VRAM Budget per Pipeline

| Pipeline | Peak VRAM | Notes |
|----------|-----------|-------|
| fusion-ralph | 0 GB | Pure geometry (Blender CPU) |
| asset-forge-ralph | 12-16 GB | Hunyuan3D v2.5 (may need offload on 8GB) |
| character-ralph | 8-12 GB | Flux image gen + Hunyuan3D |
| video-ralph | 8-10 GB | LTX-2 video gen |
| audio-ralph | 4-6 GB | AudioLDM + TTS |
| tileset-ralph | 6-8 GB | SDXL texture gen |
| style-transfer-ralph | 8-10 GB | IP-Adapter + style models |
| upscale-ralph | 4-6 GB | RealESRGAN |
| inpaint-ralph | 8-10 GB | Flux inpainting |
| autorig-ralph | 7-8 GB | UniRig skeleton + skin prediction (near VRAM limit, close ComfyUI first) |
| skeuomorph-ralph | 8-16 GB | Hunyuan3D v2.5 PBR + SD1.5 ControlNet texturing (sequential, not concurrent) |

**Constraint**: RTX 3070 has 8GB VRAM. Pipelines requiring >8GB will need model offloading or lighter alternatives. Back-pressure should prefer lower-VRAM options when queue is busy.

---

## Adding a New Pipeline

1. Create `pipelines/{name}-ralph/` with `PROMPT.md`, `stages/`, `gates/`, `output/`
2. Define stages as individual mini-ralph markdown files
3. Define gates with PASS/WARN/FAIL criteria
4. Initialize `output/pipeline-state.json`
5. Add entry to this manifest
6. Test with: `/ralph-loop "Read pipelines/{name}-ralph/PROMPT.md..." --max-iterations 5`
