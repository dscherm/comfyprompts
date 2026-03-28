# ComfyUI Toolchain — Tool Reference

Complete reference for all MCP tools across the two servers in the toolchain, organized by category with parameters, descriptions, and pipeline integration notes.

## Server Architecture

```
Claude Code
├── comfyui-mcp   (83+ tools) — AI generation via ComfyUI
├── blender-mcp   (19 tools)  — Live Blender control via socket
└── output/shared/ — Cross-server asset handoff directory
```

---

## comfyui-mcp Tools

### 1. Configuration & Health

Tools for checking server status, listing models, and managing defaults.

| Tool | Parameters | Description |
|------|-----------|-------------|
| `health_check` | — | Check ComfyUI MCP Server health: connection status, VRAM, models, workflows |
| `list_models` | — | List all available checkpoint models in ComfyUI |
| `get_defaults` | — | Get current effective defaults for image/audio/video generation |
| `set_defaults` | `image`, `audio`, `video` (dicts), `persist` (bool) | Set runtime defaults for generation parameters |

**Use cases:**
- Start of any session: `health_check` to verify ComfyUI is reachable
- Before generation: `list_models` to pick the right checkpoint
- Batch workflows: `set_defaults` to avoid repeating common params

**Pipeline integration:** Every pipeline's Stage 1 (INTAKE) should call `health_check` to verify the server is up.

---

### 2. Workflow Management

Tools for discovering, validating, and running parametric ComfyUI workflows.

| Tool | Parameters | Description |
|------|-----------|-------------|
| `list_workflows` | — | List all available workflows with IDs, names, descriptions, and inputs |
| `run_workflow` | `workflow_id`, `overrides` (dict), `options` (dict), `return_inline_preview` | Run a workflow with parameter overrides |
| `validate_workflow` | `workflow_id` | Check if a workflow can run (required nodes, models, VRAM) |

**Use cases:**
- Discover what generation capabilities exist: `list_workflows`
- Run any ComfyUI workflow by ID with custom params: `run_workflow`
- Pre-flight check before queuing expensive jobs: `validate_workflow`

**Pipeline integration:** art-to-rig-ralph Stage 4 (MESH-GEN), scene-ralph Stage 2 (ASSET-GEN), and all generation pipelines use `run_workflow` as the core generation primitive.

---

### 3. Dynamic Workflow Tools

Auto-registered tools from parametric workflow JSON files in `workflows/mcp/`. Each workflow with `PARAM_*` placeholders becomes its own MCP tool (e.g., `generate_image`, `generate_video`, `generate_song`, `generate_3d`). Parameters are extracted from the workflow's `.meta.json` sidecar.

| Tool | Typical Parameters | Description |
|------|-------------------|-------------|
| `generate_image` | `prompt`, `negative_prompt`, `width`, `height`, `seed`, `steps`, `cfg`, `checkpoint` | Generate an image using the default image workflow |
| `generate_video` | `prompt`, `negative_prompt`, `width`, `height`, `seed`, `steps` | Generate a video clip |
| `generate_song` | `tags`, `lyrics`, `seed`, `steps` | Generate a music track |
| `generate_3d` | `prompt`, `image` (optional), `seed` | Generate a 3D model (GLB) from text or image |
| *(others vary by installed workflows)* | | |

**Use cases:**
- Quick image generation without knowing workflow IDs
- Each tool is typed and documented per its meta.json

**Pipeline integration:** These are the primary generation tools used by art-to-rig-ralph (Stage 2: CONCEPT-ART, Stage 4: MESH-GEN), character-ralph, video-ralph, audio-ralph, tileset-ralph, and scene-ralph (Stage 2: ASSET-GEN).

---

### 4. Job & Queue Management

Tools for tracking generation progress and managing the ComfyUI queue.

| Tool | Parameters | Description |
|------|-----------|-------------|
| `get_queue_status` | — | Get queue status: running jobs, queued jobs, estimated wait |
| `get_job` | `prompt_id` | Check if a specific job completed, get its outputs |
| `cancel_job` | `prompt_id` | Cancel a queued or running job |
| `list_assets` | `limit`, `workflow_id`, `session_id` | List recently generated assets |
| `get_asset_metadata` | `asset_id` | Get full metadata and provenance for an asset |

**Use cases:**
- After queueing a generation: poll `get_job` until complete
- Check if ComfyUI is busy before starting: `get_queue_status`
- Browse what was generated: `list_assets`

