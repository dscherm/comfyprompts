---
title: Before deleting a training-output dir, verify a deployed copy or the dataset survives — don't infer "superseded" from a version suffix
severity: high
tags: [disk-cleanup, lora, training, rm-rf, data-loss, windows]
source: hand-authored
created: 2026-07-19
project: comfyui-toolchain
---

## Symptom

A disk-space cleanup deleted E: LoRA training-output dirs judged "superseded"
because their names carried a `_v1` / `_v2` / `_gritty` suffix. Four of them
(`soapbox_kart_parts_v1`, `soapbox_racers_v2`, `soapbox_racers_gritty`,
`vibrant_rpg_char_ink`) had **no deployed copy** anywhere, and `rm -rf` on
Git-Bash/Windows **hard-deletes** (it does NOT go to the Recycle Bin). The
trained weights were gone — recoverable only by retraining, and only because the
source datasets happened to still exist. The user had to ask "you didn't delete
the recent ones, did you?" to surface it.

## Root cause

A version suffix does not mean "superseded" — `_v2` is often the *newest, only*
copy, not a replaced one. Inferring deletability from the filename skips the one
check that matters: whether the artifact exists anywhere else. `rm -rf` bypasses
the Recycle Bin, so the guess is unrecoverable, not merely inconvenient.

## Mitigation

1. **Guard every training-output delete on a real check.** Delete a LoRA's E:
   output dir ONLY if a deployed winner is confirmed present in
   `ComfyUI/models/loras/` (assert the file exists, then delete — a scripted
   `[ -f "$winner" ] && rm -rf "$dir"` loop), OR the dataset survives for retrain.
2. **Bucket by evidence, not by name.** "Deployed → safe to delete the archive"
   and "not deployed → keep or confirm the dataset" — never "has a _vN suffix →
   superseded".
3. **Surface what's unrecoverable before acting.** For a bulk delete, list the
   dirs with no deployed copy and no surviving dataset separately, and get
   explicit confirmation — those are the retrain-only losses.
4. On Windows/Git-Bash, treat `rm -rf` as permanent (no Recycle Bin). When in
   doubt, move to a `_trash/` dir first, or reconstitute deployed winners back
   into the folders afterward (as was done here) rather than deleting blind.
