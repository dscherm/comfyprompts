# Quality Gate 3: ENHANCE

## PASS Criteria (ALL must pass)
- [ ] Enhanced images exist in `output/enhanced/` for every upscaled image
- [ ] Each enhanced image is a valid PNG >50KB (not blank or corrupt)
- [ ] Enhanced image resolution matches the upscaled resolution (no resolution loss)
- [ ] `output/enhanced/enhance-log.json` exists with entries for all processed images
- [ ] No enhanced image shows signs of over-processing (plastic/waxy appearance, halo artifacts)
- [ ] Caption verification confirms content is preserved (no hallucinated changes from edit tools)

## WARN Criteria (log but don't block)
- [ ] Enhancement was skipped for all images (no quality issues found -- this is acceptable)
- [ ] Any image required enhancement revert due to quality degradation
- [ ] Caption after enhancement shows fewer details than caption before (possible detail loss)
- [ ] Color shift detected between upscaled and enhanced versions
- [ ] Enhanced file size is significantly larger than upscaled (>2x, possible format issue)

## FAIL Criteria (block advancement)
- [ ] Any enhanced image is missing (neither enhanced nor copied from upscaled)
- [ ] Any enhanced image is corrupt or blank (0 bytes, invalid PNG)
- [ ] Enhancement introduced catastrophic artifacts (visible distortion, wrong colors, content change)
- [ ] Enhanced image resolution is smaller than the upscaled version
- [ ] `enhance-log.json` is missing or malformed
- [ ] Caption verification reveals the image content was fundamentally altered by enhancement

## Validation Method
```bash
# Check enhanced files exist for each upscaled image
for img in pipelines/upscale-ralph/output/enhanced/enhanced-*.png; do
  if [ -f "$img" ]; then
    size=$(stat --printf="%s" "$img")
    echo "$img: ${size} bytes"
  else
    echo "No enhanced images found"
  fi
done

# Verify log exists
if [ -f "pipelines/upscale-ralph/output/enhanced/enhance-log.json" ]; then
  echo "Enhance log: OK"
else
  echo "Enhance log: MISSING"
fi
```

## Gate Result Output
Write to `output/gate-03-result.json`:
```json
{
  "stage": "3-enhance",
  "result": "PASS|WARN|FAIL",
  "checks": [
    { "name": "enhanced_images_exist", "passed": true, "detail": "5/5 enhanced images present" },
    { "name": "files_valid", "passed": true, "detail": "All PNGs valid, >50KB each" },
    { "name": "resolution_maintained", "passed": true, "detail": "All images at upscaled resolution" },
    { "name": "enhance_log_exists", "passed": true, "detail": "enhance-log.json present" },
    { "name": "no_over_processing", "passed": true, "detail": "No halos or waxy appearance detected" },
    { "name": "content_preserved", "passed": true, "detail": "Caption verification passed for 5/5 images" }
  ],
  "warnings": [],
  "blocking_errors": [],
  "recommendation": "Proceed to export stage"
}
```
