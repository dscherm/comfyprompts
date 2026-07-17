---
title: Suppressing a hue in a negative prompt rotates the flood to its complement — it doesn't remove it
severity: medium
tags: [prompting, flux, negative-prompt, lora, dataset-generation]
source: hand-authored
created: 2026-07-16
project: comfyui-toolchain
---

## Symptom

A generation floods the frame with an unwanted colour. You add that colour to the
negative prompt. The flood returns — same size, same flatness — in a *different*
colour. Adding the new colour to the negative rotates it again.

Measured across three pilots on the occult_providence dataset (2026-07-16), 30
generations, ~30 min of 3090 Ti time:

| pilot | negative | resulting flood |
|---|---|---|
| v1 | suppress **blue** (`blue tint, blue skin, blue light, blue wash`) | flat **RED** backgrounds |
| v3 | suppress **red** + `coloured background, colour wash, tinted backdrop` | flat **CYAN** backgrounds |

The subject was on-spec in both. Only the field behind it moved around the colour
wheel, landing each time on roughly the complement of whatever was suppressed.

## Root cause

Something in the *positive* side of the recipe — the LoRA's learned bias, a lighting
clause, a style token — demands a coloured field behind the figure. The negative
prompt cannot remove that demand; it only removes one *answer* to it. The sampler
satisfies the demand with the nearest hue not under suppression, which is why the
result reads as the complement.

Negatives subtract candidates. They do not subtract requirements.

## Mitigation

1. **If a defect returns in a new colour after you negate it, STOP adding negatives.**
   That recurrence is the diagnostic: the requirement lives in the positive prompt or
   the model, and no amount of negation will reach it. Three rounds of this cost three
   pilots.
2. **Find what is demanding it.** Here, entries using `CREATURE_STY` (no lighting
   clause) mostly came out on plain white, while `HUMAN_STY` — carrying *"moody
   asymmetric side lighting"* plus a `flat frontal lighting` negative — flooded almost
   every time. The lighting clause was asking for a coloured light field.
3. **The positive fix is not free either.** Pinning the background positively (`on a
   plain white background`) DID kill the flood — and silently destroyed the ink style,
   turning carved linework into soft digital painting. The only cells that kept the
   style were the ones that never got the phrase. Check the whole image after a prompt
   fix, not just the defect you targeted.
4. **Consider post-processing over prompt-wrestling.** The fields were flat and
   uniform — trivially chroma-keyable without touching the figure or its linework.
   Three prompt pilots to move a colour around lost to a few lines of masking.

## Notes (optional)

Suppression is not always wrong: the anti-blue negative was genuinely REQUIRED here to
beat the LoRA's blue bias (A/B: with it, ember-orange landed at 0.44%; without it, the
same prompt rendered blue). The failure mode is using suppression to fix a defect it
cannot reach — background composition — not using it at all. Related:
`style-attribute-needs-an-object-to-carry-it`.
