# Fantasy RPG Tileset — 16×16 (Vol. 1)

A top-down fantasy RPG tileset: seamless terrain, autotile transitions, and
object sprites. 65 tiles, cohesive 16-bit palette.

## Contents (`tiles/` = individual PNGs · `atlas.png` = packed sheet)

- **Terrain (11):** grass (+2 variants), grass_flowers, dark_grass, dirt, water,
  deep_water, stone, sand, cobble_path. All seamless / self-tiling.
- **Transitions (48):** Wang **corner autotile** sets for grass→dirt, grass→water,
  grass→sand (16 tiles each). Corner-continuous, so they connect cleanly.
- **Objects (6):** tree, bush, rock, flowers, mushroom, signpost
  (transparent background — overlay on any terrain).

## Files
- `atlas.png` — 128×256 packed sheet (16×16 cells, power-of-2).
- `atlas_4x.png` — 4× preview.
- `metadata.json` — every tile: name, category, atlas x/y/w/h; transitions also
  carry `{top, base, corner_mask}` (mask bits: TL=1, TR=2, BR=4, BL=8 = grass corner).
- `tiles/*.png` — individual 16×16 tiles.
- `mockup.png` / `mockup_3x.png` — sample map.
- `showcase.png` — terrain / transition / object overview.

## Autotile (transitions)
Each transition set is a 16-tile **2-corner Wang** set. For a cell, look at its
4 corners: each is either the "top" terrain (grass) or the "base" (dirt/water/sand).
The 4-bit `corner_mask` (TL=1, TR=2, BR=4, BL=8 set when that corner is grass)
selects the tile. mask 0 = all base, mask 15 = all grass.

## Engine import
- **Godot 4:** import `atlas.png`, new TileSet, tile size 16. Use the transition
  sets as a Terrain (corner/Wang) layer; map each tile's `corner_mask` to its
  corner peering bits. **Tested in Godot 4.6** — a runnable example is in
  `examples/godot_import/` (loads the atlas, builds the TileSet, places the sample
  map). It renders pixel-identical to `mockup.png` (proof: `godot_validation.png`).
- **Unity (2D Tilemap):** slice `atlas.png` at 16px (or use `tiles/`). Use Rule
  Tiles for autotiling; the 16 Wang tiles cover the corner cases.
- **Godot/Unity/LÖVE/etc.:** `metadata.json` gives engine-agnostic regions.
- **RPG Maker (MV/MZ):** native tiles are 48px — upscale these 3× (nearest) first.

## Notes
- 16×16 native, nearest-neighbor scaling only (never bilinear — it blurs pixels).
- Objects are on transparent background for layering.
- Transitions cover the primary pairs (grass↔dirt/water/sand). More pairs +
  animated water are planned for Vol. 2.

## License
Royalty-free for personal & commercial games/projects. Do not resell or
redistribute the tileset files as an asset pack. No third-party IP.
