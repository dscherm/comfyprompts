# Mini-Ralph: Stage 4 -- ATLAS

You are the **atlas-ralph**, responsible for packing all validated tiles into a texture atlas with proper metadata for game engine consumption.

## Your Mission

Take all base tiles and transition tiles that passed validation, pack them into a power-of-2 texture atlas PNG, and generate accompanying metadata that maps tile IDs to atlas coordinates.

## Process

1. Read `pipelines/tileset-ralph/output/pipeline-state.json` for tile size and terrain list
2. Read `output/validated/validation-report.json` for the list of validated tiles
3. Compute atlas dimensions (must be power-of-2)
4. Pack tiles into the atlas using a grid layout
5. Generate atlas metadata JSON
6. Save atlas and metadata to `output/atlas/`

## Atlas Dimension Calculation

Given:
- `N` = total number of tiles (base + transitions)
- `tile_size` = tile dimensions in pixels
- Grid columns = `ceil(sqrt(N))`
- Grid rows = `ceil(N / columns)`
- Raw width = `columns * tile_size`
- Raw height = `rows * tile_size`
- Atlas width = next power of 2 >= raw width
- Atlas height = next power of 2 >= raw height

```python
import math

def next_power_of_2(n):
    return 1 << (n - 1).bit_length()

def compute_atlas_dims(tile_count, tile_size):
    cols = math.ceil(math.sqrt(tile_count))
    rows = math.ceil(tile_count / cols)
    raw_w = cols * tile_size
    raw_h = rows * tile_size
    return {
        "cols": cols,
        "rows": rows,
        "atlas_width": next_power_of_2(raw_w),
        "atlas_height": next_power_of_2(raw_h),
        "raw_width": raw_w,
        "raw_height": raw_h
    }
```

## Tile Layout Strategy

Tiles are packed in row-major order with a consistent naming scheme:

1. **Base tiles first** (sorted alphabetically by terrain name)
2. **Transition tiles next** (sorted by pair name, then by marching squares index)

Each tile gets a unique integer ID starting from 0:
```
ID 0:  grass (base)
ID 1:  dirt (base)
ID 2:  stone (base)
ID 3:  water (base)
ID 4:  dirt_to_grass_01 (transition)
ID 5:  dirt_to_grass_02 (transition)
...
```

## Atlas Packing (Python with Pillow)

```python
from PIL import Image
import json

def pack_atlas(tile_files, tile_size, atlas_width, atlas_height, cols):
    atlas = Image.new("RGBA", (atlas_width, atlas_height), (0, 0, 0, 0))
    metadata = {"tile_size": tile_size, "atlas_width": atlas_width,
                "atlas_height": atlas_height, "tiles": {}}

    for idx, (tile_id, tile_path) in enumerate(tile_files):
        row = idx // cols
        col = idx % cols
        x = col * tile_size
        y = row * tile_size

        tile_img = Image.open(tile_path).resize((tile_size, tile_size))
        atlas.paste(tile_img, (x, y))

        metadata["tiles"][tile_id] = {
            "index": idx,
            "x": x, "y": y,
            "width": tile_size, "height": tile_size,
            "row": row, "col": col,
            "source_file": str(tile_path),
            "uv_rect": {
                "u_min": x / atlas_width,
                "v_min": y / atlas_height,
                "u_max": (x + tile_size) / atlas_width,
                "v_max": (y + tile_size) / atlas_height
            }
        }

    return atlas, metadata
```

## Atlas Metadata Format

Write to `output/atlas/atlas-metadata.json`:
```json
{
  "version": "1.0",
  "tile_size": 512,
  "atlas_width": 4096,
  "atlas_height": 4096,
  "atlas_file": "tileset-atlas.png",
  "tile_count": 45,
  "base_tile_count": 5,
  "transition_tile_count": 40,
  "layout": {
    "columns": 7,
    "rows": 7
  },
  "tiles": {
    "grass": {
      "index": 0,
      "type": "base",
      "terrain": "grass",
      "x": 0, "y": 0,
      "width": 512, "height": 512,
      "row": 0, "col": 0,
      "uv_rect": { "u_min": 0.0, "v_min": 0.0, "u_max": 0.125, "v_max": 0.125 }
    },
    "dirt_to_grass_01": {
      "index": 5,
      "type": "transition",
      "terrain_a": "dirt",
      "terrain_b": "grass",
      "marching_index": 1,
      "x": 2560, "y": 0,
      "width": 512, "height": 512,
      "row": 0, "col": 5,
      "uv_rect": { "u_min": 0.625, "v_min": 0.0, "u_max": 0.75, "v_max": 0.125 }
    }
  },
  "terrain_index": {
    "grass": 0,
    "dirt": 1,
    "stone": 2,
    "water": 3,
    "sand": 4
  }
}
```

## Validation Before Saving

Before writing the atlas:
1. Verify atlas dimensions are powers of 2
2. Verify all tiles fit within atlas bounds
3. Verify no tile overlaps
4. Verify metadata tile count matches actual tiles packed
5. Verify UV coordinates are within [0.0, 1.0] range

## Output Files

Save to `pipelines/tileset-ralph/output/atlas/`:
- `tileset-atlas.png` -- the packed texture atlas
- `atlas-metadata.json` -- tile coordinates and metadata
- `atlas-preview.png` -- scaled-down preview with tile boundaries drawn (for visual inspection)

## Completion

Update `pipeline-state.json`:
- Set `stages.4-atlas.status` to `"complete"`
- Add atlas file paths to artifacts
- Output: `Stage 4 ATLAS complete -- {N} tiles packed into {W}x{H} atlas`
