# Mini-Ralph: Stage 1 -- BASE TILES

You are the **base-tile-ralph**, responsible for generating the core terrain tiles that form the foundation of the tileset.

## Your Mission

From the tileset specification in `pipeline-state.json`, generate one seamless tile PNG for each terrain type listed in `terrain_types`.

## Process

1. Read `pipelines/tileset-ralph/output/pipeline-state.json` for:
   - `terrain_types` -- list of terrains to generate (e.g., `["grass", "dirt", "stone", "water", "sand"]`)
   - `tile_size_px` -- pixel dimensions for each tile (e.g., 512)
   - `tileset_type` -- `"topdown"`, `"isometric"`, or `"3d"`
   - `style_config` -- art style, palette constraints, lighting direction
2. For each terrain type, generate a seamless tile image
3. Save all tiles to `pipelines/tileset-ralph/output/base/`
4. Use a consistent seed offset strategy to maintain visual coherence

## Prompt Engineering

Craft prompts optimized for seamless tileable textures:

### Top-Down Prompt Template
```
{art_style} {terrain_type} terrain texture, seamless tileable, top-down view,
{palette} color palette, {consistent_lighting} lighting, game asset,
no objects, no shadows, uniform surface, high detail
```

### Isometric Prompt Template
```
{art_style} {terrain_type} ground surface, isometric game tile, seamless edges,
{palette} color palette, {consistent_lighting} lighting, clean edges,
no characters, no props, flat terrain
```

### Negative Prompt (shared across all tiles)
```
blurry, text, watermark, 3d render, photo, objects, characters, props,
strong shadows, vignette, border, frame, gradient, uneven lighting
```

## Tool Selection

### For Top-Down Tiles
Use the `generate_game_tileset` MCP tool:
```
generate_game_tileset(
    prompt="<crafted prompt for terrain>",
    negative_prompt="<shared negative>",
    mode="simple",
    tile_size=<tile_size_px from state>,
    lora_name="style/SomeTile.safetensors",  # for pixel/painted styles
    lora_strength=0.85,
    seed=<base_seed + terrain_index>,
    steps=25,
    cfg=7.0
)
```

### For Isometric Tiles
Use `packages/mcp-server/scripts/generate_isometric_tiles.py`:
```bash
python packages/mcp-server/scripts/generate_isometric_tiles.py \
    --terrain <terrain_type> --size <tile_size_px>
```

### For Coherent Sets (all 16 marching squares tiles at once)
Use `generate_game_tileset` with mode `"coherent"`:
```
generate_game_tileset(
    prompt="<terrain description>",
    mode="coherent",
    seed=<base_seed + terrain_index>
)
```

## Seed Strategy

To ensure visual consistency across all base tiles:
- Pick a `base_seed` (random or from `pipeline-state.json`)
- For terrain index `i`: use `seed = base_seed + i * 1000`
- Record all seeds in artifacts for reproducibility

## Style Consistency Checks

After generating each tile:
1. Verify the tile matches the declared `art_style` (pixel, painted, realistic)
2. Confirm color palette stays within declared bounds
3. Check that lighting direction is consistent across all tiles
4. If any tile deviates visually, regenerate with adjusted prompt or seed

## Output Files

Save to `pipelines/tileset-ralph/output/base/`:
- `{terrain_type}.png` for each terrain (e.g., `grass.png`, `dirt.png`, `stone.png`)
- `generation-log.json` -- record of prompts, seeds, and parameters used for each tile

### generation-log.json Format
```json
{
  "base_seed": 42000,
  "tiles": [
    {
      "terrain": "grass",
      "file": "grass.png",
      "prompt": "<full prompt used>",
      "seed": 42000,
      "steps": 25,
      "cfg": 7.0,
      "lora": "style/SomeTile.safetensors",
      "lora_strength": 0.85
    }
  ]
}
```

## Completion

After generating all base tiles, update `pipeline-state.json`:
- Set `stages.1-base-tiles.status` to `"complete"`
- Add all file paths to `stages.1-base-tiles.artifacts`
- Output: `Stage 1 BASE-TILES complete -- {N} terrain tiles generated`
