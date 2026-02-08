# TRELLIS.2 Integration Plan for ComfyUI MCP Server

**Date:** 2026-02-06
**Author:** 3D Workflow Researcher

---

## 1. Overview

TRELLIS.2 is Microsoft Research's state-of-the-art 3D generation model released in December 2025. It features 4 billion parameters and generates high-quality 3D assets with full PBR materials from a single image in seconds.

- **License:** MIT (fully open source)
- **Repository:** https://github.com/microsoft/TRELLIS.2
- **Paper:** https://arxiv.org/abs/2506.16504

## 2. Key Capabilities

| Feature | Details |
|---|---|
| Input | Single image |
| Output | 3D mesh with full PBR materials (albedo, roughness, metallic, normal) |
| Resolution 512^3 | ~3 seconds (2s shape + 1s material) |
| Resolution 1024^3 | ~17 seconds (10s shape + 7s material) |
| Resolution 1536^3 | ~60 seconds (35s shape + 25s material) |
| Architecture | O-Voxel sparse voxel structure |
| Parameters | 4 billion |
| Topology | Complex topology support, sharp features |

## 3. ComfyUI Wrapper Options

### Option A: PozzettiAndrea/ComfyUI-TRELLIS2 (Recommended)
- **Repository:** https://github.com/PozzettiAndrea/ComfyUI-TRELLIS2
- **Status:** Active development
- **Installation:** ComfyUI Manager or manual `python install.py`
- **Pros:** Automated installation, good documentation

### Option B: visualbruno/ComfyUI-Trellis2
- **Repository:** https://github.com/visualbruno/ComfyUI-Trellis2
- **Status:** Active development
- **Pros:** More node types (mesh refiner, fill holes, smooth normals)
- **Cons:** Manual wheel installation required

### Recommendation
Start with **PozzettiAndrea/ComfyUI-TRELLIS2** for simpler installation. Evaluate visualbruno's wrapper if additional mesh processing nodes are needed.

## 4. System Requirements

### Hardware
- **Minimum VRAM:** 8GB (512^3 only)
- **Recommended VRAM:** 16GB (1024^3 comfortable)
- **Ideal VRAM:** 24GB (1536^3, full resolution)
- **GPU:** NVIDIA CUDA-capable

### Software
- Python 3.10+
- PyTorch 2.0+ with CUDA support
- Tested: torch 2.7.0+cu128, torch 2.8.0
- Windows 11 (verified compatibility)

## 5. Model Files Required

All models auto-download from HuggingFace on first run.

### From microsoft/TRELLIS-image-large/ckpts:
- `ss_dec_conv3d_16l8_fp16.json` + `.safetensors`

### From microsoft/TRELLIS.2-4B/ckpts:
- `ss_flow_img_dit_1_3B_64_bf16.json` + `.safetensors`
- `shape_dec_next_dc_f16c32_fp16.json` + `.safetensors`
- `slat_flow_img2shape_dit_1_3B_512_bf16.json` + `.safetensors`
- `slat_flow_img2shape_dit_1_3B_1024_bf16.json` + `.safetensors`
- `tex_dec_next_dc_f16c32_fp16.json` + `.safetensors`
- `slat_flow_imgshape2tex_dit_1_3B_512_bf16.json` + `.safetensors`
- `slat_flow_imgshape2tex_dit_1_3B_1024_bf16.json` + `.safetensors`

### Auto-downloaded additional models:
- `facebook/dinov3-vitl16-pretrain-lvd1689m` (image encoder)
- `briaai/RMBG-2.0` (background removal)

**Estimated total model size:** ~15-20GB

## 6. Installation Steps

```bash
# 1. Navigate to custom_nodes
cd D:\Projects\ComfyUI\custom_nodes

# 2. Clone the wrapper
git clone https://github.com/PozzettiAndrea/ComfyUI-TRELLIS2.git

# 3. Install dependencies
cd ComfyUI-TRELLIS2
python install.py

# 4. Restart ComfyUI
# Models will auto-download on first workflow execution
```

## 7. Planned MCP Workflow

Once installed, create `trellis2_image_to_3d_pbr.json` with these PARAM_* parameters:

| Parameter | Type | Default | Description |
|---|---|---|---|
| PARAM_STR_IMAGE_PATH | string | (required) | Input image path |
| PARAM_INT_RESOLUTION | int | 512 | Voxel resolution (512/1024/1536) |
| PARAM_INT_SEED | int | 0 | Random seed |
| PARAM_INT_SHAPE_STEPS | int | 30 | Shape generation steps |
| PARAM_INT_TEXTURE_STEPS | int | 20 | Texture generation steps |

### Expected Output
- GLB mesh with embedded PBR materials
- Separate PBR texture maps (albedo, roughness, metallic, normal) if extracted

## 8. Comparison with Existing 3D Workflows

| Feature | TripoSR | TripoSG | Hunyuan3D v2.5 | TRELLIS.2 |
|---|---|---|---|---|
| Speed | ~30s | ~2min | ~5min | ~3-60s |
| Geometry | Low | Medium-High | Very High | Very High |
| Textures | None | None | Baked + PBR attrs | Full PBR maps |
| PBR Maps | No | No | Attributes only | Albedo + Roughness + Metallic + Normal |
| VRAM | ~4GB | ~8GB | ~12GB | ~8-24GB |
| License | MIT | Apache 2.0 | Tencent | MIT |

## 9. Integration Priority

TRELLIS.2 should be the **highest priority** new 3D integration because:
1. It's the only model that generates true PBR material maps (not just attributes)
2. MIT license allows commercial use
3. Fastest high-quality option at 512^3 (~3 seconds)
4. Fills the biggest gap in the current pipeline: no PBR texture maps

## 10. Next Steps

1. **Install** ComfyUI-TRELLIS2 wrapper in custom_nodes
2. **Test** basic image-to-3D generation at 512^3 on current hardware
3. **Evaluate** output quality (mesh topology, PBR map quality, UV unwrapping)
4. **Create** MCP-parameterized workflow JSON
5. **Create** .meta.json validation file
6. **Register** in config.py WORKFLOWS and CHECKPOINTS dicts
7. **Test** end-to-end through MCP server API
