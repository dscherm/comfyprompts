# MCP Server Integration Plan

Audit completed 2026-02-06 by the MCP Server Developer agent.

---

## 1. Existing Tool Catalog (54 tools across 10 modules)

### Generation Tools (auto-registered from workflows) -- `tools/generation.py`
| # | Tool | Source Workflow | Description |
|---|------|----------------|-------------|
| 1 | `generate_image` | `generate_image.json` | Flux-based image generation |
| 2 | `generate_song` | `generate_song.json` | AceStep audio generation |
| 3 | `generate_video` | `generate_video.json` | Wan 2.1 video generation |
| 4 | `generate_3d` | `generate_3d.json` | 3D model generation |
| 5 | `image_to_3d` | `image_to_3d.json` | Image-to-3D conversion |
| 6 | `image_to_3d_simple` | `image_to_3d_simple.json` | Simplified image-to-3D |
| 7 | `image_to_3d_triposg` | `image_to_3d_triposg.json` | TripoSG-based image-to-3D |
| 8 | `upscale` | `upscale.json` | Workflow-based upscale |
| 9 | `image_variations` | `image_variations.json` | IPAdapter-based variations |
| 10 | `inpaint` | `inpaint.json` | Inpainting workflow |
| 11 | `img2img` | `img2img.json` | Image-to-image transform |
| 12 | `remove_background` | `remove_background.json` | Background removal |
| 13 | `generate_image_lora` | `generate_image_lora.json` | Image gen with LoRA |
| 14 | `generate_image_controlnet` | `generate_image_controlnet.json` | ControlNet generation |
| 15 | `image_to_video` | `image_to_video.json` | Image-to-video conversion |
| 16 | `style_transfer_ipadapter` | `style_transfer_ipadapter.json` | Style transfer (IPAdapter) |
| 17 | `style_transfer_multi_reference` | `style_transfer_multi_reference.json` | Multi-ref style transfer |
| 18 | `style_transfer_weighted` | `style_transfer_weighted.json` | Weighted style transfer |
| 19 | `regenerate` | (uses stored workflow) | Re-run with overrides |

### Asset & Viewing Tools -- `tools/asset.py`, `tools/job.py`
| # | Tool | Description |
|---|------|-------------|
| 20 | `view_image` | Inline thumbnail preview |
| 21 | `get_queue_status` | ComfyUI queue status |
| 22 | `get_job` | Job polling by prompt_id |
| 23 | `list_assets` | Browse generated assets |
| 24 | `get_asset_metadata` | Full provenance data |
| 25 | `cancel_job` | Cancel queued/running job |

### Configuration Tools -- `tools/configuration.py`
| # | Tool | Description |
|---|------|-------------|
| 26 | `health_check` | Server + ComfyUI health status |
| 27 | `list_models` | Available checkpoint models |
| 28 | `get_defaults` | Current effective defaults |
| 29 | `set_defaults` | Set runtime/persistent defaults |

### Workflow Tools -- `tools/workflow.py`
| # | Tool | Description |
|---|------|-------------|
| 30 | `list_workflows` | Workflow catalog |
| 31 | `run_workflow` | Run any workflow with overrides |

### Publish Tools -- `tools/publish.py`
| # | Tool | Description |
|---|------|-------------|
| 32 | `get_publish_info` | Publish config status |
| 33 | `set_comfyui_output_root` | Configure ComfyUI output path |
| 34 | `publish_asset` | Publish to web project directory |

### Upscale Tools -- `tools/upscale.py`
| # | Tool | Description |
|---|------|-------------|
| 35 | `upscale_image` | ESRGAN upscaling (programmatic) |
| 36 | `list_upscale_models` | Available upscale models |

### Variations Tools -- `tools/variations.py`
| # | Tool | Description |
|---|------|-------------|
| 37 | `generate_variations` | img2img variations with seed sweep |

