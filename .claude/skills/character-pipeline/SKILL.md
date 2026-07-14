---
name: character-pipeline
description: Run the proven end-to-end game-character pipeline — concept T-pose view → TRELLIS.2 SINGLE-view mesh → mesh prep → TRELLIS texture paint → UV/bake → AccuRIG rig (one manual GUI step) → Unity Humanoid + shared Mixamo clips → strict validation PASS. Use when the user wants a new Soapbox character (or any humanoid) taken from images to a validated, animated, textured Unity asset. Args - character id/name + a front T-pose image (single view; multiview corrupts).
---

# Character Pipeline (proven on The Rookie, 2026-07-03)

Takes `<name>` + two T-pose concept views to a **textured, rigged, animated,
strictly-validated Unity Humanoid**. Every phase has a machine gate; two steps
are manual (AccuRIG GUI ~2 min; Unity menu clicks). Run phases in order; do not
skip gates. Show the user each visual checkpoint and wait for their OK
(interactive bridge mode).

**Inputs required**: `<name>` (lowercase id, e.g. `bones`), a front T-pose
image in `D:/Projects/ComfyUI/input/` (single view — multiview corrupts; wide T-pose, separated limbs,
**CLOSED FISTS** — spread fingers reconstruct as mittens/claws; see memory
`project_mv_ortho_fists`). Character descriptions for Soapbox live in
`pipelines/art-to-rig-ralph/output/intake/characters-intake.json`.

**Image generation rules** (winning recipe in
`pipelines/art-to-rig-ralph/docs/CHARACTER-BATCH-RESUME.md`; mv_ortho LoRA
strength 1.0, 768×1024, pose tokens FIRST and LAST):
- **No thin bare limbs** — bare arms vanish in TRELLIS sparse reconstruction
  (punk_king lost both arms 3 times until re-concepted with thick studded
  sleeves + gauntlets; the cape was a red herring). Sleeve/armor every limb.
- **Keep negatives LIGHT** (`open palms, spread fingers, arms lowered, arms at
  sides, A-pose` + at most a couple more) — piling on pose negatives collapses
  the T into an A-pose.
- No large cloth sheets spanning behind limbs (capes must hang inside the
  arm silhouette or stop at the waist).

**Key paths** (all scripts under `pipelines/art-to-rig-ralph/scripts/` unless
noted; Blender = `"C:/Program Files/Blender Foundation/Blender 5.0/blender.exe"`;
Unity project = `D:/Projects/soapbox-unity`).

## Phase 0 — Preflight
- `curl -s http://localhost:8188/system_stats` — ComfyUI must be up on the
  3090 Ti venv (if down: `D:/Projects/ComfyUI/run_3090ti.ps1`; NEVER plain
  system python — memory `project_comfyui_torch_xformers_pin`).
- Confirm both input images exist in `D:/Projects/ComfyUI/input/`.

## Phase 1 — Mesh generation (TRELLIS.2 SINGLE-view, GPU ~5 min)
```
py -3.11 pipelines/art-to-rig-ralph/scripts/trellis_queue.py \
  --workflow MeshOnly --front <front>.png \
  --prefix <Name> --seed 12345
```
**SINGLE front view only.** MULTIVIEW DOES NOT WORK — `MeshOnly_MultiView` needs a
back image, corrupts geometry when fed two separate gens, and its second image
loader errors on a stale default when only `--front` is given. Use `--workflow
MeshOnly` (one image). (User prefers watching in the ComfyUI UI — the job is visible there.)
**Gate**: script exits 0 and prints `OUTPUT <glb>`. Two checks:
1. **W/H bbox ratio ≥ ~0.7** (mesh width / height, world bbox across all mesh
   objects) — confirms the arms reconstructed. Good: pip 0.81, rust 0.85;
   lost-arms failures read 0.37/0.59. If arms are missing, a seed reroll will
   NOT fix it — regenerate the concept images with thicker/sleeved limbs.
2. Render front + hand close-ups (camera at the mesh's ±X extremes, front+top
   ortho) and show the user — fingers must read as thumb + separated masses,
   not a mitten. If mitten: regenerate the concept images with clearer fists;
   do not proceed.

