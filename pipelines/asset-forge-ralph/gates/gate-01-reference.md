# Quality Gate 1: REFERENCE IMAGE

## PASS Criteria (ALL must pass)
- [ ] `output/concept/reference.png` exists
- [ ] File size is >50KB (not blank or corrupt)
- [ ] Image is a valid PNG (magic bytes: 89 50 4E 47)
- [ ] Image dimensions are at least 512x512 pixels
- [ ] Subject is visible and centered in the frame (not blank white/black image)

## WARN Criteria (log but don't block)
- [ ] Image has a busy or non-white background (may reduce 3D reconstruction quality)
- [ ] Subject is partially cropped (limbs cut off at edges)
- [ ] Image resolution is below 1024x1024 (lower quality 3D output expected)
- [ ] Multiple subjects visible in image (3D reconstruction works best with single subject)

## FAIL Criteria (block advancement)
- [ ] No image file generated
- [ ] File is corrupt or <10KB (likely blank/error image)
- [ ] `caption_image` reports subject completely mismatches project description (e.g., description says "dragon" but image shows "car")
- [ ] Image is entirely white, black, or a solid color

## Validation Method

### File existence and size check
```bash
file="pipelines/asset-forge-ralph/output/concept/reference.png"
if [ -f "$file" ]; then
  size=$(stat --printf="%s" "$file")
  echo "reference.png: ${size} bytes"
  if [ "$size" -lt 51200 ]; then
    echo "WARN: File under 50KB, may be low quality or corrupt"
  fi
  if [ "$size" -lt 10240 ]; then
    echo "FAIL: File under 10KB, likely blank or error"
  fi
else
  echo "FAIL: reference.png does not exist"
fi
```

### Semantic validation (if caption_image tool is available)
Use `caption_image` on `output/concept/reference.png` and compare the caption against the project description from `pipeline-state.json`. The caption should mention key elements of the description (species, armor, weapon type, etc.). A complete mismatch is a FAIL; partial match is a WARN.

## Gate Result Output

Write to `output/gate-01-result.json`:
```json
{
  "stage": "1-reference",
  "result": "PASS|WARN|FAIL",
  "checks": [
    { "name": "file_exists", "passed": true, "detail": "reference.png exists" },
    { "name": "file_size", "passed": true, "detail": "reference.png is 245KB (>50KB threshold)" },
    { "name": "valid_png", "passed": true, "detail": "Valid PNG header detected" },
    { "name": "subject_match", "passed": true, "detail": "Caption mentions key description elements" }
  ],
  "warnings": [],
  "blocking_errors": [],
  "recommendation": "Proceed to mesh generation"
}
```
