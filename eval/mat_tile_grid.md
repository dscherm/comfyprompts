# mat_tile LoRA — eval grid (TX3) — PENDING USER VERDICT

**Date:** 2026-07-17 · Checkpoint: `mat_tile.safetensors` (1500 steps, TX2)
· Graph: `generate_texture_tile.json` (SDXL + SeamlessTile + CircularVAEDecode,
LoraLoader) · seed 42, 25 steps, cfg 7, 1024² · Gallery artifact: tx3-eval-grid.

## Seamlessness (edge MAD, spec §6b — threshold <5%)

| material | base | 0.6 | 0.8 | 1.0 | control (0.8, tiling OFF) |
|---|---|---|---|---|---|
| red brick wall | 0.61 | 0.70 | 0.70 | 1.45 | 4.51 |
| mossy cobblestone | 1.44 | 1.77 | 1.81 | 1.79 | **10.72** |
| weathered wood planks | 2.36 | 2.99 | 2.42 | 3.88 | **8.58** |
| beach sand | 2.86 | 2.19 | 2.39 | 2.49 | **5.42** |

- **All 16 tiling-enabled cells pass** (<5%).
- **Controls validate the metric**: 2-6× higher than their enabled twins on
  identical prompts. Brick's control stays under 5% in absolute terms because
  brick courses are naturally grid-aligned — the per-prompt ratio (0.70 →
  4.51) is the meaningful signal there.

## Aesthetic (Claude pre-filter — user verdict decides)

- **red brick wall**: LoRA cells read flatter/more even than base; healthy.
- **mossy cobblestone**: **LoRA regression at 0.8+** — base renders proper
  grey stones with moss; the LoRA replaces stone structure entirely with moss
  islands on a flat lilac field. The lilac strongly resembles the
  plaster/tiles dataset entries (blue_plaster_wall, blue_floor_tiles) —
  likely dominant-mode bleed at high strength.
- **weathered wood planks / beach sand**: to be judged from the gallery.

## Open decision (user)

Per material: ship base / 0.6 / 0.8 / 1.0? If cobblestone-style bleed is
disqualifying, the fix candidates are: retrain with the plaster/tiles entries
dropped (or family-balanced repeats), or cap deployment strength at 0.6.
Verdict + chosen strength land here when given.
