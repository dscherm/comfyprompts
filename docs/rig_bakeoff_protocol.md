# Rig-and-animate bake-off — judging protocol (RB1)

**Question:** which rigging/animation path do we standardize on?
**Contenders:** AccuRIG, UniRig (local), Meshy (via coplay), Tripo (API).
**Subjects:** berserkr (humanoid, 1.80 m) + hell hound (quadruped, 1.0 m) — both
already pipeline-proven, so quality deltas attribute to the rigger, not the mesh.
**Inputs:** `eval/rig_bakeoff/inputs/` (see `manifest.json`; products/ read-only).

## Ground rules

1. **The user judges, Claude does not self-judge** (per
   `lessons/perceptual-ground-truth-needs-human-signoff.md`). Claude prepares
   identical diagnostics per lane, assembles the gallery, and records verdicts.
2. **Every lane renders the same diagnostics** from the same cameras at the same
   resolution. A lane that can't perform a diagnostic records *why* (capability
   gap is itself a result).
3. **Wide framing rule** (per VL9): every diagnostic is captured as BOTH a
   full-body view and a joint-detail view, so any artifact claim is adjudicable.
4. **Costs are results:** each lane records wall-clock time, manual steps
   required, and credit/money spent.

## Diagnostic set

### Still poses (deformation quality)

| id | berserkr | hell hound |
|---|---|---|
| S1 | deep knee bend (~90°) | front knee bend (~75°) |
| S2 | elbow bend (~100°) | hind knee bend (~75°) |
| S3 | arms raised overhead | neck dip (~45°) |
| S4 | torso twist (~40°) | spine curl |

### Animation clips (motion quality)

| id | clip | notes |
|---|---|---|
| A1 | idle | breathing/weight shift; watch for drift and jitter |
| A2 | walk | watch feet (flap/slide), hips, and joint volume loss |

Lanes use the same source clips wherever mechanically possible (the shared
Mixamo/ActorCore set for humanoids, the procedural quad cycles for the hound).
Where a lane substitutes (e.g. Meshy's animation library), the substitution is
recorded on the score sheet.

### Cameras (per diagnostic)

- **C1 full body:** 3/4 front-left, elevation 12°, subject fills ~80% of frame.
- **C2 joint detail:** centered on the diagnostic's primary joint, framed so the
  adjacent body regions (one joint up and down the chain) stay in frame.
- Resolution 1024², neutral studio lighting, identical across lanes. Clips
  render as short MP4/GIF from C1; stills from both C1 and C2.

## Score sheet (user fills one per lane × subject)

| criterion | score 1–5 | notes |
|---|---|---|
| Joint definition under bend (S1–S4: no melt/pinch/collapse) | | |
| Volume preservation (no candy-wrapper, no ballooning) | | |
| Unintended-region stability (cloth/fur/props don't shred) | | |
| Walk quality (A2: no foot flap/slide, believable gait) | | |
| Idle quality (A1: no jitter/drift) | | |
| **Overall: would you ship a game character rigged this way?** | yes / no | |

Plus per-lane facts (Claude fills): wall-clock, manual steps, cost, format
returned, skeleton type, any capability gaps.

## Lane notes (known constraints going in)

- **AccuRIG:** humanoid only; input `berserkr_cm.obj`; ONE manual GUI step
  (documented for reproducibility when it happens). Proven baseline.
- **UniRig:** both subjects; conda env `UniRig`, `CUDA_VISIBLE_DEVICES=1`
  (defaults to cuda:0 = the 3070). Known humanoid weakness: skin-weight melt
  (`lessons/unirig-skin-weights-melt-use-accurig.md`). Known label quirk:
  .l/.r anatomically swapped on -Y-facing rigs.
- **Meshy (coplay):** humanoid only; requires the Unity editor open;
  animation-library substitutions likely for A1/A2.
- **Tripo (API):** user has key + credits; spend is tracked per call. ToS:
  outputs are judged/benchmarked only, never used to train a competing model.
  Whether it accepts the quadruped at all is a recorded result.

## Deliverable flow

RB2–RB5 produce `eval/rig_bakeoff/<lane>/` renders → RB6 assembles the
side-by-side gallery artifact → user judging session (score sheets above) →
`docs/rig_bakeoff_findings.md` with verdicts verbatim, the cost table, and the
standardization recommendation signed off by the user.
