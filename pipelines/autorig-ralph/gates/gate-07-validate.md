# Quality Gate 7: VALIDATE

## PASS Criteria (ALL must pass)
- [ ] Quality report exists at `output/validated/{asset-id}_quality-report.json`
- [ ] Overall score >= 80
- [ ] Weight coverage >= 95% (or >= 90% with WARN)
- [ ] No pose test has >5 collapsed faces
- [ ] No pose test has penetration >2cm
- [ ] Bone hierarchy valid (single root, no orphans)
- [ ] At least 5 test pose screenshots saved

## WARN Criteria (log but don't block)
- [ ] Score 60-79 (marginal quality)
- [ ] Weight coverage 90-95%
- [ ] 1-5 collapsed faces in any pose
- [ ] Penetration 1-2cm in any pose
- [ ] Platform compatibility check fails for one platform

## FAIL Criteria (block advancement)
- [ ] Score < 60
- [ ] Weight coverage < 90%
- [ ] >5 collapsed faces in any pose
- [ ] Penetration >2cm in any pose
- [ ] Bone hierarchy broken (multiple roots, orphans)
- [ ] Quality report missing

## Validation Method
```bash
python -c "
import json, sys
asset_id = 'ASSET_ID'
try:
    with open(f'pipelines/autorig-ralph/output/validated/{asset_id}_quality-report.json') as f:
        data = json.load(f)
    score = data.get('score', 0)
    result = data.get('overall_result', 'FAIL')
    coverage = data.get('weight_coverage', 0)
    assert score >= 60, f'Score too low: {score}'
    assert coverage >= 0.90, f'Coverage too low: {coverage:.2%}'
    if score >= 80:
        print(f'PASS: score {score}/100, coverage {coverage:.2%}')
    else:
        print(f'WARN: score {score}/100 (target 80+), coverage {coverage:.2%}')
except Exception as e:
    print(f'FAIL: {e}')
    sys.exit(1)
"
```
