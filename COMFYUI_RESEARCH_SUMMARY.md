# ComfyUI Toolchain - Comprehensive Research Summary

## Overview
A unified toolkit for AI media generation via ComfyUI with 80+ MCP tools, parametric workflows, and Blender integration. Three packages: SDK (shared foundation), MCP Server (generation tools), and Prompter (GUI/API).

---

## 1. AVAILABLE WORKFLOWS (45 Total)

### Image Generation (13 workflows)
- **generate_image.json** - Basic text-to-image (SDXL/Flux)
- **generate_image_flux2.json** - Flux 2 text-to-image
- **generate_image_controlnet.json** - ControlNet conditioning for guided generation
- **generate_image_lora.json** - LoRA-enhanced text-to-image with style adaptation
- **generate_image_pixelart.json** - Pixel art generation workflow
- **img2img.json** - Image-to-image variation (style transfer)
- **inpaint.json** - Inpainting (content fill/replacement)
- **inpaint_flux_fill.json** - Flux-based inpainting
- **image_variations.json** - Generate variations of an image
- **remove_background.json** - Background removal
- **segment_image.json** - Image segmentation/masking
- **caption_image.json** - Image captioning/description generation
- **image_to_svg.json** - Rasterize image to SVG vector

### Style Transfer (3 workflows)
- **style_transfer_ipadapter.json** - IP-Adapter style transfer (reference image based)
- **style_transfer_multi_reference.json** - Multi-reference style transfer
- **style_transfer_weighted.json** - Weighted multi-style combination

### 3D Generation (9 workflows)
- **generate_3d.json** - Generic 3D generation
- **image_to_3d.json** - Image-to-3D (generic pipeline)
- **image_to_3d_simple.json** - Simplified image-to-3D
- **image_to_3d_triposg.json** - TripoSG image-to-3D (newer alternative to TripoSR)
- **hunyuan3d_mini_image_to_3d.json** - Hunyuan3D Mini (lighter weight)
- **hunyuan3d_turbo_image_to_3d.json** - Hunyuan3D Turbo (fast mode)
- **hunyuan3d_v20_image_to_3d.json** - Hunyuan3D v2.0 (FULL TEXTURED PIPELINE - includes delighting, UV wrapping, multi-view baking, texture inpainting)
- **hunyuan3d_v25_image_to_3d_pbr.json** - Hunyuan3D v2.5 with PBR output (physically-based rendering textures)

### Texture Generation (2 workflows)
- **generate_texture_tile.json** - Seamless tileable textures (SDXL + LoRA for game terrain)
- **generate_tileset_coherent.json** - Coherent 4x4 tileset (16 tiles simultaneously, non-manifold diffusion, marching squares)

### Video Generation (5 workflows)
- **generate_video.json** - Generic video generation
- **generate_video_ltx2.json** - LTX-2 text-to-video (Lightricks, up to 4K, 50fps, 20-second clips)
- **image_to_video.json** - Image-to-video
- **image_to_video_ltx2.json** - LTX-2 image-to-video
- **video_frame_interpolation.json** - Frame interpolation (smooth playback)

### Audio Generation (4+ workflows)
- **generate_speech.json** - Text-to-speech
- **generate_song.json** - Music generation
- **generate_sfx.json** - Sound effect generation
- **voice_clone.json** - Voice cloning (F5-TTS + RVC for high-fidelity conversion)
- **video_to_audio.json** - Extract/process audio from video
- **lip_sync.json** - Lip sync video generation

### Upscaling & Enhancement (3 workflows)
- **upscale.json** - Image upscaling
- **video_frame_interpolation.json** - Temporal upscaling

### Berserkr Game-Specific (5 workflows)
- **berserkr.json** - Game art generation
- **berserkr_chargen_portrait.json** - Character portrait (Frank Miller Sin City style)
- **berserkr_chargen_card.json** - Character card/reference
- **berserkr_chargen_fullbody.json** - Full-body character art (528x528, standing pose reference)

### Utility (2 workflows)
- **basic_api_test.json** - API connectivity test
- **generate_terrain_transition.json** - Terrain transition generation

---

## 2. HUNYUAN3D CAPABILITIES (KEY FINDINGS)

