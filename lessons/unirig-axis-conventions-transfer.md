---
title: UniRig bone-local axis conventions transfer across meshes — tune once, reuse
severity: low
tags: [unirig, rigging, blender, pose]
source: hand-authored
created: 2026-07-16
project: comfyui-toolchain
---

## Symptom

Posing a UniRig (ArticulationXL) skeleton via rotation_euler needs the
right bone-local axis per joint, and the generic bone_N names give no
hint. Naive expectation: re-derive axes by visual iteration for every new
mesh. Observed instead (2026-07-16 rig bake-off): axes tuned on one rig
(berserkr — 2 visual iterations to find axis 0 = flex for knees/elbows/
upper-arm raise/spine bend) worked FIRST-PASS on a different mesh's rig
(exemplar, 52 bones incl. finger chains).

## Root cause

UniRig's skeleton generator emits consistent bone-local orientation
conventions across meshes of the same body plan — the local flex axis
lands on the same euler index. The arbitrariness is per-generator, not
per-mesh.

## Mitigation

1. Keep a per-body-plan axis table (humanoid: axis 0 = flex on calf,
   forearm, upper-arm raise, spine bend; see
   eval/rig_bakeoff/unirig/*_bone_map.json) and start every new UniRig
   pose map from it.
2. Identify bones by world POSITION (chains from the root; legs = low-z
   chains, arms = lateral mid-height chains) — never by name.
3. Only visual-iterate on the poses that miss; expect most to land.

## Notes (optional)

Scope: rotation direction (sign) can still vary with limb side; verify
renders before shipping. For ANIMATION (not stills) the world-axis
quaternion method in quad_anim_v2.py remains the robust path — this
lesson is about quick diagnostic posing.