### Webhook Tools -- `tools/webhook.py`
| # | Tool | Description |
|---|------|-------------|
| 38 | `set_webhook` | Register webhook |
| 39 | `remove_webhook` | Unregister webhook |
| 40 | `list_webhooks` | List registered webhooks |
| 41 | `get_webhook_log` | Delivery log |
| 42 | `update_webhook` | Update webhook config |

### External App Tools -- `tools/external.py`
| # | Tool | Description |
|---|------|-------------|
| 43 | `get_external_app_status` | Blender/Unreal availability |
| 44 | `export_to_blender` | Launch Blender with asset |
| 45 | `export_to_unreal` | Import asset into UE project |
| 46 | `convert_3d_format` | Convert glb/gltf/fbx/obj |
| 47 | `auto_rig_model` | Blender Rigify auto-rigging |
| 48 | `list_rig_types` | Available rig types |
| 49 | `animate_model` | Procedural animation |
| 50 | `list_animation_types` | Available animation types |
| 51 | `import_mocap` | BVH/FBX mocap import |
| 52 | `smart_rig_model` | Multi-backend rigging (UniRig/Tripo/Rigify) |
| 53 | `get_rigging_backends` | Backend availability status |
| 54 | `tripo_rig_and_animate` | Tripo3D cloud rig + animate |
| 55 | `list_tripo_animations` | Tripo3D animation presets |

### Style Preset Tools -- `tools/style_presets.py`
| # | Tool | Description |
|---|------|-------------|
| 56 | `list_style_presets` | Available style presets |
| 57 | `get_style_preset` | Preset details |
| 58 | `apply_style_preset` | Apply style to prompt |
| 59 | `create_custom_style_preset` | Create custom preset |
| 60 | `delete_custom_style_preset` | Delete custom preset |

### Batch Tools -- `tools/batch.py`
| # | Tool | Description |
|---|------|-------------|
| 61 | `batch_generate` | Multi-variation generation |
| 62 | `batch_generate_with_styles` | Same prompt x multiple styles |
| 63 | `batch_generate_seeds` | Same params x multiple seeds |

### Export Tools -- `tools/export.py`
| # | Tool | Description |
|---|------|-------------|
| 64 | `list_export_presets` | Social media presets |
| 65 | `get_export_preset` | Preset details |
| 66 | `export_image` | Crop/resize for platform |
| 67 | `batch_export_image` | Export to multiple platforms |
| 68 | `set_watermark` | Set watermark image |
| 69 | `create_export_preset` | Custom export preset |
| 70 | `delete_export_preset` | Delete custom preset |

### Prompt Library Tools -- `tools/prompt_library_tools.py`
| # | Tool | Description |
|---|------|-------------|
| 71 | `save_prompt` | Save prompt to library |
| 72 | `list_prompts` | List saved prompts |
| 73 | `get_prompt` | Get prompt details |
| 74 | `use_prompt` | Use prompt + track usage |
| 75 | `favorite_prompt` | Favorite/unfavorite |
| 76 | `update_prompt` | Update saved prompt |
| 77 | `delete_prompt` | Delete saved prompt |
| 78 | `get_prompt_categories` | List categories |
| 79 | `get_prompt_tags` | List tags |
| 80 | `save_template` | Save prompt template |
| 81 | `list_templates` | List templates |
| 82 | `get_template` | Get template details |
| 83 | `fill_template` | Fill template variables |
| 84 | `delete_template` | Delete template |
| 85 | `get_prompt_history` | Prompt usage history |
| 86 | `save_from_history` | Save from history |
| 87 | `clear_prompt_history` | Clear history |
| 88 | `get_prompt_library_stats` | Library statistics |

---

## 2. Workflow Files (20 workflows)

