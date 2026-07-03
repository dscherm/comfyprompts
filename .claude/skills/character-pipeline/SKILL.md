---
name: character-pipeline
description: Run the proven end-to-end game-character pipeline — concept T-pose views → TRELLIS.2 multi-view mesh → mesh prep → TRELLIS texture paint → UV/bake → AccuRIG rig (one manual GUI step) → Unity Humanoid + shared Mixamo clips → strict validation PASS. Use when the user wants a new Soapbox character (or any humanoid) taken from images to a validated, animated, textured Unity asset. Args - character id/name + front and back T-pose images.
---

# Character Pipeline (proven on The Rookie, 2026-07-03)

Takes `<name>` + two T-pose concept views to a **textured, rigged, animated,
strictly-validated Unity Humanoid**. Every phase has a machine gate; two steps
are manual (AccuRIG GUI ~2 min; Unity menu clicks). Run phases in order; do not
skip gates. Show the user each visual checkpoint and wait for their OK
(interactive bridge mode).

**Inputs required**: `<name>` (lowercase id, e.g. `bones`), front + back T-pose
images in `D:/Projects/ComfyUI/input/` (wide T-pose, separated limbs,
**CLOSED FISTS** — spread fingers reconstruct as mittens/claws; see memory
`project_mv_ortho_fists`). Character descriptions for Soapbox live in
`pipelines/art-to-rig-ralph/output/intake/characters-intake.json`.

**Key paths** (all scripts under `pipelines/art-to-rig-ralph/scripts/` unless
noted; Blender = `"C:/Program Files/Blender Foundation/Blender 5.0/blender.exe"`;
Unity project = `D:/Projects/soapbox-unity`).

## Phase 0 — Preflight
- `curl -s http://localhost:8188/system_stats` — ComfyUI must be up on the
  3090 Ti venv (if down: `D:/Projects/ComfyUI/run_3090ti.ps1`; NEVER plain
  system python — memory `project_comfyui_torch_xformers_pin`).
- Confirm both input images exist in `D:/Projects/ComfyUI/input/`.