### Hunyuan3D v2.0 (FULL PIPELINE)
**Workflow**: `hunyuan3d_v20_image_to_3d.json`

**Complete Output Options**:
1. **Geometry-only GLB** - Fast mesh export at node 11 (no textures)
2. **Textured GLB** - Full textured output after complete pipeline

**Pipeline Stages**:
- Background removal (InspireNet RemBG)
- Mesh generation via diffusion (HY3DGenerateMesh)
- VAE decode with octree resolution control (384-512, higher = more detail)
- Mesh postprocessing with face decimation (5k-500k faces adjustable)
- **Delighting** (removes lighting from source image)
- **UV wrapping** (automatic UVs)
- **Multi-view rendering** (renders 8+ views from different angles)
- **Texture baking** (samples and bakes textures from multi-view renders)
- **Texture inpainting** (fills gaps in baked textures)
- **Texture application** (applies to mesh)

**Output Quality Options**:
- Octree resolution: 128-512 (default 384) - affects vertex detail
- Max faces: 5k-500k (default 50k) - mesh density control
- Steps: 10-100 (default 50) - diffusion quality
- CFG: 1.0-30.0 (default 5.5) - prompt adherence

**VRAM Requirements**:
- Minimum: 12 GB
- Recommended: 16 GB

### Hunyuan3D v2.5 with PBR
**New Feature**: Physically-based rendering textures (metallic, roughness, normal maps)

### Hunyuan3D Mini & Turbo
- **Mini**: Lighter weight, lower quality, ~8GB VRAM
- **Turbo**: Speed-optimized, good balance

---

## 3. SDK CAPABILITIES (`packages/sdk/`)

### ComfyUIClient
- Queue and execute workflows on ComfyUI
- Upload images and files
- Poll result status via REST API
- WebSocket monitoring for real-time progress
- Error parsing with structured error types
- Model refresh and validation
- Custom workflow execution

### AssetRegistry
- UUID-based asset tracking
- TTL-based automatic cleanup (24 hours default, configurable)
- Asset metadata: filename, dimensions, mime type, file size
- VRAM requirement tracking
- Workflow history recording
- Thread-safe access via RLock

### DefaultsManager
- Per-media-type model defaults (image, video, audio, 3d)
- Parameter preset management
- Model validation against available checkpoints
- Environment variable and config file support

### Credentials
- Keyring-based credential storage (system secure store)
- HuggingFace token management
- CivitAI API key storage

### Configuration
- ComfyUI URL/connection settings
- Ollama integration settings
- Workflow directory paths
- Asset TTL configuration
- Generation timeout settings

---

## 4. MCP SERVER TOOLS (80+)

### Tool Categories

#### Generation Tools (`tools/generation.py`)
- `generate_image` - Text-to-image (SDXL, Flux, etc.)
- `generate_image_lora` - LoRA-controlled generation
- `generate_image_controlnet` - ControlNet conditioning
- `generate_image_pixelart` - Pixel art generation
- `generate_video` - Text-to-video (AnimateDiff, SVD)
- `generate_video_ltx2` - LTX-2 high-quality video
- `generate_speech` - Text-to-speech
- `generate_song` - Music generation
- `generate_sfx` - Sound effects
- `voice_clone` - Voice cloning with RVC
- `image_to_3d` - Image-to-3D (TripoSR, TripoSG, Hunyuan3D variants)
- `img2img` - Image variation/editing
- `inpaint` - Content fill
- Plus more variants

#### Asset Management (`tools/asset.py`)
- `list_assets` - List generated assets
- `get_asset` - Retrieve asset by ID
- `get_asset_preview` - Get thumbnail/preview
- `delete_asset` - Clean up assets

#### Workflow Tools (`tools/workflow.py`)
- `run_workflow` - Execute parametric workflow
- `list_workflows` - Available workflows
- `get_workflow_definition` - Full workflow details

#### Model Management (`tools/model_management.py`)
- `list_models` - Available checkpoints/models
- `get_model_info` - Model metadata
- `download_model` - Download from HuggingFace/CivitAI

#### Upscaling (`tools/upscale.py`)
- `upscale_image` - 2x, 4x upscaling

