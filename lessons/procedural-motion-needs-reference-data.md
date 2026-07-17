---
title: Procedural motion/behavior needs reference data, not hand-fudged formulas
severity: medium
tags: [animation, procedural, research, biomechanics, modelling]
source: hand-authored
created: 2026-07-17
project: comfyui-toolchain
---

## Symptom

Half of a synthesized behaviour is built from real reference data and reads
convincingly; the other half is invented from an ad-hoc formula and reads wrong —
and the wrong half is exactly the fudged one. Observed 2026-07-17 building a
procedural walk: the LEGS used a normative sagittal gait table (hip/knee angles
per % of cycle) and looked natural; the ARMS used an invented `sin` scaling with
a DEAD-STRAIGHT elbow, and looked wrong in every way the user flagged in turn —
hands clipping the body, elbow in the wrong plane, snake-like swing — until the
actual arm-swing kinematics were researched (elbow ~30 deg ROM, flexes forward;
upper arm leads, forearm/hand follow with drag).

## Root cause

Inventing the math for something that mimics a real physical process is the same
mistake as assuming a rig convention instead of measuring it: a plausible formula
is not the real relationship. The real motion has structure (phase lags, joint
coupling, overlap/drag) that a symmetric sine cannot express, and the eye catches
the difference immediately. A reference exists for almost any real motion; not
consulting it is a choice to guess.

## Mitigation

1. **When synthesizing motion/behaviour that imitates something real, find the
   reference first**: biomechanics tables (gait kinematics), animation craft
   (Animator's Survival Kit: arcs, overlap, drag, follow-through), published
   curves. Cite it in the code.
2. **If one part is researched and another fudged, the fudged part is where it
   will look wrong** — audit the fudged part first when something reads off,
   rather than tuning parameters on the researched part.
3. **Match fidelity across parts.** Don't pair a data-driven leg with a
   hand-waved arm; the mismatch is conspicuous.
4. Capture the reference itself as a durable artifact (a wiki page), so the next
   use starts from the data, not another guess.

## Notes (optional)

Same family as the "measure, don't assume" rig lessons
([[unirig-axis-conventions-transfer]], the knee-sign / palm-sign fixes): whether
the unknown is a rig's convention or a body's kinematics, measure or look it up —
do not invent it. Reference lives at wiki `anatomy-of-the-human-walk-cycle`.