**Pipeline integration:** All pipelines use `get_job` to wait for generation completion. validate-ralph uses `list_assets` to scan outputs.

---

### 5. Asset Viewing

Tools for inspecting generated assets inline in chat.

| Tool | Parameters | Description |
|------|-----------|-------------|
| `view_image` | `asset_id`, `mode` ("thumb"/"full"), `max_dim`, `max_b64_chars` | View a generated image inline in chat |
| `view_video` | `asset_id` | Get a video asset's URL and metadata |
| `get_video_info` | `asset_id` | Get detailed video metadata (duration, codec, dimensions) |
| `resolve_asset` | `asset_id` | Resolve asset to ComfyUI input filename for multi-stage pipelines |
| `get_asset_local_path` | `asset_id` | Get local filesystem path for external tools |

**Use cases:**
- Closed-loop iteration: generate -> `view_image` -> adjust prompt -> regenerate
- Multi-stage pipelines: `resolve_asset` to chain workflows (e.g., image -> img2img)
- External tool handoff: `get_asset_local_path` for Blender/ffmpeg

**Pipeline integration:** art-to-rig-ralph uses `resolve_asset` to chain concept art -> background removal -> mesh generation. scene-ralph uses `view_image` for quality checks between stages.

---

### 6. Image Variations & Upscaling

Tools for modifying existing images.

| Tool | Parameters | Description |
|------|-----------|-------------|
| `generate_variations` | `asset_id`, `num_variations`, `variation_strength`, `seed`, `prompt`, `negative_prompt`, `model` | Generate img2img variations of an existing image |
| `upscale_image` | `asset_id`, `scale_factor` (2 or 4), `upscale_model` | AI upscale using ESRGAN models |

**Use cases:**
- Explore variations: generate one image, then `generate_variations` with different strengths
- Upscale for print/web: `upscale_image` with 4x for high-res output
- Style transfer: provide a new prompt with high `variation_strength`

**Pipeline integration:** upscale-ralph uses `upscale_image` as its core tool. inpaint-ralph uses `generate_variations` for iterative refinement. scene-ralph Stage 6 (REFINE) uses both for final polish.

---

### 7. Style Presets

Tools for managing and applying artistic styles to prompts.

| Tool | Parameters | Description |
|------|-----------|-------------|
| `list_style_presets` | — | List all available style presets |
| `get_style_preset` | `preset_id` | Get full details of a preset |
| `apply_style_preset` | `preset_id`, `prompt`, `override_settings` | Apply a style to your prompt (returns enhanced prompt + settings) |
| `create_custom_style_preset` | `preset_id`, `name`, `description`, `prompt_prefix/suffix`, `negative_prompt`, `recommended_cfg/steps`, `suggested_lora` | Create a reusable custom style |
| `delete_custom_style_preset` | `preset_id` | Delete a custom preset |

**Use cases:**
- Consistent art direction: apply the same style across a batch
- Compare styles: `batch_generate_with_styles` uses these internally

**Pipeline integration:** art-to-rig-ralph Stage 2 (CONCEPT-ART) uses style presets to match the art direction from Stage 1 intake. style-transfer-ralph is built entirely around these tools.

---

### 8. Batch Generation

Tools for generating multiple outputs efficiently.

| Tool | Parameters | Description |
|------|-----------|-------------|
| `batch_generate` | `workflow_id`, `base_params`, `variations` (list of override dicts), `common_seed` | Run a workflow N times with different params |
| `batch_generate_with_styles` | `prompt`, `style_preset_ids` (list), `base_params`, `common_seed` | Generate same prompt with multiple style presets |
| `batch_generate_seeds` | `workflow_id`, `params`, `count`, `start_seed` | Generate N variations with different random seeds |

**Use cases:**
- Prompt exploration: try 8 different prompts in one call
- Seed hunting: `batch_generate_seeds` with count=8 to find the best variation
- Style comparison: same subject across 5 art styles

**Pipeline integration:** art-to-rig-ralph Stage 2 uses batch generation for multiple character views. tileset-ralph generates multiple tiles in parallel. character-ralph generates concept variations.

---

### 9. Prompt Library

Tools for saving, organizing, and reusing prompts.

