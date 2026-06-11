# Quality Gate 1: BASE TILES

## PASS Criteria (ALL must pass)
- [ ] One PNG file exists in `output/base/` for each terrain type listed in `pipeline-state.json`
- [ ] Each PNG is a valid image file, >10KB (not blank or corrupt)
- [ ] Each PNG has dimensions matching `tile_size_px` from pipeline state (e.g., 512x512)
- [ ] All tiles have identical dimensions (no mixed sizes)
- [ ] `output/base/generation-log.json` exists with prompts and seeds for each tile
- [ ] At least 3 base tiles generated (minimum viable tileset)

## WARN Criteria (log but don't block)
- [ ] A tile's mean brightness is >90% or <10% of 255 (nearly all white or all black -- likely generation failure)
- [ ] Color palette deviates significantly from `style_config.palette` if specified
- [ ] Caption check suggests a tile does not match the intended terrain type
- [ ] Any tile file size is suspiciously small (<20KB for a 512x512 tile)

## FAIL Criteria (block advancement -- re-run Stage 1)
- [ ] Any terrain type from the specification has no corresponding PNG
- [ ] Any PNG is 0 bytes or fails to open as a valid image
- [ ] Tile dimensions do not match `tile_size_px` (wrong resolution generated)
- [ ] `generation-log.json` is missing (cannot reproduce tiles)
- [ ] Fewer than 3 terrain tiles generated

## Validation Method
```python
from PIL import Image
from pathlib import Path
import json

state = json.load(open("output/pipeline-state.json"))
terrain_types = state["terrain_types"]
tile_size = state["tile_size_px"]
base_dir = Path("output/base")

for terrain in terrain_types:
    tile_path = base_dir / f"{terrain}.png"
    assert tile_path.exists(), f"Missing: {tile_path}"
    img = Image.open(tile_path)
    assert img.size == (tile_size, tile_size), f"Wrong size: {img.size}"
    assert tile_path.stat().st_size > 10240, f"Too small: {tile_path.stat().st_size}B"

assert (base_dir / "generation-log.json").exists(), "Missing generation log"
```

## Gate Logic
- If FAIL on missing tiles: re-trigger Stage 1 for the specific missing terrains only
- If FAIL on wrong dimensions: re-trigger Stage 1 with corrected `tile_size` parameter
- If WARN on palette: log for manual review but allow advancement
