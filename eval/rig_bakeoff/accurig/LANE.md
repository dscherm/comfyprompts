# AccuRIG lane record (RB2)

## Lane facts (for the RB6 score sheet)

| fact | value |
|---|---|
| Cost | $0 (free tool) |
| Manual effort | one GUI session by the user (~5 min): import exemplar_cm.obj, auto-rig with defaults, export FBX |
| Skeleton | CC_Base, 61 vgroups — full finger AND toe chains (richest skeleton of any lane) |
| Output | binary FBX, centimeter scale, T-pose actions only (clips come via the proven Unity Humanoid path, not the FBX) |
| Subject | exemplar (user-supplied), same mesh as UniRig/Meshy lanes |

## Diagnostics rendered

`exemplar/`: S1 deep knee bend, S2 elbow bend, S4 forward spine bend — all
clean, world-axis poses (`exemplar_bone_map.json`). A1/A2 clips absent by
design (see above).

## S3 (arms raised) EXCLUDED — unresolved posing anomaly, do not judge from it

Raising the upper arms in Blender smears the sleeve/shoulder geometry into
giant membranes on this FBX — under every method tried (local euler axis 1
and 2, both signs; world-axis quaternion, both signs; clavicle-assisted
25°+55°). Facts that bound the cause:

- The identical world-axis method renders S3 cleanly on the UniRig rig of
  the SAME mesh, and S1/S2/S4 of THIS rig are clean.
- A control test on the proven berserkr_accurig.fbx (a rig that animates
  correctly through Unity in production) smears identically → NOT a defect
  of this rig session.
- Displacement audit: an 80° upper-arm rotation moved forearm/hand verts
  >1.2 m where the maximum rigid arc is ~0.54 m — more than geometry
  allows, implicating Blender's direct posing of CC twist-bone chains
  rather than the skin weights.

Conclusion: judging AccuRIG shoulders requires the Unity-baked-clip path
(as production does), not direct Blender posing. The smeared S3 renders are
an artifact of the harness/rig interaction and are unadjudicable; treat the
lane's shoulder quality as PENDING a Unity-path render.

Judging happens in RB6 (user, per docs/rig_bakeoff_protocol.md).
