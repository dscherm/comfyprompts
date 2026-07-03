# GS1 — barbarian batch-retarget report

| clip | bones | window (src f) | frames | root motion | src_z | fidelity | dir err | mag | mesh | p99 | ok |
|------|:-----:|:--------------:|:------:|-------------|:-----:|:--------:|:-------:|:---:|:----:|:---:|:--:|
| idle | 18/20 | 30-170 | 141 | off | auto | OK_INPLACE | 0.0 | 1.00 | OK | 1.98 | YES |
| walk | 18/20 | 12-132 | 121 | transfer | auto_travel | OK | 0.0 | 1.00 | MELT | 2.76 | NO |
| run | 18/20 | 12-132 | 121 | off | auto | OK_INPLACE | 0.0 | 1.00 | OK | 1.98 | YES |
| attack | 18/20 | 20-150 | 131 | off | auto | OK_INPLACE | 0.0 | 1.00 | MELT | 2.08 | NO |
| hit | 18/20 | 20-150 | 131 | off | auto | OK_INPLACE | 0.0 | 1.00 | MELT | 2.06 | NO |
| dodge | 18/20 | 8-110 | 103 | transfer | auto_travel | OK | 0.0 | 1.00 | MELT | 2.76 | NO |
| block | 18/20 | 20-170 | 151 | off | auto | OK_INPLACE | 0.0 | 1.00 | MELT | 2.01 | NO |
| wave | 18/20 | 20-170 | 151 | off | auto | OK_INPLACE | 0.0 | 1.00 | OK | 1.95 | YES |
| celebrate | 18/20 | 20-170 | 151 | off | auto | OK_INPLACE | 0.0 | 1.00 | OK | 2.00 | YES |

Output FBX: `output/export/barbarian/<clip>.fbx`  ·  Proof frames: `validation/retarget/gs1_barbarian/`

GATE (all three required): bones >= 18; `fidelity` (exported hip
travel vs the transfer's EXPECTED_TRAVEL: dir err <= 15 deg, mag
0.7-1.4; in-place clips must not drift); `mesh` (integrity under
motion: p99 edge stretch <= 2.0 and bounds within [0.5, 1.8] of
rest — catches weight melting/scramble; calibrated: AccuRIG walk
1.80 OK vs UniRig walk 2.76 MELT vs crossed-skin 18.6 MELT).
Proof frames remain a REQUIRED human check for pose naturalness
(limb plane) — no numeric gate covers it.
