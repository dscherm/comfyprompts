---
title: A style attribute defined only in a spec table won't render — it needs an object in the prompt to carry it
severity: medium
tags: [prompting, dataset-generation, lora, art-direction, character-bible]
source: hand-authored
created: 2026-07-16
project: comfyui-toolchain
---

## Symptom

A design doc assigns a per-entry visual attribute in a table column, the generation
script renders from that doc, and the attribute is simply absent from the output —
or is replaced by whatever the model defaults to.

Observed on occult_providence (2026-07-16). `CHARACTER_BIBLE.md` gave all 20 roster
entries an accent colour in a table (detective→red, antiquarian→blue, medium→violet).
Measured over the 156-image dataset, **only ~9 images** carried the accent the bible
calls the style's defining trait: 77 had no accent at all, 37 were flooded, and the
25 that scored "in band" were mostly diffuse blue *tinting*, not a spot.

Exactly one entry worked (3/6 seeds) — the Lantern-Bearer, the only entry whose
**description** named a discrete small emissive object with an explicit colour word:
*"a faceless herald in black holding a **green-flamed lantern**."*

## Root cause

The prompt is built from the description, not the table. A colour sitting in a spec
column is invisible to the sampler — there is nothing in the text to attach it to and
no object in the scene to carry it. The model does the only thing it can: it applies
the colour as global tinting, or falls back on the LoRA's default bias.

Both halves are required. The Ashling's description said *"ember eyes"* — a small
object, but the colour only *implied* — and it rendered **blue**. Changed to
*"eyes burning **ember-orange**"*, it rendered orange at 0.44% coverage.

A second, independent instance of the same bug: the generation script's descriptions
had silently **drifted from the bible** — the antiquarian's "forbidden book" and the
shutterbug's camera were dropped from `build_phase1_spec.py`. Those entries lost the
very objects that could have carried their accent, and both scored 0/9.

## Mitigation

1. **Every visual attribute needs a noun in the prompt to attach to.** Write
   `<explicit colour word> + <discrete small object>`, preferably emissive. Anchoring
   all 20 entries this way landed the attribute **10/10** in pilot v3 (gold crucifix,
   green charm-bottle, crimson blood at the mouth, acid-green churn eyes).
2. **Implied colour is not colour.** "ember" → blue. "ember-orange" → orange.
3. **Diff the generation script's descriptions against the design doc.** They drift.
   The bible is not the prompt; only the prompt is the prompt.
4. **Some subjects are structurally anti-spec and need reframing, not anchoring.** A
   "roiling nuclear-chaos sun" cannot be a *small* accent — it is the whole frame.
   Reframed to "a black void torn by a single small sulfur-yellow rip", it landed at
   1.0% with linework intact.
5. **Watch for attributes that are achromatic by definition** (bone-grey, white). They
   can never register on a chroma metric, and low coverage there is SUCCESS, not
   failure — don't "fix" an entry that is already correct.

## Notes (optional)

The rule also predicts multi-accent violations: once objects carry colour, an entry can
acquire several (the Cunning-Woman came out with red lips + green bottle + gold cork —
three accents against a one-accent spec, caught by `judge_image`, missed by both the
chroma metric and the human reviewer). Ask a judge for a distinct-colour COUNT, not
just presence. Related: `negative-hue-suppression-rotates-the-flood`,
`whole-frame-metric-cannot-separate-subject-from-background`.
