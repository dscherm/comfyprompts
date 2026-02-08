# Flux 2 Migration Plan & Research Report

**Date:** 2026-02-06
**Author:** image-researcher agent
**Status:** Research Complete

---

## 1. EXECUTIVE SUMMARY

All 11 existing MCP server image workflows use Flux 1 Dev FP8 (`flux1-dev-fp8.safetensors`) with `CheckpointLoaderSimple`. Flux 2 uses a fundamentally different loading architecture (separate UNETLoader + CLIPLoader + VAELoader instead of CheckpointLoaderSimple), a new text encoder (Mistral 3 Small instead of T5+CLIP), and a new VAE. **Existing workflows cannot be trivially adapted -- they require structural rewrites of the loader nodes.** However, the KSampler, VAEDecode, and SaveImage nodes remain compatible.

Additionally, two critical new model families should be added: **Flux Fill** (dedicated inpainting/outpainting) and **Flux Kontext** (instruction-based editing), which use Flux 1 architecture but are purpose-built models.

---

## 2. FLUX 2 DEV - CAPABILITIES & ARCHITECTURE

### 2A. Key Improvements Over Flux 1
- **4MP output** - Up to 2048x2048 or equivalent aspect ratios (vs 1024x1024 for Flux 1)
- **Multi-reference support** - Up to 10 reference images for identity/style consistency
- **Better typography** - Professional-grade text rendering in generated images
- **Improved prompt adherence** - Mistral-based text encoder understands complex prompts better
- **Better photorealism** - Improved lighting, skin, fabric, and hand detail
- **Hex-code color accuracy** - Exact brand color matching
- **Klein variants** - 4B and 9B distilled models for sub-second generation

### 2B. Architecture Changes from Flux 1

| Component | Flux 1 | Flux 2 Dev | Impact |
|-----------|--------|------------|--------|
| **Model Loading** | `CheckpointLoaderSimple` (single node) | Separate `UNETLoader` + `CLIPLoader` + `VAELoader` (3 nodes) | **BREAKING** - All workflows need rewrite |
| **Text Encoder** | T5-XXL + CLIP-L (DualCLIPLoader) | Mistral 3 Small (single CLIPLoader) | **BREAKING** - Different encoder architecture |
| **VAE** | `ae.safetensors` (Flux 1 VAE) | `flux2-vae.safetensors` (new VAE) | **BREAKING** - New VAE file |
| **Diffusion Model** | `flux1-dev-fp8.safetensors` (checkpoint) | `flux2_dev_fp8mixed.safetensors` (unet) | **BREAKING** - Different model format |
| **Latent Image** | `EmptySD3LatentImage` | `EmptySD3LatentImage` (same) | Compatible |
| **KSampler** | `KSampler` | `KSampler` (same) | Compatible |
| **CLIPTextEncode** | `CLIPTextEncode` | `CLIPTextEncode` (same) | Compatible |
| **VAEDecode** | `VAEDecode` | `VAEDecode` (same) | Compatible |
| **SaveImage** | `SaveImage` | `SaveImage` (same) | Compatible |

### 2C. Node Structure Comparison

**Flux 1 (Current):**
```
CheckpointLoaderSimple --> model, clip, vae
  |-> CLIPTextEncode (positive)
  |-> CLIPTextEncode (negative)
  |-> EmptySD3LatentImage
  |-> KSampler --> VAEDecode --> SaveImage
```

**Flux 2 Dev (New):**
```
UNETLoader -----------> model
CLIPLoader -----------> clip (Mistral encoder)
VAELoader ------------> vae
  |-> CLIPTextEncode (positive)
  |-> CLIPTextEncode (negative, optional for Flux 2)
  |-> EmptySD3LatentImage
  |-> KSampler --> VAEDecode --> SaveImage
  |-> [Optional: LoadImage x N for reference images]
```

### 2D. Recommended Sampler Settings for Flux 2 Dev
- **Steps:** 20-30 (same as Flux 1)
- **CFG:** 1.0-3.5 (Flux 2 works well with lower CFG)
- **Sampler:** euler, dpmpp_2m
- **Scheduler:** simple, normal
- **Denoise:** 1.0 for t2i, 0.5-0.8 for img2img

