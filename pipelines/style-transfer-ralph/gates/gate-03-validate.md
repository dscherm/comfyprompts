# Quality Gate 3: VALIDATE

## PASS Criteria (ALL must pass)
- [ ] `output/validated/validation-report.json` exists and is valid JSON
- [ ] Caption similarity mean across batch is >80%
- [ ] No individual image has caption similarity <50%
- [ ] Color palette mean distance is <70 (within reasonable range of reference palette)
- [ ] Content preservation check passes for all images (subjects still recognizable)
- [ ] Validation report `overall` is "PASS" or "WARN"

## WARN Criteria (log but don't block)
- [ ] Caption similarity mean is between 80% and 85% (borderline consistency)
- [ ] 1-2 images flagged as palette outliers but within 2 standard deviations
- [ ] Brightness variation across batch is higher than ideal (std_dev 25-30)
- [ ] Some images had low content preservation SSIM (<0.3) but captions confirm subject is retained

## FAIL Criteria (block advancement -- re-run Stage 2 for failing images)
- [ ] Caption similarity mean is <80% (batch is not stylistically cohesive)
- [ ] Any image has caption similarity <50% (completely wrong style)
- [ ] Color palette mean distance >70 (significant color drift from reference)
- [ ] Content preservation failed for >20% of images (style transfer destroyed content)
- [ ] Validation report `overall` is "FAIL"
- [ ] More than 30% of images are outliers on any metric

## Validation Method
```python
import json

report = json.load(open("output/validated/validation-report.json"))

# Caption consistency
cs = report["style_consistency"]["caption_similarity"]
assert cs["mean"] >= 0.80, f"Caption similarity too low: {cs['mean']:.0%}"
assert cs["min"] >= 0.50, f"Worst image caption similarity: {cs['min']:.0%}"

# Color palette
cp = report["style_consistency"]["color_palette"]
assert cp["mean_distance"] < 70, f"Palette distance too high: {cp['mean_distance']}"

# Content preservation
cp = report["content_preservation"]
assert cp["subjects_lost"] / report["total_images_checked"] < 0.20, "Too many subjects lost"

# Overall
assert report["overall"] in ("PASS", "WARN")
```

## Gate Logic
- If FAIL on caption similarity: identify the worst-performing images and re-transfer them with stronger prompt prefix
- If FAIL on palette distance: re-transfer with adjusted IP-Adapter weight (increase for closer match to reference colors)
- If FAIL on content preservation: re-transfer with reduced IP-Adapter weight (style is overpowering content)
- Failed images are added to `images_to_restyle` and only those images are re-processed in Stage 2
