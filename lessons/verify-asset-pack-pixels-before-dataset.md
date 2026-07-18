---
title: A staged asset pack's name lies — render a contact sheet before building a dataset on it
severity: medium
tags: [dataset, assets, verification, lora, contact-sheet]
source: hand-authored
created: 2026-07-17
project: comfyui-toolchain
---

## Symptom

A task assumed a pre-downloaded pack of "top-down RPG tiles" (TX5) was ready to
prep into a training set. The zip filenames and the task description both said
"tiles". Building the dataset directly on them would have trained a "top-down
seamless tile" LoRA on the wrong pixels.

On inspection the 73 PNGs were: **isometric diamond tilesheets** (wrong
projection), plus PBR **source maps** (blue normal maps, grey height/displacement
maps, a black-and-white cutout mask) — not top-down colour tiles at all. Only
**4 of 73** were usable flat top-down albedo.

## Root cause

Filenames and human labels describe *intent*, not *content*. A pack authored for
one purpose (an isometric tileset shipped with its Blender source maps) can be
mislabelled or repurposed by whoever staged it. Nothing but the pixels tells you
what a "tile" image actually is — projection, whether it's albedo vs a normal/height
map, single tile vs assembled sheet, transparent vs opaque.

## Mitigation

1. **Before curating or prepping, render a labelled contact sheet** of the raw
   pack (thumbnail every image on a neutral bg with its filename + dimensions) and
   LOOK. Cheap: `PIL` grid, ~20 lines. This is the same "training data is ground
   truth" discipline as the human-signoff gate, applied one step earlier.
2. **Classify what you see, don't assume:** projection (top-down vs isometric vs
   perspective), map type (albedo vs normal=blue / height=grey / mask=b&w), and
   whether it's a single tile or an assembled sheet.
3. **When the pack doesn't fit the task, don't force it.** Divert the unusable-but-
   valid data to where it *does* fit (here: the isometric sheets seeded a new
   `tile_iso` LoRA) and source correct data for the original task.
4. Record the usable/unusable split in the manifest so the next reader trusts the
   provenance. See [[reverify-cc0-per-source-page]] for the license side of the
   same "verify, don't trust the label" rule.
