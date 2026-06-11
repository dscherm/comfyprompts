# Quality Gate 5: EXPORT (Final Gate)

## PASS Criteria (ALL must pass)
- [ ] `output/final/tileset-atlas.png` exists and matches `output/atlas/tileset-atlas.png`
- [ ] `output/final/tileset-metadata.json` exists and is valid JSON
- [ ] `output/final/tile-index.json` exists and is valid JSON
- [ ] `output/final/TILESET-MANIFEST.md` exists and contains all required sections
- [ ] Tile index maps every tile ID to its terrain name
- [ ] Metadata tile count matches atlas tile count from Stage 4
- [ ] All export files are non-empty (>0 bytes)

## WARN Criteria (log but don't block)
- [ ] Engine-specific export (`.tres`, Unity JSON) was requested but could not be generated
- [ ] 3D tile generation was requested but some terrains failed GLB conversion
- [ ] Total export package size exceeds 100MB
- [ ] TILESET-MANIFEST.md is missing optional sections (engine-specific import instructions)

## FAIL Criteria (block advancement -- re-run Stage 5)
- [ ] Atlas PNG missing from `output/final/`
- [ ] Metadata JSON missing or invalid
- [ ] TILESET-MANIFEST.md missing
- [ ] Tile index is empty or has wrong tile count
- [ ] Atlas PNG in `output/final/` differs from `output/atlas/` (copy error)
- [ ] 3D tiles requested (`tileset_type == "3d"`) but zero GLBs produced

## Validation Method
```python
from pathlib import Path
import json

final = Path("output/final")

# Required files
assert (final / "tileset-atlas.png").exists()
assert (final / "tileset-metadata.json").exists()
assert (final / "tile-index.json").exists()
assert (final / "TILESET-MANIFEST.md").exists()

# Non-empty
for f in final.iterdir():
    if f.is_file():
        assert f.stat().st_size > 0, f"Empty file: {f.name}"

# Metadata consistency
meta = json.load(open(final / "tileset-metadata.json"))
index = json.load(open(final / "tile-index.json"))
assert len(index) == len(meta["tiles"]), "Index/metadata tile count mismatch"

# 3D check if applicable
state = json.load(open("output/pipeline-state.json"))
if state.get("tileset_type") == "3d":
    glb_dir = final / "3d"
    assert glb_dir.exists(), "3D output directory missing"
    glbs = list(glb_dir.glob("*.glb"))
    assert len(glbs) > 0, "No GLB files produced"
```

## Pipeline Completion

When this gate passes:
1. All 5 gates have passed
2. TILESET-MANIFEST.md is the single source of truth for the tileset
3. Atlas and metadata are ready for game engine import
4. Output: `<promise>TILESET COMPLETE</promise>`
