---
title: Rig-quality judging galleries need motion clips and posed-diagnostic labels
severity: medium
tags: [eval, human-in-the-loop, gallery, rigging, judging]
source: hand-authored
created: 2026-07-16
project: comfyui-toolchain
---

## Symptom

Two judging distortions in the 2026-07-16 rig bake-off, both from gallery
design rather than the rigs: (1) the user's direct feedback — "it's tough
to judge with just images" — stills alone under-informed the verdict until
looping walk MP4s were added; (2) the user read a posed diagnostic still
(arms-overhead, applied by the render harness) as an animation choice —
"i'm assuming it would be easy to change the animation so the arms are
down" — scoring commentary aimed at something that isn't part of the lane.

## Root cause

Rigs exist to move; a still can only show deformation at one instant, and
a reviewer naturally reads any depicted pose as authored content unless
told otherwise. The gallery presented harness-posed diagnostics and
lane-supplied animations with identical visual weight.

## Mitigation

1. Every rig-judging gallery includes at least one LOOPING motion clip per
   lane that can produce one; a lane that cannot is shown with an explicit
   "no motion path" note — absence is a scored fact, not an empty cell.
2. Label harness-posed stills as such ("posed diagnostic — bone rotation
   applied by the render harness, not lane output") so deformation is
   scored, not the pose choice.
3. Short single-cycle clips are fine — loop them (`<video autoplay loop
   muted playsinline>`); 1s at 640² H.264 is ~20KB, cheap to embed as a
   data URI.

## Notes (optional)

Blender builds without the FFmpeg encoder (file_format enum lacks FFMPEG)
render PNG frame sequences instead; assemble with system ffmpeg
(scripts/rig_bakeoff/blender_render_clip_video.py documents the pattern).
Related: bakeoff-subject-needs-user-approval-first,
perceptual-ground-truth-needs-human-signoff.
