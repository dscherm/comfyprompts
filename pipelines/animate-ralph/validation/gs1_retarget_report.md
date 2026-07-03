# GS1 — barbarian batch-retarget report

| clip | bones | window (src f) | frames | root motion | src_z | misalign | ok |
|------|:-----:|:--------------:|:------:|-------------|:-----:|:--------:|:--:|
| idle | 18/20 | 30-170 | 141 | off | auto | 82.4 | YES |
| walk | 18/20 | 12-132 | 121 | transfer | auto | 91.0 | YES |
| run | 18/20 | 12-132 | 121 | off | auto | 72.3 | YES |
| attack | 18/20 | 20-150 | 131 | off | auto | 82.4 | YES |
| hit | 18/20 | 20-150 | 131 | off | auto | 71.8 | YES |
| dodge | 18/20 | 8-110 | 103 | transfer | auto | 124.0 | YES |
| block | 18/20 | 20-170 | 151 | off | auto | 96.6 | YES |
| wave | 18/20 | 20-170 | 151 | off | auto | 71.5 | YES |
| celebrate | 18/20 | 20-170 | 151 | off | auto | 90.8 | YES |

Output FBX: `output/export/barbarian/<clip>.fbx`  ·  Proof frames: `validation/retarget/gs1_barbarian/`

## Caveats (2026-07-03 re-run, post-fix)

- Re-generated with the FIXED retarget_mocap.py (rotation-only transfer, keyed
  locations, side-swap detection, chain-child ALIGN, src_z=auto). All 9 proof
  renders now show upright, source-tracking poses — compare git history for the
  pre-fix scrambled frames.
- The `misalign` column is diag_facing's travel-vs-feet-facing angle. It is
  MEANINGLESS for in-place clips (travel is noise) and unreliable in general —
  do NOT gate on it. Judge the proof frames.
- Root motion (walk/dodge "transfer") reproduces the pose correctly but travel
  magnitude/direction vs facing has not been re-verified — open follow-up.