| File | Has PARAM_* | Auto-Tool |
|------|-------------|-----------|
| `generate_image.json` | Yes | `generate_image` |
| `generate_song.json` | Yes | `generate_song` |
| `generate_video.json` | Yes | `generate_video` |
| `generate_3d.json` | Yes | `generate_3d` |
| `image_to_3d.json` | Yes | `image_to_3d` |
| `image_to_3d_simple.json` | Yes | `image_to_3d_simple` |
| `image_to_3d_triposg.json` | Yes | `image_to_3d_triposg` |
| `upscale.json` | Yes | `upscale` |
| `image_variations.json` | Yes | `image_variations` |
| `inpaint.json` | Yes | `inpaint` |
| `img2img.json` | Yes | `img2img` |
| `remove_background.json` | Yes (+meta) | `remove_background` |
| `generate_image_lora.json` | Yes | `generate_image_lora` |
| `generate_image_controlnet.json` | Yes | `generate_image_controlnet` |
| `image_to_video.json` | Yes | `image_to_video` |
| `style_transfer_ipadapter.json` | Yes | `style_transfer_ipadapter` |
| `style_transfer_multi_reference.json` | Yes | `style_transfer_multi_reference` |
| `style_transfer_weighted.json` | Yes | `style_transfer_weighted` |
| `basic_api_test.json` | Possibly | `basic_api_test` |

---

## 3. Architecture Strengths

1. **Auto-discovery workflow system** -- Drop a JSON with `PARAM_*` placeholders into `workflows/` and a tool is auto-registered. This is the primary integration point for new capabilities.
2. **Stable identity + provenance** -- Robust asset tracking with full history snapshots enables reliable regenerate/iterate cycles.
3. **Thin adapter pattern** -- ComfyUI is the source of truth; server just proxies. Low maintenance.
4. **Multi-source defaults** -- Clean precedence chain for configuration.
5. **Publish system** -- Safe, validated asset publishing to web projects with atomic operations.
6. **Webhook system** -- Event-driven integration for external pipelines.
7. **Comprehensive 3D pipeline** -- Generation through rigging through animation through export.

---

## 4. Agent SDK Extraction Status

**Location:** `D:\Projects\comfyui-agent-sdk`
**Version:** 0.1.0 (early extraction, incomplete)

**Extracted modules:**
- `client/comfyui_client.py` -- ComfyUI client (with WebSocket monitor)
- `client/errors.py` -- Error types
- `assets/models.py`, `assets/registry.py`, `assets/processor.py` -- Asset system
- `defaults/manager.py` -- Defaults management
- `config.py` -- Configuration
- `credentials.py` -- Credential management

**Not yet extracted:**
- WorkflowManager (core workflow discovery/rendering)
- PublishManager / PublishConfig
- WebhookManager
- StylePresetsManager
- ExportPresetsManager
- PromptLibrary
- ExternalAppManager (Blender/Unreal)
- All tool registration modules

**Assessment:** The SDK is in early stages. Core client/asset/defaults modules have been extracted but the majority of business logic remains in the MCP server. The SDK has additional features not in the MCP server (HuggingFace hub integration, keyring credentials, WebSocket monitor, Ollama recommender).

---

## 5. Integration Plan for New Workflows

### 5.1 How to Add New Workflows (For All Team Members)

The simplest path for any team member adding new capabilities:

1. **Create a ComfyUI workflow JSON** with `PARAM_*` placeholders
2. **Place it in `workflows/`** directory
3. **Optionally add a `.meta.json`** file for constraints, defaults, and description
4. **Restart the server** -- tool auto-registers

**Placeholder format:**
```
PARAM_PROMPT        -> str (required)
PARAM_INT_STEPS     -> int (optional)
PARAM_FLOAT_CFG     -> float (optional)
PARAM_BOOL_HIRES    -> bool (optional)
```

**Binding:** The placeholder value must be `"PARAM_<TYPE>_<NAME>"` placed in the exact `[node_id, input_name]` position.

### 5.2 New Workflows Likely Needed

Based on the team's research domains:

