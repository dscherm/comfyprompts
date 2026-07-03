# MV3D — Multi-View / Higher-Fidelity 2D→3D: STATUS & RESUME

**Goal:** eliminate webbed hands + loose-clothing limb-fusion at the reconstruction
stage (not prompt hacks, not LoRA retrain). Plan: `mv3d-reconstruction-plan.md`.

## UPDATE (2026-07-02 evening): TRELLIS.2 MULTI-VIEW proven end-to-end on a real character

**The Rookie (player char) shipped through the full pipeline** using TRELLIS.2
**multi-view** (front+back T-pose inputs `A_front/A_back.png`):

- **Fists-vs-spread A/B settled**: fists input → thumb + separated finger masses;
  spread input → mitten/claw collapse (confirms `project_mv_ortho_fists`). Winner:
  `Rookie_MV_fists_00001_.glb`.
- Full chain: mesh-prep (481k→48.8k faces, 1.8m, grounded) → UniRig (40 bones,
  100% weights) → stray-finger fix + full weld (23.4k verts, watertight) →
  `rename_unirig_bones.py` (19/19 role coverage) → Unity/Unreal/Blender/STL exports.
- Package: `output/final/player_char/` (committed; see its ASSET-CARD.md).
- **BUG FOUND AND FIXED — `retarget_mocap.py` (animate-ralph) was broken pipeline-wide**
  (GS1 "passing" proofs were mangled; gate rubber-stamped 99-160° misalign). Three
  stacked root causes, all fixed 2026-07-02 (see the script's docstring): (1) un-keyed
  pose locations — export baked rotations against stale last-frame locations; (2)
  rename_unirig_bones assigns .l/.r by raw ±X, anatomically MIRRORED on -Y-facing
  rigs, crossing limbs vs the anatomical Mixamo map (now auto-detected + map swapped);
  (3) FBX stub bone axes — ALIGN now uses joint-to-child-joint bind directions.
  src_z="auto" derives facing from bind poses. Validated: Rookie idle+walk, barbarian
  idle — upright, tracking, root motion works. GS1 batch re-run still pending.
- IK posing (2-bone chains on forearms) proven live in Blender; Euler-on-UniRig-bones
  remains a trap.
- Next for MV3D: texturing stage for TRELLIS geometry-only outputs; MV4 A/B
  (TRELLIS vs Hunyuan3D single-view) still open below.

## Where we are (2026-07-02)

**Strategy landed on: try higher-fidelity SINGLE-view first (TRELLIS.2), multi-view only if needed.**

### DONE
- **MV1** — models on disk: Hunyuan3D-2mv (`ComfyUI/models/diffusion_models/hy3dgen/
  hunyuan3d-dit-v2-0-mv-fast-fp16.safetensors`) AND **TRELLIS.2-4B** (16 GB,
  `ComfyUI/models/microsoft/TRELLIS.2-4B`).
- **TRELLIS.2 installed + WORKING**: `ComfyUI-Trellis2` node, all 6 CUDA extensions
  import, DINOv3 present. **It produced a real mesh** → `ComfyUI/output/Pistol_00001_.glb`
  (8.5 MB) from the test char.
- **MV3** — `workflows/mcp/trellis2_image_to_3d.json` registered; **backends fixed to
  sdpa + xformers** (flash_attn is NOT installed — see caveat).

### THE VERDICT (TRELLIS.2 single-view, first result)
- ✅ Clean high-quality mesh; **separated TOES** (topology win — thin structures work,
  unlike single-view Hunyuan3D 2.0 which webs them); **thumb separated**.
- ❌ **4 fingers fused into a mitten** — but this is **input-limited** (512px generated
  char, fingers not clearly separated), NOT a TRELLIS failure (it nailed the toes).
- Renders: scratchpad `trellis_full.png`, `hand_front.png`, `hand_persp.png` (may be gone
  after compaction — re-render from the GLB via the headless script pattern).

### NEXT STEP (was in progress, blocked)
- **MV4 A/B**: generate a **Hunyuan3D-2.0 mesh of the SAME input** (`input/trellis_test_nobg.png`)
  via `hunyuan3d_v20_geometry_only` (octree 256, 200k faces, prefix hy3d_ab), render its
  hands+toes identically, compare. Key question: does Hunyuan3D web the toes TRELLIS
  separated? **BLOCKED:** ComfyUI crashed after the heavy TRELLIS run — relaunch first.
- Then: **MV5** wire the winner into the art-to-rig reconstruction stage, OR for
  separated FINGERS try (a) higher-res/clearer-finger input, or (b) TRELLIS/Hunyuan3D
  **multi-view** (side views resolve finger gaps — Hunyuan3D-2mv is downloaded, needs
  the multi-view INPUT problem solved; see plan MV2 — the SDXL multiview_full_body tool
  garbled, no novel-view synth installed).

## CRITICAL ENV NOTES (don't relearn these)
- **ComfyUI MUST run on the venv python** (`D:\Projects\ComfyUI\run_3090ti.ps1` uses
  `venv\Scripts\python.exe`). An automated `Start-Process` relaunch grabbed the SYSTEM
  python once (no xformers → same flash_attn error). If ComfyUI is down, relaunch via
  run_3090ti.ps1.
- **torch/xformers**: env is torch **2.9.1+cu126** + **xformers 0.0.33.post2**. Do NOT
  `pip install xformers` plain (pulls 0.0.35 → upgrades torch to 2.12 → breaks the CUDA
  extensions' ABI). Recovery = pin torch + let pip resolve xformers, all from the cu126
  index. See memory `project_comfyui_torch_xformers_pin`.
- **TRELLIS backends**: `Trellis2LoadModel` → `backend=sdpa`, `sparse_backend=xformers`
  (flash_attn not installed; sparse stage has no sdpa option).
- **run_workflow gotcha**: pass the image override explicitly
  (`overrides={"PARAM_STR_IMAGE_PATH":"..."}`) — no-override leaves the placeholder
  literal. The registered MCP tool's run_workflow path is NOT yet verified end-to-end
  (TRELLIS proven via the example UI workflow instead) — re-verify on resume.
- **User preference**: run/watch heavy 3D gen in the ComfyUI UI, not blind via MCP
  (memory `feedback_watch_heavy_gen_in_comfyui`).

## Key paths
- TRELLIS mesh: `ComfyUI/output/Pistol_00001_.glb`
- Test input (RGBA cutout): `ComfyUI/input/trellis_test_nobg.png`
- Registered tool: `workflows/mcp/trellis2_image_to_3d.json` (backends sdpa/xformers)
- TRELLIS example workflows: `ComfyUI/custom_nodes/ComfyUI-Trellis2/example_workflows/MeshOnly*.json`
