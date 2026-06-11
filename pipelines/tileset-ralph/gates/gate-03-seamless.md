# Quality Gate 3: VALIDATE SEAMLESS

## PASS Criteria (ALL must pass)
- [ ] `output/validated/validation-report.json` exists and is valid JSON
- [ ] Edge pixel comparison passes for all base tiles (MAD < 5% of 255, i.e., < 12.75 per channel)
- [ ] No base tile has a FAIL result in seamless checks
- [ ] Color consistency check passes (no outlier tiles beyond 2 standard deviations)
- [ ] All tiles have correct dimensions matching `tile_size_px`
- [ ] Overall result in validation report is "PASS" or "WARN"

## WARN Criteria (log but don't block)
- [ ] Some transition tiles have edge MAD between 5% and 10% (minor seam visible at tile boundaries)
- [ ] Color brightness range across the set exceeds 30% but is below 40%
- [ ] Caption check found minor style inconsistency (e.g., "painterly" vs "painted")
- [ ] One or two tiles needed regeneration but passed on retry

## FAIL Criteria (block advancement -- re-run Stage 1 or Stage 2)
- [ ] Any base tile has edge MAD > 10% (visible seam when tiled)
- [ ] More than 25% of transition tiles fail seamless check
- [ ] Color consistency check shows outlier tiles (brightness deviation > 40%)
- [ ] Validation report `overall` is "FAIL"
- [ ] Dimension check fails (mixed tile sizes in the set)

## Validation Method
```python
import json

report = json.load(open("output/validated/validation-report.json"))

# Check seamless results
sc = report["seamless_checks"]
fail_rate = sc["failed"] / report["total_tiles_checked"]
assert fail_rate == 0 or (fail_rate < 0.25 and sc["failed"] == 0 for base tiles)

# Check color consistency
assert report["color_consistency"]["result"] != "FAIL"

# Check dimensions
assert report["dimension_checks"]["all_correct"] is True

# Overall
assert report["overall"] in ("PASS", "WARN")
```

## Gate Logic
- If FAIL on base tile seamless: re-trigger Stage 1 for that specific terrain with adjusted LoRA strength
- If FAIL on transition seamless: re-trigger Stage 2 for the affected pairs
- If FAIL on color consistency: re-trigger Stage 1 with tighter palette constraints in the prompt
- Increment `tiles_to_regenerate` list and pass back to the appropriate stage