#### From Image Research (Task #1)
- **`generate_image_sdxl.json`** -- SDXL-specific workflow (dual CLIP encoders, refiner)
- **`generate_image_sd3.json`** -- SD3/SD3.5 workflow (triple-CLIP)
- **`face_swap.json`** -- Face swap using ReActor/InsightFace
- **`face_restore.json`** -- GFPGAN/CodeFormer face restoration
- **`depth_map.json`** -- Depth estimation (MiDaS/Marigold)
- **`semantic_segmentation.json`** -- Segmentation map generation

#### From Video Research (Task #2)
- **`generate_video_wan2.json`** -- Updated Wan 2.1/2.2 workflow
- **`generate_video_hunyuan.json`** -- HunyuanVideo workflow
- **`video_upscale.json`** -- Video upscaling
- **`video_interpolation.json`** -- Frame interpolation (RIFE/FILM)
- **`video_to_video.json`** -- Video style transfer

#### From 3D Research (Task #3)
- **`generate_3d_sv3d.json`** -- Stability AI SV3D multi-view
- **`generate_3d_instantmesh.json`** -- InstantMesh workflow
- **`texture_generation.json`** -- Texture map generation for 3D models

#### From Speech/Audio Research (Task #5)
- **`generate_tts.json`** -- Text-to-speech (if a ComfyUI TTS node exists)
- **`generate_sfx.json`** -- Sound effects generation
- **`audio_separate.json`** -- Audio source separation

#### From Animation Research (Task #4)
- No new workflow JSON needed -- animation is handled by Blender integration tools

### 5.3 New MCP Tools Needed (Beyond Auto-Registration)

Some capabilities require programmatic tools beyond simple workflow wrapping:

#### Image Pipeline Tools (`tools/image_pipeline.py` -- new file)
| Tool | Purpose |
|------|---------|
| `face_swap` | Composite face from one image onto another (multi-step: detect, align, swap, blend) |
| `tile_upscale` | Tiled upscale for images larger than VRAM allows (split, upscale, stitch) |
| `compare_images` | Side-by-side comparison of two assets (useful for iteration) |

#### Video Pipeline Tools (`tools/video_pipeline.py` -- new file)
| Tool | Purpose |
|------|---------|
| `extract_frames` | Extract frames from video asset for processing |
| `create_video_from_frames` | Assemble processed frames back into video |
| `get_video_info` | Video metadata (duration, fps, codec, resolution) |

#### Model Management Tools (`tools/model_management.py` -- new file)
| Tool | Purpose |
|------|---------|
| `list_loras` | List available LoRA models |
| `list_controlnet_models` | List ControlNet models |
| `list_vae_models` | List VAE models |
| `get_node_info` | Get ComfyUI node class info |
| `list_installed_nodes` | List custom node packs |

#### Pipeline Composition Tools (`tools/pipeline.py` -- new file)
| Tool | Purpose |
|------|---------|
| `run_pipeline` | Execute a multi-step pipeline (e.g., generate -> upscale -> publish) |
| `get_pipeline_templates` | List pre-defined pipeline templates |

### 5.4 Infrastructure Improvements Needed

#### Async Job Support Enhancement
The current polling model (`get_job`) works but is inefficient for long-running tasks (video, 3D). Consider:
- **WebSocket progress events** -- Stream node-level progress to MCP clients
- **Long-poll endpoint** -- Block until completion instead of polling every 1s
- **Generation timeout configurability per-workflow** -- Video/3D can take 5-10 minutes vs 30s for images

#### Multi-Asset Output Support
Currently `_extract_first_asset_info()` returns only the first asset. Some workflows produce multiple outputs:
- Multi-view 3D generates N images
- Batch processes within a single workflow
- Video workflows that also save a thumbnail

**Recommendation:** Add `register_multiple_assets()` to `AssetRegistry` and update `register_and_build_response()` to support arrays.

#### Asset Type Expansion
The `view_image` tool only supports images. Needed:
- **`view_video`** -- Inline video preview (first frame as thumbnail + metadata)
- **`play_audio`** -- Audio preview (waveform visualization or just metadata)
- **`view_3d`** -- 3D model preview (render thumbnail via Blender headless)