---

## 3. FLUX 2 KLEIN - LOW VRAM VARIANTS

### 3A. Model Variants

| Model | Params | Steps | Speed (RTX 5090) | VRAM | Use Case |
|-------|--------|-------|-------------------|------|----------|
| Klein 4B Distilled | 4B | 4 | ~1.2s | 8.4 GB | Interactive/production, sub-second generation |
| Klein 4B Base | 4B | 20-30 | ~17s | 9.2 GB | Higher quality, fine-tuning capable |
| Klein 9B Distilled | 9B | 4 | Faster | ~16 GB | Best quality at high speed |
| Klein 9B Base | 9B | 20-30 | Slower | ~18 GB | Maximum quality |

### 3B. Klein Architecture Differences
- **Text Encoder:** Qwen 3 4B (`qwen_3_4b.safetensors`) instead of Mistral 3 Small
- **VAE:** Same `flux2-vae.safetensors`
- **Distilled models:** Must use CFG=1.0, steps=4
- **Capabilities:** Unified text-to-image AND image editing (style transforms, object replacement, multi-reference composition)

### 3C. Klein Model Files

| File | Size | Path | Download |
|------|------|------|----------|
| `flux-2-klein-4b-fp8.safetensors` (distilled) | ~4 GB | `models/diffusion_models/` | `huggingface.co/black-forest-labs/FLUX.2-klein-4b-fp8` |
| `flux-2-klein-base-4b-fp8.safetensors` (base) | ~4 GB | `models/diffusion_models/` | `huggingface.co/black-forest-labs/FLUX.2-klein-base-4b-fp8` |
| `qwen_3_4b.safetensors` | ~4 GB | `models/text_encoders/` | `huggingface.co/Comfy-Org/flux2-klein-4B` (split_files/text_encoders/) |
| `flux2-vae.safetensors` | ~336 MB | `models/vae/` | (shared with Flux 2 Dev) |

---

## 4. FLUX FILL DEV - DEDICATED INPAINTING/OUTPAINTING

### 4A. Why It Matters
Current `inpaint.json` uses generic Flux 1 Dev + `SetLatentNoiseMask`, which is a hack -- it wasn't designed for inpainting. Flux Fill is a purpose-built 12B parameter inpainting model with:
- Native mask understanding
- Better edge blending
- Outpainting support (extend beyond canvas)
- Higher quality fills that match surrounding content

### 4B. Architecture
Uses Flux 1 architecture (DualCLIPLoader with T5+CLIP-L), NOT Flux 2 architecture:
```
UNETLoader (flux1-fill-dev) --> model
DualCLIPLoader (clip_l + t5xxl) --> clip
VAELoader (ae.safetensors) --> vae
LoadImage --> image + mask
  |-> InpaintModelConditioning (image, mask, vae, positive, negative)
  |-> DifferentialDiffusion (model)
  |-> KSampler --> VAEDecode --> SaveImage
```

### 4C. Key Nodes
- `InpaintModelConditioning` - Combines image, mask, and conditioning (built-in to ComfyUI core)
- `DifferentialDiffusion` - Improves inpainting edge quality (built-in to ComfyUI core)
- `UNETLoader` / `DualCLIPLoader` / `VAELoader` - Standard loaders (built-in)

### 4D. Model Files

| File | Size | Path | Download |
|------|------|------|----------|
| `flux1-fill-dev.safetensors` | 23.8 GB | `models/diffusion_models/` | `huggingface.co/black-forest-labs/FLUX.1-Fill-dev` |
| `clip_l.safetensors` | ~235 MB | `models/text_encoders/` | `huggingface.co/comfyanonymous/flux_text_encoders` |
| `t5xxl_fp16.safetensors` | ~9.8 GB | `models/text_encoders/` | `huggingface.co/comfyanonymous/flux_text_encoders` |
| `ae.safetensors` | ~320 MB | `models/vae/` | `huggingface.co/black-forest-labs/FLUX.1-schnell` |

