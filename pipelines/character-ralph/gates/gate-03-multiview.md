# Quality Gate 3: MULTIVIEW

## PASS Criteria (ALL must pass)
- [ ] At least 3 of 4 view images exist in `output/multiview/`
- [ ] Front view (`view-front.png`) exists (this is the critical 3D input)
- [ ] Each existing image is a valid PNG and >50KB
- [ ] Character is recognizable across all views (same clothing, colors, proportions)
- [ ] Front view shows full body with clean background

## WARN Criteria (log but don't block)
- [ ] Only 3 of 4 views generated (3D conversion can proceed with fewer views)
- [ ] Moderate inconsistency between views (slight color or proportion differences)
- [ ] Pose varies between views (not all in same A-pose/T-pose)
- [ ] Background is not perfectly clean in some views
- [ ] Side view shows front-facing character (wrong rotation)
- [ ] Missing multiview-sheet.png composite

## FAIL Criteria (block advancement)
- [ ] Fewer than 2 views generated
- [ ] Front view missing entirely
- [ ] All images are blank, corrupt, or <10KB
- [ ] Views show completely different characters (different clothing, different person)
- [ ] All views show the same angle (no actual rotation)
- [ ] Images are severely deformed

## Validation Method

### File check
```bash
views_dir="pipelines/character-ralph/output/multiview"
count=0
for f in view-front.png view-side.png view-back.png view-34.png; do
  if [ -f "$views_dir/$f" ]; then
    size=$(stat --printf="%s" "$views_dir/$f")
    echo "$f: ${size} bytes"
    if [ "$size" -gt 51200 ]; then
      count=$((count + 1))
    else
      echo "  WARNING: File too small"
    fi
  else
    echo "$f: MISSING"
  fi
done
echo "Valid views: $count / 4"
```

### Consistency check
Caption all generated views and compare:
- Character identity keywords should appear in all captions
- Clothing description should be consistent
- View angle should differ between images (front vs side vs back)
- Art style should be consistent

### View angle verification
- Front view caption should mention "facing camera", "front", or similar
- Side view should mention "profile", "side view", or similar
- Back view should mention "rear", "back", "facing away", or similar
- 3/4 view should mention "angle", "three-quarter", or similar

### Gate Result Format
Write to `output/gate-03-result.json`:
```json
{
  "stage": "3-multiview",
  "result": "PASS|WARN|FAIL",
  "checks": [
    { "name": "front_view_exists", "passed": true, "detail": "view-front.png exists, 198KB" },
    { "name": "view_count", "passed": true, "detail": "4/4 views generated" },
    { "name": "character_consistency", "passed": true, "detail": "Same character across all views" },
    { "name": "angle_variety", "passed": true, "detail": "Different angles confirmed via captions" },
    { "name": "background_quality", "passed": true, "detail": "Clean backgrounds on all views" }
  ],
  "warnings": [],
  "blocking_errors": [],
  "recommendation": "Proceed to 3D conversion using front view as primary input"
}
```
