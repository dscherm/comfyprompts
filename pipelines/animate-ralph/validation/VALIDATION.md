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

## Notes for a real animate-ralph run
- **Bone naming:** to use the mocap reference library + `retarget_maps/`, first run
  autorig-ralph's "rename bones to standard names" step (UniRig `bone_N` → Mecanim/standard).
  Procedural keyframing (as here) works directly on generic names.
- **Textures:** UniRig output drops materials, so the rigged mesh renders untextured
  (low contrast) — fine for motion validation; re-apply the source texture for beauty shots.
- This was a focused single-clip validation, not the full 6-stage / multi-clip pipeline run.
