# Rig bake-off findings (RB6) — FINAL

**Final verdicts (user score sheet, 2026-07-16, verbatim):**

| criterion | UniRig | AccuRIG | Meshy |
|---|---|---|---|
| Joint definition under bend | 5 | 1 | 5 |
| Volume preservation | 5 | 1 | 5 |
| Unintended-region stability | 5 | 1 | 4 |
| Walk quality | 5 | 1 | 4 |
| **Ship it?** | **yes** | **no** | **yes** |

UniRig notes (verbatim): *"i'm assuming it would be easy to change the
animation so the arms are down, but the legs look perfect."* (Reading: the
S3 arms-overhead DIAGNOSTIC pose read as animation — it is a posed still,
trivially changeable; the deformation under it is what was judged.)

## Standardization decision

1. **Quadrupeds: UniRig.** Only capable lane, top scores, already the
   pipeline standard.
2. **Humanoid rigging: UniRig** (perfect scores, free, fully automated,
   finger chains on clean meshes).
3. **Humanoid motion: Meshy** (5 credits buys rig + walk/run clips,
   automated end-to-end via scripts/rig_bakeoff/meshy_rig.py) whenever a
   character must move and hand/procedural animation isn't planned —
   UniRig's humanoid animation gap stands.
4. **AccuRIG: rejected by the user for this pipeline.** Caveats recorded
   for fairness: its S1/S2/S4 stills rendered clean; the shoulder question
   was unadjudicable in Blender (posing artifact, see accurig/LANE.md); it
   had no motion clip in the gallery; and prior production (berserkr via
   Unity Humanoid) shipped successfully on it. The verdict binds this
   bake-off's standardization, not a retroactive judgment of shipped work.
5. **Tripo (RB5): closed as skipped** — account unfunded (balance 0), user
   cost preference against funding; the lane harness is ready
   (tsk_ key in keyring) if that ever changes.

---

# Earlier interim record (still-image round)

**Date:** 2026-07-16 · **Judge:** the user (per protocol, Claude does not self-judge)
**Evidence:** eval/rig_bakeoff/ lanes + judging gallery artifact (three lanes,
identical diagnostics on the user-supplied exemplar mesh + UniRig hell hound).

## User verdicts (verbatim, from the still-image round)

> "i would ship both unirig and meshy, but i don't want to pay for something
> if i don't have to. also you didn't provide the frames for the exemplar
> walking for unirig. and it's tough to judge with just images"

Read: **UniRig and Meshy both pass the ship bar on rig quality; cost
preference favors UniRig; judgment is provisional until motion clips are
reviewed.** The missing UniRig exemplar walk is the lane's structural gap,
not a rendering omission — see below.

## The asymmetry the verdict surfaces

| | UniRig | Meshy | AccuRIG |
|---|---|---|---|
| Humanoid rig quality (user) | ship | ship | S1/S2/S4 clean; shoulders unadjudicated (Blender posing artifact — judge via Unity clip) |
| Quadruped | **only lane that can** | no | no |
| Humanoid animation path | **none** — generic skeleton, no library; retargeting is this project's documented failure zone | walk/run bundled with the rig | proven Unity Humanoid path (shared Mixamo/ActorCore clips), manual |
| Cost | $0 | 5 credits/character (balance 1300) | $0 + one GUI session |
| Automation | full | full (REST API) | one manual GUI step |
| Fingers | yes (this mesh) | no | yes + toes |

"Free" UniRig is only free for rigging; for a humanoid that needs to MOVE,
the animation still has to come from somewhere. Meshy's 5 credits buy the
rig AND locomotion clips. AccuRIG is free end-to-end but manual and needs
the Unity leg.

## Interim recommendation (to confirm after the motion round)

1. **Quadrupeds: UniRig** — unchanged, it is the only local option and the
   hound results are proven (existing pipeline standard).
2. **Humanoids: decide after motion review** between:
   - **Meshy** — cheapest fully-automated rig+motion (5 credits), weakest
     skeleton (24 bones, no fingers);
   - **AccuRIG + Unity clips** — free, richest skeleton, proven in
     production, but manual;
   - UniRig humanoid rigging remains fine for STATIC/previz uses.
3. **Tripo lane (RB5): propose closing as skipped** — account has 0
   credits, and the user's cost preference argues against funding it while
   two shippable lanes are free/near-free. The lane script is ready if
   credits ever appear.

## Motion round (in progress)

Walk clips rendered as MP4 (Meshy exemplar walk; UniRig hound procedural
walk) and embedded in the judging gallery. AccuRIG motion requires the
Unity-baked path and is deferred with its shoulder question. Final verdicts
and the standardization sign-off land here after the user reviews motion.
