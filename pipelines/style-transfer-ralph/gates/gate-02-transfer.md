# Quality Gate 2: TRANSFER

## PASS Criteria (ALL must pass)
- [ ] Styled output exists for every target image listed in `pipeline-state.json`
- [ ] Each styled output is a valid PNG, >50KB (not blank or failed generation)
- [ ] `output/styled/transfer-log.json` exists and is valid JSON
- [ ] Transfer log shows >80% success rate (at least 80% of targets styled successfully)
- [ ] No styled output is an exact copy of the reference image (style was actually transferred, not just copied)

## WARN Criteria (log but don't block)
- [ ] Some targets required retry with adjusted parameters (logged in transfer-log)
- [ ] 1-2 targets failed but batch success rate is still >80%
- [ ] Some styled outputs are significantly different in file size from others (>3x ratio)
- [ ] IP-Adapter weight was adjusted during the batch (inconsistent transfer strength)

## FAIL Criteria (block advancement -- re-run Stage 2)
- [ ] More than 20% of targets failed style transfer
- [ ] No styled outputs exist at all
- [ ] `transfer-log.json` is missing
- [ ] All styled outputs are <50KB (likely blank or failed generations)
- [ ] All styled outputs are identical (same seed used for all, no content variation)

## Validation Method
```python
from pathlib import Path
import json

state = json.load(open("output/pipeline-state.json"))
target_count = len(state["target_images"])
styled_dir = Path("output/styled")

# Check styled outputs exist
styled = list(styled_dir.glob("styled_*.png"))
assert len(styled) > 0, "No styled outputs found"

# Check file sizes
for s in styled:
    assert s.stat().st_size > 51200, f"Styled output too small (likely blank): {s.name}"

# Check transfer log
log = json.load(open(styled_dir / "transfer-log.json"))
success_rate = log["succeeded"] / log["total_targets"]
assert success_rate >= 0.8, f"Success rate too low: {success_rate:.0%}"

# Check not all identical (compare file sizes as quick proxy)
sizes = [s.stat().st_size for s in styled]
assert len(set(sizes)) > 1 or len(styled) == 1, "All outputs appear identical"
```

## Gate Logic
- If FAIL on low success rate: re-run Stage 2 with adjusted IP-Adapter weight or different workflow
- If FAIL on blank outputs: check ComfyUI server connectivity, then retry
- If FAIL on identical outputs: verify seed incrementing is working correctly
- If WARN on retries: acceptable, the retry logic is working as intended
