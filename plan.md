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
  "passes": false
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
  "passes": false
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
  "passes": false
}
```