**FP8 alternative:** `flux1-fill-dev-fp8.safetensors` (~12 GB) for lower VRAM.

**VRAM:** ~16-24 GB (full), ~12 GB (FP8), ~6-8 GB (GGUF Q4-Q5)

---

## 5. FLUX KONTEXT DEV - INSTRUCTION-BASED EDITING

### 5A. Capabilities
- Natural language image editing ("change the hat to red", "make it a sunset scene")
- Character consistency across edits
- Style transfer via text instructions
- Text modification in images
- Iterative editing (edit -> edit -> edit)
- 12B parameters

### 5B. Architecture
Also uses Flux 1 architecture (DualCLIPLoader with T5+CLIP-L):
```
UNETLoader (flux1-dev-kontext) --> model
DualCLIPLoader (clip_l + t5xxl) --> clip
VAELoader (ae.safetensors) --> vae
LoadImage --> reference image
  |-> CLIPTextEncode (editing instruction)
  |-> KSampler --> VAEDecode --> SaveImage
```

### 5C. Model Files

| File | Size | Path | Download |
|------|------|------|----------|
| `flux1-dev-kontext_fp8_scaled.safetensors` | ~12 GB | `models/diffusion_models/` | `huggingface.co/Comfy-Org/flux1-kontext-dev_ComfyUI` |
| `clip_l.safetensors` | ~235 MB | `models/text_encoders/` | (shared with Flux Fill) |
| `t5xxl_fp8_e4m3fn_scaled.safetensors` | ~4.9 GB | `models/text_encoders/` | `huggingface.co/comfyanonymous/flux_text_encoders` |
| `ae.safetensors` | ~320 MB | `models/vae/` | (shared with Flux Fill) |

**GGUF alternative:** Available at `huggingface.co/QuantStack/FLUX.1-Kontext-dev-GGUF`

**VRAM:** ~12-16 GB (FP8), ~4-8 GB (GGUF Q3-Q5)

---

## 6. CUSTOM NODE REQUIREMENTS

### 6A. Built-in Nodes (No Installation Needed)
All of these are in ComfyUI core (latest version required):
- `UNETLoader` / `UnetLoaderGGUF` (GGUF variant needs custom node)
- `CLIPLoader` / `DualCLIPLoader`
- `VAELoader`
- `KSampler`
- `CLIPTextEncode`
- `VAEDecode` / `VAEEncode`
- `EmptySD3LatentImage`
- `InpaintModelConditioning`
- `DifferentialDiffusion`
- `LoadImage`
- `SaveImage`

### 6B. Custom Nodes Required

| Node | Purpose | Install | Required For |
|------|---------|---------|-------------|
| `ComfyUI-GGUF` (city96) | GGUF model loading | ComfyUI Manager or git clone | GGUF variants of all models |
| (none) | Flux 2 Dev basic | Built-in | Flux 2 Dev FP8/BF16 |
| (none) | Flux Fill basic | Built-in | Flux Fill FP8 |
| (none) | Flux Kontext basic | Built-in | Flux Kontext FP8 |

**Key finding: Flux 2, Flux Fill, and Flux Kontext all work with built-in ComfyUI nodes (v0.3.39+). Only GGUF quantization requires the ComfyUI-GGUF custom node.**

### 6C. ComfyUI Version Requirements
- Flux 2 Dev: ComfyUI v0.3.39+ (Nov 2025)
- Flux 2 Klein: ComfyUI v0.3.42+ (Jan 2026)
- Flux Fill: ComfyUI v0.3.30+ (mid 2025)
- Flux Kontext: ComfyUI v0.3.42+ (Jun 2025 nightly, later stabilized)

---

## 7. MIGRATION PLAN

### 7A. Strategy: Add New Workflows, Keep Old Ones

**Do NOT replace existing Flux 1 workflows.** Instead:
1. Add new Flux 2 workflow files alongside existing ones
2. Keep Flux 1 workflows as fallback (they still work and are stable)
3. Let the defaults_manager system handle model selection
4. Users can choose which generation to use

### 7B. Workflow Migration Matrix

