# Quality Gate 4: FINALIZE (Final Gate)

## PASS Criteria (ALL must pass)
- [ ] Final image exists at `output/final/result.png`
- [ ] Final image is a valid PNG >50KB
- [ ] Final evaluation score >= `quality_threshold` (or accepted-best with documented reason)
- [ ] All critical-severity problems from the last evaluation are resolved (or explicitly accepted)
- [ ] `output/final/GENERATION-REPORT.md` exists with complete iteration history
- [ ] `output/final/finalize-log.json` exists with acceptance details
- [ ] Final caption confirms the image content matches the original prompt intent

## WARN Criteria (log but don't block)
- [ ] Final score is below threshold but was accepted as best available (loop budget exhausted)
- [ ] Minor-severity problems remain unresolved
- [ ] Image was not upscaled (below target resolution but upscaling was skipped or unavailable)
- [ ] Total correction loops reached max_loops (indicates the prompt may be difficult for generation)
- [ ] Final file size is very large (>20MB, may be slow to transfer)

## FAIL Criteria (block -- re-run Stage 4)
- [ ] Final image is missing from `output/final/`
- [ ] Final image is corrupt or blank
- [ ] GENERATION-REPORT.md is missing or empty
- [ ] finalize-log.json is missing
- [ ] Final caption reveals the image content was corrupted during finalization/upscaling
- [ ] Upscaling was attempted but produced a corrupt or blank output

## Validation Method
```bash
# Check final deliverables
for f in "result.png" "GENERATION-REPORT.md" "finalize-log.json"; do
  path="pipelines/inpaint-ralph/output/final/$f"
  if [ -f "$path" ]; then
    size=$(stat --printf="%s" "$path")
    echo "$f: ${size} bytes"
  else
    echo "$f: MISSING"
  fi
done
```

## Gate Result Output
Write to `output/gate-04-result.json`:
```json
{
  "stage": "4-finalize",
  "result": "PASS|WARN|FAIL",
  "checks": [
    { "name": "final_image_exists", "passed": true, "detail": "result.png exists, 8.2MB" },
    { "name": "file_valid", "passed": true, "detail": "Valid PNG, 4096x4096 (upscaled)" },
    { "name": "score_acceptable", "passed": true, "detail": "Final score 0.85 >= threshold 0.8" },
    { "name": "critical_issues_resolved", "passed": true, "detail": "All critical problems resolved" },
    { "name": "report_exists", "passed": true, "detail": "GENERATION-REPORT.md present and complete" },
    { "name": "log_exists", "passed": true, "detail": "finalize-log.json present" },
    { "name": "caption_verified", "passed": true, "detail": "Final caption matches original prompt intent" }
  ],
  "warnings": [],
  "blocking_errors": [],
  "recommendation": "All checks passed. Pipeline complete."
}
```

## Pipeline Completion
When this gate passes:
1. All 4 gates have passed (with Stage 2 and 3 potentially having looped multiple times)
2. GENERATION-REPORT.md documents the full correction history
3. The final image is the best achievable result through iterative refinement
4. Output: `<promise>INPAINT COMPLETE</promise>`
