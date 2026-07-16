# Meshy lane record (RB4)

## Lane facts (for the RB6 score sheet)

| fact | value |
|---|---|
| Cost | 5 credits (balance was 1300; ~USD cents) |
| Wall-clock | 90 s cloud time, fully automated (scripts/rig_bakeoff/meshy_rig.py) |
| Manual effort | none (direct REST API; key in keyring) |
| Skeleton | Mixamo-style, 24 bones — NO finger or toe bones (vs UniRig 52 w/ fingers, AccuRIG 61 w/ fingers+toes) |
| Input constraint | **≤300k faces** — the exemplar (490k) had to be decimated to 280k, the only lane whose input mesh differs (recorded deviation); also wants textured GLB (accepted our untextured one anyway) |
| Output | rigged GLB + FBX, plus pre-made walking/running animation GLBs (no idle — A1 gap) |
| Animations | walk/run included free with the rig; wider library exists via a separate animation endpoint |

## Route history (why not coplay)

coplay-mcp's auto_rig_3d_model failed opaquely 4x with nothing in Unity's
console; the direct API revealed the cause: the 490k-face input exceeded
Meshy's 300k cap (the coplay wrapper surfaces no error detail). Lane now
runs via the REST API — reproducible without Unity open.

## Diagnostics

`exemplar/`: S1/S2/S3/S4 stills (world-axis poses, `exemplar_bone_map.json`)
+ A2 walk frame strip sampled from anim_walking_glb_url.glb. The two ~42MB
full animation GLBs are NOT committed — re-download via the URLs in
task_result.json (task 019f6c48-6d46-754a-ae35-695dc57e78a2).

Judging happens in RB6 (user, per docs/rig_bakeoff_protocol.md).
