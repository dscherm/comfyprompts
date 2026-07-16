---
title: CC_Base/AccuRIG shoulders smear under direct Blender posing — judge from Unity clips
severity: high
tags: [accurig, cc-base, blender, fbx, rigging, posing]
source: hand-authored
created: 2026-07-16
project: comfyui-toolchain
---

## Symptom

Rotating a CC_Base upper arm (AccuRIG FBX import) in Blender smears the
sleeve/shoulder geometry into giant membranes — under EVERY posing method:
local euler (both axes, both signs), world-axis quaternion (both signs),
and clavicle-assisted (25°+55°). Observed 2026-07-16 on two independent
AccuRIG exports (the bake-off exemplar AND the production-proven
berserkr_accurig.fbx control). Knee, elbow, and spine posing on the same
rigs is clean; the same mesh rigged by UniRig raises arms cleanly.

A displacement audit pins it as impossible-for-rigid-rotation: an 80°
upper-arm rotation moved forearm/hand verts >1.2 m where the maximum rigid
arc is ~0.54 m.

Separate but compounding: AccuRIG FBXs also carry a `Key|0_T-Pose`
SHAPE-KEY action on the mesh (in addition to the armature's pose action)
that keeps morphing vertices toward bind pose during any posed render —
smearing ALL poses — unless cleared.

## Root cause

The shape-key smear is fully understood: clear `mesh.animation_data` and
`mesh.data.shape_keys.animation_data` after import (armature-only clearing
is not enough). The shoulder smear's precise mechanism is NOT pinned down
(twist-chain interaction with Blender's FBX import is implicated); what is
established is that it is not the skin weights — these rigs animate
correctly through the Unity Humanoid path in production.

## Mitigation

1. On any FBX import for posed rendering, clear ALL animation data: the
   armature's, the mesh's, and the shape-keys' (see
   scripts/rig_bakeoff/blender_render_protocol.py `_import_scene`).
2. Do not pose CC_Base upper arms / clavicles directly in Blender for
   quality judgment; render shoulder diagnostics from a Unity-baked clip
   instead. Knee, elbow, and spine direct posing is validated and fine.
3. If a pose smears, run the displacement audit (compare max displacement
   vs the rigid arc = 2·r·sin(θ/2)) before blaming weights — impossible
   displacement means harness/import artifact, not rig quality.

## Notes (optional)

The 2026-07-16 bake-off scored AccuRIG all-1s partly under this shadow;
docs/rig_bakeoff_findings.md records the fairness caveats. Related:
unirig-axis-conventions-transfer (world-axis posing that IS reliable),
hand-rolled-retarget-limb-plane.
