# tile_topdown dataset manifest

Built 2026-07-17 (TX5). **29 images**, terrains: dirt 9, grass 4, path 5, sand 5, stone 3, water 3.

All sources are **CC0 / public domain**, each source page independently
license-verified on 2026-07-17 (not taken from the downloader's self-report).
Prep: `scripts/train_lora/prep_dataset.py --max-edge 1024`, RGB. Curated +
captioned by `scripts/train_lora/build_tile_topdown_dataset.py`. Captions are
short SDXL tags: `tile_topdown, <terrain> tile, top-down RPG tileset, seamless
texture, even lighting`.

## CC0 sources (all independently verified)

| source (OpenGameArt) | author | license | # used |
|---|---|---|---|
| <https://opengameart.org/content/ground-textures-free> | ForKotLow | **CC0** | 4 |
| <https://opengameart.org/content/seamless-dirt> | n4 | **CC0** | 7 |
| <https://opengameart.org/content/tileable-dirt-textures> | Cethiel | **CC0** | 4 |
| <https://opengameart.org/content/updated-grassland-tileset-stylized> | rubberduck | **CC0** | 4 |
| <https://opengameart.org/content/simple-seamless-tiles-of-dirt-and-sand> | LuminousDragonGames | **CC0** | 2 |
| <https://opengameart.org/content/2048-digitally-painted-tileable-desert-sand-texture> | txturs | **CC0** | 1 |
| <https://opengameart.org/content/seamless-water-tiles> | Hazmat Harry | **CC0** | 2 |
| <https://opengameart.org/content/y2k-water-texture> | GGBotNet | **CC0** | 1 |
| <https://opengameart.org/content/seamless-cobblestone-texture> | HellGate | **CC0** | 1 |
| <https://opengameart.org/content/floor-tile-texture> | Ravaen | **CC0** | 1 |
| <https://opengameart.org/content/200-tile-floor-textures> | Screaming Brain Studios | **CC0** | 2 |

## Per-image provenance

| dataset file | terrain | caption phrase | source | license |
|---|---|---|---|---|
| dirt__dark_dirt__sources_ground__dirt_ground_v3.png | dirt | dark dirt | <https://opengameart.org/content/updated-grassland-tileset-stylized> | CC0 |
| dirt__dirt__Dirt_01.png | dirt | dirt | <https://opengameart.org/content/tileable-dirt-textures> | CC0 |
| dirt__dirt__Dirt_02.png | dirt | dirt | <https://opengameart.org/content/tileable-dirt-textures> | CC0 |
| dirt__dirt__Dirt_2.png | dirt | dirt | <https://opengameart.org/content/simple-seamless-tiles-of-dirt-and-sand> | CC0 |
| dirt__dirt__sources_ground__dirt_ground.png | dirt | dirt | <https://opengameart.org/content/updated-grassland-tileset-stylized> | CC0 |
| dirt__dirt__sources_ground__dirt_ground_v2.png | dirt | dirt | <https://opengameart.org/content/updated-grassland-tileset-stylized> | CC0 |
| dirt__dry_dirt__Dirt_04.png | dirt | dry dirt | <https://opengameart.org/content/tileable-dirt-textures> | CC0 |
| dirt__plowed_dirt__Dirt_03.png | dirt | plowed dirt | <https://opengameart.org/content/tileable-dirt-textures> | CC0 |
| dirt__red_dirt__dirt.png | dirt | red dirt | <https://opengameart.org/content/seamless-dirt> | CC0 |
| grass__dry_grass__dry_grass.jpg | grass | dry grass | <https://opengameart.org/content/ground-textures-free> | CC0 |
| grass__grass__grass.png | grass | grass | <https://opengameart.org/content/seamless-dirt> | CC0 |
| grass__grass__grass_1_0.png | grass | grass | <https://opengameart.org/content/ground-textures-free> | CC0 |
| grass__grass__grass_2.jpg | grass | grass | <https://opengameart.org/content/ground-textures-free> | CC0 |
| path__cobblestone_path__cobblestone.png | path | cobblestone path | <https://opengameart.org/content/seamless-dirt> | CC0 |
| path__cobblestone_path__cobblestone_diffuse.png | path | cobblestone path | <https://opengameart.org/content/seamless-cobblestone-texture> | CC0 |
| path__gravel_ground__ground_0.jpg | path | gravel ground | <https://opengameart.org/content/ground-textures-free> | CC0 |
| path__gravel_path__gravel_512x512_00.png | path | gravel path | <https://opengameart.org/content/seamless-dirt> | CC0 |
| path__gravel_path__gravel_512x512_02.png | path | gravel path | <https://opengameart.org/content/seamless-dirt> | CC0 |
| sand__beach_sand__beach_sand.png | sand | beach sand | <https://opengameart.org/content/seamless-dirt> | CC0 |
| sand__desert_sand__sand_1.jpg | sand | desert sand | <https://opengameart.org/content/2048-digitally-painted-tileable-desert-sand-texture> | CC0 |
| sand__sand__Sand1.png | sand | sand | <https://opengameart.org/content/simple-seamless-tiles-of-dirt-and-sand> | CC0 |
| sand__sand__sand.png | sand | sand | <https://opengameart.org/content/seamless-dirt> | CC0 |
| sand__sand__sources_ground__sand.png | sand | sand | <https://opengameart.org/content/updated-grassland-tileset-stylized> | CC0 |
| stone__stone_floor__floortiles_0.png | stone | stone floor | <https://opengameart.org/content/floor-tile-texture> | CC0 |
| stone__tiled_stone_floor__Rectangle_Marble_Tile_01-512x512.png | stone | tiled stone floor | <https://opengameart.org/content/200-tile-floor-textures> | CC0 |
| stone__tiled_stone_floor__Rectangle_Marble_Tile_03-512x512.png | stone | tiled stone floor | <https://opengameart.org/content/200-tile-floor-textures> | CC0 |
| water__deep_water__dark_water.jpg | water | deep water | <https://opengameart.org/content/seamless-water-tiles> | CC0 |
| water__shallow_water__light_water.jpg | water | shallow water | <https://opengameart.org/content/seamless-water-tiles> | CC0 |
| water__water__y2k_water_texture.png | water | water | <https://opengameart.org/content/y2k-water-texture> | CC0 |

## Deliberately excluded (present in the raw haul, not trained on)

| raw file | reason |
|---|---|
| oga_grass_beach_water_impossiblerealms/terrain_1.png | level mockup (a composed scene with a cross-shaped pond), not a seamless terrain tile |
| oga_grass_beach_water_impossiblerealms/terrain_tiles24.png | tiny 256px spritesheet with magenta transparency key — not a usable tile |
| oga_stone_floor_ogreofwart/floor1.png | single slab with a dark border frame — would teach the LoRA to draw tile borders (not seamless) |
| oga_stone_floor_ogreofwart/floor2.png | 3x3 grid of framed slabs (spritesheet) — not a seamless full-frame tile |
| oga_dirt_sand_luminousdragon/Dirt_3.png | near-duplicate flat ochre dirt (kept Dirt_2 as the representative) |
| oga_dirt_sand_luminousdragon/Dirt_4.png | near-duplicate flat ochre dirt |
| oga_dirt_sand_luminousdragon/Dirt_5.png | near-duplicate flat ochre dirt |
| oga_dirt_sand_luminousdragon/Dirt_6.png | near-duplicate flat ochre dirt |
| oga_dirt_sand_luminousdragon/Dirt_7.png | near-duplicate flat ochre dirt |
| oga_dirt_sand_luminousdragon/Dirt_8.png | near-duplicate flat ochre dirt |
| oga_dirt_sand_luminousdragon/Dirt_9.png | near-duplicate flat ochre dirt |
| oga_dirt_sand_luminousdragon/Dirt_10.png | near-duplicate flat ochre dirt |
| oga_dirt_sand_luminousdragon/Sand2.png | near-duplicate flat ochre sand (kept Sand1) |
| oga_n4_seamless_pattern/gravel_512x512_01.png | near-duplicate grey gravel (kept _00 and _02) |
| oga_n4_seamless_pattern/gravel_512x512_03.png | near-duplicate grey gravel |
| oga_n4_seamless_pattern/stone.png | dropped in the TX5 boost — reads as snow/plaster, not stone floor; replaced by 3 genuine CC0 stone floors (Ravaen + 2 Screaming Brain rectangle tiles) |
| oga_floor_sbs/Rectangle_Marble_Tile_05-512x512.png | black marble — too dark for an even-lit terrain tile |
| oga_floor_sbs/WO_Marble_Tile_01-512x512.png | high-contrast checker pattern — decorative, not terrain-like |

## Rejected at source (not CC0 / too small / unverifiable)

| source page | reason |
|---|---|
| https://opengameart.org/content/topdown-tileset | CC-BY 3.0 / CC-BY-SA 3.0 only, no CC0 option |
| https://opengameart.org/content/handpainted-stone-floor-texture | CC-BY 4.0 (requires attribution) |
| https://opengameart.org/content/hand-painted-stone-floor-texture | CC-BY 4.0 (requires attribution) |
| https://opengameart.org/content/animated-water-texture-128px | CC0 but only 128px frames, below 256px minimum |
| https://opengameart.org/content/top-down-water-tiles | license box could not be read via fetch (page returned no license markup); not verifiable, so excluded |
| https://opengameart.org/content/terrain-tiles | license box could not be read via fetch (page returned no license/file markup); not verifiable, so excluded |
| https://opengameart.org/content/simple-seamless-tiles-of-dirt-and-sand (file 'Dirt 1 .png') | downloaded file was corrupt/not a valid image (33KB); other 11 files from this CC0 page were kept |
| kenney.nl roguelike/RPG & RPG-base packs | CC0 but tiles are 16-64px pixel-art, below 256px minimum for SDXL — not downloaded |
| https://opengameart.org/content/texture-water | CC-BY 3.0 / OGA-BY 3.0 (requires attribution) — not CC0 (TX5 boost) |
| https://opengameart.org/content/top-down-dungeon-pack | CC0 but floor tiles are 64px, below the 256px bar (TX5 boost) |

## Honest limitations (read before training / TX6)

- **Mostly photographic, not stylized-game.** The genuine CC0 top-down
  *game-tile* sources were scarce: the one stylized set (ImpossibleRealms)
  was a level mockup + a magenta-keyed spritesheet, both unusable. What
  survived is largely photographic seamless terrain — closer to `mat_tile`'s
  aesthetic than a hand-painted tile look. A distinctly stylized look would
  need a different CC0 source or a generation/upres pass.

- **water (3)** — Hazmat Harry x2 + GGBotNet Y2K; **stone floor (3)** — Ravaen
  + 2 Screaming Brain rectangle floors. Both families were boosted from the
  first cut (2 / 1) at the user's request; other CC0 water was 128px or
  CC-BY, and OGA stone floors were mostly framed/gridded or 64px.

- dirt is the deepest family (9) — best genuine CC0 variety was in dirt.

## Trigger / usage

Trigger `tile_topdown`; SDXL LoRA (kohya, spec §5); feeds the orthogonal
seamless path (`generate_texture_tile.json` + SeamlessTile + CircularVAEDecode).
Recommended strength ~0.8 (sweep 0.6-1.0 in TX7 eval).
