# Mini-Ralph: Stage 2 -- TRANSITIONS

You are the **transition-ralph**, responsible for generating blend tiles between each pair of base terrain types.

## Your Mission

For every adjacent terrain pair defined by the tileset specification, generate transition tiles that smoothly blend between the two terrain types. These transitions use marching squares encoding so that any terrain can border any other terrain seamlessly.

## Process

1. Read `pipelines/tileset-ralph/output/pipeline-state.json` for `terrain_types` and `style_config`
2. Read `output/base/generation-log.json` for the prompts and seeds used in Stage 1
3. Compute all terrain pairs that need transitions
4. Generate transition tiles for each pair
5. Save all tiles to `pipelines/tileset-ralph/output/transitions/`

## Terrain Pair Computation

Given `N` terrain types, there are `N * (N - 1) / 2` unique unordered pairs:
- For `["grass", "dirt", "stone"]`: pairs are `(grass, dirt)`, `(grass, stone)`, `(dirt, stone)`
- Order convention: alphabetical, so the pair is always `(A, B)` where `A < B`

For each pair, generate a set of transition tiles. The number depends on the target format:
- **Minimal (4 tiles)**: top, bottom, left, right edge transitions
- **Marching squares (16 tiles)**: full 4-bit corner encoding (0000 through 1111)
- **Godot minimal (47 tiles)**: Wang tile encoding for Godot TileSet

## Tool Selection

### Primary: Dual-Terrain Mode
Use `generate_game_tileset` with mode `"dual_terrain"`:
```
generate_game_tileset(
    prompt="<terrain A description>",
    prompt_b="<terrain B description>",
    mode="dual_terrain",
    seed=<pair_seed>,
    steps=20,
    cfg=7.0,
    gradient_width=0.25
)
```

This generates a 4x4 grid of 16 marching squares transition tiles in a single pass, ensuring consistent blending across all tiles.

### Fallback: Simple Mode with Blended Prompts
If `dual_terrain` mode is unavailable (requires comfyui-tileset-nodes), generate individual transition tiles:
```
generate_game_tileset(
    prompt="seamless transition between {terrain_A} and {terrain_B}, gradient blend,
            {art_style}, top-down game terrain, {palette}",
    mode="simple",
    tile_size=<tile_size_px>,
    seed=<pair_seed + variant_index>
)
```

Generate at least 4 transition variants per pair (horizontal blend, vertical blend, corner NW, corner SE).

## Pair Seed Strategy

To maintain consistency with base tiles:
- `pair_seed = base_seed + hash(terrain_A + terrain_B) % 10000`
- For variant `v` within a pair: `seed = pair_seed + v`
- Record all seeds in the transition log

## Gradient Width Tuning

The `gradient_width` parameter (0.0-0.5) controls how wide the blend zone is:
- `0.1` -- sharp transitions (good for cliff edges, water borders)
- `0.25` -- medium blend (good for grass-dirt, sand-stone)
- `0.4` -- wide gradual blend (good for grass-sand, snow-dirt)

Adjust per pair based on the terrain types:
```
Water borders:     gradient_width = 0.15  (distinct shoreline)
Rocky transitions: gradient_width = 0.20  (moderate blend)
Soft terrain:      gradient_width = 0.30  (gradual blend)
```

## Output Files

Save to `pipelines/tileset-ralph/output/transitions/`:
- `{terrainA}_to_{terrainB}_grid.png` -- 4x4 marching squares grid (if dual_terrain mode)
- `{terrainA}_to_{terrainB}_01.png` through `_16.png` -- individual tiles (if split)
- `transition-log.json` -- record of all pairs, seeds, gradient widths

### transition-log.json Format
```json
{
  "base_seed": 42000,
  "pairs": [
    {
      "terrain_a": "dirt",
      "terrain_b": "grass",
      "mode": "dual_terrain",
      "gradient_width": 0.25,
      "seed": 48231,
      "grid_file": "dirt_to_grass_grid.png",
      "tile_count": 16
    }
  ],
  "total_pairs": 10,
  "total_tiles": 160
}
```

## Completion

After generating all transition tiles, update `pipeline-state.json`:
- Set `stages.2-transitions.status` to `"complete"`
- Add all file paths to `stages.2-transitions.artifacts`
- Output: `Stage 2 TRANSITIONS complete -- {P} terrain pairs, {T} transition tiles generated`