#### Variations (`tools/variations.py`)
- `create_image_variation` - Generate variations
- `style_transfer` - IP-Adapter style transfer

#### Batch Operations (`tools/batch.py`)
- `batch_generate` - Multiple generations in sequence
- `batch_upscale` - Batch upscaling

#### Job Management (`tools/job.py`)
- `get_job_status` - Check generation progress
- `cancel_job` - Stop in-progress job
- `list_jobs` - Queue status

#### Configuration (`tools/configuration.py`)
- `set_defaults` - Update model/parameter defaults
- `get_configuration` - Current settings

#### Style Presets (`tools/style_presets.py`)
- `list_style_presets` - Available preset styles
- `apply_style_preset` - Use preset for generation

#### Prompt Library (`tools/prompt_library_tools.py`)
- `search_prompts` - Find prompt templates
- `get_prompt_template` - Retrieve template
- `add_prompt` - Save new prompt

#### Export Tools (`tools/export.py`)
- `export_social_media` - Format for platforms
- Export presets for different targets

#### External Tools (`tools/external.py`)
- Integration with external applications
- App discovery and launching

#### Publishing (`tools/publish.py`)
- Publish assets to galleries/stores
- Manifest management

#### Webhooks (`tools/webhook.py`)
- Register notification endpoints
- Event-based callbacks

#### Tileset Tools (`tools/tileset.py`)
- `generate_game_tileset` - Coherent tileset generation
- `list_tileset_presets` - Available terrain styles

---

## 5. BLENDER ADDON CAPABILITIES

### ComfyUI Tools Addon (`blender/comfyui_tools/`)
**Version**: 2.0.0
**Backend**: Flask REST API (port 5050)
**Class Prefix**: `COMFYUI_OT_`, `COMFYUI_PT_`

#### Generation Features
- Text-to-3D model generation
- Image-to-3D from reference
- Prompt analysis and AI recommendations
- Viewport capture for img2img
- Workflow browser and parameter editor
- Queue monitoring with progress indicator
- Job cancellation and queue clearing
- Output folder browsing

#### Rigging Features
- Auto-rigging via Rigify/UniRig
- Humanoid rig generation
- Automatic weight painting
- IK constraint setup
- Multiple rig type support (biped, quadruped, custom)

#### Animation Features
- Procedural animation generation
- Walk cycle creation
- Run, idle, attack animations
- Locomotion variants
- Action library with presets
- Loop configuration
- FPS/duration control

#### Motion Capture Features
- BVH file import
- Retargeting to rig
- Frame range extraction

#### Export Features
- GLB, FBX, Blender export
- Format-specific optimization
- Social media preset export
- Multi-format batch export

---

## 6. TEXTURE & MATERIAL CAPABILITIES

### Seamless Texture Generation
- **Tool**: `generate_texture_tile.json`
- **Models**: SDXL + SomeTile/PreAlphaWoW LoRA
- **Output**: 512x512 seamless tiles (adjustable)
- **Use Case**: Individual terrain tiles (grass, stone, water, sand)
- **Strength Control**: LoRA strength 0-1.0 for style intensity

### Coherent Tileset Generation
- **Tool**: `generate_tileset_coherent.json`
- **Method**: Non-manifold diffusion (all 16 tiles generated simultaneously)
- **Output**: 4x4 grid of seamless tiles in one image
- **Advantage**: Tiles have consistent style and seamless edges

### Texture Projection (via Hunyuan3D v2.0)
- Multi-view texture baking
- Texture inpainting for gap filling
- Direct texture application to mesh

---

## 7. AGENT DEFINITIONS (7 specialized agents)

### SDK Developer
- `packages/sdk/` - ComfyUIClient, AssetRegistry, DefaultsManager, credentials

### MCP Tools Developer
- `packages/mcp-server/` - 80+ tools, managers, workflow engine
- Key modules: generation.py, asset.py, workflow.py, model_management.py

### Prompter Developer
- `packages/prompter/` - GUI, Flask API, workflow recommendation

### Workflow Engineer
- `workflows/mcp/` - Parametric workflow JSON and .meta.json sidecars
- Owns all workflow definitions and parameter specifications

