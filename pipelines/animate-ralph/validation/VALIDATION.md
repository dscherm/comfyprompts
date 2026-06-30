# animate-ralph — end-to-end validation (mv_ortho → … → animation)

**Date:** 2026-06-25

Validated that animate-ralph closes the full art-to-animation chain on a character we
generated from scratch — extending the mv_ortho proof one stage further:

```
mv_ortho art  →  Hunyuan3D mesh  →  UniRig rig  →  animate-ralph clip
(wide T-pose)    (separable limbs)   (28-bone)       (wave, exported GLB)
```

## What was run
- **Input rig:** the UniRig-rigged barbarian (`barbarian_rigged.fbx`, 28 bones, generic
  `bone_N` names) produced earlier in the mv_ortho chain.
- **Clip:** a 48-frame (2s @ 24fps) **wave** — procedural keyframing via blender-mcp
  (`bone_8` shoulder raise + `bone_10` forearm flap). Procedural, not mocap-retarget,
  because UniRig rigs have generic bone names (the mocap path needs a retarget map).
- **Export:** `output/export/barbarian_wave.glb` (4.6 MB, with animation; gitignored as
  pipeline output).

## Result — PASS
Rendered keyframes confirm the motion (`wave_rest.png` → `wave_arm_raised.png` →
`wave_forearm_flap.png`): from a symmetric T-pose the right arm raises and the forearm
flaps side-to-side while the torso, legs, and left arm stay put. Clean, isolated
articulation — the rig animates correctly and exports as a game-ready clip.

## Bone-rename WIRED IN (mocap-retarget groundwork)

`scripts/rename_unirig_bones.py` (reusable, headless) auto-detects bone roles by
topology/position and renames a UniRig rig + its vertex groups to the standard role
names the retarget maps target (`hips`, `upperarm.l`, `foot.r`, …). On the barbarian it
hits **19/19 `mixamo_to_unirig.json` targets** → `barbarian_renamed.glb` is retarget-ready.

The detection logic is lifted from autorig-ralph's `apply_driving_pose.py`, but that
topology heuristic **missed the arms** on this UniRig skeleton, so this script adds a
**position-based arm fallback** (bones out to the side at shoulder height) + a head
fallback — taking coverage from 10/19 → 19/19.

```bash
blender --background --python pipelines/animate-ralph/scripts/rename_unirig_bones.py -- \
    <unirig_rigged.fbx> <renamed.glb>
```

## Rotation retarget — WORKING (mocap walk transfers; proven live)

`scripts/retarget_mocap.py` transfers a Mixamo/Rokoko (`Character1_*`) clip onto the renamed
rig via `mixamo_to_unirig.json`. Bone matching is **20/20**. The first attempt collapsed to a
flat sprawl — root-caused via the blender-mcp visual loop to a **scale bug**: the mocap source
is scaled 0.01 (Mixamo cm→m) and `.to_3x3()` baked that scale into the rotation matrices.
**Fix: pure quaternions** (scale-free). Result, rendered live: an **upright barbarian walking**
— legs cycling through stride poses across frames (`validation/retarget/walk_f00..59.png`).

So the full chain reaches library-driven mocap:
```
mv_ortho → Hunyuan3D → UniRig → rename_unirig_bones (19/19) → retarget_mocap (Mixamo walk)
```

**Export: SOLVED — use FBX, not glTF.** Chasing the "broken export" uncovered a stack of
issues that were mostly *rendering* artifacts, plus one real one:
- The exported scene had a stray **Icosphere** (size 2) that my render scripts framed instead
  of the character; the character is at **~0.01 scale** (UniRig bind pose) so it sat invisible;
  and its material needed **force-opaque** + a clip-safe camera. Fixing the *render* showed the
  character fine.
- The real blocker: **Blender's glTF exporter DROPS the baked armature animation** (exports a
  static rest pose), confirmed by identical frames. **FBX retains it** — distinct walk poses
  across frames (`validation/retarget/fbx_walk_f00.png` vs `fbx_walk_f40.png`). FBX is also the
  game-engine animation format, so it's the right target.

Deliverable: `output/export/barbarian_walk.fbx` (rigged + animated). Imports at ~0.01 scale —
set the engine's FBX import **Scale Factor ≈ 100** (same as stock Mixamo FBX).

**Full chain working end-to-end:** mv_ortho → Hunyuan3D → UniRig → rename (19/19) →
retarget (Mixamo walk) → **animated FBX**.