| Existing Workflow | Migration Action | New File | Priority |
|---|---|---|---|
| `generate_image.json` | Add Flux 2 variant | `generate_image_flux2.json` | HIGH |
| `generate_image_lora.json` | Keep as-is (LoRA ecosystem is Flux 1) | N/A | SKIP for now |
| `generate_image_controlnet.json` | Keep as-is (ControlNet Union is Flux 1) | N/A | SKIP for now |
| `img2img.json` | Add Flux 2 variant with ref images | `img2img_flux2.json` | MEDIUM |
| `inpaint.json` | Add Flux Fill variant | `inpaint_flux_fill.json` | HIGH |
| `upscale.json` | No change needed (model-agnostic) | N/A | SKIP |
| `remove_background.json` | No change needed (model-agnostic) | N/A | SKIP |
| `image_variations.json` | Replace with Flux 2 multi-ref | `image_variations_flux2.json` | MEDIUM |
| `style_transfer_*.json` | Keep SDXL versions, add Flux 2 ref-based | `style_transfer_flux2.json` | LOW |
| N/A (new) | Add Flux Kontext editing | `edit_image_kontext.json` | HIGH |
| N/A (new) | Add outpainting | `outpaint_flux_fill.json` | MEDIUM |
| N/A (new) | Add Klein fast generation | `generate_image_klein.json` | MEDIUM |

### 7C. Phase 1: Critical New Workflows (Implement First)

#### 1. `generate_image_flux2.json` - Flux 2 Dev Text-to-Image
```json
{
  "1": {
    "inputs": {"unet_name": "flux2_dev_fp8mixed.safetensors"},
    "class_type": "UNETLoader",
    "_meta": {"title": "Load Diffusion Model"}
  },
  "2": {
    "inputs": {"clip_name": "mistral_3_small_flux2_fp8.safetensors", "type": "flux"},
    "class_type": "CLIPLoader",
    "_meta": {"title": "Load Text Encoder"}
  },
  "3": {
    "inputs": {"vae_name": "flux2-vae.safetensors"},
    "class_type": "VAELoader",
    "_meta": {"title": "Load VAE"}
  },
  "4": {
    "inputs": {"width": "PARAM_INT_WIDTH", "height": "PARAM_INT_HEIGHT", "batch_size": 1},
    "class_type": "EmptySD3LatentImage",
    "_meta": {"title": "Empty Latent Image"}
  },
  "5": {
    "inputs": {"text": "PARAM_PROMPT", "clip": ["2", 0]},
    "class_type": "CLIPTextEncode",
    "_meta": {"title": "Positive Prompt"}
  },
  "6": {
    "inputs": {"text": "PARAM_NEGATIVE_PROMPT", "clip": ["2", 0]},
    "class_type": "CLIPTextEncode",
    "_meta": {"title": "Negative Prompt"}
  },
  "7": {
    "inputs": {
      "seed": "PARAM_INT_SEED",
      "steps": "PARAM_INT_STEPS",
      "cfg": "PARAM_FLOAT_CFG",
      "sampler_name": "PARAM_STR_SAMPLER_NAME",
      "scheduler": "PARAM_STR_SCHEDULER",
      "denoise": "PARAM_FLOAT_DENOISE",
      "model": ["1", 0],
      "positive": ["5", 0],
      "negative": ["6", 0],
      "latent_image": ["4", 0]
    },
    "class_type": "KSampler",
    "_meta": {"title": "KSampler"}
  },
  "8": {
    "inputs": {"samples": ["7", 0], "vae": ["3", 0]},
    "class_type": "VAEDecode",
    "_meta": {"title": "VAE Decode"}
  },
  "9": {
    "inputs": {"filename_prefix": "ComfyUI_Flux2", "images": ["8", 0]},
    "class_type": "SaveImage",
    "_meta": {"title": "Save Image"}
  }
}
```

