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

## E. Kit quality — raise procedural kits to KayKit-grade

Driven by `tools/asset_generators/village_kit/QUALITY_RUBRIC.md` (deep-research:
`docs/kaykit_research.md`). Gate: `kit_quality_check.py`. Do NOT use ComfyUI;
note ComfyUI follow-ups instead. Work each kit item-by-item (village, city
medieval + occult, characters).

- [x] Add per-piece **tri-count** to `kit_pipeline.py` output and assert the
      KayKit band (20..~5659 tris) in `kit_quality_check.py`. DONE (078024e):
      pipeline/productize write `tris.json`; the gate flags out-of-band pieces
      (over-budget = MUST, under-20 = WARN). All shipped kits 44..2284 (in band).
- [ ] Add a **beveled-box / edge-bevel** helper to `kitlib` and apply to primary
      silhouette edges (KayKit's soft-catch highlight) without exploding tris.
- [ ] Add **trim helpers** (window frame, door frame + handle/hinge, roof
      ridge/eaves/gutter, base course) and apply uniformly across pieces.
- [ ] Add a **grid-quantize + base-origin pivot** pass so environment pieces snap
      seamlessly (square grid for village/city; hex option later).
- [x] **Color-atlas texturing** (design: `docs/kit_texturing_design.md`). DONE
      end-to-end (078024e + 519a470): `Kit(atlas=True)` builds a shared
      gradient+AO+pattern atlas (planks/brick/straw/stained-glass) + emission and
      per-face UV-unwraps each primitive into its swatch. `--atlas` flag now in
      `kit_pipeline`/`productize`; `save_atlas` ships a 512² master + 128² thumb
      (`atlas_color.png`/`atlas_emit.png`) and packs the image so GLB/glTF/USD/FBX
      embed it (OBJ gets a copy beside the .mtl). Verified in Blender renders +
      Godot showcases. All three spec kits (occult/village/city) reshipped in atlas
      mode and gate-PASS. (ComfyUI follow-up: optional AI atlas art / hero normal
      bakes.)
- [ ] **Modular parts decomposition** (design: `docs/kit_texturing_design.md`):
      break buildings into snap parts on the grid — wall/wall_window/wall_door/
      wall_corner, door/door_frame/window, floor/roof_slope/roof_corner/chimney,
      stairs/railing/post/beam — base-centre origins; keep whole buildings as
      pre-assembled showcases built from the parts. Main lever toward 200+ pieces.

### Atlas — RESUME HERE (handoff for post-compaction)

**Done + committed** (kitlib `Kit(atlas=True)`): shared 256² gradient+AO+emission
atlas; per-face planar-UV into colour swatches; material PATTERNS (wood planks,
brick/stone masonry, straw thatch courses); gable roofs routed through the atlas;
stained glass = multicolour leaded mosaic (blue/rose/amber/green) on `gem`/`rune`
only; `ghostfire` = plain glow (water). Chapel door rebuilt as wood doors + cross.
Proven end-to-end (kitlib → GLB → Godot). Helper scripts in scratchpad:
`build_atlas_kit.py <spec> <out>` (builds a spec's pieces in atlas mode) and
`atlas_proof.py`. Showcases: `scratchpad/show_atlas*` (ATLAS-Village/-City/
-Village-Med/-City-Med) — relaunch after edits (Godot locks the dir; close first).

**DONE (078024e + 519a470):** steps 1-4 below complete. `--atlas` wired into
kit_pipeline + productize; `save_atlas` ships 512²+128² atlas PNGs and packs for
GLB/glTF/USD/FBX embed (OBJ copy beside .mtl); separate-glTF + USD exporters
added (DAE pruned on Blender 5.0); tri-count `tris.json` + band gate; CITY
cathedral rose `ghostfire→gem`. All three spec kits (occult/village/city)
reshipped in atlas mode, `kit_quality_check` PASS (0 must), Godot showcases
rebuilt + verified.

**Remaining next steps (do in order):**
1. [x] **Legacy v1/v2 kits** — DONE (e942260). `kit_full.py` / `kit_vol2.py`
   refactored from pre-spec standalone scripts into importable specs
   (`PIECES`/`TITLE`/`AESTHETIC`, kit_vol2 also `PALETTE_OVERRIDE`/
   `EMISSION_OVERRIDE`; `_bind(kit)` adapter binds the primitive helpers at build
   time; build/render moved under `__main__`) — geometry bodies unchanged.
   `village_kit_grimforge_v1` (28 pcs) + `_v2` (23 pcs) reshipped in atlas mode,
   gate PASS. **All 5 GrimForge kit products are now atlas.**
2. The OTHER big lever: **modular parts + 200+ density** (task above).
   - [x] **Building parts system** (`kit_parts.py`, spec `kit_parts_v1.py`, product
     `parts_kit_grimforge_v1`): 21 snap-together parts on the 1-unit grid — walls
     (plain/plaster/wood/window/door/half/corner), floor/foundation, roofs
     (gable/slope/flat) + chimney, openings (door/door_arch/window), structure
     (pillar/post_beam/arch/stairs/railing), + a `house_demo` assembled from parts.
     Gate PASS. TODO toward 200+: recolour variants (stone/plaster/wood ×
     each wall), more part types (bay window, dormer, buttress, gate, well-parts),
     and splice parts into the building kits. Now 30 parts (added arch/buttress/
     bay/balcony/awning/porch/lean-to/gate) + a `house_demo` cottage that passes
     the §4b house-assembly criteria. **productize 3/4 catalog camera: DONE** —
     `HERO_VIEW="3q"` on a spec renders a corner 3/4 catalog (no more manual swap).
   - [x] Ground/path/road **tile set** (`kit_tiles.py`, `ALL_TILES`):
     cobble/flagstone/gravel/moss/mud grounds, dirt path cross/tee/end, cobble
     road straight/corner/cross/tee — grid-modular 1x1, spliced into the four
     environment kits (village v1 40, v2 35, df-village/city 24 each). New atlas
     patterns: shingle (roofs), cobble, gravel. Still TODO: building parts
     (wall/floor/door/window/roof-slope) toward 200+.
3. **beveled-box/edge-bevel** + **trim helpers** + **grid-quantize/base-pivot**
   passes (tasks above). Bevels feed the tri band already being reported.

**Known nits to polish:** thatch pattern still reads subtly on very large roof
faces (pattern fills one swatch per face — consider world-size UV tiling); tune
per-colour emission strength. (CITY cathedral rose gem swap: DONE.)
- [x] Extend `productize.py` exporters with **DAE + plain glTF** (KayKit ships
      FBX/OBJ/DAE/GLTF). DONE (078024e): added separate-glTF + USD exporters; DAE
      is best-effort and pruned at runtime because Blender 5.0 removed the Collada
      add-on entirely (no `io_scene_collada` module) — USD fills the same
      interchange role natively and the gate accepts DAE-or-USD.
- [ ] Auto-generate **per-piece gallery + hero + turntable** in `productize.py`.
- [ ] Grow each kit toward **200+ pieces**: more small props / nature /
      modular connectors + recolor variants (recolors count toward variety).
- [ ] Wire `kit_quality_check.py` into `productize.py` / CI as a build gate.
