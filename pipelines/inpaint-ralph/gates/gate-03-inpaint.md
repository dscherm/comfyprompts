# Quality Gate 3: INPAINT

## PASS Criteria (ALL must pass)
- [ ] Inpainted image exists at `output/inpainted/loop-{NNN}.png`
- [ ] Inpainted image is a valid PNG >50KB (not blank or corrupt)
- [ ] Inpainted image has the same or similar resolution as the source image (no unexpected resize)
- [ ] `output/inpainted/inpaint-log-{NNN}.json` exists with details of fixes applied
- [ ] At least one problem from the evaluation was addressed
- [ ] The inpainted image is visually different from the source (the edit tool actually made changes)

## WARN Criteria (log but don't block)
- [ ] Not all identified problems were addressed in this loop iteration (deferred to next loop)
- [ ] Inpainting tool produced subtle changes that may not significantly improve the score
- [ ] Multiple inpainting attempts were needed (first attempt failed or produced poor results)
- [ ] Inpainted image file size is significantly different from source (>3x larger or <0.3x smaller)
- [ ] Inpainting tool returned warnings about the edit instruction

## FAIL Criteria (block -- re-run Stage 3)
- [ ] No inpainted image was produced (inpainting tool failed entirely)
- [ ] Inpainted image is corrupt or blank (0 bytes, invalid format)
- [ ] Inpainted image is identical to the source (no changes were made despite edit instruction)
- [ ] Inpainting introduced catastrophic artifacts (solid color regions, extreme distortion)
- [ ] `inpaint-log.json` is missing (no record of what was attempted)
- [ ] All inpainting tools failed (ComfyUI and CoPlay MCP both unavailable)

## Score Improvement Expectation

While this gate does not directly check the evaluation score (that happens in Gate 2), it does verify that the inpainting produced meaningful changes. The expectation is:
- The inpainted image should be different enough from the source to potentially improve the score
- If the image appears unchanged, the inpainting instruction may need to be more specific
- The actual score improvement is verified when the pipeline returns to Stage 2

## Validation Method
```bash
# Check inpainted image exists
loop_num=$(cat pipelines/inpaint-ralph/output/pipeline-state.json | python -c "import sys,json; print(json.load(sys.stdin)['correction_loop']['current_loop'])")
inpaint_file="pipelines/inpaint-ralph/output/inpainted/loop-$(printf '%03d' $loop_num).png"

if [ -f "$inpaint_file" ]; then
  size=$(stat --printf="%s" "$inpaint_file")
  echo "Inpainted image: ${size} bytes"
else
  echo "Inpainted image: MISSING"
fi

# Check inpaint log
log_file="pipelines/inpaint-ralph/output/inpainted/inpaint-log-$(printf '%03d' $loop_num).json"
if [ -f "$log_file" ]; then
  echo "Inpaint log: OK"
else
  echo "Inpaint log: MISSING"
fi
```

## Gate Result Output
Write to `output/gate-03-result.json`:
```json
{
  "stage": "3-inpaint",
  "result": "PASS|WARN|FAIL",
  "checks": [
    { "name": "inpainted_image_exists", "passed": true, "detail": "loop-001.png exists, 2.8MB" },
    { "name": "file_valid", "passed": true, "detail": "Valid PNG, 1024x1024" },
    { "name": "resolution_maintained", "passed": true, "detail": "1024x1024 matches source" },
    { "name": "inpaint_log_exists", "passed": true, "detail": "inpaint-log-001.json present" },
    { "name": "problems_addressed", "passed": true, "detail": "1/2 problems addressed (wings added)" },
    { "name": "image_changed", "passed": true, "detail": "Image differs from source (edit applied)" }
  ],
  "warnings": [],
  "blocking_errors": [],
  "recommendation": "Inpainting applied successfully. Return to evaluation for re-scoring."
}
```

## After Gate Pass
When this gate passes, the pipeline returns to Stage 2 (evaluate) to re-score the inpainted image. This is the core of the self-correction loop.
