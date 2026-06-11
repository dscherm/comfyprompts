# Quality Gate 4: ATLAS

## PASS Criteria (ALL must pass)
- [ ] `output/atlas/tileset-atlas.png` exists and is >100KB
- [ ] Atlas dimensions are powers of 2 (e.g., 2048x2048, 4096x4096)
- [ ] `output/atlas/atlas-metadata.json` exists and is valid JSON
- [ ] Metadata tile count matches the total number of tiles packed
- [ ] Every base terrain tile appears in the metadata
- [ ] Every validated transition tile appears in the metadata
- [ ] All UV coordinates in metadata are within [0.0, 1.0] range
- [ ] No two tiles overlap in the atlas (non-overlapping bounding boxes)

## WARN Criteria (log but don't block)
- [ ] Atlas has significant empty space (>40% of atlas area is unused padding)
- [ ] Atlas exceeds 4096x4096 (may cause issues on mobile GPUs)
- [ ] Some transition tiles were excluded due to validation failures (reduced coverage)
- [ ] Atlas file size exceeds 50MB (may be slow to load)

## FAIL Criteria (block advancement -- re-run Stage 4)
- [ ] Atlas PNG is missing, 0 bytes, or corrupt
- [ ] Atlas dimensions are not powers of 2
- [ ] Metadata JSON is missing or invalid
- [ ] Metadata references tiles that are not in the atlas
- [ ] Tile count in metadata does not match tiles in atlas
- [ ] UV coordinates are out of bounds
- [ ] Tiles overlap in the atlas layout

## Validation Method
```python
from PIL import Image
import json
import math

atlas = Image.open("output/atlas/tileset-atlas.png")
meta = json.load(open("output/atlas/atlas-metadata.json"))

w, h = atlas.size

# Power of 2 check
assert w & (w - 1) == 0 and w > 0, f"Width {w} not power of 2"
assert h & (h - 1) == 0 and h > 0, f"Height {h} not power of 2"

# Dimensions match metadata
assert meta["atlas_width"] == w
assert meta["atlas_height"] == h

# UV bounds check
for tile_id, tile in meta["tiles"].items():
    uv = tile["uv_rect"]
    assert 0.0 <= uv["u_min"] < uv["u_max"] <= 1.0, f"UV X out of bounds: {tile_id}"
    assert 0.0 <= uv["v_min"] < uv["v_max"] <= 1.0, f"UV Y out of bounds: {tile_id}"

# Overlap check (simplified: no two tiles share the same grid cell)
positions = set()
for tile_id, tile in meta["tiles"].items():
    pos = (tile["row"], tile["col"])
    assert pos not in positions, f"Overlap at {pos}: {tile_id}"
    positions.add(pos)
```

## Gate Logic
- If FAIL on power-of-2: re-run Stage 4 with corrected dimension calculation
- If FAIL on missing tiles: re-run Stage 4 with complete tile list from validation report
- If WARN on large atlas: consider reducing tile_size_px or splitting into multiple atlases
