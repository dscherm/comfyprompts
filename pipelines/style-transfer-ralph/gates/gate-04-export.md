# Quality Gate 4: EXPORT (Final Gate)

## PASS Criteria (ALL must pass)
- [ ] `output/final/STYLE-MANIFEST.md` exists and contains all required sections
- [ ] `output/final/style-preset-final.json` exists and is valid JSON
- [ ] `output/final/export-log.json` exists and is valid JSON
- [ ] At least one export format directory exists under `output/final/exports/`
- [ ] Full-resolution styled images exist in `output/final/exports/full_resolution/`
- [ ] Export count in log matches the expected number (targets x platforms)
- [ ] All exported files are non-empty (>0 bytes)

## WARN Criteria (log but don't block)
- [ ] Some platform-specific exports failed (e.g., Instagram resize) but full-resolution exports exist
- [ ] Total export package size exceeds 500MB
- [ ] Style preset could not be saved via `create_custom_style_preset` (preset tools unavailable)
- [ ] STYLE-MANIFEST.md is missing optional sections (reproducibility instructions)

## FAIL Criteria (block advancement -- re-run Stage 4)
- [ ] `STYLE-MANIFEST.md` is missing
- [ ] No export files exist in `output/final/exports/`
- [ ] `export-log.json` is missing
- [ ] Full-resolution exports are missing (no source-quality outputs preserved)
- [ ] `style-preset-final.json` is missing (style not persisted for reuse)
- [ ] All exported files are 0 bytes or corrupt

## Validation Method
```python
from pathlib import Path
import json

final = Path("output/final")

# Required files
assert (final / "STYLE-MANIFEST.md").exists(), "Missing style manifest"
assert (final / "style-preset-final.json").exists(), "Missing final preset"
assert (final / "export-log.json").exists(), "Missing export log"

# Exports directory
exports = final / "exports"
assert exports.exists(), "Missing exports directory"
assert any(exports.iterdir()), "Exports directory is empty"

# Full resolution
full_res = exports / "full_resolution"
assert full_res.exists(), "Missing full-resolution exports"
full_res_files = list(full_res.glob("*.png")) + list(full_res.glob("*.jpg"))
assert len(full_res_files) > 0, "No full-resolution files"

# Non-empty check
for f in full_res_files:
    assert f.stat().st_size > 0, f"Empty file: {f.name}"

# Export log consistency
log = json.load(open(final / "export-log.json"))
assert log["total_exports"] > 0, "No exports recorded in log"
```

## Pipeline Completion

When this gate passes:
1. All 4 gates have passed
2. STYLE-MANIFEST.md documents the complete style definition and results
3. All exports are ready for use
4. Style preset is saved for future reuse
5. Output: `<promise>STYLE TRANSFER COMPLETE</promise>`
