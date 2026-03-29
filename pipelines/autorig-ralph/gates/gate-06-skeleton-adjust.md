# Quality Gate 6: SKELETON-ADJUST

## PASS Criteria (ALL must pass)
- [ ] Adjustment report exists at `output/adjusted/{asset-id}_adjust-report.json`
- [ ] IK chains configured for arms (chain_count=3 each)
- [ ] IK chains configured for legs (chain_count=2 each, with pole targets)
- [ ] Bone rolls recalculated
- [ ] Proportion checks pass (head, hips, knees within expected height ratios)
- [ ] At least 2 test poses validated with screenshots

## WARN Criteria (log but don't block)
- [ ] No twist bones added (acceptable for Blender-only export)
- [ ] One proportion check slightly outside expected range
- [ ] Pole targets cause minor knee direction issue (adjustable)

## FAIL Criteria (block advancement)
- [ ] No IK chains configured
- [ ] Adjustment report missing
- [ ] Proportion checks show skeleton dramatically misaligned with mesh (>20% off)
- [ ] Test pose causes IK solver failure

## Validation Method
```bash
python -c "
import json, sys
asset_id = 'ASSET_ID'
try:
    with open(f'pipelines/autorig-ralph/output/adjusted/{asset_id}_adjust-report.json') as f:
        data = json.load(f)
    ik = data.get('ik_chains', [])
    assert len(ik) >= 4, f'Expected 4 IK chains, got {len(ik)}'
    assert data.get('bone_rolls_corrected', False), 'Bone rolls not corrected'
    poses = data.get('test_poses_validated', [])
    assert len(poses) >= 2, f'Expected 2+ test poses, got {len(poses)}'
    print(f'PASS: {len(ik)} IK chains, {len(data.get(\"twist_bones_added\",[]))} twist bones')
except Exception as e:
    print(f'FAIL: {e}')
    sys.exit(1)
"
```
