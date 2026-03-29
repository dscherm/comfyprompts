# Quality Gate 7: PACKAGE (Final Gate)

## PASS Criteria (ALL must pass)
- [ ] `output/final/CHARACTER-SHEET.md` exists and contains all sections with real data
- [ ] `output/final/package-report.json` exists and is valid JSON
- [ ] All required image files exist in `output/final/images/`:
  - `portrait.png` (>100KB)
  - `fullbody.png` (>100KB)
  - `view-front.png` (>50KB)
  - `view-side.png` (>50KB)
  - `view-back.png` (>50KB)
  - `view-34.png` (>50KB)
- [ ] All required model files exist in `output/final/models/`:
  - `character-mesh.glb` (>100KB)
  - `character-rigged.glb` (>100KB)
- [ ] At least 3 animation files exist in `output/final/animations/`:
  - `anim-idle.glb` (>50KB)
  - `anim-walk.glb` (>50KB)
  - `anim-run.glb` (>50KB)
- [ ] CHARACTER-SHEET.md has no unfilled placeholder text (no `[TODO]`, `[placeholder]`, or empty fields)

## WARN Criteria (log but don't block)
- [ ] Total package size >500MB (very large character)
- [ ] `anim-attack.glb` missing (acceptable for non-combat characters)
- [ ] `multiview-sheet.png` composite not included
- [ ] Character description in CHARACTER-SHEET.md is minimal (<50 characters)
- [ ] package-report.json has zero values in mesh_stats

## FAIL Criteria (block -- re-run Stage 7)
- [ ] CHARACTER-SHEET.md missing entirely
- [ ] package-report.json missing or invalid JSON
- [ ] Any required image file missing from `output/final/images/`
- [ ] Both model files missing from `output/final/models/`
- [ ] Fewer than 2 animation files in `output/final/animations/`
- [ ] CHARACTER-SHEET.md contains unfilled template placeholders
- [ ] Files are corrupt (0 bytes or invalid headers)

## Validation Method

### File completeness check
```bash
final_dir="pipelines/character-ralph/output/final"

echo "=== Images ==="
for f in portrait.png fullbody.png view-front.png view-side.png view-back.png view-34.png; do
  if [ -f "$final_dir/images/$f" ]; then
    size=$(stat --printf="%s" "$final_dir/images/$f")
    echo "  $f: ${size} bytes"
  else
    echo "  $f: MISSING"
  fi
done

echo "=== Models ==="
for f in character-mesh.glb character-rigged.glb; do
  if [ -f "$final_dir/models/$f" ]; then
    size=$(stat --printf="%s" "$final_dir/models/$f")
    echo "  $f: ${size} bytes"
  else
    echo "  $f: MISSING"
  fi
done

echo "=== Animations ==="
for f in anim-idle.glb anim-walk.glb anim-run.glb anim-attack.glb; do
  if [ -f "$final_dir/animations/$f" ]; then
    size=$(stat --printf="%s" "$final_dir/animations/$f")
    echo "  $f: ${size} bytes"
  else
    echo "  $f: MISSING ($([ "$f" = "anim-attack.glb" ] && echo 'optional' || echo 'required'))"
  fi
done

echo "=== Documents ==="
for f in CHARACTER-SHEET.md package-report.json; do
  if [ -f "$final_dir/$f" ]; then
    size=$(stat --printf="%s" "$final_dir/$f")
    echo "  $f: ${size} bytes"
  else
    echo "  $f: MISSING"
  fi
done
```

### Placeholder check
Scan CHARACTER-SHEET.md for unfilled placeholders:
```bash
if grep -qE '\[TODO\]|\[placeholder\]|\[FILL\]|\[\]' "$final_dir/CHARACTER-SHEET.md"; then
  echo "FAIL: Unfilled placeholders found in CHARACTER-SHEET.md"
else
  echo "PASS: No placeholders detected"
fi
```

### JSON validation
```bash
python -c "import json; json.load(open('$final_dir/package-report.json'))" && \
  echo "PASS: Valid JSON" || echo "FAIL: Invalid JSON"
```

### Gate Result Format
Write to `output/gate-07-result.json`:
```json
{
  "stage": "7-package",
  "result": "PASS|WARN|FAIL",
  "checks": [
    { "name": "character_sheet_exists", "passed": true, "detail": "CHARACTER-SHEET.md exists, 2.4KB" },
    { "name": "package_report_exists", "passed": true, "detail": "package-report.json valid JSON" },
    { "name": "images_complete", "passed": true, "detail": "6/6 images present" },
    { "name": "models_complete", "passed": true, "detail": "2/2 models present" },
    { "name": "animations_complete", "passed": true, "detail": "3/3 required animations present" },
    { "name": "no_placeholders", "passed": true, "detail": "No unfilled placeholders in CHARACTER-SHEET.md" }
  ],
  "warnings": [],
  "blocking_errors": [],
  "recommendation": "Package complete. All gates passed."
}
```

## Pipeline Completion

When this gate passes:
1. All 7 gates have passed
2. CHARACTER-SHEET.md is the single source of truth for the character
3. All assets are organized in `output/final/` and ready for engine import
4. Output: `<promise>CHARACTER COMPLETE</promise>`
