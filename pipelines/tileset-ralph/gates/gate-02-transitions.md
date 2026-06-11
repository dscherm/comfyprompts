# Quality Gate 2: TRANSITIONS

## PASS Criteria (ALL must pass)
- [ ] Transition tiles exist for all required terrain pairs (N*(N-1)/2 pairs)
- [ ] Each transition tile is a valid PNG, >10KB
- [ ] Each transition tile has dimensions matching `tile_size_px` (or is a valid 4x4 grid at 4x tile_size)
- [ ] `output/transitions/transition-log.json` exists with pair metadata
- [ ] Each transition visually contains elements of both terrain types (not a duplicate of either base tile)

## WARN Criteria (log but don't block)
- [ ] Some pairs used fallback mode ("simple" with blended prompts) instead of "dual_terrain"
- [ ] Gradient width may be too sharp or too soft for certain terrain pairs (subjective)
- [ ] Transition tile count is less than 16 per pair (reduced marching squares coverage)
- [ ] File sizes vary dramatically between pairs (>3x ratio, may indicate generation inconsistency)

## FAIL Criteria (block advancement -- re-run Stage 2)
- [ ] Any terrain pair has zero transition tiles
- [ ] Any transition PNG is 0 bytes or corrupt
- [ ] Transition tiles are exact copies of base tiles (no blending occurred)
- [ ] `transition-log.json` is missing
- [ ] Total transition tile count is 0

## Validation Method
```python
from pathlib import Path
import json
from itertools import combinations

state = json.load(open("output/pipeline-state.json"))
terrains = sorted(state["terrain_types"])
tile_size = state["tile_size_px"]
trans_dir = Path("output/transitions")

expected_pairs = list(combinations(terrains, 2))
log = json.load(open(trans_dir / "transition-log.json"))

for a, b in expected_pairs:
    # Check for grid file or individual tiles
    grid = trans_dir / f"{a}_to_{b}_grid.png"
    first_tile = trans_dir / f"{a}_to_{b}_01.png"
    assert grid.exists() or first_tile.exists(), f"Missing transitions for {a}-{b}"

assert log["total_pairs"] == len(expected_pairs), "Pair count mismatch"
```

## Gate Logic
- If FAIL on missing pairs: re-trigger Stage 2 for the specific missing pairs
- If FAIL on corrupt files: regenerate the affected pair with a new seed
- If WARN on fallback mode: acceptable, note in pipeline state for future improvement
