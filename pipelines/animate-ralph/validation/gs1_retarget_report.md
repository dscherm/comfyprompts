# GS1 — barbarian batch-retarget report

| clip | bones | window (src f) | frames | root motion | src_z | fidelity | dir err | mag | ok |
|------|:-----:|:--------------:|:------:|-------------|:-----:|:--------:|:-------:|:---:|:--:|
| idle | 18/20 | 30-170 | 141 | off | auto | OK_INPLACE | 0.0 | 1.00 | YES |
| walk | 18/20 | 12-132 | 121 | transfer | auto_travel | OK | 0.0 | 1.00 | YES |
| run | 18/20 | 12-132 | 121 | off | auto | OK_INPLACE | 0.0 | 1.00 | YES |
| attack | 18/20 | 20-150 | 131 | off | auto | OK_INPLACE | 0.0 | 1.00 | YES |
| hit | 18/20 | 20-150 | 131 | off | auto | OK_INPLACE | 0.0 | 1.00 | YES |
| dodge | 18/20 | 8-110 | 103 | transfer | auto_travel | OK | 0.0 | 1.00 | YES |
| block | 18/20 | 20-170 | 151 | off | auto | OK_INPLACE | 0.0 | 1.00 | YES |
| wave | 18/20 | 20-170 | 151 | off | auto | OK_INPLACE | 0.0 | 1.00 | YES |
| celebrate | 18/20 | 20-170 | 151 | off | auto | OK_INPLACE | 0.0 | 1.00 | YES |

Output FBX: `output/export/barbarian/<clip>.fbx`  ·  Proof frames: `validation/retarget/gs1_barbarian/`

`fidelity` compares the exported clip's hip travel against the
transfer's own EXPECTED_TRAVEL: dir err <= 15 deg and mag 0.7-1.4
for travelling clips; in-place clips just must not drift. This is
the gate (plus bones >= 18) — still eyeball the proof frames for
pose quality.
