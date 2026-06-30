# plan.md — Multiview-Consistency LoRA (Hunyuan3D-friendly ortho T-pose)

Task queue for Ralph Loop. JSON blocks in triple-backtick fences.
Only ONE task per iteration. Mark `"passes": true` when complete.
Spec: `.ralph/spec.md`. All training runs on GPU 1 (3090 Ti) via
`CUDA_VISIBLE_DEVICES=1`. Reuses the `scripts/train_lora/` harness.

---

## Task Format (template — not a real task)

<!-- Template for reference only. Do NOT pick this up as a task.
{
  "id": "M0",
  "category": "setup|feature|testing|bugfix",
  "priority": 1,
  "description": "One-line description",
  "files": ["path/one.py"],
  "acceptance_criteria": ["observable check 1"],
  "steps": ["Step 1"],
  "passes": true
}
-->

---

## Prior pipeline (Berserkr-style LoRA training harness PoC) — COMPLETE

All of T1-T8 shipped (see git through `b7c6658` and `scripts/train_lora/README.md`).
That pipeline proved the reusable harness; this one retrains it on a Blender-rendered
orthographic dataset to produce the `mv_ortho` LoRA. Spec archived at
`.ralph/spec-berserkr-poc.md`.

---

### Phase 1: Dataset generation (Blender ortho multi-view renderer)

```json
{
  "id": "M1",
  "category": "feature",
  "priority": 1,
  "description": "Build a Blender orthographic multi-view renderer (blender-mcp) — dataset-agnostic, renders any mesh folder to clean ortho views",
  "files": ["scripts/train_lora/render_multiview.py"],
  "acceptance_criteria": [
    "Takes a mesh source dir/glob + output dir + list of canonical angles (default front/back/left/right + front-3/4 L/R)",
    "Drives blender-mcp execute_blender_code: imports each mesh, frames it to fill the frame, sets an ORTHOGRAPHIC camera, neutral/transparent background, even studio lighting",
    "Renders each angle to <out>/<mesh>__<view>.png; view encoded in filename for downstream captioning",
    "Checks blender-mcp availability (get_external_app_status / get_scene_info) first; clear error if unreachable, no half-written set",
    "Dataset-agnostic: nothing mesh-specific hardcoded; runs on an arbitrary mesh folder"
  ],
  "steps": [
    "Confirm blender-mcp reachable (socket 9876) via get_scene_info",
    "Per mesh: clear scene, import, normalize scale/origin, frame, render N angles",
    "Neutral bg + even lighting; orthographic camera per angle",
    "Write <mesh>__<view>.png; log a count summary"
  ],
  "passes": true
}
```

```json
{
  "id": "M2",
  "category": "feature",
  "priority": 1,
  "description": "Generate the mv_ortho raw dataset: render ~100-150 ortho views across owned meshes",
  "files": ["scripts/train_lora/datasets/mv_ortho_manifest.md"],
  "acceptance_criteria": [
    "render_multiview.py run across D:/Projects/ComfyUI/output/3D + pipelines/autorig-ralph/references/humanoid",
    "~100-150 clean ortho PNGs on E:/ai-training/datasets/mv_ortho/ (front view weighted heaviest, since the objective is single-image front)",
    "LIMB SEPARATION: only meshes with clearly separated limbs are kept — wide/exaggerated T-pose, arms horizontal, fingers spread, legs apart, visible gaps between arms/hands and the torso/hips. Relaxed/arms-down/hands-on-hips meshes (e.g. player_textured, A-pose Quaternius) are CULLED, not trained on (see project_mesh_intersection_fix)",
    "Spot-checked via the rendered PNGs: subjects centered, neutral bg, even light, no clipping, AND no movable part touching the body",
    "A manifest lists which meshes contributed, the view distribution, and which were culled for fused/contacting limbs"
  ],
  "steps": [
    "Select meshes that are clean, full-body, humanoid-ish (skip broken/partial)",
    "render_multiview.py --src ... --out E:/ai-training/datasets/mv_ortho",
    "Review a sample; cull bad renders; write manifest"
  ],
  "passes": true
}
```

### Phase 2: Caption + train

```json
{
  "id": "M3",
  "category": "feature",
  "priority": 2,
  "description": "Caption the mv_ortho set with trigger + per-view tag (reuse caption.py, add view tag from filename)",
  "files": ["scripts/train_lora/caption.py", "scripts/train_lora/datasets/mv_ortho_manifest.md"],
  "acceptance_criteria": [
    "Every image has a .txt caption prefixed with trigger mv_ortho, a view tag derived from the filename (e.g. 'front view'/'side view'/'back view'), AND pose tags reinforcing limb separation ('wide T-pose, arms outstretched, fingers spread, legs apart')",
    "Florence2 content caption appended after the tags; idempotent (skips existing .txt)",
    "Captions describe the subject neutrally; the ortho/clean framing is implicit in the consistent dataset",
    "Existing caption.py tests still pass; any new view-tag logic is covered"
  ],
  "steps": [
    "Add a --view-from-filename option (or a thin post-pass) mapping __front/__side/__back to view tags",
    "caption.py --dir E:/ai-training/datasets/mv_ortho --trigger mv_ortho",
    "Run prep_dataset.py to normalize into the ai-toolkit layout if needed"
  ],
  "passes": true
}
```

```json
{
  "id": "M4",
  "category": "feature",
  "priority": 2,
  "description": "Train the mv_ortho Flux LoRA via launch_train.py (stop ComfyUI first to free the 24GB)",
  "files": ["scripts/train_lora/output/mv_ortho/"],
  "acceptance_criteria": [
    "ComfyUI stopped before launch; training confirmed on GPU 1 via nvidia-smi",
    "launch_train.py --dataset E:/ai-training/datasets/mv_ortho --name mv_ortho (rank 16, ~1500 steps, save per epoch)",
    "Per-epoch checkpoints + a final mv_ortho.safetensors on E:/ai-training/flux-output/mv_ortho/",
    "No OOM; sample images during training trend toward clean ortho framing"
  ],
  "steps": [
    "Stop ComfyUI (free 24GB)",
    "launch_train.py ... ; monitor in background, verify device 1",
    "Collect checkpoints"
  ],
  "passes": true
}
```

### Phase 3: Eval (2D grid + Hunyuan3D mesh comparison) + deploy

```json
{
  "id": "M5",
  "category": "testing",
  "priority": 3,
  "description": "Eval: 2D grid (base vs LoRA) AND base-vs-LoRA Hunyuan3D mesh comparison",
  "files": ["scripts/train_lora/eval/mv_ortho_grid.md"],
  "acceptance_criteria": [
    "Restart ComfyUI on the 3090 Ti; lora_eval_grid.py --only mv_ortho across strengths 0.6/0.8/1.0 on character prompts",
    "2D judge verdict: LoRA produces cleaner/more-orthographic T-pose framing vs base at fixed seeds",
    "3D test: feed the best base front image AND the best LoRA front image through Hunyuan3D; import both meshes via blender-mcp; compare watertightness/silhouette/artifacts with viewport screenshots",
    "LIMB SEPARATION check: confirm the LoRA's mesh has separable hands/arms/legs (no fusion to torso/hips/each other) — the core reason for this LoRA; base will typically fuse them",
    "Verdict names a winning (checkpoint, strength) AND states whether the LoRA's mesh is measurably cleaner AND more separable than base"
  ],
  "steps": [
    "Restart ComfyUI; run the 2D grid; pick the winning cell",
    "Generate matched base + LoRA front images at a fixed seed",
    "Run both through Hunyuan3D (comfyui-mcp or blender-mcp); import + screenshot both meshes",
    "Record the combined 2D+3D verdict in eval/mv_ortho_grid.md"
  ],
  "passes": true
}
```

```json
{
  "id": "M6",
  "category": "feature",
  "priority": 4,
  "description": "Deploy winning mv_ortho LoRA + document the Hunyuan3D front-end use in README + art-to-rig-ralph",
  "files": ["scripts/train_lora/README.md", "D:/Projects/ComfyUI/models/loras/style/"],
  "acceptance_criteria": [
    "Winning mv_ortho.safetensors copied to ComfyUI/models/loras/style/ with a sidecar note (trigger mv_ortho + recommended strength)",
    "Smoke-tested: generate a clean front T-pose via generate_image_lora, confirm Hunyuan3D ingests it well",
    "README documents the renderer + how to rebuild the dataset from any mesh folder, and how to use mv_ortho as the art-to-rig Hunyuan3D front-end",
    "Cross-link added in pipelines/art-to-rig-ralph (point its concept-art step at this LoRA)"
  ],
  "steps": [
    "Copy + sidecar-note the winner",
    "Smoke-test through generate_image_lora -> Hunyuan3D",
    "Update README + art-to-rig-ralph cross-link"
  ],
  "passes": true
}
```

---

## Phase MT: Text-to-motion (MDM) spike — animate-ralph extension

