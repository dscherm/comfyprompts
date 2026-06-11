# Quality Gate 1: ANALYZE

## PASS Criteria (ALL must pass)
- [ ] All input images listed in `pipeline-state.json` are readable files (valid PNG, JPEG, WEBP, or TIFF)
- [ ] No input files are corrupt (all >1KB and decodable)
- [ ] Per-image analysis reports exist in `output/analysis/` for every input image
- [ ] `output/analysis/analysis-summary.json` exists and contains entries for all images
- [ ] Each analysis report has: resolution, aspect ratio, content type, and recommended upscale model
- [ ] At least one caption was generated successfully (Florence-2 captioning is operational)

## WARN Criteria (log but don't block)
- [ ] Any input image is below 128x128 pixels (very low resolution, upscale quality may be poor)
- [ ] Any input image has severe quality issues (severity: "severe" for any issue type)
- [ ] Content type classification is "mixed" for any image (model selection may be suboptimal)
- [ ] Caption generation failed for some images (fallback to manual content type assignment)
- [ ] Input images have widely varying aspect ratios (batch export cropping may be inconsistent)

## FAIL Criteria (block advancement)
- [ ] Any input file listed in `pipeline-state.json` does not exist or is unreadable
- [ ] Any input file is corrupt (0 bytes, invalid header, cannot be decoded)
- [ ] No analysis reports were generated (complete analysis failure)
- [ ] `analysis-summary.json` is missing or malformed
- [ ] Zero images have a content type classification (model selection impossible)

## Validation Method
```bash
# Verify analysis files exist for each input image
for report in pipelines/upscale-ralph/output/analysis/analysis-*.json; do
  if [ -f "$report" ]; then
    size=$(stat --printf="%s" "$report")
    echo "$report: ${size} bytes"
  fi
done

# Verify summary exists
if [ -f "pipelines/upscale-ralph/output/analysis/analysis-summary.json" ]; then
  echo "Summary report: OK"
else
  echo "Summary report: MISSING"
fi
```

## Gate Result Output
Write to `output/gate-01-result.json`:
```json
{
  "stage": "1-analyze",
  "result": "PASS|WARN|FAIL",
  "checks": [
    { "name": "all_files_readable", "passed": true, "detail": "5/5 input images readable" },
    { "name": "no_corrupt_files", "passed": true, "detail": "All files valid" },
    { "name": "analysis_reports_exist", "passed": true, "detail": "5/5 reports generated" },
    { "name": "summary_exists", "passed": true, "detail": "analysis-summary.json present" },
    { "name": "content_types_assigned", "passed": true, "detail": "3 photo, 2 anime" },
    { "name": "caption_operational", "passed": true, "detail": "Florence-2 captioned 5/5 images" }
  ],
  "warnings": [],
  "blocking_errors": [],
  "recommendation": "Proceed to upscale stage"
}
```
