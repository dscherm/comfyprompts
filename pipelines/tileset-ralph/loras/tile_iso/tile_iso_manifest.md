# tile_iso dataset manifest

Built 2026-07-17 (TI1). **38 isometric diamond tiles**, terrains: cliff 10, dirt 6, grass 6, rock 8, sand 6, water 2.

## Single CC0 source (verified)

- **rubberduck** — OpenGameArt "updated grassland tileset (stylized)" — **CC0**, verified 2026-07-17 (exact-byte match to the OGA download).
- <https://opengameart.org/content/updated-grassland-tileset-stylized>

## Method

`scripts/train_lora/build_tile_iso_dataset.py` — the pack renders each tile as a
gap-separated alpha blob, so connected-component labeling (scipy.ndimage) isolates
single tiles. Each is flattened onto neutral grey (128,128,128), padded to a square
(preserves the 2:1 diamond shape without train-time distortion), upscaled to 512px,
then normalized by `prep_dataset.py --max-edge 1024`. Near-duplicate flats are
dropped by perceptual hash; blobs dominated by pure-black cliff faces (>42%) are
rejected. Captions: `tile_iso, <terrain> tile, isometric RPG tileset, diamond tile,
even lighting`.

## Tiles per source sheet

| sheet | terrain | # tiles |
|---|---|---|
| dirt_tiles | dirt | 6 |
| grass_tiles | grass | 6 |
| grassland_1x1 | grassy cliff | 4 |
| grassland_2x2 | grassy cliff | 6 |
| rock_cliffs | rock | 8 |
| sand_tiles | sand | 6 |
| water_v01 | water | 1 |
| water_v02 | water | 1 |

## Notes / limitations

- **Cliff/rock tiles are iso OBJECTS**, not flat ground, so they carry directional
  self-shadowing; the shared `even lighting` caption token fits the ground tiles
  (grass/dirt/sand/water) better than the cliff structures. Kept because they teach
  the isometric diamond-footprint aesthetic. A few cliff pieces retain a dark inner
  gorge face (legitimate iso art, below the 42% black-reject threshold).

- Ground tiles (grass/dirt/sand) are near-identical within a terrain — a handful
  of representatives each is enough for a focused aesthetic LoRA.

- **NOT an orthogonal-seamless dataset.** These do not wrap-tile; tile_iso uses the
  standalone SDXL path (spec §8), no SeamlessTile / edge-MAD.

## Trigger / usage

Trigger `tile_iso`; SDXL LoRA (kohya, spec §5). Standalone iso-tile generator — not
wired into `generate_texture_tile.json`. Deferred: TI2 (train), TI3 (eval), TI4 (deploy).