| Tool | Parameters | Description |
|------|-----------|-------------|
| `save_prompt` | `prompt`, `name`, `tags`, `negative_prompt`, `description`, `category` | Save a prompt for reuse |
| `list_prompts` | `category`, `tags`, `search`, `favorites_only`, `limit` | Browse saved prompts with filters |
| `get_prompt` | `prompt_id` | Get full prompt details |
| `use_prompt` | `prompt_id` | Get prompt for generation + track usage |
| `favorite_prompt` | `prompt_id`, `favorite` | Mark/unmark as favorite |
| `update_prompt` | `prompt_id`, + any field to update | Update a saved prompt |
| `delete_prompt` | `prompt_id` | Delete a prompt |
| `get_prompt_categories` | — | List all categories |
| `get_prompt_tags` | — | List all tags with counts |
| `save_template` | `template_id`, `name`, `template` (with `{variables}`), `variables`, `example_values`, `category` | Save a prompt template |
| `list_templates` | `category`, `search` | Browse templates |
| `get_template` | `template_id` | Get template with variable definitions |
| `fill_template` | `template_id`, `values` (dict) | Fill template variables, get ready-to-use prompt |
| `delete_template` | `template_id` | Delete a template |
| `get_prompt_history` | `limit`, `search`, `workflow_id` | Browse recent prompt history |
| `save_from_history` | `history_index`, `name`, `tags` | Save a used prompt to library |
| `clear_prompt_history` | — | Clear all history |
| `get_prompt_library_stats` | — | Library statistics |

**Use cases:**
- Build a prompt library: save successful prompts with tags for easy retrieval
- Consistent characters: create templates like `"{character_name}, {pose}, fantasy illustration"` and fill per-character
- Track what works: `get_prompt_history` to review recent generations

**Pipeline integration:** character-ralph uses templates for consistent character generation across views. art-to-rig-ralph saves successful prompts for batch reuse.

---

### 10. Model Management

Tools for inspecting ComfyUI's installed models.

| Tool | Parameters | Description |
|------|-----------|-------------|
| `list_loras` | — | List all LoRA models |
| `list_controlnet_models` | — | List all ControlNet models |
| `list_vae_models` | — | List all VAE models |
| `list_upscale_models` | — | List all upscale models |
| `list_samplers` | — | List all sampler algorithms |
| `list_schedulers` | — | List all noise schedulers |
| `refresh_model_cache` | — | Refresh model cache after installing new models |

**Use cases:**
- Before generation: check which LoRAs or ControlNets are available
- After installing a new model: `refresh_model_cache`

**Pipeline integration:** All pipelines' intake stages check model availability. validate-ralph cross-references workflow requirements against installed models.

---

### 11. External App Integration (Blender, Unreal)

Tools for exporting assets to 3D applications and rigging/animating models.

| Tool | Parameters | Description |
|------|-----------|-------------|
| `get_external_app_status` | — | Check Blender, Unreal, and blender-mcp availability |
| `publish_for_blender` | `asset_id`, `filename`, `shared_dir` | Copy asset to shared dir for blender-mcp handoff |
| `export_to_blender` | `asset_id`, `action` | Launch Blender with asset loaded (headless) |
| `export_to_unreal` | `asset_id`, `project_path`, `package_path` | Import asset into Unreal Engine project |
| `convert_3d_format` | `asset_id`, `target_format`, `output_dir` | Convert between GLB/FBX/OBJ using Blender |
| `auto_rig_model` | `asset_id`, `rig_type`, `auto_weights`, `generate_ik`, `save_blend_file`, `output_dir` | Auto-rig with Rigify/biped/quadruped/simple skeleton |
| `list_rig_types` | — | List rig types with descriptions and use cases |
| `animate_model` | `blend_file_path`, `animation_type`, `duration`, `fps`, `loop`, `intensity`, `output_format`, `output_dir`, `render_video` | Generate procedural animation (walk, run, idle, wave, jump, nod, look_around) |
| `list_animation_types` | — | List animation types with recommended durations |
| `import_mocap` | `blend_file_path`, `mocap_file_path`, `scale`, `start_frame`, `use_fps_scale`, `output_format`, `output_dir` | Import BVH/FBX mocap to rigged model |
| `smart_rig_model` | `asset_id`, `backend` (auto/unirig/tripo/rigify), `rig_type`, `save_output`, `output_dir` | Auto-rig with best available backend |
| `get_rigging_backends` | — | Check UniRig, Tripo3D, Rigify availability |
| `tripo_rig_and_animate` | `asset_id`, `animation` (e.g. "preset:walk"), `output_dir` | One-step cloud rig + animate via Tripo3D |
| `list_tripo_animations` | — | List Tripo3D animation presets |

