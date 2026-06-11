# Fix Plan — Workflow Library Drift (found by scripts/workflow_validator.py, 2026-06-10)

Full validation of `workflows/mcp/` against the live ComfyUI install
(`scripts/cache/object_info.json`, 2151 node classes) found **22 of 48
workflows reference models or nodes that don't exist on this machine**.
Full per-file detail: `scripts/cache/validation_report.txt`.
Re-check any single fix with:
`python scripts/workflow_validator.py workflows/mcp/<name>.json --object-info scripts/cache/object_info.json`

## A. Workflows referencing models that are not downloaded

Decide per workflow: download the model (SDK keyring has HF/CivitAI tokens) OR
re-point the workflow at an installed equivalent OR mark the workflow as
requires-download in its .meta.json so the MCP tool can fail gracefully.

- [x] `blender_pose_to_render` — re-pointed to `sd_xl_base_1.0.safetensors` + `OpenPoseXL2.safetensors` (both installed); resolution defaults updated to 1024x1024 (SDXL-native). PASS, zero model errors.
- [x] `blender_depth_guided` — deferred with `requires_download`: `v1-5-pruned-emaonly.ckpt` + `control_v11f1p_sd15_depth.pth` (no SDXL/Flux depth controlnet installed). PASS with (deferred download) warnings.
- [x] `blender_normal_texturing` — deferred with `requires_download`: `v1-5-pruned-emaonly.ckpt` + `control_v11p_sd15_normalbae.pth` (no SDXL/Flux normal controlnet installed). PASS with (deferred download) warnings.
- [x] `edit_image_kontext` — text encoders installed 2026-06-11 (`t5xxl_fp8_e4m3fn_scaled` + `clip_l` → models/text_encoders); kontext fp8 unet downloading → activate on arrival.
- [x] `generate_image_flux2` — deferred with `requires_download`: `flux2_dev_fp8mixed.safetensors` (unet) + `mistral_3_small_flux2_fp8.safetensors` (clip) + `flux2-vae.safetensors` (vae) from Comfy-Org/flux2-dev. PASS with (deferred download) warnings.
- [x] `generate_image_pixelart` — deferred with `requires_download`: `style/PixelArtV3Flux.safetensors` (lora, CivitAI). PASS with (deferred download) warnings.
- [x] `generate_song` — deferred with `requires_download`: `ace_step_v1_3.5b.safetensors` (checkpoint) + ComfyUI-AceStepAudio nodes from ACE-Step/ACE-Step-v1-3.5B. PASS with (deferred download) warnings.
- [x] `generate_video_ltx2` / `image_to_video_ltx2` — deferred with `requires_download`: `ltx-2-19b-distilled-fp8.safetensors` from Lightricks/LTX-2. PASS with (deferred download) warnings.
- [x] `hunyuan3d_mini_image_to_3d` / `hunyuan3d_turbo_image_to_3d` — **ACTIVE as of 2026-06-11**: the mini-turbo fp16 weights were salvaged from the HF cache (tencent/Hunyuan3D-2mini, copied to `models/diffusion_models/hy3dgen/hunyuan3d-dit-v2-mini-turbo-fp16.safetensors`) and both workflows re-pointed to it. PASS clean. The cache copy was then deleted (part of a 30.5 GB C: cleanup that also removed unused SDXL-diffusers/sd-turbo/siglip cache repos).
- [x] `hunyuan3d_v25_image_to_3d_pbr` — deferred with `requires_download`: `hy3dgen/hunyuan3d-dit-v2-5-fp16.safetensors` from tencent/Hunyuan3D-2. PASS with (deferred download) warnings.
- [x] `inpaint_flux_fill` — text encoders installed 2026-06-11; official Fill repo is license-gated (no local HF token) → public Q5_K_S GGUF downloading instead; workflow gets UNETLoader→UnetLoaderGGUF rewire on arrival.
- [x] `lip_sync` — deferred with `requires_download`: `wav2lip.pth` + ComfyUI_wav2lip + ComfyUI-VideoHelperSuite nodes. PASS with (deferred download) warnings.
- [x] `video_frame_interpolation` — **ACTIVE as of 2026-06-11**: VideoHelperSuite + Frame-Interpolation packs installed; RIFE/VHS spec defaults filled. PASS clean, no defer.
- [x] `video_to_audio` — deferred with `requires_download`: `mmaudio_44k.safetensors` + ComfyUI-MMAudio + ComfyUI-VideoHelperSuite nodes. PASS with (deferred download) warnings.

## B. Workflows referencing node classes not present in object_info

May mean the custom_node pack failed to import at boot (check
`D:\Projects\ComfyUI\user\comfyui.log`) or class names changed upstream.

- [x] `generate_3d` / `image_to_3d` — rebuilt with real installed classes: ImageRemoveBackground→`InspyrenetRembg`, added `TripoSRModelLoader` (tripoSR.ckpt) wired into `TripoSRSampler.model`, SaveTripoSRMesh→`SaveGLB`. No import failure existed; the class names had changed. PASS.
- [x] `generate_speech` / `voice_clone` — rebuilt with TTS-Audio-Suite's real class names: `UnifiedTTSTextNode`, `F5TTSEngineNode`, `CharacterVoicesNode` (+ `RVCEngineNode`/`UnifiedVoiceChangerNode` for voice_clone). PASS. Note: F5-TTS weights auto-download (>1GB) on first GPU run.

## C. Node spec drift (newer node versions added required inputs)

- [x] `UNETLoader` — `weight_dtype` added in edit_image_kontext, generate_image_flux2, inpaint_flux_fill (values from object_info enum).
- [x] `ImageResize+` — `interpolation`, `method`, `condition` (+ `width`/`height`/`multiple_of` required by ComfyUI API despite spec defaults) added in hunyuan3d mini/turbo/v25 workflows.
- [x] `TransparentBGSession+` — `mode` (+ `use_jit`) added wherever used. Also fixed in the same pass: LTXAVTextEncoderLoader input restructure (ltx2 x2), TripoSGVAEDecoder decode params, ImageCompositeMasked x/y/resize_source, CV2InpaintTexture inpaint_method.

## D. Hygiene (warnings, not failures)

- [x] Sidecar/workflow placeholder alignment: validator normalizes type-hint prefixes and understands `prompt_template`-composed params (berserkr false positives); genuinely missing declarations added to face_id_portrait and hunyuan3d_v20_geometry_only sidecars. Zero sidecar warnings remain.
- [x] `scripts/cache/` added to .gitignore.
- [x] `tests/test_workflow_validation.py` added: structural validation of all workflows/mcp always; live object_info check under `@pytest.mark.integration`. Also revived the long-dead `test_workflows.py`/`test_smoke.py` fixtures (wrong workflows dir since initial monorepo commit). Full suite: 460 passed.
