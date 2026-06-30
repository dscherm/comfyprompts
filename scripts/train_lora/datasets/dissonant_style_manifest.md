# dissonant_style — dataset manifest

*LoRA: `dissonant_style` (working name; may be rebranded at listing, like
berserkr→grimforge). Built 2026-06-30. Phase DS in `plan.md`.*

## What this is

A **distinctive retro-futurist style LoRA** trained on the user's own
**DissonantDreams** game art — a cohesive, art-directed aesthetic: hot
pink/cyan/black/cream palette, halftone screen-print + chrome airbrush, 70s-80s
sci-fi-paperback energy. Chosen because **art-directed > generic-prompted**: the
scrapped `stylized_game` produced generic AI output with no edge; this is an
ownable look with essentially no equivalent on Flux.

## Provenance & IP

- **Source:** `D:/Projects/DissonantDreams/assets/art/` (the user's own game).
- These are the user's **art-directed, curated Outputs** (AI-generated for the
  DissonantDreams game, then hand-selected) — same IP posture as the
  grimforge/berserkr dataset. **IP-clean:** original, no third-party art, no named
  characters/celebrities/living-artist styles.
- **License:** Flux-dev → the trained LoRA ships **FREE** on CivitAI (a Flux-dev
  Derivative can't be sold). Sell Outputs, not the weights. Can cross-promote the
  DissonantDreams game.

## Curation — 50 "striking only" (interiors dropped)

The 125 candidate illustrations split into two sub-styles. Per the user's
decision, only the **striking painterly/figure work** was kept; the 75 sketchy
2-tone architectural interiors (`zc_corp`/`zc_res`/`zc_und`) were **excluded** so
the LoRA learns the distinctive figure/scene look, not generic interiors.

| Kept (50) | Source folder | n |
|-----------|---------------|---|
| Retro-futurist scenes/figures | `art/cards/rf_*` | 23 |
| Scenarios (sci-fi posters/scenes) | `art/scenarios` | 14 |
| Class portraits (pink/cyan halftone) | `art/characters` | 11 |
| Key art (box cover/back) | `art/key_art` | 2 |
| **Excluded** — sketchy 2-tone interiors | `art/cards/zc_*` | 75 |

## Pipeline state

- [x] Staged 125 → curated to **50**, removed `zc_*` interiors.
- [x] `prep_dataset.py --max-edge 1024` → `E:/ai-training/datasets/dissonant_style`
  (50 scanned / 50 included / 0 dupes / 27 resized).
- [x] `caption.py --trigger dissonant_style` (Florence-2-large, detailed_caption,
  prepend) → **50/50 captioned, 0 failed**. Captions describe content neutrally;
  the style is implicit in the consistent set.
- [ ] **DS2 — train** (proven recipe: rank 16/alpha 16, 1500 steps, lr 1e-4,
  adamw8bit, flowmatch, EMA 0.99, multi-res 512/768/1024, GPU 1 — **needs ComfyUI
  stopped** to free the 24 GB).
- [ ] DS3 — eval on NEW subjects (prove transferable style, not memorization).
- [ ] DS4 — deploy + FREE CivitAI listing (distinctive-hook framing + game cross-promo).

## Note on dataset size

50 is on the smaller side vs the 148-image grimforge set, but the style is highly
consistent (a single art-directed look), which trains well at this size. If the
eval (DS3) shows the LoRA is undertrained or memorizing, options: add the best of
the excluded interiors for volume, or augment via img2img on the existing 50.