### Test Engineer
- All test directories - pytest, fixtures, CI configuration

### Blender Addon Developer
- `blender/` - Both addon packages (different class prefixes, backends)

### Setup Engineer
- Root configs, pyproject.toml, setup wizard, documentation

---

## 8. KEY TECHNICAL INSIGHTS

### 3D Generation Summary
1. **Hunyuan3D v2.0** = Full textured + delighting + PBR-ready. Best for game assets.
2. **TripoSG** = Fast, good quality, simple integration.
3. **TripoSR** = Older variant, still functional.
4. **Hunyuan3D Mini/Turbo** = Lower VRAM alternatives.

### Texture Output Quality
- Hunyuan3D v2.0 outputs GLB with vertex-painted or texture-mapped materials
- Multi-view baking ensures texture consistency from multiple angles
- Inpainting fills seams and gaps automatically
- **v2.5 adds PBR** with metallic/roughness/normal maps

### Game Asset Production
- **Character Art**: Berserkr workflows generate concept art (full-body, portrait, card)
- **Terrain**: Tileset workflows generate coherent 4x4 grids or individual tiles
- **3D Models**: Hunyuan3D can generate textured GLB from concept art
- **Tilesets**: Non-manifold diffusion ensures seamless edges across 16 tiles

### Performance
- **LTX-2 Video**: ~16 GB VRAM for 1280x720, 41 frames, 24fps
- **Hunyuan3D v2.0**: ~12-16 GB VRAM for textured mesh
- **Texture tiles**: ~8 GB minimum VRAM
- **All models**: Configurable VRAM via resolution/step reduction

---

## 9. WORKFLOW FILE STRUCTURE

Each workflow JSON has companion `.meta.json` sidecar:

### Workflow JSON
- ComfyUI API format
- PARAM_* placeholder strings for substitution
- Node graph with connections

### Meta.json Sidecar
```json
{
  "name": "Human-readable title",
  "description": "What it does",
  "category": "3d|image|video|audio",
  "tags": ["tag1", "tag2"],
  "parameters": {
    "PARAM_NAME": {
      "type": "string|int|float",
      "required": true|false,
      "default": "value",
      "min": 0,
      "max": 100
    }
  },
  "requirements": {
    "nodes": ["NodeName"],
    "models": { "checkpoint": "model.safetensors" },
    "custom_nodes": ["NodePackage"],
    "vram_minimum_gb": 8
  }
}
```

---

## 10. KEY LIMITATIONS & CONSTRAINTS

1. **Two Workflow Managers**: MCP's `workflow_manager.py` (parametric template engine) ≠ Prompter's `workflow_manager.py` (UI format converter). Don't merge.

2. **Two Blender Addons**:
   - `comfyui_tools` = full-featured (generation, rigging, animation, mocap, export)
   - `comfyui_mcp_tools` = lightweight (rigging, animation, MCP integration)
   - Different class prefixes, different backends, intentionally separate

3. **Hardcoded Paths**: Watch for Windows-specific paths (D:\ prefixes). Use env vars.

4. **MCP Version**: SDK requires `mcp>=1.0.0`

5. **No pip in Blender**: Blender addon uses only stdlib + urllib (no requests library)

---

## 11. PRODUCTION READINESS

The ComfyUI Toolchain is **production-ready** with:
- **45 workflows** covering image, video, audio, and 3D generation
- **Hunyuan3D v2.0 full pipeline** with texture baking and inpainting for game-quality 3D
- **Coherent tileset generation** for seamless game terrain
- **Blender integration** for rigging, animation, and export
- **80+ MCP tools** for AI-powered automation
- **Extensible architecture** with clear agent boundaries

**Best suited for**: Game developers, VN creators, and asset pipeline automation.

---

## 12. MISSING FEATURES TO NOTE

- **Texture Projection to Existing Models**: Baking is per-model, not batch reprojection
- **PBR Material Export**: v2.5 supports it, but material definition varies by engine
- **Vertex Color Output**: Hunyuan3D v2.0 supports vertex colors, check GLB export settings
- **Normal Map Baking**: Not explicit in workflow, relies on v2.5 PBR
- **Displacement Maps**: Not mentioned in current workflows