**Head-bone artifact — FIXED.** Root cause: UniRig's auto-rename mis-detected the upper
spine ("neck" was actually the arm-branch bone, "head" hung off an unnamed bone), so the
mocap head/neck rotations swung the head into a stretched spike. Fix: `retarget_mocap.py`
now **skips `head`+`neck`** (leaves them at rest — a neutral head reads fine on a walk; arms
are separate bones, still retargeted). Re-rendered: spike gone, walk intact
(`validation/retarget/fbx_walk_f*.png`). Deliverable `barbarian_walk.fbx` refreshed.

**Root motion (forward locomotion) — DONE.** The walk used to play **in place**: the
retarget pinned *every* bone — including the hips/root — to its rest world position
(`loc = rest translation`), discarding the source clip's forward travel. Headless probes
confirmed the source (`rokoko_legacy_halo_elitewalking.fbx`, `Character1_*`, matching the
map) carries 0.54 of hip travel that was being thrown away. Fix: a `[root_motion]` arg on
`retarget_mocap.py`:
- `transfer` (**default**) — replays the source hips' world travel onto the target hips,
  added to **every** bone's world target as a rigid shift (so the whole body advances, not
  just a detached hip), `location`-keyed on the hips only. Scaled by the **leg-length
  ratio** (hips→foot Euclidean distance — orientation/sign-safe; hip-height ratio gave a
  bogus negative scale because UniRig rigs import with the hips below origin).
- `off` — legacy in-place behavior. `<float>` — synthesize a constant forward speed for
  genuinely in-place source clips.

Verified on the barbarian: output hips travel **0.50 world units** (~½ leg-length) over the
60-frame clip (`HAS_ROOT_MOTION`); top-down renders show the character translating across
the ground (`validation/retarget/rootmotion_top_f0{01,60}.png`); gait intact in 3/4 view
(`rootmotion_ortho_f0{01,30,60}.png`). **Foot-slide check passes** — each foot still hits a
planted stance (`min` horizontal speed ≈ 0.0001) while the body advances, and the swing foot
peaks higher than in-place (0.215 vs 0.115) to keep up: real locomotion, not moonwalking.
Deliverables: `output/export/barbarian_walk.fbx` (now forward-moving) +
`barbarian_walk_inplace.fbx` (legacy in-place, kept for engine-driven locomotion).
- **Textures:** UniRig output drops materials, so the rigged mesh renders untextured
  (low contrast) — fine for motion validation; re-apply the source texture for beauty shots.
- This was a focused single-clip validation, not the full 6-stage / multi-clip pipeline run.

## Text-to-motion (MDM) — NOVEL clip generated + retargeted (Phase MT, 2026-06-27)

Extended the mocap-library path with a **text-to-motion** alternative: a text prompt →
novel animation → same retarget chain → animated barbarian FBX. Model: **MDM**
(`humanml_enc_512_50steps`, 50 steps), research/non-commercial weights → **previz only**.

```
text prompt  →  MDM  →  mdm_to_source.py  →  retarget_mocap.py  →  animated barbarian FBX
"walks fwd       results.npy   mdm_clip.fbx        (root motion)        (faces its travel)
 and waves"      (22-joint xyz) Character1_* bones   18/20 bones
```

- **MT1 — generate:** `python -m sample.generate ... --text_prompt "a person walks forward
  and waves"` on the 3090 Ti → `results.npy` (6 samples, 22-joint xyz, 120 frames). Env
  fixes: the HumanML3D `text_only` loader asserts `len>1`, so `dataset/HumanML3D/test.txt`
  must hold the full split (it had been cut to a single id); and SMPL `.pkl` load needs
  `chumpy`, patched for numpy 1.26 (`chumpy/__init__.py` imported removed `np.bool` etc.).
- **MT2 — source + retarget:** `mdm_to_source.py results.npy mdm_clip.fbx` builds a
  `Character1_*`-named animated armature (positions→bone-aim solve); `retarget_mocap.py`
  onto `barbarian_renamed.glb` matches **18/20** bones, `root_motion transfer` (leg-ratio
  scale 1.07). Hips travel **3.71** world units, Z≈0 → grounded forward locomotion.
- **MT3 — facing calibration:** the `load_joints` Y-up→Z-up map was already correct
  (character is **upright, not rolled**), so only the source facing needed aligning to the
  travel direction. Measured objectively with `diag_facing.py` (feet `+Y`/toe direction =
  true front, vs hips displacement = travel): at `src_z=0` the body faced **39°** off its
  travel. `src_z` rotates **facing** (travel is invariant), ≈ −1.08°/deg. **`src_z=-36`**
  drives misalignment to **0.7°** — the character now walks facing where it travels.
  Proof: `validation/retarget/barbarian_mdm_{ortho34,top}_f*.png`.