**Use cases:**
- Full 3D pipeline: `generate_3d` -> `smart_rig_model` -> `animate_model` -> `export_to_unreal`
- Cross-server workflow: `publish_for_blender` -> blender-mcp `execute_blender_code`
- Format conversion: GLB -> FBX for Unreal via `convert_3d_format`

**Pipeline integration:**
- **art-to-rig-ralph** Stage 6 (RIG): `smart_rig_model` or `auto_rig_model` for headless path; `publish_for_blender` for blender-mcp path
- **animate-ralph** Stages 2-4: `animate_model` for headless; blender-mcp snippets for interactive
- **asset-forge-ralph** Stages 4-5: `smart_rig_model` + `animate_model`
- **scene-ralph** Stage 2: `publish_for_blender` to hand off generated assets to Blender
- **fusion-ralph** Stage 5: `convert_3d_format` + `export_to_blender` for mesh splitting

---

### 12. Export & Social Media

Tools for formatting images for different platforms.

| Tool | Parameters | Description |
|------|-----------|-------------|
| `list_export_presets` | `platform` (optional filter) | List presets for Instagram, TikTok, YouTube, Twitter, etc. |
| `get_export_preset` | `preset_id` | Get preset dimensions and details |
| `export_image` | `asset_id`, `preset_id`, `crop_mode`, `quality`, `add_watermark`, `watermark_position`, `watermark_opacity` | Export image to platform-specific format |
| `batch_export_image` | `asset_id`, `preset_ids` (list), `crop_mode`, `add_watermark` | Export to multiple platforms at once |
| `set_watermark` | `watermark_path` | Set watermark PNG for future exports |
| `create_export_preset` | `preset_id`, `name`, `width`, `height`, `platform`, `description`, `max_file_size_mb`, `quality` | Create custom export preset |
| `delete_export_preset` | `preset_id` | Delete custom preset |

**Use cases:**
- Social media pipeline: generate -> `batch_export_image` for Instagram + Twitter + TikTok in one call
- Branded exports: `set_watermark` once, then every `export_image` with `add_watermark=True`

**Pipeline integration:** character-ralph Stage 7 (EXPORT) uses these for delivering character art in multiple platform sizes.

---

### 13. Publishing

Tools for deploying assets to web projects.

| Tool | Parameters | Description |
|------|-----------|-------------|
| `get_publish_info` | — | Get publish config and status |
| `set_comfyui_output_root` | `path` | Set ComfyUI output directory (persists across restarts) |
| `publish_asset` | `asset_id`, `target_filename`, `manifest_key`, `web_optimize`, `max_bytes`, `overwrite` | Publish asset to web project directory |

**Use cases:**
- Web deployment: generate -> `publish_asset` with `web_optimize=True` to deploy to a website
- Asset management: use `manifest_key` to track published assets in a manifest JSON

**Pipeline integration:** Any pipeline's final stage can use `publish_asset` to deploy deliverables.

---

### 14. Webhooks

Tools for event-driven integrations.

| Tool | Parameters | Description |
|------|-----------|-------------|
| `set_webhook` | `url`, `events` (list), `secret` | Register webhook for generation_completed, asset_published, job_failed, etc. |
| `remove_webhook` | `webhook_id` | Remove webhook |
| `list_webhooks` | — | List all registered webhooks |
| `get_webhook_log` | `webhook_id`, `event`, `limit` | View delivery log for debugging |
| `update_webhook` | `webhook_id`, `active`, `events` | Enable/disable or change subscribed events |

**Use cases:**
- Slack notifications: webhook on `generation_completed` to post to a channel
- CI/CD: trigger downstream builds when assets are published
- Monitoring: webhook on `job_failed` for alerting

**Pipeline integration:** hot-reload-ralph can use webhooks to trigger rebuilds. validate-ralph can fire webhooks on validation failures.

---

### 15. Tileset Generation

| Tool | Parameters | Description |
|------|-----------|-------------|
| `generate_game_tileset` | `prompt`, `prompt_b`, `negative_prompt`, `mode` (simple/transition), `output_format` (godot_minimal/atlas), `tile_size`, `lora_name`, `lora_strength`, `seed`, + sampler/scheduler/model params | Generate coherent game tilesets with terrain transitions |

**Use cases:**
- 2D game development: generate grass/dirt/water tilesets with seamless transitions
- Godot/Unity integration: output directly as atlas or minimal tileset

**Pipeline integration:** tileset-ralph is built around this tool, running it iteratively with different terrain types and transition pairs.

---

## blender-mcp Tools

These tools require Blender running with the BlenderMCP addon active on port 9876.