#### 2. `inpaint_flux_fill.json` - Flux Fill Dedicated Inpainting
```json
{
  "1": {
    "inputs": {"unet_name": "flux1-fill-dev.safetensors"},
    "class_type": "UNETLoader",
    "_meta": {"title": "Load Flux Fill Model"}
  },
  "2": {
    "inputs": {
      "clip_name1": "t5xxl_fp8_e4m3fn_scaled.safetensors",
      "clip_name2": "clip_l.safetensors",
      "type": "flux"
    },
    "class_type": "DualCLIPLoader",
    "_meta": {"title": "Load CLIP Encoders"}
  },
  "3": {
    "inputs": {"vae_name": "ae.safetensors"},
    "class_type": "VAELoader",
    "_meta": {"title": "Load VAE"}
  },
  "4": {
    "inputs": {"image": "PARAM_STR_IMAGE_PATH", "upload": "image"},
    "class_type": "LoadImage",
    "_meta": {"title": "Load Source Image"}
  },
  "5": {
    "inputs": {"image": "PARAM_STR_MASK_PATH", "upload": "image"},
    "class_type": "LoadImage",
    "_meta": {"title": "Load Mask"}
  },
  "6": {
    "inputs": {"image": ["5", 0], "channel": "red"},
    "class_type": "ImageToMask",
    "_meta": {"title": "Image to Mask"}
  },
  "7": {
    "inputs": {"text": "PARAM_PROMPT", "clip": ["2", 0]},
    "class_type": "CLIPTextEncode",
    "_meta": {"title": "Positive Prompt"}
  },
  "8": {
    "inputs": {"text": "PARAM_NEGATIVE_PROMPT", "clip": ["2", 0]},
    "class_type": "CLIPTextEncode",
    "_meta": {"title": "Negative Prompt"}
  },
  "9": {
    "inputs": {
      "positive": ["7", 0],
      "negative": ["8", 0],
      "vae": ["3", 0],
      "pixels": ["4", 0],
      "mask": ["6", 0]
    },
    "class_type": "InpaintModelConditioning",
    "_meta": {"title": "Inpaint Conditioning"}
  },
  "10": {
    "inputs": {"model": ["1", 0]},
    "class_type": "DifferentialDiffusion",
    "_meta": {"title": "Differential Diffusion"}
  },
  "11": {
    "inputs": {
      "seed": "PARAM_INT_SEED",
      "steps": "PARAM_INT_STEPS",
      "cfg": "PARAM_FLOAT_CFG",
      "sampler_name": "PARAM_STR_SAMPLER_NAME",
      "scheduler": "PARAM_STR_SCHEDULER",
      "denoise": "PARAM_FLOAT_DENOISE",
      "model": ["10", 0],
      "positive": ["9", 0],
      "negative": ["9", 1],
      "latent_image": ["9", 2]
    },
    "class_type": "KSampler",
    "_meta": {"title": "KSampler"}
  },
  "12": {
    "inputs": {"samples": ["11", 0], "vae": ["3", 0]},
    "class_type": "VAEDecode",
    "_meta": {"title": "VAE Decode"}
  },
  "13": {
    "inputs": {"filename_prefix": "ComfyUI_FluxFill", "images": ["12", 0]},
    "class_type": "SaveImage",
    "_meta": {"title": "Save Image"}
  }
}
```

