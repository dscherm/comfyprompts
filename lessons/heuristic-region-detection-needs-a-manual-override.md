---
title: Geometry-region heuristics fail on outliers — ship a manual override, don't over-tune
severity: low
tags: [blender, mesh, heuristic, materials, iteration-discipline]
source: hand-authored
created: 2026-07-18
project: comfyui-toolchain
---

## Symptom

A position+width heuristic assigned a brown "grip" material to low-poly swords:
find the crossguard = the widest lateral cross-section on the handle half, paint
the narrow band just below it. It worked cleanly on 3 of 4 swords. The **broadsword**
defeated it — its widest cross-section is mid-BLADE, not the guard — so the brown
landed on the blade. Four tuning passes (restrict guard search to the bottom
half → bottom 35 %, add a lateral-width filter, add a gap) never fixed that one
mesh; it was dropped.

## Root cause

A geometry-region heuristic encodes assumptions about TYPICAL proportions ("the
handle end is widest and lowest"). Outliers violate the assumption, and tuning a
threshold to catch the outlier tends to shift the failure elsewhere — you chase a
moving target instead of converging.

## Mitigation

1. **Add the manual-override escape hatch FROM THE START**, not after the auto-
   detector fails. (Here: an optional explicit grip-band `<lo> <hi>` arg.) A
   heuristic that's right for the majority + a manual override for outliers beats a
   "perfect" auto-detector.
2. **Cap the tuning.** After ~2-3 attempts on ONE stubborn instance, switch to the
   override or drop that instance and move on — the marginal fix isn't worth more
   iterations (4 here before dropping the broadsword).
3. When you do drop an instance, say so and why in the manifest/commit — an honest
   "dropped, geometry defeated the heuristic" beats a silently-mis-coloured asset.
