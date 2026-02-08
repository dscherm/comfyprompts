# Workflow Architecture Report

Comprehensive pipeline mapping and architecture design for the ComfyUI ecosystem.

**Author:** Workflow Architect Agent
**Date:** 2026-02-06
**Scope:** comfyui-mcp-server, comfyui-prompter

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Current Workflow Inventory](#current-workflow-inventory)
3. [PARAM System Documentation](#param-system-documentation)
4. [Pipeline Capability Map](#pipeline-capability-map)
5. [Bottlenecks and Missing Connections](#bottlenecks-and-missing-connections)
6. [Cross-Domain Pipeline Designs](#cross-domain-pipeline-designs)
7. [Workflow Standards](#workflow-standards)
8. [Recommendations](#recommendations)

---

## Executive Summary

The ComfyUI ecosystem currently spans two projects:

- **comfyui-mcp-server**: 20 workflow JSON files (19 active + 1 API test), ~40 MCP tools, full asset lifecycle management, Blender/Unreal integration, batch processing, style presets, publish system
- **comfyui-prompter**: 25+ workflow entries in config.py (UI-format workflows on disk at `D:/workflows`), Ollama-based prompt recommender, Blender addon, model registry

The MCP server uses **API-format** workflows with `PARAM_*` placeholders for automatic tool registration. The prompter uses **UI-format** workflows with `widgets_values` arrays and requires explicit conversion to API format.

**Key finding:** The two systems are complementary but do not share a common workflow format or parameter system. The MCP server's PARAM system is more automation-friendly. The prompter has broader workflow coverage (especially video and 3D) but requires manual integration.

---

## Current Workflow Inventory

### MCP Server Workflows (`D:\Projects\comfyui-mcp-server\workflows\`)

| Workflow | Domain | Input | Output | PARAM Count | Key Params |
|----------|--------|-------|--------|-------------|------------|
| `generate_image` | Image | text | PNG | 8 | prompt, negative_prompt, width, height, seed, steps, cfg, denoise, sampler, scheduler |
| `generate_image_lora` | Image | text | PNG | 10 | + lora_name, lora_strength |
| `generate_image_controlnet` | Image | text + image | PNG | 10 | + control_image, controlnet_type, controlnet_strength |
| `img2img` | Image | text + image | PNG | 8 | prompt, image_path, denoise, etc. |
| `inpaint` | Image | text + image + mask | PNG | 8 | prompt, image_path, mask_path, etc. |
| `image_variations` | Image | image | PNG | 8 | image_path, prompt, denoise, etc. |
| `upscale` | Image | image | PNG | 2 | image_path, upscale_model |
| `remove_background` | Image | image | PNG | 1 | image_path |
| `style_transfer_ipadapter` | Image | text + style image | PNG | 8 | prompt, style_image, weight, etc. |
| `style_transfer_weighted` | Image | text + 2 style images | PNG | 12 | prompt, style_image_1/2, weight_1/2, overall_weight |
| `style_transfer_multi_reference` | Image | text + 2 style images | PNG | 9 | prompt, style_image_1/2, weight |
| `generate_video` | Video | text | MP4 | 10 | prompt, width, height, frames, fps, etc. |
| `image_to_video` | Video | text + image | MP4 | 10 | prompt, image_path, frames, fps, etc. |
| `generate_3d` | 3D | text | Mesh | 5 | prompt, negative_prompt, seed, steps, cfg, resolution |
| `image_to_3d` | 3D | image | Mesh | 1 | image_path, resolution |
| `image_to_3d_simple` | 3D | image | Mesh | 1 | image_path, resolution |
| `image_to_3d_triposg` | 3D | image | GLB | 1 | image_path, resolution |
| `generate_song` | Audio | tags + lyrics | MP3 | 5 | tags, lyrics, lyrics_strength, seed, steps, cfg, seconds |
| `basic_api_test` | Test | none | PNG | 0 | (hardcoded, no PARAM placeholders) |

### Prompter Workflow Database (`comfyui-prompter/config.py`)

| Workflow | Type | Checkpoint | Notes |
|----------|------|-----------|-------|
| `Default_Comfy_Workflow.json` | text_to_image | any | Basic generation |
| `NSFW Flux 1 Dev GGUF TXT2IMG with UltraRealistic Lora.json` | text_to_image | flux1-dev-Q6_K.gguf | High quality + LoRA |
| `EP19 SDXL INPAINT.json` | 2d_image | Juggernaut_X_RunDiffusion | Inpainting |
| `EP20 Flux Dev Q8 Sketch 2 Image.json` | 2d_image | flux1-dev-fp8 | Sketch to image |
| `EP20 Flux Dev Q8 Sketch 2 Image and Poses.json` | 2d_image | flux1-dev-fp8 | Sketch + pose control |
| `Image To Vector SVG.json` | conversion | none | Raster to SVG |
| `Flux Vector SVG Workflow Update.json` | conversion | flux1-dev-fp8 | Text to SVG |
| `triposg_image_to_3d.json` | 3d_generation | VAST-AI/TripoSG | Fast 3D |
| `triposg_simple.json` | 3d_generation | VAST-AI/TripoSG | Simple 3D |
| `TripoSG.json` | 3d_generation | VAST-AI/TripoSG | Full TripoSG |
| `hy3d_example_01 (1) - Copy.json` | 3d_generation | hunyuan3d-dit-v2-0 | High quality 3D + textures |
| `Tripo-单图生3D.json` | 3d_generation | VAST-AI/TripoSG | Single image to 3D |
| `Tripo-多视图生3D.json` | 3d_generation | VAST-AI/TripoSG | Multi-view to 3D |
| `text_to_video_wan.json` | video_generation | wan2.1_t2v_1.3B | Text to video |
| `Wan+2.1+Image+to+Video+14B+480p+Q4_K_S+GGUF.json` | video_generation | Wan2.1_14B_VACE | Image to video |
| `混元1.5+文生视频720P.json` | video_generation | hunyuan_video_720 | 720p text to video |
| `混元图生视频+HunyuanVideoImagesGuider.json` | video_generation | hunyuan_video_720 | Image to video (Hunyuan) |
| 3x Retrofuture Style workflows | 2d_image | flux1-dev-fp8 | Themed styles |

---

## PARAM System Documentation

### Overview

The PARAM system is the MCP server's mechanism for turning static ComfyUI workflow JSON into dynamic, parameterized MCP tools. When `WorkflowManager` scans the `workflows/` directory, it finds `PARAM_*` placeholder strings in node input values and exposes them as tool parameters.

### Placeholder Format

```
PARAM_<TYPE_HINT>_<PARAMETER_NAME>
```

| Prefix | Python Type | Example | Extracted Name |
|--------|------------|---------|----------------|
| `PARAM_` (no type) | `str` | `PARAM_PROMPT` | `prompt` |
| `PARAM_STR_` | `str` | `PARAM_STR_IMAGE_PATH` | `image_path` |
| `PARAM_INT_` | `int` | `PARAM_INT_STEPS` | `steps` |
| `PARAM_FLOAT_` | `float` | `PARAM_FLOAT_CFG` | `cfg` |
| `PARAM_BOOL_` | `bool` | `PARAM_BOOL_TILE` | `tile` |

### Binding System

Each PARAM placeholder records its **binding**: `[node_id, input_name]`. A single parameter can bind to multiple nodes (e.g., `PARAM_FLOAT_LORA_STRENGTH` binds to both `strength_model` and `strength_clip` in the LoRA loader).

```json
{
  "2": {
    "inputs": {
      "lora_name": "PARAM_STR_LORA_NAME",
      "strength_model": "PARAM_FLOAT_LORA_STRENGTH",
      "strength_clip": "PARAM_FLOAT_LORA_STRENGTH"
    },
    "class_type": "LoraLoader"
  }
}
```

### Required vs Optional

Parameters are classified as required or optional based on name:

**Always required:** `prompt`, `tags`, `lyrics`, `image_path`, `mask_path`, `control_image`, `style_image`, `lora_name`, `controlnet_type`, `upscale_model`

**Always optional:** `seed`, `width`, `height`, `steps`, `cfg`, `sampler_name`, `scheduler`, `denoise`, `negative_prompt`, `seconds`, `lyrics_strength`, `fps`, `frames`, `resolution`, `lora_strength`, `controlnet_strength`

### Default Value Resolution

When a parameter is not provided, the `DefaultsManager` resolves it through this precedence chain:

1. **Explicit value** (passed by caller)
2. **Runtime defaults** (set via `set_defaults` MCP tool)
3. **Config file** (`~/.config/comfy-mcp/config.json`)
4. **Environment variables**
5. **Hardcoded defaults** (in `DefaultsManager`)

Special case: `seed` generates a random value if not provided.

### Namespaces

Default values are scoped by namespace, determined from `workflow_id`:

| Namespace | Workflow IDs |
|-----------|-------------|
| `image` | `generate_image`, `generate_image_lora`, `generate_image_controlnet`, `img2img`, `inpaint`, etc. |
| `video` | `generate_video`, `image_to_video` |
| `3d` | `generate_3d`, `image_to_3d` |
| `audio` | `generate_song` |

### Metadata Sidecar Files (`.meta.json`)

Optional sidecar files provide additional metadata:

```json
{
  "name": "Remove Background",
  "description": "Removes background from images using AI.",
  "requirements": {
    "nodes": ["BRIA_RMBG_Zho"],
    "alternatives": [{"node": "BiRefNet", "install": "ComfyUI-BiRefNet"}]
  },
  "category": "editing",
  "tags": ["background", "removal", "transparency"],
  "override_mappings": {},
  "constraints": {}
}
```

### Inline Defaults (`_defaults`)

Style transfer workflows demonstrate inline defaults within node definitions:

```json
{
  "7": {
    "class_type": "IPAdapter",
    "inputs": {
      "weight": "PARAM_FLOAT_WEIGHT"
    },
    "_defaults": {
      "PARAM_FLOAT_WEIGHT": 0.8
    }
  }
}
```

Note: These `_defaults` are **not currently processed** by `WorkflowManager._extract_parameters()`. They exist as documentation hints but don't feed into the default resolution chain. This is a gap.

---

## Pipeline Capability Map

### What Can Currently Chain (MCP Server)

```
TEXT ──> generate_image ──> [PNG]
         │                    │
         │                    ├──> upscale ──> [PNG (4x)]
         │                    ├──> remove_background ──> [PNG (transparent)]
         │                    ├──> img2img ──> [PNG (variation)]
         │                    ├──> image_to_3d ──> [Mesh/GLB]
         │                    │                      │
         │                    │                      ├──> export_to_blender ──> [Blender opens]
         │                    │                      ├──> convert_3d_format ──> [FBX/OBJ/glTF]
         │                    │                      ├──> auto_rig_model ──> [.blend (rigged)]
         │                    │                      │                          │
         │                    │                      │                          ├──> animate_model ──> [GLB/FBX (animated)]
         │                    │                      │                          └──> import_mocap ──> [GLB/FBX (mocap)]
         │                    │                      ├──> smart_rig_model ──> [.blend (rigged)]
         │                    │                      ├──> tripo_rig_and_animate ──> [GLB (rigged+animated)]
         │                    │                      └──> export_to_unreal ──> [UE Project]
         │                    │
         │                    ├──> image_to_video ──> [MP4]
         │                    ├──> style_transfer_* ──> [PNG (styled)]
         │                    ├──> inpaint (+ mask) ──> [PNG (inpainted)]
         │                    └──> publish_asset ──> [web directory]
         │
         └──> generate_image_lora ──> [PNG (LoRA-styled)]
         └──> generate_image_controlnet ──> [PNG (ControlNet-guided)]

TEXT ──> generate_video ──> [MP4]
TEXT ──> generate_3d ──> [Mesh] (text-to-image-to-3D internally)
TEXT ──> generate_song ──> [MP3]

BATCH:
  batch_generate ──> [multiple assets]
  batch_generate_with_styles ──> [styled variations]
  batch_generate_seeds ──> [seed variations]
```

### What Can Currently Chain (Prompter)

```
TEXT ──> (Ollama recommender selects workflow) ──> ComfyUI API ──> [Output]
         │
         ├──> text_to_image workflows (multiple models)
         ├──> sketch_to_image (ControlNet)
         ├──> inpainting (SDXL)
         ├──> image_to_3d (TripoSG, Hunyuan3D)
         ├──> text_to_video (Wan 2.1, Hunyuan)
         ├──> image_to_video (Wan 2.1 VACE, Hunyuan)
         ├──> image_to_svg (vector conversion)
         └──> styled generation (Retrofuture presets)

Blender Addon:
  Blender ──> API Server ──> ComfyUI ──> Blender (texture/model import)
```

---

## Bottlenecks and Missing Connections

### Critical Gaps

1. **No pipeline orchestration layer.** Each MCP tool is independent. Multi-step pipelines (e.g., generate -> upscale -> remove_bg -> 3D -> rig) require the AI agent to chain calls manually. There is no declarative pipeline definition.

2. **Asset handoff between stages is URL-based.** The `image_to_3d` workflow needs `PARAM_STR_IMAGE_PATH` (a ComfyUI filename), but `generate_image` returns an `asset_id`. The agent must use `view_image` or know the raw filename to chain. There is no `use_asset_as_input(asset_id)` helper.

3. **No quality gate between pipeline stages.** Batch generation produces N results, but there is no automated scoring/filtering. The agent must use `view_image` to manually inspect each result.

4. **3D workflow coverage is fragmented.** MCP server has TripoSR-based workflows (older model). Prompter has TripoSG and Hunyuan3D v2.0 workflows but in UI format. The MCP server's `image_to_3d_triposg.json` uses TripoSG but the prompter has more advanced versions.

5. **Video pipeline is Wan 2.1 only (MCP server).** The prompter also has Hunyuan Video workflows, but these are not ported to API format with PARAM placeholders.

6. **No text-to-speech (TTS) workflow.** Audio is limited to music generation (`generate_song` via AceStep). Character dialogue pipelines need TTS.

7. **No lip sync pipeline.** Audio + animation -> lip sync is listed as a target pipeline but has zero implementation.

8. **Inline `_defaults` in style transfer workflows are ignored.** The `WorkflowManager` does not read `_defaults` keys from workflow JSON nodes. These defaults only work if `DefaultsManager` happens to have matching values.

9. **Prompter workflows are not usable via MCP.** The prompter's 25+ workflows use UI format (`widgets_values` arrays). They would need conversion to API format + PARAM placeholders to be usable by the MCP server.

### Moderate Gaps

10. **No image captioning/description workflow.** Useful as input to variation pipelines (describe existing image -> generate variations).

11. **No depth/normal map generation workflow.** Useful for 3D pipeline (generate depth map -> use as ControlNet input for consistent multi-view).

12. **No multi-view generation for 3D.** TripoSG and Hunyuan3D produce better results from multiple views, but there is no workflow to generate consistent multi-view images from a single prompt.

13. **No texture generation workflow.** 3D models from TripoSG have basic textures. No workflow for generating/refining PBR textures (diffuse, normal, roughness).

14. **Blender scripts lack error reporting.** The auto-rig and animate scripts write to stdout, but errors in Blender Python are hard to diagnose from the MCP tool level.

15. **No webhook/callback for long-running pipelines.** Video generation and 3D generation can take 3-5+ minutes. The webhook system exists but is not integrated with pipeline orchestration.

---

## Cross-Domain Pipeline Designs

### Pipeline 1: Full Character Creation

**Goal:** `text description -> concept image -> 3D model -> rigged -> animated -> exported`

```
Stage 1: Concept Art Generation
  Tool: generate_image (or generate_image_lora with character LoRA)
  Input: text description of character
  Output: asset_id (PNG, front-facing, neutral pose)
  Quality gate: view_image -> agent approval

Stage 2: Background Removal
  Tool: remove_background
  Input: asset_id from Stage 1
  Output: asset_id (PNG with transparency)

Stage 3: 3D Model Generation
  Tool: image_to_3d (use image_to_3d_triposg for GLB output)
  Input: asset_id from Stage 2 (or Stage 1)
  Output: asset_id (GLB mesh)

Stage 4: Auto-Rigging
  Tool: smart_rig_model (tries UniRig -> Tripo3D -> Rigify)
  Input: asset_id from Stage 3
  Output: .blend file path with rigged skeleton

Stage 5: Animation
  Tool: animate_model (procedural) OR import_mocap (from library)
  Input: .blend path from Stage 4
  Output: GLB/FBX with animation

Stage 6: Export
  Tool: export_to_blender OR export_to_unreal OR publish_asset
  Input: animated model from Stage 5
  Output: final deliverable
```

**Missing pieces for this pipeline:**
- Asset-to-input bridging (Stage 1 output -> Stage 2 input needs filename mapping)
- Multi-view generation for better 3D (optional Stage 1.5)
- Texture refinement after 3D generation (optional Stage 3.5)
- Pipeline orchestrator that tracks state across stages

**Proposed new workflow:** `generate_character_concept.json`
- FLUX-based with character-optimized prompt template
- Forces front-facing, T-pose, neutral background
- PARAM_PROMPT for character description
- Fixed resolution (1024x1024) for 3D-ready output

### Pipeline 2: Scene Generation (Text -> Image -> Video)

**Goal:** `text description -> scene image -> animated video`

```
Stage 1: Scene Image
  Tool: generate_image
  Input: scene description
  Output: asset_id (PNG)

Stage 2: Upscale (optional)
  Tool: upscale
  Input: asset_id from Stage 1
  Output: asset_id (high-res PNG)

Stage 3: Image to Video
  Tool: image_to_video
  Input: asset_id from Stage 1 or 2 + motion prompt
  Output: asset_id (MP4)

Stage 4: Publish
  Tool: publish_asset
  Input: asset_id from Stage 3
  Output: web-ready file
```

**Missing pieces:**
- Camera motion control (pan, zoom, orbit) is not parameterized
- No video upscaling workflow
- No video-to-video style transfer

### Pipeline 3: Content Production (Batch -> Quality Filter -> Publish)

**Goal:** `prompt + settings -> N variations -> scored/filtered -> published`

```
Stage 1: Batch Generation
  Tool: batch_generate_seeds (or batch_generate_with_styles)
  Input: prompt, settings, count
  Output: N asset_ids

Stage 2: Quality Assessment
  Tool: [NEW] score_images (proposed)
  Input: list of asset_ids
  Output: sorted list with quality scores
  Implementation: Use CLIP score, aesthetic predictor, or agent inspection

Stage 3: Selection
  Tool: Agent decision (view top N, pick best)
  Input: scored list
  Output: selected asset_id(s)

Stage 4: Post-Processing
  Tool: upscale + export preset (social media sizing)
  Input: selected asset_id
  Output: sized/optimized variants

Stage 5: Publish
  Tool: publish_asset (with manifest for hot-swap)
  Input: processed asset_ids
  Output: web-published files
```

**Missing pieces:**
- Automated quality scoring (CLIP score, aesthetic score)
- Batch post-processing (upscale all selected at once)
- Publish queue/batch publish

### Pipeline 4: Character Dialogue (Audio + Animation -> Lip Sync)

**Goal:** `text dialogue -> TTS audio -> lip sync animation on rigged character`

```
Stage 1: Text-to-Speech
  Tool: [NEW] generate_tts
  Input: text, voice_id, emotion
  Output: asset_id (WAV/MP3)
  Implementation: Integrate F5-TTS, Bark, or Coqui TTS via ComfyUI nodes

Stage 2: Audio Analysis
  Tool: [NEW] analyze_audio_phonemes
  Input: audio asset_id
  Output: phoneme timing data (JSON)
  Implementation: Use Whisper for transcription + alignment

Stage 3: Lip Sync Application
  Tool: [NEW] apply_lip_sync
  Input: rigged .blend path, phoneme data, audio path
  Output: animated .blend with lip sync
  Implementation: Blender script mapping phonemes to shape keys/bones

Stage 4: Video Render
  Tool: animate_model (with render_video=True)
  Input: lip-synced .blend
  Output: MP4 video with audio

Stage 5: Composite (optional)
  Tool: [NEW] composite_video
  Input: character video + background image/video
  Output: final scene video
```

**Missing pieces (all of them - this pipeline is not yet started):**
- TTS workflow/tool
- Phoneme extraction/alignment
- Lip sync Blender script
- Video compositing
- Shape key system on 3D models for facial animation

---

## Workflow Standards

### File Naming Convention

```
<action>_<domain>[_<variant>].json
```

Examples:
- `generate_image.json` - base image generation
- `generate_image_lora.json` - image generation with LoRA
- `image_to_3d.json` - image input to 3D output
- `image_to_3d_triposg.json` - image to 3D using TripoSG specifically
- `style_transfer_ipadapter.json` - style transfer via IP-Adapter

### Required Structure for MCP-Compatible Workflows

Every workflow in `workflows/` must:

1. Be in **API format** (dict of `node_id: {class_type, inputs}`), NOT UI format
2. Use `PARAM_*` placeholders for at least one input (otherwise it won't register as a tool)
3. Have `PARAM_PROMPT` (or domain-specific required param) as the primary required input
4. Include `_meta.title` on each node for readability
5. End with a `Save*` node (`SaveImage`, `SaveVideo`, `SaveAudioMP3`, etc.) so ComfyUI produces output

### Optional Enhancements

- **`.meta.json` sidecar**: Name, description, requirements, tags, constraints
- **`_defaults` on nodes**: Document intended default values (future: auto-parse)
- **Output key hints**: Use recognizable `SaveImage`, `SaveVideo`, `SaveAudioMP3`, `TripoSGExportMesh` class types so `_guess_output_preferences()` correctly identifies output type

### Parameter Naming Conventions

| Domain | Standard Parameters |
|--------|-------------------|
| All | `PARAM_PROMPT`, `PARAM_INT_SEED`, `PARAM_INT_STEPS`, `PARAM_FLOAT_CFG` |
| Image | `PARAM_INT_WIDTH`, `PARAM_INT_HEIGHT`, `PARAM_FLOAT_DENOISE`, `PARAM_NEGATIVE_PROMPT` |
| Image (sampler) | `PARAM_STR_SAMPLER_NAME`, `PARAM_STR_SCHEDULER` |
| Image (input) | `PARAM_STR_IMAGE_PATH`, `PARAM_STR_MASK_PATH`, `PARAM_STR_CONTROL_IMAGE` |
| LoRA | `PARAM_STR_LORA_NAME`, `PARAM_FLOAT_LORA_STRENGTH` |
| ControlNet | `PARAM_STR_CONTROLNET_TYPE`, `PARAM_FLOAT_CONTROLNET_STRENGTH` |
| Style | `PARAM_STR_STYLE_IMAGE`, `PARAM_FLOAT_WEIGHT` |
| Video | `PARAM_INT_FRAMES`, `PARAM_INT_FPS` |
| 3D | `PARAM_INT_RESOLUTION` |
| Audio | `PARAM_TAGS`, `PARAM_LYRICS`, `PARAM_INT_SECONDS`, `PARAM_FLOAT_LYRICS_STRENGTH` |

### Adding a New Workflow Checklist

1. Export from ComfyUI as API format JSON (or write by hand)
2. Replace dynamic inputs with `PARAM_*` placeholders
3. Save to `workflows/<action>_<domain>[_<variant>].json`
4. (Optional) Create `.meta.json` sidecar with metadata
5. Restart MCP server -- workflow auto-discovered and registered as tool
6. Test: call the new tool via MCP client with required params
7. Verify: output appears in asset registry

---

## Recommendations

### High Priority

1. **Build an asset-to-input bridge utility.** Create a helper function `resolve_asset_for_workflow(asset_id) -> comfyui_filename` that takes an asset_id from the registry and returns the filename usable as `PARAM_STR_IMAGE_PATH`. This is the single biggest blocker for multi-stage pipelines.

2. **Port key prompter workflows to MCP format.** The highest-value targets:
   - Hunyuan3D v2.0/v2.5 (higher quality 3D than TripoSR)
   - Hunyuan Video 720p (text-to-video and image-to-video)
   - Sketch-to-Image with ControlNet (already exists as `generate_image_controlnet` but SDXL version from prompter is different)
   - Image-to-SVG conversion

3. **Parse `_defaults` from workflow JSON.** The style transfer workflows already have `_defaults` embedded. Modify `WorkflowManager._extract_parameters()` to read these and use them as fallback defaults, bridging the gap with `DefaultsManager`.

4. **Add multi-view generation workflow.** For better 3D results: generate front/side/back views using consistent seed + ControlNet depth, then feed to multi-view 3D pipeline.

### Medium Priority

5. **Design a pipeline orchestrator tool.** A new MCP tool `run_pipeline(stages=[...])` that takes a declarative pipeline definition and executes stages sequentially, passing asset_ids between stages. This eliminates the need for agents to manually chain tools.

6. **Add quality scoring.** Integrate CLIP score or aesthetic predictor as a ComfyUI workflow node. Expose as `score_image(asset_id)` tool for automated quality filtering in batch pipelines.

7. **Add TTS workflow.** F5-TTS or Bark TTS via ComfyUI custom nodes. This unlocks the character dialogue pipeline.

8. **Improve Blender script error reporting.** Blender scripts should write structured JSON results to a temp file that the MCP tool reads back, instead of parsing stdout.

### Lower Priority

9. **Add video upscaling workflow.** Use a video super-resolution model (Real-ESRGAN Video or similar) to upscale generated videos.

10. **Add texture generation workflow.** Generate PBR texture maps (diffuse, normal, roughness) for 3D models using Stable Diffusion with texture-specific LoRAs.

11. **Add lip sync pipeline.** Requires TTS + Whisper phoneme extraction + Blender shape key animation. Complex but high value for character content.

12. **Unify prompter and MCP server workflow formats.** Long-term: create a shared workflow registry that both systems can consume, with automatic format conversion.

---

## Appendix: Node Type Coverage

### ComfyUI Nodes Used Across All Workflows

**Image Pipeline:**
- `CheckpointLoaderSimple`, `CLIPTextEncode`, `EmptySD3LatentImage`, `EmptyLatentImage`
- `KSampler`, `VAEDecode`, `VAEEncode`, `SaveImage`
- `LoadImage`, `ImageToMask`, `SetLatentNoiseMask`
- `LoraLoader`, `ControlNetLoader`, `FluxUnionControlNetApply`
- `IPAdapterUnifiedLoader`, `IPAdapter`, `IPAdapterAdvanced`, `IPAdapterEncoder`, `IPAdapterCombineEmbeds`, `IPAdapterEmbeds`
- `ImageBatch`
- `UpscaleModelLoader`, `ImageUpscaleWithModel`
- `BRIA_RMBG_Zho` (background removal)

**Video Pipeline:**
- `UnetLoaderGGUF`, `CLIPLoader`, `VAELoader`
- `WanImageToVideo`, `CreateVideo`, `SaveVideo`

**3D Pipeline:**
- `TripoSRModelLoader`, `TripoSRSampler`, `SaveTripoSRMesh`, `TripoSRViewer`
- `TripoSGModelLoader`, `TripoSGImageToMesh`, `TripoSGVAEDecoder`, `TripoSGExportMesh`
- `ImageRemoveBackground` (preprocessing for 3D)

**Audio Pipeline:**
- `EmptyAceStepLatentAudio`, `TextEncodeAceStepAudio`
- `ModelSamplingSD3`, `LatentApplyOperationCFG`, `LatentOperationTonemapReinhard`
- `ConditioningZeroOut`, `VAEDecodeAudio`, `SaveAudioMP3`

**Not Yet Used (Available in Prompter but Missing from MCP):**
- `Hy3DModelLoader`, `Hy3DCameraConfig`, `Hy3DExportMesh`, `Hy3DPostprocessMesh` (Hunyuan3D)
- `HunyuanVideoSampler` (Hunyuan Video)
- `WanVideoSampler` (Wan text-to-video alternative node)
- `ControlNetApplyAdvanced` (SDXL ControlNet)
- `AIO_Preprocessor` (Sketch preprocessing)
- SVG conversion nodes