### 1. Scene Inspection

| Tool | Parameters | Description |
|------|-----------|-------------|
| `get_scene_info` | — | Get full Blender scene info (objects, materials, lights, camera) |
| `get_object_info` | `object_name` | Get detailed info about a specific object |
| `get_viewport_screenshot` | `max_size` (default 800) | Capture viewport as an image — enables visual feedback loops |

**Use cases:**
- After importing: `get_scene_info` to see what's in the scene
- Visual validation: `get_viewport_screenshot` to verify rigging, poses, scene layout
- Debug: `get_object_info` to check mesh stats, material assignments

**Pipeline integration:** art-to-rig-ralph Stage 6 (RIG) and animate-ralph Stages 2-4 use `get_viewport_screenshot` for visual validation — the key advantage over headless Blender.

---

### 2. Code Execution

| Tool | Parameters | Description |
|------|-----------|-------------|
| `execute_blender_code` | `code` (Python string) | Execute arbitrary Python (`bpy`) in the live Blender session |

**This is the most powerful tool in the toolchain.** It can do anything Blender can do — import, model, rig, animate, render, export. Use the snippets in `packages/mcp-server/scripts/blender_snippets/` as templates.

**Available snippets:**
| Snippet | Purpose |
|---------|---------|
| `import_glb.py` | Import GLB/GLTF into scene |
| `rig_humanoid.py` | Rig mesh with humanoid skeleton (Rigify or fallback) |
| `rig_quadruped.py` | Rig mesh with quadruped skeleton |
| `animate_walk.py` | Generate walk cycle on rigged armature |
| `animate_idle.py` | Generate idle/breathing animation |
| `scene_setup.py` | Set up 3-point lighting + camera |
| `export_glb.py` | Export scene to GLB |

**Pipeline integration:** scene-ralph Stages 3-5 (SCENE-BUILD, MATERIALS, RENDER) are built entirely on `execute_blender_code`. art-to-rig-ralph and animate-ralph use it as their preferred Path A when blender-mcp is available.

---

### 3. Poly Haven Assets

Free HDRIs, textures, and 3D models from polyhaven.com.

| Tool | Parameters | Description |
|------|-----------|-------------|
| `get_polyhaven_status` | — | Check if Poly Haven is enabled in Blender |
| `get_polyhaven_categories` | `asset_type` (hdris/textures/models/all) | List categories with counts |
| `search_polyhaven_assets` | `asset_type`, `categories` | Search for assets, sorted by popularity |
| `download_polyhaven_asset` | `asset_id`, `asset_type`, `resolution` (1k/2k/4k), `file_format` | Download and import asset into Blender |
| `set_texture` | `object_name`, `texture_id` | Apply downloaded texture to an object |

**Use cases:**
- Realistic lighting: download an HDRI for environment lighting
- PBR materials: download wood/metal/fabric textures for objects
- Quick props: download a 3D model from Poly Haven's library

**Pipeline integration:** scene-ralph Stage 4 (MATERIALS) uses Poly Haven for HDRI environments and PBR textures. fusion-ralph Stage 5 uses materials for presentation renders.

---

### 4. Sketchfab Models

Search and download 3D models from Sketchfab's library.

| Tool | Parameters | Description |
|------|-----------|-------------|
| `get_sketchfab_status` | — | Check if Sketchfab is enabled |
| `search_sketchfab_models` | `query`, `categories`, `count`, `downloadable` | Search models by keyword |
| `download_sketchfab_model` | `uid` | Download and import model into Blender |

**Use cases:**
- Scene dressing: search for props, furniture, vehicles
- Reference models: download a model as a starting point

**Pipeline integration:** scene-ralph Stage 3 can use Sketchfab models for scene props when AI generation isn't needed.

---

### 5. 3D Generation (Hyper3D Rodin)

Generate 3D models from text or images using Rodin's cloud API.

| Tool | Parameters | Description |
|------|-----------|-------------|
| `get_hyper3d_status` | — | Check if Hyper3D is enabled |
| `generate_hyper3d_model_via_text` | `text_prompt`, `bbox_condition` | Generate 3D from text description |
| `generate_hyper3d_model_via_images` | `input_image_paths` or `input_image_urls`, `bbox_condition` | Generate 3D from reference images |
| `poll_rodin_job_status` | `subscription_key` or `request_id` | Check generation progress |
| `import_generated_asset` | `name`, `task_uuid` or `request_id` | Import completed model into Blender |

