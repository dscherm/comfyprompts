# Quality Gate 4: SKIN-WEIGHTS

## PASS Criteria (ALL must pass)
- [ ] Weight report exists at `output/weighted/{asset-id}_weight-report.json`
- [ ] Weight coverage >= 95%
- [ ] Weighted mesh exported to `output/weighted/{asset-id}_weighted.glb`
- [ ] All vertex groups correspond to existing bones
- [ ] No vertex has total weight sum < 0.01 (effectively unweighted)
- [ ] Weight tool recorded (unirig/proximity/blender_auto)

## WARN Criteria (log but don't block)
- [ ] Coverage 90-95% (acceptable but not ideal)
- [ ] Primary tool failed, fallback used
- [ ] Split mesh strategy required
- [ ] >100 vertices with very low weights (< 0.05)
- [ ] Weight smoothing applied more than once

## FAIL Criteria (block advancement)
- [ ] Coverage < 90%
- [ ] Weighted mesh missing
- [ ] Weight report missing
- [ ] >5% of vertices have no vertex group assignment
- [ ] All weight tools failed

## Validation Method
```bash
python -c "
import json, sys
asset_id = 'ASSET_ID'
try:
    with open(f'pipelines/autorig-ralph/output/weighted/{asset_id}_weight-report.json') as f:
        data = json.load(f)
    coverage = data.get('coverage', 0)
    assert coverage >= 0.90, f'Coverage too low: {coverage:.2%}'
    if coverage < 0.95:
        print(f'WARN: Coverage {coverage:.2%} (target 95%)')
    else:
        print(f'PASS: Coverage {coverage:.2%} via {data.get(\"tool_used\")}')
except Exception as e:
    print(f'FAIL: {e}')
    sys.exit(1)
"
```