#### Workflow Metadata Enhancement
The `.meta.json` system should be expanded:
- **`timeout_seconds`** -- Per-workflow timeout override
- **`output_type`** -- Expected output type (image, video, audio, 3d)
- **`multi_output`** -- Whether workflow produces multiple outputs
- **`required_nodes`** -- List of custom nodes required
- **`required_models`** -- List of models required (for validation)

---

## 6. Manager Module Status

| Manager | File | Status | Notes |
|---------|------|--------|-------|
| WorkflowManager | `managers/workflow_manager.py` | Mature | Auto-discovery works well |
| DefaultsManager | `managers/defaults_manager.py` | Mature | Multi-source precedence |
| AssetRegistry | `managers/asset_registry.py` | Mature | Stable identity, TTL |
| PublishManager | `managers/publish_manager.py` | Mature | Path-safe, atomic |
| WebhookManager | `managers/webhook_manager.py` | Mature | HMAC, retries, logging |
| StylePresetsManager | `managers/style_presets_manager.py` | Mature | Built-in + custom |
| ExportPresetsManager | `managers/export_presets_manager.py` | Mature | Social media sizing |
| PromptLibrary | `managers/prompt_library.py` | Mature | Templates, history |
| ExternalAppManager | `managers/external_app_manager.py` | Mature | Blender/Unreal/Mocap |
| TripoClient | `managers/tripo_client.py` | Mature | Cloud rigging API |
| UniRigClient | `managers/unirig_client.py` | Mature | AI rigging backend |

**No new manager modules are needed** for the planned integrations. The existing architecture handles new capabilities well through:
- Workflow auto-discovery (WorkflowManager)
- Existing asset pipeline (AssetRegistry + helpers)
- Existing publish pipeline (PublishManager)

---

## 7. Priority Integration Roadmap

### Phase 1: Low-Hanging Fruit (workflow-only additions)
1. Add model management tools (`list_loras`, `list_controlnet_models`, `list_vae_models`)
2. Add new image workflows from team research (SDXL, face restore, depth map)
3. Add per-workflow timeout in `.meta.json` and WorkflowManager

### Phase 2: Video/Audio Enhancement
4. Add video workflows (Wan 2.2, HunyuanVideo, frame interpolation)
5. Add `view_video` / `get_video_info` tools
6. Add audio workflows (TTS, SFX if ComfyUI nodes exist)

### Phase 3: Pipeline & Multi-Asset
7. Add multi-asset output support in AssetRegistry
8. Add `run_pipeline` for multi-step orchestration
9. WebSocket progress streaming

### Phase 4: SDK Extraction
10. Extract remaining managers to `comfyui-agent-sdk`
11. Move workflow discovery to SDK
12. Publish SDK v0.2.0

---

## 8. Key Integration Rules

For any team member contributing new workflows or tools:

1. **Naming convention:** `verb_noun` (e.g., `generate_image`, `upscale_image`, `export_to_blender`)
2. **Workflow file naming:** Matches tool name (e.g., `generate_image.json` -> `generate_image` tool)
3. **Parameter types:** Use `PARAM_INT_`, `PARAM_FLOAT_`, `PARAM_BOOL_` prefixes for typed params
4. **Required params:** Only `PARAM_PROMPT`, `PARAM_TAGS`, `PARAM_LYRICS` should be required
5. **Defaults:** Add to `.meta.json` or `DefaultsManager` hardcoded defaults
6. **Testing:** Add test in `tests/` directory
7. **Error handling:** Return `{"error": "message"}` dict, never raise exceptions from tools
8. **Asset registration:** Always use `register_and_build_response()` helper
9. **Webhook dispatch:** Add webhook events for new generation tools
10. **Documentation:** Update `docs/REFERENCE.md` with new tool signatures
