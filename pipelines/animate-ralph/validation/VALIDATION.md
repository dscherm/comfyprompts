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

## What's left for library-driven mocap (the hard part)
With names aligned, the remaining step is the **rotation retarget itself** — transferring
Mixamo `Character1_*` clip rotations onto the renamed rig. This needs rest-pose-relative
transfer + facing/scale calibration (Mixamo and UniRig rest poses/orientations differ),
which is best done with a retarget addon (Rokoko/Auto-Rig Pro) or the blender-mcp visual
loop, not a blind headless rotation-copy. The naming groundwork (this script) is the
prerequisite that was missing. Procedural keyframing (the wave above) works today without it.
- **Textures:** UniRig output drops materials, so the rigged mesh renders untextured
  (low contrast) — fine for motion validation; re-apply the source texture for beauty shots.
- This was a focused single-clip validation, not the full 6-stage / multi-clip pipeline run.