```bash
# reproduce the calibrated clip
blender --background --python scripts/retarget_mocap.py -- \
    barbarian_renamed.glb mdm_clip.fbx mixamo_to_unirig.json out.glb 0 119 -36 transfer
```

Deliverable: `barbarian_mdm.fbx` (rigged + animated, faces travel). Research-license previz.

### MT4 — promoted into the pipeline + one-command orchestrator

The bridge scripts are now the pipeline's single source of truth under
`scripts/`: `mdm_to_source.py` and `diag_facing.py` (facing/travel measurement) joined
`retarget_mocap.py` and `render_rootmotion.py`. **`generate_motion.py`** orchestrates the
whole chain in one command — `[MDM generate] → mdm_to_source → retarget_mocap → FBX`:

```bash
# CPU/Blender only: reuse an existing MDM results.npy, auto-calibrate facing
python scripts/generate_motion.py --results <results.npy> \
    --rig barbarian_renamed.glb --out out/walkwave.fbx --auto-face

# full chain incl. GPU generation (ComfyUI must be stopped first)
python scripts/generate_motion.py --generate --prompt "a person walks forward and waves" \
    --rig barbarian_renamed.glb --out out/walkwave.fbx --auto-face
```

- **GPU gate (explicit + enforced):** generation is OFF unless `--generate` is passed, and
  the orchestrator **refuses while ComfyUI is listening on :8188** (`--force-gpu` overrides)
  so it never silently grabs the 3090 Ti. Stop ComfyUI first; restart with `run_3090ti.ps1`.
- **`--auto-face`:** retargets a src_z=0 probe, measures misalignment via `diag_facing.py`,
  and solves `src_z = -misalign / 1.08` (the measured facing response) so the body faces its
  travel with no hand-tuning. Verified end-to-end: probe misalign 39° → `src_z=-36.1` →
  final **18/20 bones, misalign 0.5°**.
- Defaults (Blender exe, MDM dir/venv/model, tmp) are env-overridable
  (`BLENDER_EXE`, `MDM_DIR`, `MDM_PYTHON`, `MDM_MODEL`, `MDM_TMP`).

**LICENSE CAVEAT — PREVIZ ONLY.** MDM and its AMASS / HumanML3D weights are
**research / non-commercial**. Every clip from this path is **previsualization, not
shippable game content** — block out motion and validate the rig with it, but ship only
clips from a commercially-licensed source (e.g. the Mixamo/Rokoko library path). The
license note is printed by `generate_motion.py` on every run.

**Three prompts validated end-to-end through `generate_motion.py --generate --auto-face`**
(proof frames in `validation/retarget/`), each 18/20 bones:

| prompt | src_z (auto) | misalign | hip travel | reads as |
|--------|-------------:|---------:|-----------:|----------|
| "a person walks forward and waves" | −36 | 0.7° | 3.71 (horizontal) | upright walk, faces travel, waves |
| "a person jumps and punches the air" | 130 | −8.7° | 0.05 (in place) | upright, arm extended in a punch |
| "a person crouches down and picks something up" | −22.4 | 2.2° | 0.61 (Z −0.51) | forward bend/reach, hips drop = crouch |

Notes: for near-in-place motions (jump, crouch) the net f0→fN hip travel is small, so the
**travel direction is ill-defined and `--auto-face` is less meaningful** (the jump's −8.7°
residual reflects this, not a retarget error) — facing calibration matters mainly for
locomotion. The `--auto-face` single-probe linear solve (slope 1.08) lands within a few
degrees; for a hero clip, hand-set `--src-z` after reading the `diag_facing` report.
The path accepts any HumanML3D-style prompt — generation is the only GPU-gated step.

## Phase GS — Unity packaging + validation (barbarian Humanoid clip set)

The proven single-character chain was packaged as a **shippable, multi-clip Humanoid
animation set** for the game project (`../soapbox-unity`), mirroring the kart deploy.

**Shippable path (GS1–GS3, committed):**
```
commercial mocap library  →  batch_retarget.py  →  9 barbarian FBX clips
(Rokoko/Mixamo, licensed)     (rename + retarget    (idle/walk/run/attack/hit/
                               + per-clip root motion) dodge/block/wave/celebrate)
        →  package_for_unity.py  →  soapbox-unity/Assets/Animations/Barbarian/
           (Humanoid import, BarbarianAvatar, Barbarian.controller + ANIMATION-MANIFEST.json)
```

