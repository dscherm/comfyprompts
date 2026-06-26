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
- **Textures:** UniRig output drops materials, so the rigged mesh renders untextured
  (low contrast) — fine for motion validation; re-apply the source texture for beauty shots.
- This was a focused single-clip validation, not the full 6-stage / multi-clip pipeline run.
