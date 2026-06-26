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

## Rotation retarget — ATTEMPTED, confirmed needs calibration

Built `scripts/retarget_mocap.py` (rest-pose-relative world-rotation transfer, parents-first)
and ran it: renamed barbarian + `rokoko_legacy_zombiewalk.fbx` via `mixamo_to_unirig.json`.
- **Bone matching: 20/20** (map resolves cleanly to the renamed rig).
- **Result: BROKEN** — the rig collapses to a flat sprawl. Ruled out orientation (the same
  renamed rig renders perfectly upright statically), so it's the transfer math, not import.

This empirically confirms the earlier call: a **blind headless rest-relative transfer is not
enough** — proper retargeting needs the rest-pose calibration that addons (Rokoko/Auto-Rig
Pro) or a visual-iteration loop provide. `retarget_mocap.py` is kept as the tool skeleton +
this finding (clearly marked NOT WORKING), not a shippable retarget.

**Working today:** procedural keyframing (the wave above) and the bone-rename groundwork
(19/19, retarget-ready). **Next:** drive the retarget through a retarget addon or reconnect
blender-mcp for visual calibration.
- **Textures:** UniRig output drops materials, so the rigged mesh renders untextured
  (low contrast) — fine for motion validation; re-apply the source texture for beauty shots.
- This was a focused single-clip validation, not the full 6-stage / multi-clip pipeline run.
