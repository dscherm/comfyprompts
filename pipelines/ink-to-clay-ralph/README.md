# ink-to-clay-ralph

**Ink→Clay image translator (FLUX).** Turns any 2D drawing (ink/comic, sprite,
concept art) into a clean "3D-clay" render — smooth matte forms, soft even light,
plain grey/white background, clear silhouette — the look that reconstructs
cleanly in **TRELLIS image-to-3D**. Purpose: let *arbitrary art* enter the
3D-model pipeline.

- **Brief:** `D:/Projects/soapbox-sabotage/docs/lora-ink-to-clay-spec.md`
- **Target look:** `products/soapbox_characters_v1/concepts/*.png`
- **Orchestrator prompt:** [`PROMPT.md`](PROMPT.md) · **Requirements:** [`prd.md`](prd.md)

## The idea in one line

It's an **image→image** transform (not text→image): preserve the drawing's
subject/composition, restyle only its surface + lighting + background into clay.

## Two approaches

| | Approach A (MVP) | Approach B (target) |
|---|---|---|
| Technique | FLUX style LoRA + **img2img** @ denoise ~0.6 | FLUX.1 **Kontext** paired-edit LoRA |
| Data | clay-look images only (trigger `clay3d`) | aligned `(ink, clay)` pairs |
| Inference | init latent = ink → KSampler(+LoRA) → decode; optional lineart ControlNet | single-pass reference edit |
| Trade | fast, but denoise is a manual knob | faithful, one-shot; needs paired data |

Do **A first** (lock the look), then **B** (fidelity).

## Free paired data (Stage 1)

Render the **same subject + same seed** twice with `soapbox_char_final_v1`:
clay = `mv_ortho`@0.85 + char@0.65; ink = char@0.9 (no mv_ortho, "heavy ink,
white background"). Aligned pair. ~50–150 subjects →
`E:/ai-training/datasets/ink_to_clay_v1/{ink,clay}/<id>.png`.

## Stages

`DATASET → TRAIN-A → INFER-A → TRAIN-B → INFER-B → RECON-EVAL`
Completion promise: **`INK TO CLAY COMPLETE`**.

## Run

```bash
# from repo root, with the ralph loop
$RALPH_HOME/ralph.sh 20    # (targets this pipeline dir via PROMPT.md)
```

**GPU note:** training stages (2, 4) are **GPU-gated** — generation and training
share the 3090 Ti and run sequentially. Stop ComfyUI to free 24 GB before a
train run, restart after. Do not start training without the human's go-ahead.

## The acceptance test that matters

Not "does it look clay-ish" — feed the output straight into
`trellis2_image_to_3d` and confirm the **mesh** is clean. That gate (Stage 6) is
the whole point.

## Deliverables

Two LoRAs (`E:/ai-training/flux-output/ink_to_clay_v1_a*`, `_b*`), both ComfyUI
inference workflow JSONs, this README's recommended denoise/weights, and 3–5
before/after examples including one TRELLIS reconstruction.
