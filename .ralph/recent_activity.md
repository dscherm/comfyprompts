# Recent Activity (auto-generated)

## 2026-03-26 - Task 3: Map ComfyUI Installation

**Goal:** Verify ComfyUI installation at C:\Users\Teacher\ComfyUI — models, custom nodes, output paths, and workflow compatibility.

**Findings:**

- **ComfyUI Version:** 0.16.4
- **Checkpoints installed:** 512-inpainting-ema.safetensors, dreamshaper_8.safetensors, v1-5-pruned-emaonly-fp16.safetensors, v1-5-pruned-emaonly.safetensors
- **LoRAs installed:** blindbox_V1Mix.safetensors
- **ControlNets installed:** NONE
- **VAE:** ae.safetensors
- **Custom nodes:** NONE (only example_node.py.example and websocket_image_save.py)
- **Output directory:** default (ComfyUI/output/)
- **COMFYUI_OUTPUT_ROOT env var:** NOT SET

**Workflow-Model Gap Analysis:**

Most workflows reference models NOT installed:
- `flux1-dev-fp8.safetensors` — referenced by 10+ workflows (generate_image, img2img, inpaint, etc.) — **NOT INSTALLED**
- `sd_xl_base_1.0.safetensors` — referenced by face_id_portrait, style_transfer_* — **NOT INSTALLED**
- `stable_audio_open_1.0.safetensors` — referenced by generate_sfx — **NOT INSTALLED**
- `ace_step_v1_3.5b.safetensors` — referenced by generate_song — **NOT INSTALLED**
- `flux-dev-controlnet-union.safetensors` — referenced by generate_image_controlnet — **NOT INSTALLED**
- LTX2 video checkpoint — referenced by generate_video_ltx2, image_to_video_ltx2 — **NOT INSTALLED**
- TripoSR model — referenced by generate_3d — **NOT INSTALLED**

Only `basic_api_test` could potentially work with installed models, but its meta.json says `v1-5-pruned-emaonly.ckpt` while the actual JSON hardcodes `flux1-dev-fp8.safetensors` (also not installed). The installed `v1-5-pruned-emaonly.safetensors` is close but has different extension.

**Custom node dependencies missing:**
- ComfyUI-Flux-Union-ControlNet (for generate_image_controlnet)
- IPAdapter nodes (for style_transfer_*, face_id_portrait)
- TripoSR nodes (for generate_3d)
- wav2lip nodes (for lip_sync)
- AceStep nodes (for generate_song)

**Verification:** Data provided by human operator (direct filesystem inspection). Workflow analysis via grep of workflows/mcp/*.json and *.meta.json.

**Status:** COMPLETE