#### 3. `edit_image_kontext.json` - Flux Kontext Instruction Editing
```json
{
  "1": {
    "inputs": {"unet_name": "flux1-dev-kontext_fp8_scaled.safetensors"},
    "class_type": "UNETLoader",
    "_meta": {"title": "Load Kontext Model"}
  },
  "2": {
    "inputs": {
      "clip_name1": "t5xxl_fp8_e4m3fn_scaled.safetensors",
      "clip_name2": "clip_l.safetensors",
      "type": "flux"
    },
    "class_type": "DualCLIPLoader",
    "_meta": {"title": "Load CLIP Encoders"}
  },
  "3": {
    "inputs": {"vae_name": "ae.safetensors"},
    "class_type": "VAELoader",
    "_meta": {"title": "Load VAE"}
  },
  "4": {
    "inputs": {"image": "PARAM_STR_IMAGE_PATH", "upload": "image"},
    "class_type": "LoadImage",
    "_meta": {"title": "Load Source Image"}
  },
  "5": {
    "inputs": {"text": "PARAM_PROMPT", "clip": ["2", 0]},
    "class_type": "CLIPTextEncode",
    "_meta": {"title": "Edit Instruction"}
  },
  "6": {
    "inputs": {"pixels": ["4", 0], "vae": ["3", 0]},
    "class_type": "VAEEncode",
    "_meta": {"title": "Encode Source Image"}
  },
  "7": {
    "inputs": {
      "seed": "PARAM_INT_SEED",
      "steps": "PARAM_INT_STEPS",
      "cfg": "PARAM_FLOAT_CFG",
      "sampler_name": "PARAM_STR_SAMPLER_NAME",
      "scheduler": "PARAM_STR_SCHEDULER",
      "denoise": "PARAM_FLOAT_DENOISE",
      "model": ["1", 0],
      "positive": ["5", 0],
      "negative": ["5", 0],
      "latent_image": ["6", 0]
    },
    "class_type": "KSampler",
    "_meta": {"title": "KSampler"}
  },
  "8": {
    "inputs": {"samples": ["7", 0], "vae": ["3", 0]},
    "class_type": "VAEDecode",
    "_meta": {"title": "VAE Decode"}
  },
  "9": {
    "inputs": {"filename_prefix": "ComfyUI_Kontext", "images": ["8", 0]},
    "class_type": "SaveImage",
    "_meta": {"title": "Save Image"}
  }
}
```

### 7D. Phase 2: Low-VRAM & Variations

#### 4. `generate_image_klein.json` - Klein 4B Fast Generation
- Uses `UNETLoader` with `flux-2-klein-4b-fp8.safetensors`
- Uses `CLIPLoader` with `qwen_3_4b.safetensors`
- Uses `VAELoader` with `flux2-vae.safetensors`
- Distilled: CFG=1.0, steps=4
- Base: CFG=3.5, steps=20-30

#### 5. `img2img_flux2.json` - Flux 2 Image-to-Image with Reference
- Same as generate_image_flux2.json but adds LoadImage + VAEEncode for source image
- Optionally supports reference images for consistency

#### 6. `outpaint_flux_fill.json` - Canvas Extension
- Same architecture as inpaint_flux_fill.json
- Mask covers the new canvas area instead of an object

### 7E. Phase 3: GGUF Variants
For each workflow, provide GGUF variants that use `UnetLoaderGGUF` instead of `UNETLoader`:
- `generate_image_flux2_gguf.json` - Q4/Q5 for 6-8GB VRAM
- `inpaint_flux_fill_gguf.json`
- `edit_image_kontext_gguf.json`

---

## 8. TOTAL MODEL DOWNLOAD REQUIREMENTS

### 8A. Minimum Downloads for All New Workflows

