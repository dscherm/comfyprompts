# Quality Gate 3: CONCEPT-FORGE

## PASS Criteria (ALL must pass)
- [ ] `output/concept/primary-concept.png` exists
- [ ] File size is >50KB (not blank or corrupt)
- [ ] Image is a valid PNG (magic bytes: 89 50 4E 47)
- [ ] Image dimensions are at least 512x512 pixels
- [ ] `caption_image` output confirms the subject matches the pipeline's asset type and description

## WARN Criteria (log but don't block)
- [ ] Image is below 1024x1024 (upscale was skipped or failed -- downstream 3D quality may be reduced)
- [ ] Caption does not mention any material from the material palette (material enrichment may not have transferred)
- [ ] Background appears non-white (busy backgrounds reduce 3D reconstruction accuracy)
- [ ] Subject is partially cropped at image edges (limbs cut off)
- [ ] Multiple subjects are visible in the image

## FAIL Criteria (block advancement)
- [ ] `output/concept/primary-concept.png` does not exist
- [ ] File is corrupt or under 10KB (blank/error output)
- [ ] Image is entirely white, black, or a solid color
- [ ] `caption_image` reports the subject completely mismatches the project description (e.g., description says "dragon" but image shows "building")

## Validation Method

### File existence and size check
```bash
file="pipelines/skeuomorph-ralph/output/concept/primary-concept.png"
if [ -f "$file" ]; then
  size=$(stat --printf="%s" "$file")
  echo "primary-concept.png: ${size} bytes"
  if [ "$size" -lt 51200 ]; then
    echo "WARN: File under 50KB, may be low quality"
  fi
  if [ "$size" -lt 10240 ]; then
    echo "FAIL: File under 10KB, likely blank or error image"
  fi
else
  echo "FAIL: primary-concept.png does not exist"
fi
```

### PNG header check
```bash
python -c "
with open('pipelines/skeuomorph-ralph/output/concept/primary-concept.png','rb') as f:
    header = f.read(8)
if header[:4] == b'\\x89PNG':
    print('PASS: valid PNG header')
else:
    print('FAIL: not a valid PNG file')
"
```

### Dimension check
```bash
python -c "
from PIL import Image
img = Image.open('pipelines/skeuomorph-ralph/output/concept/primary-concept.png')
w, h = img.size
print(f'Dimensions: {w}x{h}')
if w < 512 or h < 512:
    print('FAIL: image is below 512x512 minimum')
elif w < 1024 or h < 1024:
    print('WARN: image is below 1024x1024 (reduced 3D quality expected)')
else:
    print('PASS: dimensions meet requirements')
"
```

### Semantic validation
Use `caption_image` with `more_detailed_caption` on `output/concept/primary-concept.png`. Cross-reference against:
1. The `asset_type` from `pipeline-state.json` -- caption should mention the correct type of subject
2. At least one material name from `material-palette.json` materials array -- caption should describe a material present in the palette

A complete mismatch on the subject type is a FAIL. Missing material mentions is a WARN.

## Gate Result Output

Write to `output/gate-03-result.json`:
```json
{
  "stage": "3-concept-forge",
  "result": "PASS|WARN|FAIL",
  "checks": [
    { "name": "file_exists", "passed": true, "detail": "primary-concept.png exists" },
    { "name": "file_size", "passed": true, "detail": "primary-concept.png is 312KB (>50KB threshold)" },
    { "name": "valid_png", "passed": true, "detail": "Valid PNG header detected" },
    { "name": "dimensions", "passed": true, "detail": "1024x1024 pixels" },
    { "name": "subject_match", "passed": true, "detail": "Caption mentions armored figure with steel and leather (matches description)" }
  ],
  "warnings": [],
  "blocking_errors": [],
  "recommendation": "Proceed to mesh generation"
}
```
