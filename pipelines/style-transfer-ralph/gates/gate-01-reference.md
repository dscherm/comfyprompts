# Quality Gate 1: REFERENCE

## PASS Criteria (ALL must pass)
- [ ] At least 1 reference image exists in `output/reference/` and is a valid PNG/JPEG >10KB
- [ ] `output/reference/style-preset.json` exists and is valid JSON
- [ ] Style preset contains non-empty `prompt_prefix` or `prompt_suffix` (at least one style modifier defined)
- [ ] `output/reference/style-profile.json` exists with extracted style characteristics
- [ ] If `style_config.lora_name` is specified, the LoRA weight is between 0.1 and 1.0

## WARN Criteria (log but don't block)
- [ ] Only 1 reference image provided (multi-reference workflows unavailable, limited style coverage)
- [ ] LoRA name specified but could not be verified as installed (may fail at transfer time)
- [ ] IP-Adapter weight calibration was skipped (using default weight)
- [ ] Style profile dominant colors are very similar (low color diversity in reference)
- [ ] Caption keywords extracted from reference are generic (e.g., "art", "painting" only)

## FAIL Criteria (block advancement -- re-run Stage 1)
- [ ] No reference images exist in `output/reference/`
- [ ] All reference images are corrupt, blank, or <10KB
- [ ] `style-preset.json` is missing
- [ ] Style preset has empty `prompt_prefix` AND empty `prompt_suffix` AND no LoRA (no style definition at all)
- [ ] `style-profile.json` is missing (no style analysis performed)

## Validation Method
```python
from pathlib import Path
import json

ref_dir = Path("output/reference")

# Check reference images
refs = list(ref_dir.glob("ref-*.png")) + list(ref_dir.glob("ref-*.jpg"))
assert len(refs) >= 1, "No reference images found"
for ref in refs:
    assert ref.stat().st_size > 10240, f"Reference too small: {ref.name}"

# Check style preset
preset = json.load(open(ref_dir / "style-preset.json"))
has_style = bool(preset.get("prompt_prefix")) or bool(preset.get("prompt_suffix")) or bool(preset.get("lora_name"))
assert has_style, "No style modifiers defined in preset"

# Check style profile
profile = json.load(open(ref_dir / "style-profile.json"))
assert "dominant_colors" in profile, "Style profile missing color analysis"
assert "caption_keywords" in profile, "Style profile missing caption analysis"

# LoRA weight range
if preset.get("lora_weight", 0) > 0:
    assert 0.1 <= preset["lora_weight"] <= 1.0, f"LoRA weight out of range: {preset['lora_weight']}"
```

## Gate Logic
- If FAIL on missing references: re-run Stage 1 to generate exemplar images
- If FAIL on empty preset: re-run Stage 1 with explicit style name to derive prompt modifiers
- If WARN on single reference: proceed but note that style_transfer_weighted/multi_reference workflows cannot be used