| File | Size | Shared Across | Download URL |
|------|------|---------------|--------------|
| **Flux 2 Dev** | | | |
| `flux2_dev_fp8mixed.safetensors` | ~24 GB | Flux 2 t2i, img2img, variations | `huggingface.co/Comfy-Org/flux2-dev/resolve/main/split_files/diffusion_models/flux2_dev_fp8mixed.safetensors` |
| `mistral_3_small_flux2_fp8.safetensors` | ~18 GB | Flux 2 workflows | `huggingface.co/Comfy-Org/flux2-dev/resolve/main/split_files/text_encoders/mistral_3_small_flux2_fp8.safetensors` |
| `flux2-vae.safetensors` | ~336 MB | All Flux 2 + Klein | `huggingface.co/Comfy-Org/flux2-dev/resolve/main/split_files/vae/flux2-vae.safetensors` |
| **Flux 2 Klein 4B** | | | |
| `flux-2-klein-4b-fp8.safetensors` | ~4 GB | Klein distilled | `huggingface.co/black-forest-labs/FLUX.2-klein-4b-fp8` |
| `flux-2-klein-base-4b-fp8.safetensors` | ~4 GB | Klein base | `huggingface.co/black-forest-labs/FLUX.2-klein-base-4b-fp8` |
| `qwen_3_4b.safetensors` | ~4 GB | Klein workflows | `huggingface.co/Comfy-Org/flux2-klein-4B/resolve/main/split_files/text_encoders/qwen_3_4b.safetensors` |
| **Flux Fill** | | | |
| `flux1-fill-dev.safetensors` | ~23.8 GB | Inpaint/outpaint | `huggingface.co/black-forest-labs/FLUX.1-Fill-dev/resolve/main/flux1-fill-dev.safetensors` |
| **Flux Kontext** | | | |
| `flux1-dev-kontext_fp8_scaled.safetensors` | ~12 GB | Kontext editing | `huggingface.co/Comfy-Org/flux1-kontext-dev_ComfyUI` (split_files/diffusion_models/) |
| **Shared (Flux 1 architecture)** | | | |
| `clip_l.safetensors` | ~235 MB | Flux Fill + Kontext | `huggingface.co/comfyanonymous/flux_text_encoders/resolve/main/clip_l.safetensors` |
| `t5xxl_fp8_e4m3fn_scaled.safetensors` | ~4.9 GB | Flux Fill + Kontext | `huggingface.co/comfyanonymous/flux_text_encoders/resolve/main/t5xxl_fp8_e4m3fn_scaled.safetensors` |
| `ae.safetensors` | ~320 MB | Flux Fill + Kontext | `huggingface.co/black-forest-labs/FLUX.1-schnell/resolve/main/ae.safetensors` |

**Total new download:** ~95 GB (all variants), ~60 GB (essential only: Flux 2 Dev + Fill + Kontext)

### 8B. GGUF Alternatives (Lower VRAM)

| File | Size | VRAM | Download |
|------|------|------|----------|
| `FLUX.2-dev-Q4_K_M.gguf` | ~19 GB | 6-8 GB | `huggingface.co/city96/FLUX.2-dev-gguf` |
| `FLUX.2-dev-Q5_K_M.gguf` | ~22 GB | 8-10 GB | Same repo |
| `flux1-kontext-dev-Q4_K_S.gguf` | ~7 GB | 6-8 GB | `huggingface.co/QuantStack/FLUX.1-Kontext-dev-GGUF` |

---

## 9. VRAM REQUIREMENTS SUMMARY

| Workflow | FP8 VRAM | GGUF Q4 VRAM | GGUF Q5 VRAM |
|----------|----------|--------------|--------------|
| Flux 2 Dev t2i | 12-16 GB | 6-8 GB | 8-10 GB |
| Flux 2 Klein 4B (distilled) | 8-9 GB | N/A | N/A |
| Flux Fill (inpainting) | 12-16 GB | 6-8 GB | 8-10 GB |
| Flux Kontext (editing) | 12-16 GB | 4-8 GB | 6-10 GB |
| Existing Flux 1 Dev | 12-16 GB | N/A (not setup) | N/A |

---

## 10. IMPLEMENTATION CHECKLIST

### Immediate Actions
- [ ] Create `generate_image_flux2.json` with PARAM_* placeholders
- [ ] Create `inpaint_flux_fill.json` with PARAM_* placeholders
- [ ] Create `edit_image_kontext.json` with PARAM_* placeholders
- [ ] Create `.meta.json` files for all three new workflows
- [ ] Update `defaults_manager` to support Flux 2 model defaults

### Follow-up Actions
- [ ] Create `generate_image_klein.json` for low-VRAM users
- [ ] Create GGUF variants of all new workflows
- [ ] Create `outpaint_flux_fill.json`
- [ ] Create `img2img_flux2.json` with multi-reference support
- [ ] Add Flux 2 / Klein / Fill / Kontext models to prompter config.py
- [ ] Test all workflows end-to-end

### Architecture Changes Needed
- [ ] Ensure `workflow_manager.py` handles UNETLoader/CLIPLoader/VAELoader node types (currently expects CheckpointLoaderSimple for model validation)
- [ ] Update namespace detection in `generation.py` for new workflow IDs
- [ ] Add model validation for diffusion_models folder (not just checkpoints)