## Phase 1 — Mesh generation (TRELLIS.2 multi-view, GPU ~5 min)
```
py -3.11 pipelines/art-to-rig-ralph/scripts/trellis_queue.py \
  --workflow MeshOnly_MultiView --front <front>.png --back <back>.png \
  --prefix <Name>_MV --seed 12345
```
(User prefers watching in the ComfyUI UI — the queued job is visible there.)
**Gate**: script exits 0 and prints `OUTPUT <glb>`. Then render hand close-ups
(camera at the mesh's ±X extremes, front+top ortho) and show the user —
fingers must read as thumb + separated masses, not a mitten. If mitten:
regenerate the concept images with clearer fists; do not proceed.

## Phase 2 — Mesh prep
```
Blender --background --python pipelines/art-to-rig-ralph/scripts/mesh_prep.py -- \
  --input <phase1.glb> --output output/prepared/<name>_v1_prepared.glb \
  --target-height 1.8 --max-faces 80000 --target-faces 50000
```
**Gate**: report shows ≤80k faces, 1.8m height, grounded. Show a front render.

## Phase 3 — Texture paint (TRELLIS MeshTexturing, GPU ~5 min)
```
py -3.11 pipelines/art-to-rig-ralph/scripts/trellis_queue.py \
  --workflow MeshTexturing_MultiView --front <front>.png --back <back>.png \
  --mesh <phase1_fullres.glb> --prefix <Name>_Textured --seed 12345
```
Texture the ORIGINAL full-res phase-1 mesh (not the decimated one) — the bake
in phase 4 transfers it across topologies.
**Gate**: exits 0, `OUTPUT <textured.glb>` exists.

## Phase 4 — UV unwrap + bake transfer (CPU, ~5 min)
```
Blender --background --python pipelines/art-to-rig-ralph/scripts/uv_and_bake.py -- \
  output/prepared/<name>_v1_prepared.glb <textured.glb> <workdir> <name> \
  output/prepared/<name>_for_accurig.obj
```
Produces `<name>_albedo.png` (2048), textured front/back previews, and the
AccuRIG input OBJ (welded, **cm scale, WITH UVs** — the order matters: UVs
must exist BEFORE AccuRIG; memory `project-accurig-input-format`).
**Gate (visual checkpoint)**: show the user both preview renders — the
character must be recognizably painted per the concept. Copy the albedo to
`D:/Projects/soapbox-unity/Assets/Animations/<Name>/Source/<name>_albedo.png`.

## Phase 5 — AccuRIG (MANUAL, user, ~2 min)
Ask the user to: open AccuRIG (`D:\Program Files\AccuRIG\`), load the
`_for_accurig.obj` (appears ~180cm), auto-rig, export FBX to
`D:\Projects\soapbox-unity\Assets\Animations\<Name>\Source\<name>_accurig.fbx`.
**Gate** (run immediately when they say done):
```
Blender --background --python pipelines/art-to-rig-ralph/scripts/check_accurig_fbx.py -- <fbx>
```
Must print `ACCURIG_FBX OK` (height ~1.8m, real UVs, rigid bind). If FAIL, the
error line says exactly what to fix. Also do a bind-pose render via
`pipelines/animate-ralph/scripts/render_rootmotion.py` and eyeball it (T-pose
lying down = normal Y-up view). Optionally check arm rolls (consistent within
~10° per side is fine; if wildly inconsistent run
`pipelines/animate-ralph/tools/normalize_rig_rolls_for_unity.py`).

## Phase 6 — Unity packaging + strict validation
Generate the per-character editor tools from the Rookie templates in
`D:/Projects/soapbox-unity/Assets/Editor/` (copy each file, replace
`Rookie`→`<Name>` and `rookie`→`<name>` throughout):
`SetupRookieImport.cs`, `BuildRookieAnimator.cs`, `AssignRookieTexture.cs`,
`ValidateRookieHumanoid.cs`. The Mixamo clip set is SHARED from
`Assets/Animations/Barbarian/Mixamo` (Generic clips retarget onto any Humanoid
at runtime — no downloads).

Then either (a) user clicks in the open editor: `Tools ▸ <Name> ▸ Setup
Humanoid Import` → `Build Animator` → `Assign Texture` → `Validate Humanoid
(strict)`, or (b) Unity closed → run each headlessly:
`Unity.exe -batchmode -projectPath D:/Projects/soapbox-unity -executeMethod
<Class>.RunBatch -quit` (editor at
`C:/Program Files/Unity/Hub/Editor/6000.4.0f1/Editor/Unity.exe`).

**Gate**: read the validation report (Console or
`%LOCALAPPDATA%/Unity/Editor/Editor.log`, or the batch txt) — **RESULT: PASS**
required: avatar isValid+isHuman, 9/9 clips, Animator bound, sampled poses
sane (dodge inversion is exempted as acrobatic). §5 failing = stop and
diagnose; do not hand-wave.

## Phase 7 — Package + commit
- Copy deliverables into
  `pipelines/art-to-rig-ralph/output/final/<name>/` (albedo, previews,
  ASSET-CARD.md modeled on player_char's).
- Commit soapbox-unity (rig+albedo+material+controller+editor tools) and
  comfyui-toolchain (package; `git add -f` past the output/ ignore, commit
  **with an explicit pathspec** — parallel sessions stage unrelated work).

## Known traps (cost real time — read before improvising)
- flash_attn is NOT installed: TRELLIS backends must be sdpa/xformers
  (trellis_queue.py forces this).
- AccuRIG input: plain OBJ, cm, UVs included. FBX input = shredded bind.
- Never Blender-round-trip the rigged FBX (bind desync); UVs/rolls are fixed
  BEFORE AccuRIG, texture binds in Unity.
- UniRig/retarget_mocap is previz-only (weights melt; limb plane) — ship path
  is AccuRIG + Unity Humanoid, exactly this skill.
- Lessons: `unirig-skin-weights-melt-use-accurig`,
  `hand-rolled-retarget-limb-plane`, `unity-humanoid-bone-roll-normalize`.
