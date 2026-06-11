# Quality Gate 1: GENERATE

## PASS Criteria (ALL must pass)
- [ ] `output/generated/initial-generation.png` exists
- [ ] Image file is >50KB (not blank, corrupt, or a placeholder)
- [ ] Image is a valid PNG or JPEG that can be decoded
- [ ] Image has non-zero dimensions (width > 0, height > 0)
- [ ] Image is not a solid single color (blank generation detection)
- [ ] `output/generated/generation-log.json` exists with tool and parameter details

## WARN Criteria (log but don't block)
- [ ] Image resolution is below 512x512 (low starting resolution will limit final quality)
- [ ] Image resolution is below 256x256 (very low, upscale quality will be poor)
- [ ] Generation used a fallback tool instead of the preferred tool
- [ ] Generation time exceeded 60 seconds (slow generation, may indicate server issues)
- [ ] File size is unusually small for the resolution (<10KB per megapixel)

## FAIL Criteria (block advancement)
- [ ] No image file generated (generation tool returned an error)
- [ ] Image file is 0 bytes or corrupt (invalid PNG/JPEG header)
- [ ] Image is blank (solid color, all pixels identical)
- [ ] Image is smaller than 64x64 (unusable resolution)
- [ ] `generation-log.json` is missing (no record of what was generated)
- [ ] Both primary and fallback generation tools failed

## Validation Method
```bash
# Check generated image exists and has reasonable size
if [ -f "pipelines/inpaint-ralph/output/generated/initial-generation.png" ]; then
  size=$(stat --printf="%s" "pipelines/inpaint-ralph/output/generated/initial-generation.png")
  echo "initial-generation.png: ${size} bytes"
  if [ "$size" -lt 51200 ]; then
    echo "WARNING: File size below 50KB threshold"
  fi
else
  echo "initial-generation.png: MISSING"
fi

# Check generation log
if [ -f "pipelines/inpaint-ralph/output/generated/generation-log.json" ]; then
  echo "generation-log.json: OK"
else
  echo "generation-log.json: MISSING"
fi
```

## Gate Result Output
Write to `output/gate-01-result.json`:
```json
{
  "stage": "1-generate",
  "result": "PASS|WARN|FAIL",
  "checks": [
    { "name": "image_exists", "passed": true, "detail": "initial-generation.png exists, 2.4MB" },
    { "name": "file_valid", "passed": true, "detail": "Valid PNG, 1024x1024" },
    { "name": "not_blank", "passed": true, "detail": "Image has varied pixel values" },
    { "name": "minimum_size", "passed": true, "detail": "1024x1024 >= 64x64 minimum" },
    { "name": "generation_log", "passed": true, "detail": "generation-log.json present" }
  ],
  "warnings": [],
  "blocking_errors": [],
  "recommendation": "Proceed to evaluation stage"
}
```