## Phase 2 — Mesh prep
```
Blender --background --python pipelines/art-to-rig-ralph/scripts/prep_character.py -- \
  --input <phase1.glb> --output output/prepared/<name>_v1_prepared.glb \
  --report output/prepared/<name>_v1_prepared_report.json
# NOT the kart-era mesh_prep.py: its island pass deletes TRELLIS triangle-soup
# imports entirely. prep_character.py welds first, always keeps the main island.
# Single-view sources: phase 3 uses --workflow MeshTexturing (front image only).
```
**Gate**: report shows ≤80k faces, 1.8m height, grounded. Show a front render.

## Phase 3 — Texture paint (TRELLIS MeshTexturing, GPU ~5 min)
```
py -3.11 pipelines/art-to-rig-ralph/scripts/trellis_queue.py \
  --workflow MeshTexturing --front <front>.png \
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
`D:/Projects/soapbox-unity/Assets/Animations/<name>/Source/<name>_albedo.png`.
**Dir case trap**: per-character Unity dirs are the LOWERCASE id (`pip/`,
`punk_king/`, `rust/`) — the exact paths the generated editor tools use. On
Windows `Pip`→`pip` silently aliases, but `PunkKing` vs `punk_king` are two
DIFFERENT dirs; a split here made a stale rig validate PASS while the fresh
one sat unused.

## Phase 5 — AccuRIG (MANUAL, user, ~2 min)
Ask the user to: open AccuRIG (`D:\Program Files\AccuRIG\`), load the
`_for_accurig.obj` (appears ~180cm), auto-rig, export FBX to
`D:\Projects\soapbox-unity\Assets\Animations\<name>\Source\<name>_accurig.fbx`
(**lowercase id dir** — must match the generated editor tools' paths exactly).
**Gate** (run immediately when they say done):
```
Blender --background --python pipelines/art-to-rig-ralph/scripts/check_accurig_fbx.py -- <fbx>
```
Must print `ACCURIG_FBX OK` (height ~1.8m, real UVs, rigid bind). If FAIL, the
error line says exactly what to fix. The gate measures the BIND (it clears the
embedded single-frame `0_T-Pose` action AccuRIG ships in every FBX before
measuring — that action re-poses to AccuRIG's canonical T and used to read as
spread 9–16 "shred" on perfectly rigid binds; two needless re-exports were
demanded before this was fixed on 2026-07-05). A slight A-pose bind is fine —
AccuRIG and Unity Humanoid both handle it. Optionally check arm rolls
(consistent within ~10° per side is fine; if wildly inconsistent run
`pipelines/animate-ralph/tools/normalize_rig_rolls_for_unity.py`).

## Phase 6 — Unity packaging + strict validation
Generate the per-character editor tools from the Rookie templates in
`D:/Projects/soapbox-unity/Assets/Editor/` (copy each file, replace
`Rookie`→`<Name>` for class names/menu labels and `rookie`→`<name>` for file
names, and make ALL asset paths use the lowercase id:
`Assets/Animations/<name>/...` — NOT `<Name>`):
`SetupRookieImport.cs`, `BuildRookieAnimator.cs`, `AssignRookieTexture.cs`,
`ValidateRookieHumanoid.cs`. The clip set is SHARED from
`Assets/Animations/Barbarian/Mixamo` (Humanoid clips retarget onto any
Humanoid avatar — no per-character downloads). **Locomotion clips (walk/run)
are ActorCore natives** for the CC_Base skeleton — Mixamo locomotion causes a
left-foot flop through the cross-skeleton retarget (memory
`project_unity_foot_flap`; swap procedure documented there: overwrite the FBX
in place, remap the meta's `takeName`/`lastFrame`, keep clip name/internalID).

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
- Copy deliverables into `pipelines/art-to-rig-ralph/output/final/<name>/`
  with subdirs `artwork/` (T-pose inputs), `mesh/` (prepared glb + AccuRIG
  OBJ), `rigged/` (AccuRIG FBX), `textures/` (albedo + previews), plus
  ASSET-CARD.md (model: pip/punk_king/rust cards).
- Add the character to the lineup viewer's `Characters` array in
  `Assets/Editor/BuildCharacterLineup.cs` (`Tools ▸ Characters ▸ Preview
  Lineup` — side-by-side Play-mode animation check across all racers).
- Commit soapbox-unity (rig+albedo+material+controller+editor tools) and
  comfyui-toolchain (package; `git add -f` past the output/ ignore, commit
  **with an explicit pathspec** — parallel sessions stage unrelated work).

## Known traps (cost real time — read before improvising)
- flash_attn is NOT installed: TRELLIS backends must be sdpa/xformers
  (trellis_queue.py forces this).
- **Thin bare limbs vanish in TRELLIS reconstruction** — sleeve/armor every
  limb in the concept images; W/H bbox gate catches it (punk_king took 4 mesh
  attempts, 2026-07-05).
- **Heavy pose negatives collapse the T into an A-pose** — keep the negative
  list light, pose tokens first+last in the positive.
- prep_character.py's manifold pass is guarded against double-shell TRELLIS
  meshes (unguarded `select_interior_faces` once deleted a mesh 50k→451 faces
  silently) — if PREP_DONE reports a tiny face count or short height, the
  destruction gate now exits 1 instead.
- AccuRIG input: plain OBJ, cm, UVs included. FBX input = shredded bind.
- AccuRIG FBXs embed a single-frame `0_T-Pose` action — it is NOT the bind;
  the gate clears it before measuring. Don't demand re-exports for old-style
  spread failures.
- **Unity dir case**: per-character dirs are the lowercase id; `PunkKing` vs
  `punk_king` are different dirs on Windows and a split silently validates
  stale rigs.
- **Locomotion clips must be ActorCore CC_Base natives** — Mixamo walk/run
  flop the left foot through the cross-skeleton retarget; Foot IK + muscle
  clamps made it worse (memory `project_unity_foot_flap`).
- Never Blender-round-trip the rigged FBX (bind desync); UVs/rolls are fixed
  BEFORE AccuRIG, texture binds in Unity.
- UniRig/retarget_mocap is previz-only (weights melt; limb plane) — ship path
  is AccuRIG + Unity Humanoid, exactly this skill.
- Lessons: `unirig-skin-weights-melt-use-accurig`,
  `hand-rolled-retarget-limb-plane`, `unity-humanoid-bone-roll-normalize`.

## Phase 8 (optional) — animated preview carousel in Godot

Getting a Unity Humanoid character animating in GODOT (e.g. a showcase carousel).
The ONLY path that keeps the skin intact (proven on the GrimForge Bestiary, 4 bipeds):

1. Package the char in Unity (Phase 6) so the AccuRIG rig is a valid Humanoid.
2. Bake the retargeted clip onto the skeleton in Unity: instantiate + Animator w/ avatar,
   `AnimationMode.SampleAnimationClip` each frame, record every bone `localRotation`
   (+ hips `localPosition` only; per-bone position baking flings bones) into a legacy
   `AnimationClip` — SET its `.name` (else the FBX exporter throws a dict-key error).
3. Export **Binary** FBX (default is ASCII, unreadable): `ModelExporter.ExportObjects(path,
   new Object[]{go}, new ExportModelOptions{ExportFormat=ExportFormat.Binary})`
   (package `com.unity.formats.fbx`).
4. Import into a Godot 4.6 project with its **NATIVE ufbx importer** (`godot --headless
   --path P --import`). DO NOT round-trip through Blender (FBX->GLB) — Blender's FBX
   importer breaks the Unity skinned-mesh bind and scrambles it into spikes.
5. Carousel: `load("res://chars/<n>.fbx")` -> instance, find `AnimationPlayer`, set clip
   `loop_mode = LOOP_LINEAR`, play. Verify by screenshotting the running window
   (`get_viewport().get_texture().get_image().save_png()`) — Godot can't render headless.
   Caveat: albedo does NOT survive the Unity FBX export; re-apply `_albedo.png` per material
   in Godot if you need textured (else it renders clay/grey).
   Full detail + the Blender dead-ends: memory `project_ccbase_retarget_scramble`.
