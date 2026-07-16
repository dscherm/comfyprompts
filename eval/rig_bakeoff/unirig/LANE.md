# UniRig lane record (RB3)

## Lane facts (for the RB6 score sheet)

| fact | value |
|---|---|
| Cost | $0 (local, 3090 Ti) |
| Wall-clock, berserkr rig | ~2 min (skeleton → skin → merge, models cached) |
| Wall-clock, hound rig | reused existing `_quadrig` outputs (rigged Jul 6, same 8841-vert input mesh) |
| Manual steps | none for rigging; bone-map axis tuning needed 2 visual iterations (generic bone_N skeleton, arbitrary local axes) |
| Skeleton | generic `bone_0..27` (berserkr, 28 bones incl. finger chains), `bone_0..24` (hound) |
| Output format | rigged GLB (merge keeps source material) |

## Capability gaps (scored results, not footnotes)

1. **No native animation path for humanoids.** UniRig outputs a generic
   skeleton; Mixamo/ActorCore clips can't be applied without cross-skeleton
   retargeting, which is this project's documented failure zone
   (hand-rolled-retarget-limb-plane, ccbase-retarget-scramble lessons).
   Berserkr A1/A2 clips are therefore NOT produced in this lane.
2. **Hound idle (A1) missing** — the existing `hell_hound_walk.glb` carries
   only the walk action. Walk (A2) sampled at 6 frames.
3. **.l/.r labels anatomically swapped** on -Y-facing rigs (known UniRig
   quirk, project_unirig_mirrored_side_labels) — irrelevant to stills, but a
   real cost for anyone hand-animating on this skeleton.

## Renders

- `berserkr/` — S1 knee bend, S2 elbow bend, S3 arms overhead, S4 forward
  spine bend; C1 full + C2 detail each. Bone map: `berserkr_bone_map.json`.
- `hell_hound/` — S1 front knee, S2 hind knee, S3 neck dip, S4 spine curl;
  C1+C2 each; plus `A2_hell_hound_walk_f0..5`. Bone map + clip map alongside.

Judging happens in RB6 (user, per docs/rig_bakeoff_protocol.md) — this file
records facts only, no quality opinions.
