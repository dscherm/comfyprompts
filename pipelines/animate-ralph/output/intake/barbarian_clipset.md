# Barbarian core gameplay clip set — retarget manifest (Phase GS, GS0)

Source: the **commercially-licensed Rokoko/Mixamo reference library** in
`pipelines/animate-ralph/references/humanoid/`. Target rig:
`E:/ai-training/_animtest/barbarian_renamed.glb` (UniRig, role-renamed via
`rename_unirig_bones.py`). Map: `references/retarget_maps/mixamo_to_unirig.json`.

These are the **shippable** clips (commercial license) — distinct from the MDM previz
path (`generate_motion.py`), which is research-license and must not ship.

## Selection rule discovered during bone-check

Only `rokoko_legacy_*` clips use the `Character1_*` skeleton the map targets. The
`rokoko_*_mixamo.fbx` files use `mixamorig:` bone names and **fail the map (0/20)** — e.g.
`rokoko_SwordIdleMedium_mixamo.fbx` (originally picked for block) was **culled** and
replaced with `rokoko_legacy_idle_fightstance.fbx`. **GS1 must prefer `rokoko_legacy_*`
sources** (or add a `mixamorig:`→role map later if the mixamo-named clips are wanted).

## The 9-clip set (all bone-checked at 18/20 = max; head+neck skipped by design)

| Clip | Source FBX (under `references/humanoid/`) | Matched | Frames | hips xy / z (src units) | Root motion | Loop |
|------|-------------------------------------------|:-------:|:------:|:-----------------------:|-------------|------|
| `idle` | `idle/rokoko_legacy_idle.fbx` | 18/20 | 250 | 0.356 / 0.020 | **off** (in place) | **loop** |
| `walk` | `locomotion/rokoko_legacy_halo_elitewalking.fbx` | 18/20 | 250 | 0.502 / 0.054 | **transfer** (travels) | **loop** |
| `run` | `locomotion/rokoko_legacy_jogginginplace.fbx` | 18/20 | 250 | 0.243 / 0.064 | **off** (in-place jog) | **loop** |
| `attack` | `combat/rokoko_legacy_combat_swingheavygreatsword.fbx` | 18/20 | 250 | 1.101 / 0.038 | **off** (in place) | one-shot |
| `hit` | `combat/rokoko_legacy_taunting_gettingpunched.fbx` | 18/20 | 250 | 0.329 / 0.116 | **off** (in place) | one-shot |
| `dodge` | `combat/rokoko_legacy_explosion_divebackward.fbx` | 18/20 | 250 | 0.298 / 0.036 | **transfer** (evasive move) | one-shot |
| `block` | `combat/rokoko_legacy_idle_fightstance.fbx` | 18/20 | 250 | 0.272 / 0.033 | **off** (hold guard) | **loop** |
| `wave` | `gesture/rokoko_legacy_pilot_wave.fbx` | 18/20 | 250 | 0.598 / 0.293 | **off** (in place) | one-shot |
| `celebrate` | `gesture/rokoko_legacy_emote_celebrate.fbx` | 18/20 | 250 | 0.440 / 0.026 | **off** (in place) | one-shot |

## Root-motion / loop policy rationale

Per `PROMPT.md`: **locomotion uses root motion; everything else animates in place.**
- **transfer** (replay source hip travel, leg-ratio-scaled): `walk` (clear forward
  travel 0.50) and `dodge` (an evasive movement that should carry the character back 0.30).
- **off** (in place): `idle`, `run` (source is *jog-in-place* — its 0.24 xy is foot
  shuffle, not locomotion; synthesize forward speed in-engine or via
  `retarget_mocap.py`'s `<float>` root-motion arg if a moving run is wanted later),
  `attack` (the 1.10 xy is greatsword step-through follow-through; keep in place so the
  engine drives position), `hit`, `block`, `wave`, `celebrate`.
- **loop**: `idle`, `walk`, `run`, `block` (held guard). One-shots: `attack`, `hit`,
  `dodge`, `wave`, `celebrate`.

## Notes for GS1 (batch retarget)

- All sources are **250-frame full ROM takes**. GS1 should select a **representative
  sub-range** per clip (e.g. one clean stride for `walk`/`run`, the swing arc for
  `attack`) rather than baking all 250 frames; record the chosen `f0..f1` per clip.
- **Loop seams** (`idle`, `walk`, `run`, `block`): pick f0/f1 so the first/last pose
  match, then make F-curves cyclic.
- **Watch `wave`**: `hips_z_range=0.293` is high for a wave (the pilot-wave take has
  notable vertical body motion) — verify the proof frame reads as a clean wave; if not,
  swap to another `rokoko_legacy_*` greeting/gesture.
- **Facing**: `--auto-face` (from `generate_motion.py`/`diag_facing.py`) is only
  meaningful for the travelling clips (`walk`, `dodge`); in-place clips need no facing
  calibration (`src_z=0`).
- Bone-check tool: `scripts/bonecheck_mocap.py` (rerun to vet any swapped source).