**Use cases:**
- Quick 3D from text: describe an object, get a textured mesh in Blender
- Image-to-3D: provide concept art, get a 3D model

**Pipeline integration:** Alternative to comfyui-mcp's `generate_3d` — generates directly into Blender without needing `publish_for_blender`.

---

### 6. 3D Generation (Hunyuan3D)

Generate 3D models using Tencent's Hunyuan3D (via blender-mcp's integration).

| Tool | Parameters | Description |
|------|-----------|-------------|
| `get_hunyuan3d_status` | — | Check if Hunyuan3D is enabled |
| `generate_hunyuan3d_model` | `text_prompt`, `input_image_url` | Generate 3D from text and/or image |
| `poll_hunyuan_job_status` | `job_id` | Check generation progress |
| `import_generated_asset_hunyuan` | `name`, `zip_file_url` | Import completed model into Blender |

**Use cases:**
- Similar to Hyper3D but using Hunyuan's model
- Supports both text-only and image-guided generation

**Pipeline integration:** Same role as Hyper3D — an alternative 3D generation path that outputs directly to Blender.

---

## Cross-Server Workflow Patterns

### Pattern A: ComfyUI Generates, Blender Consumes

```
comfyui-mcp: generate_3d(prompt="a wooden chair")
comfyui-mcp: publish_for_blender(asset_id=result.asset_id)
blender-mcp: execute_blender_code(import_glb snippet with published path)
blender-mcp: get_viewport_screenshot()  -- verify import
blender-mcp: execute_blender_code(rig, animate, or arrange)
blender-mcp: execute_blender_code(export_glb snippet)
```

**Used by:** art-to-rig-ralph, animate-ralph, asset-forge-ralph, scene-ralph

### Pattern B: Blender Sources, ComfyUI Enhances

```
blender-mcp: execute_blender_code(arrange scene, set camera)
blender-mcp: get_viewport_screenshot()  -- capture render
comfyui-mcp: generate_variations(image=screenshot, variation_strength=0.5)
comfyui-mcp: publish_for_blender(asset_id=enhanced_image)
blender-mcp: execute_blender_code(apply enhanced texture)
```

**Used by:** scene-ralph Stage 6 (REFINE), style-transfer-ralph

### Pattern C: Blender-Only (Direct 3D Generation)

```
blender-mcp: generate_hyper3d_model_via_text(prompt="a goblet")
blender-mcp: poll_rodin_job_status(subscription_key=...)
blender-mcp: import_generated_asset(name="goblet", task_uuid=...)
blender-mcp: get_viewport_screenshot()  -- verify
```

**Used by:** scene-ralph (for simple props), quick prototyping

---

## Pipeline-to-Tool Matrix

Which tools each pipeline primarily uses:

| Pipeline | Generation | 3D/Rigging | Animation | Export | Blender-MCP |
|----------|-----------|------------|-----------|--------|-------------|
| **art-to-rig-ralph** | `generate_image`, `run_workflow` | `smart_rig_model`, `publish_for_blender` | — | `convert_3d_format` | `execute_blender_code`, `get_viewport_screenshot` |
| **animate-ralph** | — | — | `animate_model`, snippets | `export_to_blender` | `execute_blender_code`, `get_viewport_screenshot` |
| **asset-forge-ralph** | `generate_image`, `generate_3d` | `smart_rig_model` | `animate_model` | `convert_3d_format` | Optional |
| **scene-ralph** | `generate_3d`, `generate_image` | — | — | — | `execute_blender_code`, `get_viewport_screenshot`, Poly Haven tools |
| **character-ralph** | `generate_image`, `batch_generate` | — | — | `export_image`, `batch_export_image` | Optional |
| **fusion-ralph** | `run_workflow` | — | — | `convert_3d_format` | `execute_blender_code` |
| **video-ralph** | `generate_image`, `run_workflow` | — | — | — | — |
| **audio-ralph** | `run_workflow` (audio workflows) | — | — | — | — |
| **tileset-ralph** | `generate_game_tileset` | — | — | — | — |
| **style-transfer-ralph** | `generate_variations`, `apply_style_preset` | — | — | `export_image` | — |
| **upscale-ralph** | `upscale_image` | — | — | `export_image` | — |
| **inpaint-ralph** | `generate_variations`, `run_workflow` | — | — | — | — |
| **validate-ralph** | `list_assets`, `health_check` | `get_rigging_backends` | — | — | — |
| **cleanup-ralph** | `list_assets` | — | — | — | — |