**Clip inventory (9, all Humanoid @100fps; see `Assets/Animations/Barbarian/ANIMATION-MANIFEST.json`):**
locomotion — `idle` (1.4s, loop), `walk` (1.2s, loop, root-motion), `run` (1.2s, loop,
root-motion); actions — `attack` (1.3s), `hit` (1.3s), `dodge` (1.02s, root-motion),
`block` (1.5s); emotes — `wave` (1.5s), `celebrate` (1.5s).

**Humanoid avatar — `BarbarianAvatar`** (CreateFromThisModel on `idle.fbx`, CopyFromOther
onto the other 8). All **15 required** Mecanim human bones map (hips/spine/chest/neck/head,
both arms shoulder→hand, both legs upperleg→foot). 9 filler/connector bones have no Mecanim
slot and are left unmapped (extra spine `bone_3/4`, arm twist `bone_9/11/13/16/18`, pelvis
`hip_connector.l/r`) — expected, not a mapping failure. **Animator** `Barbarian.controller`:
default `Idle`, `Speed` float drives idle↔walk↔run, triggers (`Attack/Hit/Dodge/Block/Wave/
Celebrate`) fire from AnyState and exit-time back to Idle.

**Source policy:** library retargets (`batch_retarget.py`) are **SHIPPABLE**; MDM
(`generate_motion.py`, Phase MT) output is **previz only** and never shipped.

**GS4 — validation: PARTIAL (offline artifacts complete, live editor validation deferred).**
An editor validator `Assets/Editor/ValidateBarbarianAnimImport.cs` was authored (mirrors
`ValidateKartAnimImport.cs`): it checks all 9 FBXs import as Humanoid with a usable clip,
the avatar is valid/Humanoid with ≥15 mapped bones, the controller's states/transitions/
parameters load, and a headless rig-build resolves every state's motion clip. It exposes
both a live-MCP entry (`Execute()`) and a headless batch entry (`RunBatch`, writes
`barbarian_validation_report.txt` + exit code).
- **Deferred:** the headless batch run (`-executeMethod ValidateBarbarianAnimImport.RunBatch`)
  exited **198 — "No valid Unity Editor license found"** (licensing/activation, not a
  validator or asset fault). Live coplay-mcp import + play-mode transition verification is
  therefore deferred to a licensed editor session. The artifacts (validator, packaged clips,
  avatar, controller, manifest) are in place and ready to run the moment the editor opens.

---

## Phase UH — Unity Humanoid + Mixamo (the SHIPPABLE route): **PASS** (live coplay, 2026-06-30)

Supersedes the GS4 deferral above: the live editor validation was completed via
**coplay-mcp** against Unity `6000.4.0f1` open on `../soapbox-unity`. New validator
`Assets/Editor/ValidateBarbarianHumanoid.cs` returns **RESULT: PASS** (all 4 sections).

- **UH1 — coplay round-trip:** verified (`list_unity_project_roots` →
  `get_unity_editor_state` → `ValidateBarbarianHumanoid.Execute()`); reconnect
  procedure recorded in `stages/07-unity-humanoid-packaging.md`.
- **UH2 — character:** `barbarian_accurig.fbx` → Humanoid, `CreateFromThisModel`;
  `barbarian_accurigAvatar` isValid && isHuman, **22 bones**. Embedded URP/Lit material
  extracted to `Source/Materials/Material_0.mat`, `barbarian_tex.png` on `_BaseMap`
  (UVs align). §1 PASS.
- **UH3 — Mixamo clips:** 9/9 (idle/walk/run/attack/hit/dodge/block/wave/celebrate)
  imported **CreateFromThisModel** (own humanoid avatar; runtime muscle-space retarget).
  **Generic Mixamo clips cannot use Copy-From-Other onto the AccuRIG avatar** — bone
  names mismatch, no clip emits — so the validator §2 was corrected to accept
  CreateFromThisModel OR CopyFromOther. Loop Time on idle/walk/run. §2 PASS.
- **UH4 — Animator + validate + cleanup:** all 9 `Barbarian.controller` states bound to
  their Mixamo clips (default `Idle`, `Speed` float + 6 AnyState triggers). Validator
  §3/§4 PASS. **Live play-mode** capture shows **natural arm/leg carriage** (relaxed
  idle, upright torso) — the `hand-rolled-retarget-limb-plane` previz splay (45° back-
  lean + arms-up) is gone; sampled Mixamo walk confirms a clean stride. Stale Jun-27
  previz FBXs deleted from `Assets/Animations/Barbarian/`; `ANIMATION-MANIFEST.json`
  regenerated for the Mixamo set.