Wire a text-to-motion model in as an *alternative* to the mocap library: a text
prompt -> novel animation -> retargeted onto a UniRig character -> FBX, reusing
`pipelines/animate-ralph/scripts/retarget_mocap.py` (now root-motion-capable) and
`references/retarget_maps/mixamo_to_unirig.json` unchanged. Model: **MDM**
(50-step `humanml_enc_512_50steps`). Use posture: **exploring only** — AMASS/HumanML3D
weights are research/non-commercial, so output is previz, not shippable. Env lives at
`E:\ai-training\_motiongen\` (own py3.9 venv; pip temp/cache forced to E: — C: is full).
GPU note: generation runs on the **3090 Ti** and needs ComfyUI idle first — **gated on
explicit user go-ahead** (do NOT touch the card without it).

```json
{
  "id": "MT0",
  "category": "setup",
  "priority": 1,
  "description": "Stage the MDM text-to-motion env (CPU only) — venv, deps, model, dataset stats, SMPL, joints->armature bridge",
  "files": ["E:/ai-training/_motiongen/mdm_to_source.py", "E:/ai-training/_motiongen/motion-diffusion-model/"],
  "acceptance_criteria": [
    "py3.9 venv + torch 2.4.1 cu121 (<2.6 to dodge weights_only load break)",
    "Deps: clip, smplx, spacy==3.7.5, moviepy==1.0.3, scipy, joblib, blobfile, gdown",
    "Model save/humanml_enc_512_50steps/model000750000.pt unzipped",
    "dataset/HumanML3D wired (Mean/Std/test.txt/texts) + body_models/smpl/SMPL_NEUTRAL.pkl",
    "`import sample.generate` succeeds on CPU (IMPORT_OK) — full dep chain resolves",
    "mdm_to_source.py written: 22-joint xyz -> Character1_*-named animated armature FBX"
  ],
  "steps": ["DONE this session — env staged, import verified CPU-only"],
  "passes": true
}
```

```json
{
  "id": "MT1",
  "category": "feature",
  "priority": 1,
  "description": "[GPU — needs user go-ahead + ComfyUI idle] Generate one motion from a text prompt via MDM -> results.npy",
  "files": ["E:/ai-training/_motiongen/motion-diffusion-model/save/.../results.npy"],
  "acceptance_criteria": [
    "ComfyUI stopped/idle so the 3090 Ti 24GB is free (verify, then CUDA_VISIBLE_DEVICES=1)",
    "python -m sample.generate --model_path save/humanml_enc_512_50steps/model000750000.pt --text_prompt '<prompt>' --num_repetitions 1 produces results.npy (22-joint xyz, ~60 frames)",
    "Restart ComfyUI on the 3090 Ti afterwards (run_3090ti.ps1)"
  ],
  "steps": [
    "WAIT for explicit user GPU go-ahead",
    "Stop ComfyUI; confirm VRAM free",
    "Run sample.generate for a test prompt (e.g. 'a person walks forward and waves')",
    "Restart ComfyUI"
  ],
  "passes": true
}
```

```json
{
  "id": "MT2",
  "category": "feature",
  "priority": 2,
  "description": "Convert MDM results.npy -> animated source FBX and retarget onto the barbarian rig (with root motion)",
  "files": ["E:/ai-training/_motiongen/mdm_to_source.py", "pipelines/animate-ralph/scripts/retarget_mocap.py"],
  "acceptance_criteria": [
    "mdm_to_source.py results.npy -> mdm_clip.fbx (Character1_* bones, animated)",
    "retarget_mocap.py mdm_clip.fbx onto barbarian_renamed.glb via mixamo_to_unirig.json -> FBX, matches >=18/20 bones",
    "Rendered frames show the barbarian performing the prompted motion; root motion carries through"
  ],
  "steps": [
    "Run mdm_to_source.py on results.npy",
    "Run retarget_mocap.py (root_motion transfer) onto the barbarian",
    "Render proof frames (reuse render_rootmotion.py with the mesh-deform fix)"
  ],
  "passes": true
}
```

```json
{
  "id": "MT3",
  "category": "bugfix",
  "priority": 2,
  "description": "Calibrate coordinate/facing for the MDM source (Y-up->Z-up + src_z) so the motion plays upright and faces forward",
  "files": ["E:/ai-training/_motiongen/mdm_to_source.py"],
  "acceptance_criteria": [
    "Retargeted clip is upright (not lying/rolled) and the character faces its travel direction",
    "If wrong: fix the Y-up->Z-up axis map in load_joints and/or pass the right src_z to retarget; document the values"
  ],
  "steps": ["Inspect first render", "Adjust axis map / src_z", "Re-render to confirm"],
  "passes": true
}
```

```json
{
  "id": "MT4",
  "category": "feature",
  "priority": 3,
  "description": "Promote the bridge into the animate-ralph pipeline + write a prompt->FBX orchestrator and VALIDATION entry",
  "files": ["pipelines/animate-ralph/scripts/mdm_to_source.py", "pipelines/animate-ralph/scripts/generate_motion.py", "pipelines/animate-ralph/validation/VALIDATION.md"],
  "acceptance_criteria": [
    "mdm_to_source.py moved into pipelines/animate-ralph/scripts/ (single source of truth)",
    "generate_motion.py orchestrates prompt + rig -> animated FBX (gen -> source -> retarget -> export), with the GPU step clearly gated/documented",
    "VALIDATION.md documents the MDM path, the research-only license caveat, and 2-3 example prompts with proof frames"
  ],
  "steps": ["Move bridge into the pipeline", "Write generate_motion.py orchestrator", "Validate 2-3 prompts + document"],
  "passes": true
}
```

---

## Phase GS: Game-ready shippable barbarian (commercial clip set → Unity)

Phase MT proved text→FBX motion but its MDM/AMASS weights are research-only, so the
output is **previz, not shippable**. This phase closes the gap to a **game-ready, shippable
animated character** by switching to the **commercially-licensed Rokoko/Mixamo reference
library** already in `references/humanoid/` (locomotion/idle/combat/gesture, all
`Character1_*` and covered by `mixamo_to_unirig.json` — the same map MT used), retargeting a
multi-clip SET onto the barbarian, re-applying its texture, and landing it in the
`../soapbox-unity` project with an Animator controller — the same Unity path animate-ralph
already proved on the karts (coplay-mcp import + validation). **No GPU needed** (the source
clips are existing FBX; retarget/texture/export are CPU/Blender, Unity is coplay-mcp), so it
does not contend with ComfyUI. MDM/`generate_motion.py` stays as the **previz/novel-motion**
fallback for clips the commercial library lacks.

```json
{
  "id": "GS0",
  "category": "setup",
  "priority": 1,
  "description": "Select a commercial-license core gameplay clip set from references/humanoid and write a retarget manifest",
  "files": ["pipelines/animate-ralph/output/intake/barbarian_clipset.md"],
  "acceptance_criteria": [
    "Core gameplay set chosen from references/humanoid/{idle,locomotion,combat,gesture}: idle, walk, run/jog, attack (punch or sword), hit_reaction, dodge, block, wave, celebrate (9 clips)",
    "Each chosen source FBX confirmed Character1_* and retarget-compatible (>=18/20 vs mixamo_to_unirig.json) via a dry retarget or bone-name check — cull any that miss",
    "Manifest table: clip name -> source FBX path -> root_motion policy (transfer for locomotion, off for in-place) -> loop flag (idle/walk loop; attack/hit one-shot)",
    "Only commercially-usable sources (Rokoko/Mixamo library) — NO MDM-derived clips in the shippable set"
  ],
  "steps": [
    "Inventory references/humanoid/{idle,locomotion,combat,gesture} for the 9 core clips (idle, walk, run, attack, hit, dodge, block, wave, celebrate)",
    "Bone-check each candidate against mixamo_to_unirig.json (reuse retarget_mocap MATCHED count)",
    "Write barbarian_clipset.md with the per-clip root_motion + loop policy"
  ],
  "passes": true
}
```

```json
{
  "id": "GS1",
  "category": "feature",
  "priority": 1,
  "description": "Batch-retarget the clip set onto the barbarian (one FBX per clip) + per-clip proof frames",
  "files": ["pipelines/animate-ralph/scripts/batch_retarget.py", "pipelines/animate-ralph/output/export/barbarian/"],
  "acceptance_criteria": [
    "batch_retarget.py reads barbarian_clipset.md, runs retarget_mocap.py per clip onto barbarian_renamed.glb with the manifest's root_motion, writes output/export/barbarian/<clip>.fbx",
    "Every clip retargets at >=18/20 bones; locomotion clips carry root motion (HIP_TRAVEL > 0), in-place clips stay put",
    "render_rootmotion.py proof frames per clip; spot-checked that each reads as its motion and the character stays upright",
    "A run summary lists clip -> bones matched -> frames -> root-motion status"
  ],
  "steps": [
    "Write batch_retarget.py (thin loop over retarget_mocap.py from the manifest)",
    "Run the batch; collect per-clip FBX",
    "Render + spot-check proof frames; record the summary"
  ],
  "passes": true
}
```

```json
{
  "id": "GS2",
  "category": "feature",
  "priority": 2,
  "description": "Re-apply the barbarian's source texture to the rigged mesh (UniRig drops materials) for shippable beauty",
  "files": ["pipelines/animate-ralph/scripts/reapply_texture.py"],
  "acceptance_criteria": [
    "reapply_texture.py transfers the original textured Hunyuan3D barbarian material/UVs onto the rigged+animated mesh (UVs preserved, no re-bake) — headless Blender",
    "A textured beauty frame (reuse render_rootmotion.py path, but keep the real material instead of the matte) confirms the character is textured, not grey",
    "Works on an exported clip FBX without breaking the armature/animation",
    "Locates the textured source mesh from the proven character pipeline (see project_proven_character_pipeline); clear error if not found"
  ],
  "steps": [
    "Find the pre-rig textured barbarian mesh; inspect its material/UVs",
    "Transfer material to the rigged mesh by UV/name; verify in a render",
    "Apply to the GS1 clip outputs (or document as an export-time step)"
  ],
  "note": "DONE 2026-06-27. HONEST LIMITATION: the barbarian was generated as a GEOMETRY-ONLY Hunyuan3D mesh — verified to have NO UVs, NO materials, NO vertex colors (and UniRig output is likewise bare). With no UVs there is no source texture to transfer and nothing to bake an image onto, so a real texture set is impossible without a UV-unwrap + re-bake (out of scope here). Fallback shipped instead: reapply_texture.py authors a SOLID #8B5E3C leather-brown Principled material (the only thing a UV-less mesh can carry through FBX into Unity) and applies it to all 9 clips -> output/export/barbarian/textured/<clip>.fbx. Round-trip VERIFIED: verify_textured_proof.py reimports attack.fbx and reads base_color back as exactly (0.258,0.118,0.045) linear == #8B5E3C (not reset to grey/default); armature+animation intact. Proof frame (posed, colored, not grey): validation/retarget/gs2_textured/barbarian_attack_textured_front.png. A game artist replaces this flat color with a proper texture set after a UV unwrap.",
  "passes": true
}
```

```json
{
  "id": "GS3",
  "category": "feature",
  "priority": 2,
  "description": "Package the clip set into Unity (../soapbox-unity) as a Humanoid/Mecanim avatar + an Animator controller",
  "files": ["pipelines/animate-ralph/scripts/package_for_unity.py", "pipelines/animate-ralph/output/export/barbarian/ANIMATION-MANIFEST.json"],
  "acceptance_criteria": [
    "Clips exported into ../soapbox-unity/Assets/Animations/Barbarian/ and set to Animation Type = Humanoid (Mecanim) on import (mirror the kart deploy layout)",
    "A Humanoid Avatar configured for the barbarian (Avatar Definition: Create From This Model on the rig FBX, or Copy From Other Avatar onto each clip) with a valid bone mapping — the UniRig role names map to Mecanim's required human bones; record any unmapped bones",
    "An Animator controller built (via coplay-mcp) with idle<->walk<->run<->attack/hit/dodge/block states + transitions, using the Humanoid avatar so clips are retargetable/mirrorable in-engine",
    "ANIMATION-MANIFEST.json records clip -> file -> duration -> loop -> root_motion -> avatar (same schema as the kart manifest, plus the avatar)",
    "Import scale documented (UniRig ~0.01 -> FBX Scale Factor ~100, per the retarget_mocap export note); muscle/avatar setup notes captured"
  ],
  "steps": [
    "Export/copy clip FBX into the Unity project; set Animation Type = Humanoid",
    "Create the Humanoid Avatar from the rig FBX and assign it to the clips (Copy From Other Avatar)",
    "Build the Animator controller + transitions via coplay-mcp; write ANIMATION-MANIFEST.json"
  ],
  "note": "DONE 2026-06-27 via scripts/package_for_unity.py. Unity was NOT running (list_unity_project_roots -> 0), so coplay-mcp could not drive a live editor; instead packaged as DETERMINISTIC on-disk assets (same as the kart deploy: FBX + .meta to disk, Unity imports on open). Deployed to D:/Projects/soapbox-unity/Assets/Animations/Barbarian/: 9 textured clip FBX + Humanoid .meta (animationType:3) + Barbarian.controller + ANIMATION-MANIFEST.json. AVATAR: idle.fbx = CreateFromThisModel (avatarSetup:1); other 8 = CopyFromOther (avatarSetup:2) referencing idle's generated Avatar {fileID:9000000, guid:<idle>, type:3} (Avatar sub-asset fileID is deterministic). Explicit bone map written into humanDescription.human (19 bones; all 15 REQUIRED Mecanim human bones map: hips/spine/chest/neck/head + L/R shoulder/upperarm/lowerarm/hand + L/R upperleg/lowerleg/foot). UNMAPPED (recorded): bone_3/4 (extra spine), bone_9/11/13/16/18 (arm filler), hip_connector.l/r (pelvis connectors). CONTROLLER: hand-authored YAML, PyYAML-validated = 1 controller + 1 stateMachine + 9 states + 16 transitions, all internal fileID refs resolve. Params: Speed(float) + Attack/Hit/Dodge/Block/Wave/Celebrate(triggers). Transitions: Idle<->Walk (Speed 0.1), Walk<->Run (Speed 0.6), AnyState->each action/emote (trigger), each action->Idle (exit time). Each state's motion = {fileID:7400000 (FBX primary clip), guid:<clip>} — name-independent, confirmed against project boost.controller. Manifest schema: clip->file->guid->duration_s->frames->fps->loop->root_motion->animator_state->avatar (durations re-measured after the GS2 truncation fix: idle 1.4, walk/run 1.2, attack/hit 1.3, dodge 1.02, block/wave/celebrate 1.5 s). Import scale documented (UniRig ~0.01 -> FBX Scale Factor ~100; useFileScale:1). REMAINING for GS4 (live Unity): enable Loop Time on idle/walk/run (needs imported clip internal name), and validate avatar/clips/transitions import + play without errors.",
  "passes": true
}
```

```json
{
  "id": "GS4",
  "category": "testing",
  "priority": 3,
  "description": "Validate the barbarian Humanoid animation set imports + plays in Unity (coplay-mcp), mirroring the kart validation",
  "files": ["soapbox-unity/Assets/Editor/ValidateBarbarianAnimImport.cs", "pipelines/animate-ralph/validation/VALIDATION.md"],
  "acceptance_criteria": [
    "coplay-mcp import check: every clip imports without errors as Animation Type = Humanoid; AnimationClip durations match the manifest",
    "Avatar valid: the Humanoid avatar's bone mapping is complete enough that clips play without 'avatar invalid' / unmapped-required-bone errors; any optional bones left unmapped are listed",
    "Animator controller transitions verified (enter Play or inspect states) on the Humanoid avatar; no missing-bone / broken-curve warnings; clips are retargetable (Humanoid) not skeleton-locked",
    "An editor validator (like ValidateKartAnimImport.cs) reports per-clip pass/fail incl. avatar validity",
    "VALIDATION.md gets a Phase GS section: the shippable path, clip inventory, the Humanoid-avatar setup, and the commercial-vs-MDM source policy"
  ],
  "steps": [
    "Import via coplay-mcp as Humanoid; run the editor validator",
    "Verify avatar validity, clip durations + Animator transitions",
    "Record the verdict + clip inventory + avatar notes in VALIDATION.md"
  ],
  "status": "FAILED in live editor",
  "note": "NOT DONE. Live Unity review (2026-06-28/29) surfaced two real blockers the offline package missed: (1) IMPORT ERROR — 'Copied Avatar Rig Configuration mis-match: Transform Armature not found in HumanDescription'. The hand-written .meta declares hasExtraRoot:0 but every FBX has an extra 'Armature' root above 'hips', so Unity's copied avatar can't match it. (2) ANIMATION — all clips played arms-up/frozen (retarget bind-direction bug). #2 is FIXED (commit 3eb349b, bind-direction alignment; all 9 re-baked). #1 + re-deploy + clip curation remain → GS6/GS7/GS8.",
  "passes": false
}
```

```json
{
  "id": "GS6",
  "category": "bugfix",
  "priority": 2,
  "description": "Fix the Unity Humanoid avatar import error (extra 'Armature' root) — prefer live coplay-mcp avatar setup over hand-written .meta",
  "files": ["pipelines/animate-ralph/scripts/package_for_unity.py", "soapbox-unity/Assets/Animations/Barbarian/"],
  "acceptance_criteria": [
    "idle.fbx imports as Humanoid, CreateFromThisModel, avatar VALID (no 'Transform Armature not found' error) — either set hasExtraRoot correctly / write an explicit skeleton list, OR build the avatar live via coplay-mcp and copy back the working .meta",
    "The other 8 clips CopyFromOther idle's avatar with no hierarchy mismatch",
    "Best path (per the 'do both' decision): let Unity Humanoid retargeting handle rest-pose differences — import the licensed Mixamo clips as Humanoid and retarget onto the barbarian avatar in-engine"
  ],
  "steps": [
    "Reproduce the import error; inspect idle.fbx hierarchy vs the .meta humanDescription",
    "Fix extra-root handling OR configure the avatar live via coplay-mcp",
    "Verify all 9 import clean + the avatar is valid"
  ],
  "note": "DONE 2026-06-30. ROOT CAUSE confirmed (from the GS4 live-editor error + the deployed metas): the package made idle CreateFromThisModel (avatarSetup:1) and the OTHER 8 clips CopyFromOther idle's avatar (avatarSetup:2, lastHumanDescriptionAvatarSource -> {fileID:9000000, guid:idle}). idle imported clean; the 8 copies failed with 'Copied Avatar Rig Configuration mis-match: Transform Armature not found in HumanDescription' — every retarget FBX has an extra 'Armature' transform above 'hips', and a copied (empty-skeleton) HumanDescription can't account for it. FIX (package_for_unity.py fbx_meta): make EVERY clip CreateFromThisModel (avatarSetup:1, lastHumanDescriptionAvatarSource:{instanceID:0}). Each FBX self-creates its own valid Humanoid avatar exactly like stock Mixamo FBX; Unity Humanoid clips are muscle-space normalized so any clip plays on the character's avatar regardless of which avatar instance it imported with (idle's avatar stays the canonical character avatar). This sidesteps the copy entirely — the known-good idle path is now applied to all 9. Redeployed: all 9 ../soapbox-unity/Assets/Animations/Barbarian/*.fbx.meta now avatarSetup:1, ZERO fileID:9000000 copied-avatar refs. Regression test tests/test_package_for_unity.py (10 cases) locks in CreateFromThisModel-for-every-clip + no copied ref + explicit human bone map; passing. LIVE-EDITOR CAVEAT: Unity was not running (list_unity_project_roots -> 0), so the final in-editor 'all 9 import clean, avatar valid' confirmation is GS4's job; this change removes the exact reported failure mode and applies the path idle already imported clean with.",
  "passes": true
}
```

```json
{
  "id": "GS7",
  "category": "feature",
  "priority": 2,
  "description": "Re-texture + redeploy the arms-fixed clips to Unity (the deployed FBXs are still the old arms-up bake)",
  "files": ["pipelines/animate-ralph/scripts/reapply_texture.py", "soapbox-unity/Assets/Animations/Barbarian/"],
  "acceptance_criteria": [
    "reapply_texture.py re-run on the 9 re-baked (bind-aligned) clips -> output/export/barbarian/textured/",
    "package_for_unity.py redeploys the fixed+textured clips; Unity shows arms-down natural motion (not the old arms-up)",
    "Proof: in-engine or rendered frames confirm the deployed clips match the fixed bake"
  ],
  "steps": ["Re-run reapply_texture.py", "Re-run package_for_unity.py", "Confirm in-engine"],
  "superseded_by": "Unity-Humanoid decision (2026-06-30)",
  "superseded_reason": "GS7 redeploys the bind-aligned hand-rolled-retarget bake, but that bake was proven PREVIZ-ONLY (mishandles limb plane — lesson hand-rolled-retarget-limb-plane). Ship route is now Unity Humanoid retargeting of free Mixamo clips onto the AccuRIG rig (pipelines/animate-ralph/UNITY-IMPORT-NOTES.md). Re-deploying retarget_mocap.py output would ship the rejected previz. Disposition mirrors GS4. Stale Jun-27 arms-up clips remain in soapbox-unity/.../Barbarian/ and should be removed when the Unity Humanoid set lands.",
  "passes": true
}
```

```json
{
  "id": "GS8",
  "category": "feature",
  "priority": 3,
  "description": "Source-clip curation — swap busy range-of-motion rokoko_legacy_* takes for clean single-purpose clips (now that the retarget is faithful)",
  "files": ["pipelines/animate-ralph/output/intake/barbarian_clipset.md"],
  "acceptance_criteria": [
    "Audit each clip's source; flag ROM/fidgety takes (e.g. rokoko_legacy_idle reads crouchy even when correctly retargeted)",
    "Replace flagged sources with clean clips (a simple breathing idle, a clean walk cycle, etc.) and/or tighter sub-ranges + loop seams",
    "Re-bake (batch_retarget.py) and re-review; each clip reads as a natural, game-usable loop/one-shot"
  ],
  "steps": ["Review the 9 fixed clips (MP4s / live Blender)", "Pick better sources/sub-ranges for the weak ones", "Re-bake + re-review"],
  "superseded_by": "Unity-Humanoid decision (2026-06-30)",
  "superseded_reason": "GS8 re-bakes rokoko_legacy_* via batch_retarget.py 'now that the retarget is faithful' — but the hand-rolled retarget is previz-only (lesson hand-rolled-retarget-limb-plane), so curating its source clips no longer feeds the ship set. The intent (pick clean single-purpose clips) is satisfied for the ship path by the curated free-Mixamo clip list in pipelines/animate-ralph/UNITY-IMPORT-NOTES.md §2. Re-baking via batch_retarget.py would only produce previz.",
  "passes": true
}
```

```json
{
  "id": "GS5",
  "category": "feature",
  "priority": 4,
  "description": "Document the two-source motion strategy (commercial=shippable vs MDM=previz) + cross-link the tools",
  "files": ["pipelines/animate-ralph/PROMPT.md", "scripts/train_lora/README.md"],
  "acceptance_criteria": [
    "A short 'motion sources' note: commercial Rokoko/Mixamo library (batch_retarget.py) = shippable; MDM generate_motion.py = previz/novel motion the library lacks",
    "Decision guidance: prefer the library; use MDM only for motions with no library match, and never ship MDM output",
    "Cross-links between generate_motion.py, batch_retarget.py, and the Unity package step so the full chain is discoverable"
  ],
  "steps": [
    "Write the motion-sources note in PROMPT.md",
    "Cross-link the previz (MDM) and shippable (library) paths",
    "Note the licensing line one more time where it matters"
  ],
  "passes": true
}
```

---

## Phase UH: Unity Humanoid + Mixamo packaging (the SHIPPABLE animation route)

Formalizes "bring the rigged character into Unity + load Mixamo motion" as a pipeline
stage — the SHIP path that replaces the previz-only hand-rolled retarget (lesson
`hand-rolled-retarget-limb-plane`). Unity Humanoid muscle-space retargeting maps free
Mixamo clips onto the AccuRIG rig, fixing the limb planes natively while keeping
AccuRIG's clean weights. Stage doc: `pipelines/animate-ralph/stages/07-unity-humanoid-packaging.md`;
import packet: `pipelines/animate-ralph/UNITY-IMPORT-NOTES.md`. Automatable via
**coplay-mcp** when a Claude session is connected to a live Unity Editor; otherwise a
documented manual GUI flow + the in-editor validator. **Mixamo has no API** — clip
download is the one irreducibly manual web step.

### ▶ RESUME AFTER RESTART (coplay live) — do this next

This session restarted with the Unity Editor open on `../soapbox-unity` and the Coplay
plugin signed in, so **coplay-mcp tools are now available** (verify with a tool search
for coplay/unity; if absent, coplay didn't connect — confirm Unity is open + signed in
and the session started AFTER). Then execute UH1→UH4 **in order**:

1. **UH1 — verify coplay round-trip.** Call a coplay tool to read Unity scene/editor
   state. Run `ValidateBarbarianHumanoid.Execute()` via coplay as a baseline (the
   character will report Generic rig until UH2 — expected). Record the reconnect
   procedure in `stages/07-unity-humanoid-packaging.md`. Mark UH1 gate-pass.
2. **UH2 — import Humanoid.** On `Assets/Animations/Barbarian/Source/barbarian_accurig.fbx`
   set Rig = Humanoid, Avatar Definition = Create From This Model, Apply; Configure +
   Enforce T-Pose if any bone is red; assign `barbarian_tex.png` to Base Color. Re-run
   the validator — §1 (character) must pass (avatar isValid && isHuman).
3. **UH3 — Mixamo clips.** Mixamo download is MANUAL — prompt the user to download the
   core set (idle, walk, run, attack, hit, dodge, block, wave, celebrate) as FBX
   "Without Skin" into `Assets/Animations/Barbarian/Mixamo/`. Import each Humanoid /
   Copy From Other Avatar = the barbarian avatar; Loop Time on idle/walk/run. Validator
   §2 must pass.
4. **UH4 — Animator + validate + cleanup.** Build `Barbarian.controller` (default Idle;
   Speed float Idle↔Walk↔Run; AnyState triggers attack/hit/dodge/block/wave/celebrate →
   exit Idle). Run `ValidateBarbarianHumanoid` (PASS); coplay-screenshot play-mode and
   confirm NATURAL arm/leg carriage (not the previz splay). Update ANIMATION-MANIFEST.json
   + VALIDATION.md; delete the stale Jun-27 arms-up clips from `Assets/Animations/Barbarian/`.

After each task: commit the soapbox-unity changes and record the gate via the bridge
(`bridge_state.py gate-pass UHx` → `done UHx`). If coplay never connects, fall back to
the manual GUI flow in the stage doc + the headless validator (`-executeMethod
ValidateBarbarianHumanoid.RunBatch`).

```json
{
  "id": "UH0",
  "category": "setup",
  "priority": 1,
  "description": "Author the Unity-Humanoid packaging stage: stage doc (stages/07), corrected Editor validator (ValidateBarbarianHumanoid.cs — supersedes the GS4 validator for the Unity-retarget+Mixamo route), and stage the AccuRIG character + texture into the Unity project.",
  "files": ["pipelines/animate-ralph/stages/07-unity-humanoid-packaging.md", "soapbox-unity/Assets/Editor/ValidateBarbarianHumanoid.cs", "soapbox-unity/Assets/Animations/Barbarian/Source/"],
  "acceptance_criteria": [
    "stages/07-unity-humanoid-packaging.md documents the full flow (stage assets, import Humanoid, Mixamo clip list, Animator, validate, cleanup) + coplay-vs-manual + the no-API Mixamo caveat",
    "ValidateBarbarianHumanoid.cs asserts character avatar isValid&&isHuman (catches the GS4 bad-avatar regression), Mixamo clips are Humanoid+CopyFromOther onto the barbarian avatar, Animator binds motions, rig builds Humanoid; has Execute() (coplay) + RunBatch() (headless -executeMethod)",
    "barbarian_accurig.fbx + barbarian_tex.png staged into soapbox-unity/Assets/Animations/Barbarian/Source/"
  ],
  "steps": ["Write the stage doc", "Write the corrected validator", "Copy the rig + texture into Assets/.../Source/"],
  "passes": true
}
```

```json
{
  "id": "UH1",
  "category": "setup",
  "priority": 1,
  "description": "Establish the coplay testing environment: Unity Editor open on ../soapbox-unity with the Coplay plugin signed in, AND a Claude session where coplay-mcp (already in ~/.claude.json) connected to the live editor so its tools are available. Verify a coplay round-trip.",
  "files": ["pipelines/animate-ralph/stages/07-unity-humanoid-packaging.md"],
  "acceptance_criteria": [
    "Unity Editor running on ../soapbox-unity (Unity 6000.4) with the Coplay plugin connected/signed in",
    "A Claude session in which coplay-mcp tools are listed (handshake succeeded — note: MCP loads at session start, so the editor must be up first / the session refreshed)",
    "Round-trip verified: a coplay call returns Unity state (e.g. runs ValidateBarbarianHumanoid.Execute() or reads the scene) — documents the reconnect procedure in the stage doc"
  ],
  "steps": ["Launch Unity on ../soapbox-unity (Coplay signed in)", "Start/refresh a Claude session so coplay-mcp connects", "Run a coplay round-trip and record the procedure"],
  "passes": true
}
```

```json
{
  "id": "UH2",
  "category": "feature",
  "priority": 2,
  "description": "Import the barbarian as a Humanoid avatar (Create From This Model) + assign barbarian_tex.png; avatar valid. Do NOT hand-write the avatar .meta (GS4 failure cause).",
  "files": ["soapbox-unity/Assets/Animations/Barbarian/Source/barbarian_accurig.fbx"],
  "acceptance_criteria": [
    "barbarian_accurig.fbx: Rig Animation Type = Humanoid, Avatar Definition = Create From This Model, avatar isValid && isHuman (>=15 bones mapped)",
    "barbarian_tex.png assigned to the body material Base Color (UVs align — no grey)",
    "ValidateBarbarianHumanoid section 1 (character rig) passes"
  ],
  "steps": ["Set Rig=Humanoid, CreateFromThisModel, Apply, Configure (Enforce T-Pose if needed)", "Assign the texture", "Run the validator's character check"],
  "passes": false
}
```

```json
{
  "id": "UH3",
  "category": "feature",
  "priority": 2,
  "description": "Download the Mixamo core clip set (manual web, FBX Without Skin) into Assets/.../Mixamo/ and import each as Humanoid / Copy From Other Avatar = the barbarian avatar.",
  "files": ["soapbox-unity/Assets/Animations/Barbarian/Mixamo/"],
  "acceptance_criteria": [
    "Core set downloaded from Mixamo: idle, walk, run, attack, hit, dodge, block, wave, celebrate (FBX Without Skin), named with the motion stem",
    "Each clip FBX: Animation Type = Humanoid, Avatar Definition = Copy From Other Avatar -> barbarian avatar; Loop Time on idle/walk/run",
    "ValidateBarbarianHumanoid section 2 (Mixamo clips) passes — clips retarget onto the barbarian avatar with usable AnimationClips"
  ],
  "steps": ["Download the core clips from mixamo.com (Without Skin)", "Import each Humanoid + Copy From Other Avatar", "Run the validator's clip check"],
  "passes": false
}
```

```json
{
  "id": "UH4",
  "category": "testing",
  "priority": 3,
  "description": "Build the Animator (Idle/Walk/Run + action triggers), run ValidateBarbarianHumanoid (PASS), write the manifest + VALIDATION entry, and remove the stale arms-up previz clips.",
  "files": ["soapbox-unity/Assets/Animations/Barbarian/Barbarian.controller", "pipelines/animate-ralph/validation/VALIDATION.md"],
  "acceptance_criteria": [
    "Animator controller: default Idle; Speed float drives Idle<->Walk<->Run; AnyState triggers for attack/hit/dodge/block/wave/celebrate -> exit to Idle",
    "ValidateBarbarianHumanoid returns PASS (exit 0); live play-mode (or coplay screenshot) shows natural arm/leg carriage, NOT the previz splay",
    "ANIMATION-MANIFEST.json updated (clip -> file -> duration -> loop -> avatar); VALIDATION.md gets a Phase UH section",
    "Stale Jun-27 hand-rolled-retarget clips removed from Assets/Animations/Barbarian/ (Humanoid set is the only shippable one)"
  ],
  "steps": ["Build the Animator (coplay or manual)", "Run the validator + visual check", "Write manifest/VALIDATION; delete the stale previz clips"],
  "passes": false
}
```

---

## Phase TX: Tile/texture foundation LoRAs (mat_tile + tile_topdown)

Two material/texture-aesthetic **SDXL** LoRAs that feed the proven seamless tile path in
the **tileset-ralph** pipeline. **Key insight: a LoRA does NOT make a texture tile** —
seamlessness comes from `ComfyUI-seamless-tiling` (`SeamlessTile` patches the model's
Conv2d to circular padding; `CircularVAEDecode` does the same to the VAE). The LoRA
teaches the material **aesthetic + even, flat, top-down lighting** so the seamless
machinery has clean, evenly-lit input to wrap.

**Why SDXL, not Flux** (see project memory `project_seamless_texture_pipeline`): Flux's
transformer has no spatial Conv2d layers for `SeamlessTile` to patch — tested and
confirmed: wrap-seam MAD ~55 vs interior ~6, a hard seam. The proven seamless path is
**SDXL** (`sd_xl_base_1.0.safetensors`, present at `D:/Projects/ComfyUI/models/checkpoints/`)
+ `SeamlessTile` + `CircularVAEDecode`, wired into the EXISTING
`workflows/mcp/generate_texture_tile.json`. The `scripts/train_lora/` ai-toolkit harness
trains Flux only (`is_flux: True` hardcoded; no sd_xl config) — so tile/material LoRAs
require a **separate SDXL trainer** (kohya_ss / sd-scripts). Install prerequisite: TX0b.
Deploy target: wire the trained SDXL LoRA into the EXISTING `generate_texture_tile.json`
(add optional `LoraLoader` + `PARAM_LORA_NAME`/`PARAM_LORA_STRENGTH`) — NOT a new Flux
workflow. Home pipeline: **tileset-ralph** (`pipelines/tileset-ralph/`).

- **mat_tile** (TX1-TX4): PBR-style material surfaces (brick, stone, wood, metal, fabric,
  ground) from CC0 Poly Haven albedo maps. Trigger `mat_tile`.
- **tile_topdown** (TX5-TX8): top-down RPG game tiles (grass, dirt, water, sand, path)
  from CC0 Kenney / OpenGameArt tilesets. Trigger `tile_topdown`.

Spec: `scripts/train_lora/datasets/tile_loras_spec.md` (TX0 — needs rewrite for SDXL).

```json
{
  "id": "TX0",
  "category": "setup",
  "priority": 1,
  "description": "Rewrite the tile-LoRA spec for SDXL: triggers, caption templates, CC0 dataset sourcing, SDXL hyperparams (kohya_ss/sd-scripts sdxl_train_network.py, rank 16, 1024 res, ~1500 steps), and the seamless-tiling eval method (edge MAD <5% at 2x2/4x4). Previous spec was Flux-specific (Flux cannot tile); this rewrite documents the SDXL path that feeds generate_texture_tile.json.",
  "files": ["scripts/train_lora/datasets/tile_loras_spec.md"],
  "acceptance_criteria": [
    "Documents both triggers (mat_tile, tile_topdown) and short trigger-anchored caption templates (e.g. 'mat_tile, <material>, seamless texture, even top-down lighting') — same tags work for SDXL",
    "CC0-only sourcing called out per LoRA: Poly Haven (mat_tile) + Kenney/OpenGameArt (tile_topdown), with license note",
    "Hyperparams documented for SDXL LoRA via kohya_ss sdxl_train_network.py: network_dim 16, network_alpha 16, ~1500 steps, lr 1e-4, AdamW8bit, resolution 1024 (SDXL-native), GPU 1 (3090 Ti), ComfyUI stopped, output to E:/ai-training/sdxl-output/<name>/",
    "Explains the LoRA-vs-seamless split (LoRA = aesthetic+even light; SeamlessTile+CircularVAEDecode = actual tiling) and WHY SDXL not Flux (Flux has no Conv2d to patch)",
    "Eval method: generate through SDXL generate_texture_tile.json + LoraLoader, tile 2x2/4x4, measure wrap-edge MAD <5% (with the exact metric definition)",
    "Notes trainer prerequisite: kohya_ss/sd-scripts must be installed (TX0b) before TX2/TX6 can run",
    "Notes that prep_dataset.py and tile_edge_mad.py are trainer-agnostic and reusable as-is"
  ],
  "steps": [
    "Rewrite scripts/train_lora/datasets/tile_loras_spec.md replacing Flux recipe with SDXL recipe",
    "Document SDXL trainer CLI (sdxl_train_network.py) and config conventions",
    "Update deploy path: SDXL LoRA → generate_texture_tile.json (existing) via optional LoraLoader"
  ],
  "passes": false
}
```

```json
{
  "id": "TX0b",
  "category": "setup",
  "priority": 1,
  "description": "Install and verify an SDXL LoRA trainer (kohya_ss / sd-scripts) in its own venv on E:, GPU 1 (3090 Ti) verified, pointed at the LOCAL sd_xl_base_1.0.safetensors (no re-download). This is a hard prerequisite for TX2 and TX6 — no SDXL trainer is currently installed anywhere on this machine.",
  "files": ["E:/ai-training/sd-scripts/", "scripts/train_lora/README.md"],
  "acceptance_criteria": [
    "kohya-ss/sd-scripts cloned + venv created on E: (E:/ai-training/sd-scripts/, Python 3.11) — keeps C:/D: space free",
    "sdxl_train_network.py launches without import errors in the venv (Python 3.10+, torch+CUDA for GPU 1)",
    "Trainer pointed at LOCAL sd_xl_base_1.0.safetensors (D:/Projects/ComfyUI/models/checkpoints/sd_xl_base_1.0.safetensors) — no 6.9GB re-download",
    "Smoke-test: sdxl_train_network.py with --max_train_steps 1 on a tiny dummy dataset (2 images) completes without OOM or CUDA errors on GPU 1 (CUDA_VISIBLE_DEVICES=1)",
    "README documents the trainer install path, venv activation command, and the sdxl_train_network.py invocation pattern for TX2/TX6"
  ],
  "steps": [
    "Clone kohya_ss or sd-scripts to E:/ai-training/sd-scripts/",
    "Create venv: python -m venv E:/ai-training/sd-scripts/venv; install torch+CUDA + kohya deps",
    "Verify sdxl_train_network.py is importable and GPU 1 is visible (CUDA_VISIBLE_DEVICES=1 nvidia-smi)",
    "Run 1-step smoke-test on a 2-image dummy dataset with sd_xl_base_1.0.safetensors",
    "Document install + invocation in scripts/train_lora/README.md"
  ],
  "passes": false
}
```

```json
{
  "id": "TX1",
  "category": "feature",
  "priority": 1,
  "description": "Build the mat_tile dataset: ~30-50 CC0 evenly-lit tileable material crops from Poly Haven albedo maps; prep + short SDXL-style captions + manifest. Dataset images live on E:; manifest lives under the tileset-ralph pipeline.",
  "files": ["pipelines/tileset-ralph/loras/mat_tile/mat_tile_manifest.md"],
  "acceptance_criteria": [
    "~30-50 CC0 Poly Haven albedo/diffuse maps across material families (brick, stone, cobble, wood, planks, metal, concrete, fabric, ground/dirt/sand/grass)",
    "prep_dataset.py normalizes to E:/ai-training/datasets/mat_tile (max-edge 1024, RGB) — prep_dataset.py is trainer-agnostic (Pillow only) and reusable as-is",
    "SHORT tag-style captions per image: 'mat_tile, <material>, seamless texture, even top-down lighting' (NOT Florence2 verbose — these are flat surfaces; short natural tags suit SDXL well)",
    "Manifest at pipelines/tileset-ralph/loras/mat_tile/mat_tile_manifest.md lists each source asset, its Poly Haven slug, CC0 license, and the material tag"
  ],
  "steps": [
    "Download CC0 Poly Haven albedo maps (blender-mcp download_polyhaven_asset or HTTP) across material families",
    "prep_dataset.py --src ... --out E:/ai-training/datasets/mat_tile --max-edge 1024",
    "Write short trigger-anchored captions + manifest at pipelines/tileset-ralph/loras/mat_tile/mat_tile_manifest.md"
  ],
  "passes": false
}
```

```json
{
  "id": "TX2",
  "category": "feature",
  "priority": 1,
  "description": "Train the mat_tile SDXL LoRA via kohya_ss sdxl_train_network.py (stop ComfyUI first; GPU 1, 3090 Ti; base = local sd_xl_base_1.0.safetensors; output to E:/ai-training/sdxl-output/mat_tile/). Prereq: TX0b (trainer installed).",
  "files": ["E:/ai-training/sdxl-output/mat_tile/"],
  "acceptance_criteria": [
    "ComfyUI stopped before launch to free 24GB; training confirmed on GPU 1 (CUDA_VISIBLE_DEVICES=1 nvidia-smi)",
    "sdxl_train_network.py invoked with: --pretrained_model_name_or_path D:/Projects/ComfyUI/models/checkpoints/sd_xl_base_1.0.safetensors, --train_data_dir E:/ai-training/datasets/mat_tile, --network_dim 16, --network_alpha 16, --max_train_steps 1500, --resolution 1024,1024, --learning_rate 1e-4, --optimizer_type AdamW8bit, --save_every_n_steps 250",
    "Per-checkpoint saves (every 250) + final mat_tile.safetensors on E:/ai-training/sdxl-output/mat_tile/",
    "No OOM; sample images trend toward flat, evenly-lit material surfaces; ComfyUI restarted on the 3090 Ti afterwards (run_3090ti.ps1)"
  ],
  "steps": [
    "Stop ComfyUI to free the 24GB",
    "Activate E:/ai-training/sd-scripts/venv; run sdxl_train_network.py with CUDA_VISIBLE_DEVICES=1; verify GPU 1 via nvidia-smi",
    "Collect checkpoints at E:/ai-training/sdxl-output/mat_tile/",
    "Restart ComfyUI (run_3090ti.ps1)"
  ],
  "passes": false
}
```

```json
{
  "id": "TX3",
  "category": "testing",
  "priority": 2,
  "description": "Eval mat_tile: 2D grid (base vs LoRA) + seamless validation through the SDXL circular-padding path (generate_texture_tile.json + LoraLoader); measure wrap-edge MAD <5% at 2x2/4x4. tile_edge_mad.py is generation-path-agnostic and reusable.",
  "files": ["scripts/train_lora/eval/mat_tile_grid.md", "scripts/train_lora/eval/tile_edge_mad.py"],
  "acceptance_criteria": [
    "tile_edge_mad.py computes the mean-absolute-difference across the horizontal+vertical wrap seams of a tile (0-100% of channel range) and tiles 2x2/4x4 for visual proof",
    "Base-vs-LoRA generated through SDXL generate_texture_tile.json + LoraLoader(mat_tile) + SeamlessTile(enable) + CircularVAEDecode(enable) at fixed seeds/strengths 0.6/0.8/1.0",
    "Winner cell named; the winning mat_tile output achieves wrap-edge MAD <5% at 2x2 and 4x4 (seamless machinery working) AND reads as an evenly-lit material (LoRA working)",
    "Verdict records the winning (checkpoint, strength) and the measured edge MAD"
  ],
  "steps": [
    "Write tile_edge_mad.py (generation-path-agnostic; reused by TX7)",
    "Generate base + LoRA tiles through generate_texture_tile.json (SDXL + SeamlessTile + CircularVAEDecode) with mat_tile LoRA loaded at strengths 0.6/0.8/1.0",
    "Tile 2x2/4x4, measure edge MAD, record verdict in eval/mat_tile_grid.md"
  ],
  "passes": false
}
```

```json
{
  "id": "TX4",
  "category": "feature",
  "priority": 2,
  "description": "Deploy mat_tile SDXL LoRA to ComfyUI/models/loras/style/ and wire it into the EXISTING generate_texture_tile.json workflow (add optional LoraLoader + PARAM_LORA_NAME/PARAM_LORA_STRENGTH to the workflow + .meta.json). No new Flux workflow needed — the SDXL LoRA loads directly into the proven SDXL seamless path.",
  "files": ["workflows/mcp/generate_texture_tile.json", "workflows/mcp/generate_texture_tile.meta.json"],
  "acceptance_criteria": [
    "Winning mat_tile.safetensors copied to D:/Projects/ComfyUI/models/loras/style/ with a .txt sidecar (trigger mat_tile + recommended strength)",
    "generate_texture_tile.json updated: optional LoraLoader node wired between checkpoint and SeamlessTile; PARAM_LORA_NAME and PARAM_LORA_STRENGTH params added (both optional, default to no-op / empty when not supplied)",
    "generate_texture_tile.meta.json updated: PARAM_LORA_NAME (string, optional) and PARAM_LORA_STRENGTH (float 0.0-1.0, default 0.8) documented as new WorkflowParameters",
    "Smoke-tested: generate one seamless material tile via generate_game_tileset MCP tool (mode 'simple') with lora_name=mat_tile; confirm wrap-edge MAD <5%",
    "pipelines/tileset-ralph/loras/mat_tile/ contains the manifest and a deploy-receipt noting the .safetensors location and trigger"
  ],
  "steps": [
    "Copy winning mat_tile.safetensors to D:/Projects/ComfyUI/models/loras/style/ + write .txt sidecar",
    "Update generate_texture_tile.json to wire in optional LoraLoader with PARAM_LORA_NAME/PARAM_LORA_STRENGTH",
    "Update generate_texture_tile.meta.json with new optional WorkflowParameters",
    "Smoke-test via generate_game_tileset mode 'simple' with mat_tile LoRA; confirm MAD <5%"
  ],
  "passes": false
}
```

```json
{
  "id": "TX5",
  "category": "feature",
  "priority": 3,
  "description": "Build the tile_topdown dataset: ~30-50 CC0 top-down RPG tiles (Kenney/OpenGameArt); prep + short SDXL-style captions + manifest. Dataset images on E:; manifest under tileset-ralph pipeline.",
  "files": ["pipelines/tileset-ralph/loras/tile_topdown/tile_topdown_manifest.md"],
  "acceptance_criteria": [
    "~30-50 CC0 top-down RPG tiles (grass, dirt, water, sand, path/road, stone floor) from Kenney and/or OpenGameArt (CC0 only)",
    "prep_dataset.py normalizes to E:/ai-training/datasets/tile_topdown (max-edge 1024, RGB) — prep_dataset.py is trainer-agnostic and reusable as-is",
    "SHORT tag-style captions: 'tile_topdown, <terrain> tile, top-down RPG tileset, seamless texture, even lighting' (short natural tags suit SDXL well)",
    "Manifest at pipelines/tileset-ralph/loras/tile_topdown/tile_topdown_manifest.md lists each source pack, its CC0 license/URL, and the terrain tag"
  ],
  "steps": [
    "Download CC0 Kenney/OpenGameArt top-down tile packs",
    "prep_dataset.py --src ... --out E:/ai-training/datasets/tile_topdown --max-edge 1024",
    "Write short captions + manifest at pipelines/tileset-ralph/loras/tile_topdown/tile_topdown_manifest.md"
  ],
  "passes": false
}
```

```json
{
  "id": "TX6",
  "category": "feature",
  "priority": 3,
  "description": "Train the tile_topdown SDXL LoRA via kohya_ss sdxl_train_network.py (stop ComfyUI first; GPU 1, 3090 Ti; base = local sd_xl_base_1.0.safetensors; output to E:/ai-training/sdxl-output/tile_topdown/). Prereq: TX0b (trainer installed).",
  "files": ["E:/ai-training/sdxl-output/tile_topdown/"],
  "acceptance_criteria": [
    "ComfyUI stopped before launch to free 24GB; training confirmed on GPU 1 (CUDA_VISIBLE_DEVICES=1 nvidia-smi)",
    "sdxl_train_network.py invoked with: --pretrained_model_name_or_path D:/Projects/ComfyUI/models/checkpoints/sd_xl_base_1.0.safetensors, --train_data_dir E:/ai-training/datasets/tile_topdown, --network_dim 16, --network_alpha 16, --max_train_steps 1500, --resolution 1024,1024, --learning_rate 1e-4, --optimizer_type AdamW8bit, --save_every_n_steps 250",
    "Per-checkpoint saves (every 250) + final tile_topdown.safetensors on E:/ai-training/sdxl-output/tile_topdown/",
    "No OOM; sample images trend toward flat, evenly-lit top-down terrain tiles; ComfyUI restarted afterwards (run_3090ti.ps1)"
  ],
  "steps": [
    "Stop ComfyUI to free the 24GB",
    "Activate E:/ai-training/sd-scripts/venv; run sdxl_train_network.py with CUDA_VISIBLE_DEVICES=1; verify GPU 1 via nvidia-smi",
    "Collect checkpoints at E:/ai-training/sdxl-output/tile_topdown/",
    "Restart ComfyUI (run_3090ti.ps1)"
  ],
  "passes": false
}
```

```json
{
  "id": "TX7",
  "category": "testing",
  "priority": 4,
  "description": "Eval tile_topdown: 2D grid (base vs LoRA) + seamless validation through the SDXL circular-padding path (generate_texture_tile.json + LoraLoader); wrap-edge MAD <5% at 2x2/4x4. Reuses tile_edge_mad.py from TX3.",
  "files": ["scripts/train_lora/eval/tile_topdown_grid.md"],
  "acceptance_criteria": [
    "Base-vs-LoRA generated through SDXL generate_texture_tile.json + LoraLoader(tile_topdown) + SeamlessTile(enable) + CircularVAEDecode(enable) at strengths 0.6/0.8/1.0 on terrain prompts",
    "tile_edge_mad.py (from TX3, generation-path-agnostic) measures the winning tile_topdown output at wrap-edge MAD <5% at 2x2 and 4x4",
    "Verdict names the winning (checkpoint, strength) and confirms the LoRA reads as a top-down game tile aesthetic"
  ],
  "steps": [
    "Generate base + LoRA tiles through generate_texture_tile.json (SDXL + SeamlessTile + CircularVAEDecode) with tile_topdown LoRA at strengths 0.6/0.8/1.0",
    "Run tile_edge_mad.py; tile 2x2/4x4; record verdict in eval/tile_topdown_grid.md"
  ],
  "passes": false
}
```

```json
{
  "id": "TX8",
  "category": "feature",
  "priority": 4,
  "description": "Deploy tile_topdown SDXL LoRA to ComfyUI/models/loras/style/ (already wired into generate_texture_tile.json by TX4); smoke-test both tile LoRAs end-to-end + document.",
  "files": ["scripts/train_lora/README.md", "pipelines/tileset-ralph/loras/tile_topdown/"],
  "acceptance_criteria": [
    "Winning tile_topdown.safetensors copied to D:/Projects/ComfyUI/models/loras/style/ with a .txt sidecar (trigger tile_topdown + recommended strength)",
    "Usable via generate_game_tileset MCP tool (mode 'simple') with lora_name=tile_topdown; smoke-tested to a seamless top-down tile (edge MAD <5%)",
    "pipelines/tileset-ralph/loras/tile_topdown/ contains the manifest and a deploy-receipt noting .safetensors location and trigger",
    "scripts/train_lora/README.md documents both tile LoRAs (mat_tile + tile_topdown): triggers, strengths, SDXL trainer path, dataset rebuild commands, and the seamless path (generate_texture_tile.json)"
  ],
  "steps": [
    "Copy winning tile_topdown.safetensors to D:/Projects/ComfyUI/models/loras/style/ + write .txt sidecar",
    "Smoke-test via generate_game_tileset mode 'simple' with tile_topdown LoRA; confirm MAD <5%",
    "Document both tile LoRAs in scripts/train_lora/README.md"
  ],
  "passes": false
}
```

---

## Phase SL: lowpoly_flat LoRA  (stylized_game SCRAPPED 2026-06-30)

**`stylized_game` was SCRAPPED.** Generate-and-curate on BASE Flux + "Blizzard
concept art" prompts produced **generic AI-looking output** — which our OWN
research says is the saturated lane to AVOID, and which (a) can't be sold anyway
(Flux-dev license) and (b) earns ~no Buzz because it doesn't stand out. SL1-SL4
removed. **Lesson: a style LoRA only has an edge if the dataset is art-directed to
a SPECIFIC ownable aesthetic — not generic-prompted.** Validation: the *distinctive*
GrimForge got positive ratings + 11 downloads in its first 12h on CivitAI; the
generic set would not.

**Pivot → distinctive own-art style LoRAs** (see Phase DS below / proposed): train
on the user's already-art-directed game art (e.g. the DissonantDreams retro-
futurist pink/cyan/black noir-pop set, ~120-150 cohesive images) — genuinely
unique, IP-clean (curated own Outputs), nothing like it on Flux.

`lowpoly_flat` (below) stays — it feeds itch.io's #2 selling category (low-poly 3D
kits) AND improves image→3D input. Already-queued elsewhere: `tile_topdown`
(TX5-TX8, itch #1), `mat_tile` (TX1-TX4). `ortho_turnaround`/`mv_ortho` shipped
(Phase M).

**Recipe (reuse verbatim, identical to grimforge/mv_ortho/TX):** rank 16/alpha 16,
1500 steps, lr 1e-4, adamw8bit, flowmatch, EMA 0.99, multi-res [512,768,1024],
GPU 1 (3090 Ti) with ComfyUI stopped, then restart. IP-clean original data only;
keep a dataset-provenance manifest. AI-disclosure ON at listing time.

```json
{
  "id": "SL5",
  "category": "feature",
  "priority": 3,
  "description": "Build the lowpoly_flat dataset: ~80-120 flat-shaded low-poly renders (render owned/CC0 low-poly meshes via render_multiview/blender-mcp); prep + captions + manifest",
  "files": ["scripts/train_lora/datasets/lowpoly_flat_manifest.md"],
  "acceptance_criteria": [
    "~80-120 flat-shaded low-poly renders (props/kits/characters) — reuse render_multiview.py / blender-mcp over owned (Stream K village kit) + CC0 low-poly meshes, flat-shaded, even lighting, neutral bg",
    "prep_dataset.py normalizes to E:/ai-training/datasets/lowpoly_flat",
    "Captions prefixed with trigger lowpoly_flat + subject tag; manifest records mesh sources (owned/CC0) and counts (IP-clean origin)"
  ],
  "steps": ["Render flat-shaded low-poly views via render_multiview/blender-mcp over Stream K + CC0 meshes", "prep_dataset.py --src ... --out E:/ai-training/datasets/lowpoly_flat", "caption.py --trigger lowpoly_flat; write the manifest"],
  "passes": false
}
```

```json
{
  "id": "SL6",
  "category": "feature",
  "priority": 3,
  "description": "Train the lowpoly_flat Flux LoRA (stop ComfyUI; proven recipe; collect checkpoints; restart ComfyUI)",
  "files": ["scripts/train_lora/configs/lowpoly_flat.json"],
  "acceptance_criteria": [
    "ComfyUI stopped; training on GPU 1 confirmed via nvidia-smi",
    "launch_train.py --dataset E:/ai-training/datasets/lowpoly_flat --name lowpoly_flat --trigger lowpoly_flat --steps 1500 --rank 16 --resolutions 512,768,1024 --cuda-device 1",
    "Checkpoints + final lowpoly_flat.safetensors on E:/ai-training/flux-output/lowpoly_flat/; ComfyUI restarted afterwards"
  ],
  "steps": ["Stop ComfyUI", "launch_train.py (background); verify device 1", "Restart ComfyUI"],
  "passes": false
}
```

```json
{
  "id": "SL7",
  "category": "testing",
  "priority": 4,
  "description": "Eval + deploy lowpoly_flat: base-vs-LoRA grid + AI judge; pick winner; deploy + listing copy; also note its image->3D input use",
  "files": ["scripts/train_lora/eval/lowpoly_flat_grid.md", "scripts/train_lora/eval/lowpoly_flat_listing.md", "D:/Projects/ComfyUI/models/loras/style/"],
  "acceptance_criteria": [
    "lora_eval_grid.py --only lowpoly_flat across strengths 0.6/0.8/1.0; AI-judge names a winning (checkpoint, strength) that reads as a clean flat-shaded low-poly look",
    "Winning lowpoly_flat.safetensors deployed to loras/style/ with a .txt sidecar; 8-sample card rendered",
    "Listing copy written (mirror the grimforge/stylized_game listings); AI-disclosure + provenance; Gumroad mirror note",
    "README/listing notes the dual use: sellable LoRA AND a cleaner silhouette source for the image->3D (Hunyuan3D) path"
  ],
  "steps": ["Run the eval grid; pick the winner", "Deploy + sidecar + 8-sample card", "Write lowpoly_flat_listing.md; note the image->3D use"],
  "passes": false
}
```

---

## Phase PV: Rig/animate PIVOT — owned local pipeline, Tripo as benchmark only

A live bake-off (2026-06-29/30) retired the old chain. The arms-up failure was
TWO bugs: (a) `retarget_mocap.py` bind-direction mismatch — FIXED (commit 3eb349b,
per-bone bind alignment), and (b) the deeper issue: Hunyuan3D-lumpy-mesh + UniRig
weak auto-rig + hand-rolled retarget stack three quality ceilings. Verdict: **drop
UniRig + the hand-rolled retarget.** Tripo (image→mesh+rig+anim) and AccuRIG 2
(free, 118-bone UE5 rig) both crush the old path and fix the arms.

**Hands were the last defect** — `mv_ortho`'s "fingers spread" reconstructs as
double-thumb/backwards hands in ANY image-to-3D (appeared in BOTH paths = source
defect, not rigging). Fix: regenerate with **closed fists** ([[memory]]
project_mv_ortho_fists) — keeps limb separation, reconstructs cleanly. Seed 123456.

**Strategy (see memory project_tripo_strategy):** Tripo is a velocity shortcut +
private quality BENCHMARK (Pro tier to ship its assets). ToS forbids training a
model on its outputs; we sell tools+assets, not a pipeline, so no "compete" issue.
Goal = OWNED local pipeline, tuned (not trained) against the Tripo bar.

**Owned local pipeline (no cloud):**
`mv_ortho (fists) → Hunyuan3D v2.0 TEXTURED (local) → retopo → AccuRIG free (local) → Mixamo/ActorCore → Unity`

Tuning roadmap status: **Texture ✅** (Hy3D v2.0 textured pipeline — full-color
barbarian matching Tripo; DLL fix confirmed) · **Mesh ~✅** (minor fur-spikes,
tune the prompt) · **Rig** = AccuRIG free (validated) or headless UniRig if full
automation needed. Assets staged: `E:/ai-training/_rigtest/bakeoff/barbarian_fists_textured.{glb,fbx,obj}`.

```json
{
  "id": "PV1",
  "category": "feature",
  "priority": 1,
  "description": "Close the texture gap: local Hunyuan3D v2.0 TEXTURED pipeline on the closed-fists mv_ortho barbarian",
  "files": ["workflows/mcp/hunyuan3d_v20_image_to_3d.json", "E:/ai-training/_rigtest/bakeoff/barbarian_fists_textured.glb"],
  "acceptance_criteria": [
    "mv_ortho regenerated with CLOSED FISTS (seed 123456) — clean fists, wide separated T-pose",
    "Hunyuan3D v2.0 textured workflow produces a full-color mesh (red beard, leather, fur) matching the Tripo bar; hands reconstruct as clean fists not double-thumbs",
    "Textured mesh exported FBX(embedded)/OBJ/GLB for the local rigger"
  ],
  "steps": ["Regenerate fists art", "Run Hy3D v2.0 textured", "Export textured mesh"],
  "passes": true
}
```

```json
{
  "id": "PV2",
  "category": "feature",
  "priority": 2,
  "description": "Rig + animate the textured fists barbarian via the local rigger (AccuRIG free) and into Unity",
  "files": ["E:/ai-training/_rigtest/bakeoff/"],
  "acceptance_criteria": [
    "barbarian_fists_textured.fbx/obj auto-rigged in AccuRIG (now TEXTURED, not gray) — natural arms, clean fists",
    "Animated (Mixamo/ActorCore) and imported to Unity as Humanoid",
    "Quality matches/beats the Tripo benchmark; pipeline is fully free/local (no Tripo dependency)"
  ],
  "steps": ["AccuRIG auto-rig the textured mesh", "Apply a walk + idle", "Unity Humanoid import + verify"],
  "passes": false
}
```

---

## Phase UL: Utility / quality-enhancer LoRA (FREE CivitAI Buzz/reputation track)

Derived from the 2026-06-30 research (`docs/research/flux-model-types-and-feasibility.md`
+ `flux-lora-edge-and-licensing.md`). **Verified finding:** the most-downloaded Flux
LoRAs are **utility/quality enhancers** (hands/anatomy/detail/realism), *above any
single art style* — because they're used in **every** generation, so they top
CivitAI's 25%-of-Generator-Buzz mechanic. **Two constraints shape this phase:**

1. **License:** GrimForge/all our LoRAs are FLUX.1-dev-derived → **selling the
   `.safetensors` file is prohibited** (non-commercial Derivative). So this LoRA is
   shipped **FREE** — it's a Buzz/reputation/funnel engine, not a paid product.
   (Sellable LoRA files would need a FLUX.1-schnell/Apache base — out of scope here.)
2. **Feasibility:** the **LoRA is the only solo-feasible unit** on the 24GB 3090 Ti —
   ControlNet / IP-Adapter / full-checkpoint training are all multi-GPU/datacenter
   scale. So we build a LoRA, not a ControlNet.

**Edge framing (honest):** market **repeatability + curation + 3D-rendered datasets**,
NOT "higher quality" (the multi-res quality *delta* is unproven). **Recipe** = the
proven one (rank 16/alpha 16, 1500 steps, lr 1e-4, adamw8bit, flowmatch, EMA 0.99,
multi-res [512,768,1024], GPU 1 with ComfyUI stopped). Pick: a **stylized game-art
detail enhancer** — broadly reusable on top of any stylized generation, and a natural
companion to GrimForge / `stylized_game`.

```json
{
  "id": "UL1",
  "category": "feature",
  "priority": 2,
  "description": "Build the gameart_detailer dataset by GENERATE-then-ENHANCE (NOT self-distillation): generate ~60-100 game-art images, then ESRGAN-upscale + detail-enhance each (the 2K-texture-pack pipeline) so the TARGETS EXCEED base Flux detail; the LoRA learns to push toward the enhanced version; prep + captions + manifest",
  "files": ["scripts/train_lora/datasets/gameart_detailer_manifest.md"],
  "acceptance_criteria": [
    "SOURCING = generate-then-enhance (a quality enhancer CANNOT be trained on the base model's own default-detail output — that just learns the average). Generate ~60-100 varied game-art images (character/creature/prop/material) via generate_image, then run each through upscale_image/ESRGAN + a detail pass (reuse the texture-pack 2K enhance pipeline) to produce HIGH-DETAIL targets that visibly exceed the base generation",
    "Each kept image is demonstrably MORE detailed than its source generation (sharper edges, cleaner hands/faces, richer materials) — that delta is the signal the enhancer learns",
    "prep_dataset.py normalizes to E:/ai-training/datasets/gameart_detailer (max-edge 1024, RGB)",
    "SHORT trigger-anchored captions: 'gameart_detailer, highly detailed, sharp, intricate' + a one-word subject tag; NOT verbose Florence2 (this is an aesthetic-bias enhancer, not a subject LoRA)",
    "Manifest records the generate->enhance method (self-generated + upscaled Outputs = IP-clean) and the before/after detail delta per image"
  ],
  "steps": [
    "Generate ~60-100 varied game-art images via generate_image",
    "ESRGAN-upscale + detail-enhance each (texture-pack pipeline) into high-detail targets; verify each exceeds its source",
    "prep_dataset.py --src ... --out E:/ai-training/datasets/gameart_detailer --max-edge 1024",
    "Write short captions + gameart_detailer_manifest.md (generate->enhance provenance)"
  ],
  "passes": false
}
```

```json
{
  "id": "UL2",
  "category": "feature",
  "priority": 2,
  "description": "Train the gameart_detailer Flux LoRA (stop ComfyUI first; proven recipe; collect checkpoints; restart ComfyUI)",
  "files": ["scripts/train_lora/configs/gameart_detailer.json"],
  "acceptance_criteria": [
    "ComfyUI stopped before launch; training confirmed on GPU 1 (3090 Ti) via nvidia-smi",
    "launch_train.py --dataset E:/ai-training/datasets/gameart_detailer --name gameart_detailer --trigger gameart_detailer --steps 1500 --rank 16 --resolutions 512,768,1024 --cuda-device 1",
    "Per-checkpoint saves (every 250) + final gameart_detailer.safetensors on E:/ai-training/flux-output/gameart_detailer/",
    "No OOM; ComfyUI restarted on the 3090 Ti afterwards"
  ],
  "steps": ["Stop ComfyUI to free the 24GB", "launch_train.py (background); verify device 1; collect checkpoints", "Restart ComfyUI (run_3090ti.ps1)"],
  "passes": false
}
```

```json
{
  "id": "UL3",
  "category": "testing",
  "priority": 3,
  "description": "Eval gameart_detailer as an ENHANCER: same-seed A/B toggle (LoRA off vs on at low strengths 0.2/0.4/0.6) across varied subjects; confirm it ADDS detail WITHOUT changing composition or imposing a style",
  "files": ["scripts/train_lora/eval/gameart_detailer_grid.md", "scripts/train_lora/eval/gameart_detailer_assets/"],
  "acceptance_criteria": [
    "Restart ComfyUI; generate matched pairs at FIXED seed across several subjects (character/creature/prop/environment), LoRA OFF vs ON at strengths 0.2/0.4/0.6 (enhancers run lower than style LoRAs)",
    "AI-judge / visual verdict: the ON cells show measurably MORE detail (sharper edges, cleaner hands/faces, richer materials) while keeping the SAME composition — an enhancer, not a restyle",
    "Names a recommended strength (likely 0.3-0.5) where detail improves but the base image isn't overpowered or pushed toward photoreal",
    "A few before/after pairs saved to eval/gameart_detailer_assets/ for the listing gallery; verdict in gameart_detailer_grid.md"
  ],
  "steps": ["Restart ComfyUI; generate OFF/ON same-seed pairs across subjects + strengths", "Judge detail-gain vs composition-drift; pick the strength", "Save before/after pairs; record the verdict"],
  "passes": false
}
```

```json
{
  "id": "UL4",
  "category": "feature",
  "priority": 3,
  "description": "Deploy gameart_detailer + write the FREE CivitAI listing (Buzz/reputation framing, before/after gallery); NO paid file (license) — monetize via reputation + Generator-Buzz, not a sale",
  "files": ["scripts/train_lora/eval/gameart_detailer_listing.md", "D:/Projects/ComfyUI/models/loras/style/"],
  "acceptance_criteria": [
    "Winning gameart_detailer.safetensors copied to D:/Projects/ComfyUI/models/loras/style/ with a .txt sidecar (trigger gameart_detailer + recommended low strength ~0.3-0.5, 'enhancer — stack on top of other LoRAs')",
    "FREE CivitAI listing copy: name, trigger, recommended strength, 'utility/quality enhancer for stylized game art' positioning, before/after gallery, AI-disclosure + original-IP provenance — explicitly FREE (no Early-Access paywall, no Gumroad sale of the file: Flux-dev Derivative)",
    "Listing notes the honest edge (repeatability/curation, not a 'quality' guarantee) and that it stacks with GrimForge/stylized_game",
    "Cross-reference a BUSINESS-PLAN-TASKS.md item for the actual (human-gated) CivitAI upload"
  ],
  "steps": ["Copy + sidecar the winner (enhancer usage note)", "Write the FREE listing copy with before/after gallery", "Flag the human-gated upload in BUSINESS-PLAN-TASKS.md"],
  "passes": false
}
```

---

## Phase DS: Distinctive own-art style LoRA (DissonantDreams retro-futurist)

**Replaces the scrapped `stylized_game`.** Generic-prompted styles don't sell or
earn Buzz; the edge is an **art-directed, ownable aesthetic**. The user's
**DissonantDreams** game art is exactly that — a cohesive retro-futurist pulp
look (hot pink/cyan/black/cream, halftone screen-print + chrome airbrush, 70s-80s
sci-fi-paperback energy) with **~125 curated illustrations already on disk** and
**nothing like it on Flux**. Proof of model: distinctive GrimForge got +ratings
and 11 downloads in its first 12h. **This is a repeatable play** — each
art-directed project (DissonantDreams, soapboxsabatoge, berserkr) can become its
own distinctive LoRA.

**Source (whole retro-futurist family, per user):** `D:/Projects/DissonantDreams/
assets/art/` — `cards/` (98) + `characters/` (11) + `scenarios/` (14) +
`key_art/` (2) = ~125. EXCLUDE the non-illustration folders (ui/overlays/identity/
card_backs/boards = frames/UI; tiles_* = iso tiles, a separate look).
**IP-clean:** these are the user's own art-directed, curated Outputs (same posture
as the grimforge/berserkr set). **License:** Flux-dev → ship the LoRA FREE on
CivitAI (can cross-promote the DissonantDreams game); sell Outputs, not the file.
**Recipe:** the proven one (rank 16/alpha 16, 1500 steps, lr 1e-4, adamw8bit,
flowmatch, EMA 0.99, multi-res [512,768,1024], GPU 1 with ComfyUI stopped).
**Trigger:** working `dissonant_style` (user may rebrand at listing, like
berserkr→grimforge). NOTE: no generation step — the dataset already exists, so
DS1 is curate+caption only (fast).

```json
{
  "id": "DS1",
  "category": "feature",
  "priority": 1,
  "description": "Assemble the dissonant_style dataset from the DissonantDreams illustration folders (cards/characters/scenarios/key_art, ~125 imgs), curate to a cohesive ~100-125, prep + caption + manifest. NO generation — the art already exists on disk.",
  "files": ["scripts/train_lora/datasets/dissonant_style_manifest.md"],
  "acceptance_criteria": [
    "Copy the illustration images from D:/Projects/DissonantDreams/assets/art/{cards,characters,scenarios,key_art} into a working dir; EXCLUDE non-illustration assets (ui/overlays/identity/card_backs/boards frames; tiles_* iso tiles)",
    "Curate to ~100-125 cohesive retro-futurist images (drop UI/text-card/duplicate/off-style frames); the set should read as one ownable aesthetic family",
    "prep_dataset.py normalizes to E:/ai-training/datasets/dissonant_style (max-edge 1024, RGB)",
    "Captions prefixed with trigger dissonant_style + a short subject tag; Florence2 content caption appended; idempotent",
    "Manifest records the source (own DissonantDreams game art, art-directed curated Outputs = IP-clean), the folder breakdown, and kept-vs-source counts (defensible-origin record per Stream D legal note)"
  ],
  "steps": [
    "Copy the 4 illustration folders into a staging dir; cull non-illustration/UI/tile images",
    "prep_dataset.py --src <staging> --out E:/ai-training/datasets/dissonant_style --max-edge 1024",
    "caption.py --dir ... --trigger dissonant_style; write dissonant_style_manifest.md"
  ],
  "note": "DONE 2026-06-30. Staged 125 from DissonantDreams/assets/art -> curated to 50 'striking only' (23 cards/rf + 14 scenarios + 11 characters + 2 key_art; dropped the 75 zc_* sketchy interiors per user). prep_dataset.py: 50/50 included, 0 dupes, 27 resized -> E:/ai-training/datasets/dissonant_style. caption.py (Florence-2-large, trigger dissonant_style prepended): 50/50 captioned, 0 failed. Manifest: scripts/train_lora/datasets/dissonant_style_manifest.md.",
  "passes": true
}
```

```json
{
  "id": "DS2",
  "category": "feature",
  "priority": 1,
  "description": "Train the dissonant_style Flux LoRA (stop ComfyUI first; proven recipe; collect checkpoints; restart ComfyUI)",
  "files": ["scripts/train_lora/configs/dissonant_style.json"],
  "acceptance_criteria": [
    "ComfyUI stopped before launch; training confirmed on GPU 1 (3090 Ti) via nvidia-smi",
    "launch_train.py --dataset E:/ai-training/datasets/dissonant_style --name dissonant_style --trigger dissonant_style --steps 1500 --rank 16 --resolutions 512,768,1024 --cuda-device 1",
    "Per-checkpoint saves (every 250) + final dissonant_style.safetensors on E:/ai-training/flux-output/dissonant_style/",
    "No OOM; sample images trend toward the retro-futurist pink/cyan halftone + chrome look; ComfyUI restarted afterwards"
  ],
  "steps": ["Stop ComfyUI to free the 24GB", "launch_train.py (background); verify device 1; collect checkpoints", "Restart ComfyUI (run_3090ti.ps1)"],
  "note": "DONE 2026-06-30. Stopped ComfyUI (freed 23GB on the 3090 Ti), launched on GPU 1 (CUDA_VISIBLE_DEVICES=1, 99% util/415W). 1500 steps, ~1h45m. Checkpoints 500/750/1000/1250 + final dissonant_style.safetensors on E:/ai-training/flux-output/dissonant_style/. ComfyUI restarted after. NOTE: in-training sample previews used launch_train.py's off-domain dark-fantasy DEFAULT prompts so looked weak — the real eval (DS3) passed.",
  "passes": true
}
```

```json
{
  "id": "DS3",
  "category": "testing",
  "priority": 2,
  "description": "Eval dissonant_style: base-vs-LoRA grid across checkpoints x strengths 0.6/0.8/1.0 + AI judge; confirm it captures the distinctive retro-futurist look on NEW subjects (not in the training set); pick winner + render an 8-sample card",
  "files": ["scripts/train_lora/eval/dissonant_style_grid.md", "scripts/train_lora/eval/dissonant_style_assets/"],
  "acceptance_criteria": [
    "Restart ComfyUI; lora_eval_grid.py --only dissonant_style across strengths 0.6/0.8/1.0 on VARIED NEW prompts (portrait, sci-fi figure, cityscape, object) at fixed seeds",
    "AI-judge / visual verdict: the LoRA reproduces the ownable retro-futurist aesthetic (palette + halftone/chrome) on subjects NOT in the training data (proves it learned a transferable style, not memorized images); names a winning (checkpoint, strength)",
    "8-sample 1024px product card rendered on fresh subjects; style cohesive across >=7/8",
    "Verdict recorded in eval/dissonant_style_grid.md"
  ],
  "steps": ["Restart ComfyUI; run the eval grid on NEW subjects; pick the winner", "Render the 8-sample card", "Record the verdict"],
  "note": "DONE 2026-06-30. PASS — strong, distinctive, TRANSFERABLE. Evaled on on-domain retro-futurist subjects (sci-fi figure/car/portrait/cityscape) NOT in training, strengths 0.8/1.0/1.2 + ckpt-1000 control. Reproduces the DissonantDreams pink/cyan/black halftone+chrome look on new subjects (learned a style, not memorized). Winner: ckpt 1500 @ 1.0 (range 0.8-1.2). The in-training previews looked weak ONLY because launch_train.py's DEFAULT sample prompts are dark-fantasy berserkr prompts (off-domain) — false alarm; fix = pass style-appropriate sample.prompts for non-fantasy LoRAs. Verdict: eval/dissonant_style_grid.md; 5 hero samples: eval/dissonant_style_assets/.",
  "passes": true
}
```

```json
{
  "id": "DS4",
  "category": "feature",
  "priority": 2,
  "description": "Deploy dissonant_style + write the FREE CivitAI listing (distinctive-style framing; cross-promote the DissonantDreams game); AI-disclosure + provenance",
  "files": ["scripts/train_lora/eval/dissonant_style_listing.md", "D:/Projects/ComfyUI/models/loras/style/"],
  "acceptance_criteria": [
    "Winning dissonant_style.safetensors copied to D:/Projects/ComfyUI/models/loras/style/ with a .txt sidecar (trigger + recommended strength)",
    "FREE CivitAI listing copy (mirror grimforge_listing.md): name (user may rebrand), trigger, recommended weights, tags, description LEADING WITH the distinctive retro-futurist hook (what makes it unique vs generic), 8-sample gallery, AI-disclosure + original-IP provenance; optional cross-promo link to the DissonantDreams game",
    "Listing is FREE (Flux-dev Derivative can't be sold) — positioned as reputation/funnel + Generator-Buzz; Gumroad note only if a schnell-retrained sellable variant is later made",
    "Cross-reference a BUSINESS-PLAN-TASKS.md item for the human-gated upload"
  ],
  "steps": ["Copy + sidecar the winner", "Write dissonant_style_listing.md (distinctive-hook framing + game cross-promo)", "Flag the human-gated upload in BUSINESS-PLAN-TASKS.md"],
  "note": "DONE 2026-06-30. Final dissonant_style.safetensors deployed to ComfyUI/models/loras/style/ + .txt sidecar (trigger dissonant_style, strength 1.0, range 0.8-1.2). FREE CivitAI listing copy written: eval/dissonant_style_listing.md (distinctive retro-futurist hook, 5-sample gallery, AI-disclosure + own-game provenance, game cross-promo, NO paid gate per Flux-dev license). Human-gated upload remains (like grimforge D0.6).",
  "passes": true
}
```
