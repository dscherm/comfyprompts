# Quality Gate 2: EVALUATE

This gate has special behavior due to the self-correction loop. It determines whether the image is good enough to proceed to finalization, or whether it needs inpainting corrections.

## PASS Criteria (ALL must pass to proceed to Stage 4)
- [ ] Evaluation report exists at `output/evaluations/eval-loop-{NNN}.json`
- [ ] Caption was successfully generated (Florence-2 captioning operational)
- [ ] Semantic similarity score was computed with all four dimensions scored
- [ ] Score >= `quality_threshold` from pipeline state (default 0.8)
- [ ] No critical-severity problems remain unresolved

## LOOP Criteria (triggers inpaint loop instead of blocking)
When the score is below threshold but the correction loop has budget remaining, this gate does NOT fail -- it triggers the inpaint loop:
- [ ] Score < `quality_threshold` AND `correction_loop.current_loop` < `correction_loop.max_loops`
- [ ] At least one actionable problem was identified with a suggested fix
- [ ] The evaluation report includes a clear recommendation for inpainting

In this case, the gate result is `LOOP` (not `FAIL`), and the pipeline advances to Stage 3 (inpaint) instead of retrying Stage 2.

## WARN Criteria (log but don't block)
- [ ] Score is between threshold and threshold-0.05 (barely passing, fragile)
- [ ] Caption quality is low (very short, generic description)
- [ ] Minor-severity problems remain but are not worth another loop iteration
- [ ] Score regressed from a previous loop iteration (inpainting may have hurt quality)
- [ ] Loop budget is nearly exhausted (1 loop remaining)

## FAIL Criteria (block advancement, re-run Stage 2)
- [ ] No evaluation report was generated (complete evaluation failure)
- [ ] Caption generation failed entirely (Florence-2 unavailable)
- [ ] Score could not be computed (missing dimension scores)
- [ ] Evaluation report is malformed or missing required fields
- [ ] Score < 0.3 on first evaluation AND this is the first loop (recommend regeneration)

## Special: Loop Budget Exhausted
If `correction_loop.current_loop >= correction_loop.max_loops` AND score < threshold:
- Gate result is `WARN` (not FAIL)
- Accept the best-scoring iteration from `correction_loop.score_history`
- Set decision to `FAIL_ACCEPT_BEST`
- Proceed to Stage 4 with the best available result
- Log warning: "Loop budget exhausted. Accepting best score: {best_score} (threshold: {threshold})"

## Special: Score Regression
If the current score is lower than the previous loop's score:
- Log warning: "Score regression: {previous} -> {current}"
- If this is the second consecutive regression, accept the best-scoring version
- Set decision to `FAIL_ACCEPT_BEST`

## Validation Method
```bash
# Check evaluation report exists
loop_num=$(cat pipelines/inpaint-ralph/output/pipeline-state.json | python -c "import sys,json; print(json.load(sys.stdin)['correction_loop']['current_loop'])")
eval_file="pipelines/inpaint-ralph/output/evaluations/eval-loop-$(printf '%03d' $loop_num).json"

if [ -f "$eval_file" ]; then
  score=$(cat "$eval_file" | python -c "import sys,json; print(json.load(sys.stdin)['scoring']['weighted_total'])")
  echo "Evaluation score: $score"
else
  echo "Evaluation report: MISSING"
fi
```

## Gate Result Output
Write to `output/gate-02-result.json`:
```json
{
  "stage": "2-evaluate",
  "result": "PASS|LOOP|WARN|FAIL",
  "checks": [
    { "name": "report_exists", "passed": true, "detail": "eval-loop-001.json present" },
    { "name": "caption_generated", "passed": true, "detail": "Florence-2 caption: 127 words" },
    { "name": "score_computed", "passed": true, "detail": "All 4 dimensions scored" },
    { "name": "score_meets_threshold", "passed": false, "detail": "Score 0.61 < threshold 0.8" },
    { "name": "loop_budget_remaining", "passed": true, "detail": "Loop 1/5, budget available" },
    { "name": "actionable_problems", "passed": true, "detail": "2 problems with suggested fixes" }
  ],
  "warnings": [],
  "blocking_errors": [],
  "recommendation": "Score below threshold. Proceed to inpaint stage (loop 1/5)."
}
```
