# Quality Gate 2: UPSCALE

## PASS Criteria (ALL must pass)
- [ ] Upscaled images exist in `output/upscaled/` for every input image (or documented failures with retry exhausted)
- [ ] Each upscaled image is a valid PNG >50KB (not blank or corrupt)
- [ ] Each upscaled image resolution is >= 2x the original in both width and height
- [ ] `output/upscaled/upscale-log.json` exists with entries for all processed images
- [ ] At least 80% of input images were successfully upscaled (e.g., 4/5 minimum)
- [ ] No upscaled images have catastrophic artifacts (completely wrong colors, extreme distortion)

## WARN Criteria (log but don't block)
- [ ] Any image used a fallback model instead of the recommended model
- [ ] Any image achieved less than the target scale factor (e.g., 2x instead of 4x)
- [ ] Upscaled file size is unusually large (>50MB for a single image)
- [ ] Upscaled file size is unusually small relative to resolution (possible quality issue)
- [ ] One or more images failed but were within the 20% failure tolerance

## FAIL Criteria (block advancement)
- [ ] No upscaled images were produced (complete upscale failure)
- [ ] More than 20% of input images failed upscaling (batch failure)
- [ ] Any upscaled image has zero width or zero height
- [ ] `upscale-log.json` is missing or malformed
- [ ] All upscaled images are below the original resolution (downscaled instead of upscaled)
- [ ] ComfyUI connection failure prevented all upscaling attempts

## Validation Method
```bash
# Check upscaled files exist and have reasonable size
for img in pipelines/upscale-ralph/output/upscaled/upscaled-*.png; do
  if [ -f "$img" ]; then
    size=$(stat --printf="%s" "$img")
    echo "$img: ${size} bytes"
  else
    echo "No upscaled images found"
  fi
done

# Verify log exists
if [ -f "pipelines/upscale-ralph/output/upscaled/upscale-log.json" ]; then
  echo "Upscale log: OK"
else
  echo "Upscale log: MISSING"
fi
```

## Gate Result Output
Write to `output/gate-02-result.json`:
```json
{
  "stage": "2-upscale",
  "result": "PASS|WARN|FAIL",
  "checks": [
    { "name": "upscaled_images_exist", "passed": true, "detail": "5/5 upscaled images present" },
    { "name": "files_valid", "passed": true, "detail": "All PNGs valid, >50KB each" },
    { "name": "resolution_increase", "passed": true, "detail": "All images >= 2x original resolution" },
    { "name": "upscale_log_exists", "passed": true, "detail": "upscale-log.json present" },
    { "name": "success_rate", "passed": true, "detail": "5/5 succeeded (100%)" },
    { "name": "no_catastrophic_artifacts", "passed": true, "detail": "Visual spot-check passed" }
  ],
  "warnings": [],
  "blocking_errors": [],
  "recommendation": "Proceed to enhancement stage"
}
```
