# Quality Gate 2: FULLBODY

## PASS Criteria (ALL must pass)
- [ ] `output/fullbody/fullbody.png` exists
- [ ] Image file is a valid PNG and >100KB
- [ ] Image shows a full body (head to feet visible, no major cropping)
- [ ] Character is recognizably the same as the portrait (similar face, hair, clothing style)
- [ ] Art style is consistent with the portrait (same visual language, color palette)
- [ ] Background is reasonably clean (solid color or simple, not cluttered)

## WARN Criteria (log but don't block)
- [ ] Pose is not A-pose or T-pose (rigging may be harder but not impossible)
- [ ] Feet are slightly cropped (workable for 3D but not ideal)
- [ ] Background has moderate shadows or gradients (may need cleanup)
- [ ] Character proportions differ slightly from portrait (head size, build)
- [ ] Seed file missing (`fullbody-seed.txt`)

## FAIL Criteria (block advancement)
- [ ] No full-body image generated
- [ ] Image is blank, corrupt, or <10KB
- [ ] Character is clearly a different person than the portrait (wrong gender, wrong race, completely different features)
- [ ] Only partial body visible (waist-up only, missing legs entirely)
- [ ] Art style is completely different from portrait (photorealistic vs cartoon, etc.)
- [ ] Image is severely deformed (extra limbs, broken anatomy)

## Validation Method

### File check
```bash
fullbody="pipelines/character-ralph/output/fullbody/fullbody.png"
if [ -f "$fullbody" ]; then
  size=$(stat --printf="%s" "$fullbody")
  echo "fullbody.png: ${size} bytes"
  if [ "$size" -lt 102400 ]; then
    echo "FAIL: Image too small"
  else
    echo "PASS: File exists with reasonable size"
  fi
else
  echo "FAIL: fullbody.png does not exist"
fi
```

### Consistency check
Use `caption_image` on both the portrait and full-body image. Compare captions for:
- Same character identity (gender, hair, distinguishing features)
- Same art style description
- Full body visible in the fullbody image
- Pose suitability for rigging

### Background check
Caption should not mention complex backgrounds, other characters, or heavy scene elements. Ideal: "white background", "simple background", "studio setting".

### Gate Result Format
Write to `output/gate-02-result.json`:
```json
{
  "stage": "2-fullbody",
  "result": "PASS|WARN|FAIL",
  "checks": [
    { "name": "file_exists", "passed": true, "detail": "fullbody.png exists, 312KB" },
    { "name": "full_body_visible", "passed": true, "detail": "Caption confirms head-to-feet visibility" },
    { "name": "character_consistency", "passed": true, "detail": "Same character as portrait" },
    { "name": "style_consistency", "passed": true, "detail": "Art style matches portrait" },
    { "name": "clean_background", "passed": true, "detail": "Simple background detected" }
  ],
  "warnings": [],
  "blocking_errors": [],
  "recommendation": "Proceed to multiview stage"
}
```
