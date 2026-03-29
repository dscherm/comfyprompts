# Quality Gate 3: SKELETON-PREDICT

## PASS Criteria (ALL must pass)
- [ ] Skeleton report exists at `output/skeleton/{asset-id}_skeleton-report.json`
- [ ] Bone count within expected range for body type
- [ ] Single root bone (connected hierarchy)
- [ ] No orphan bones (all bones have parent except root)
- [ ] Skeleton tool recorded (unirig/rigify/meshy/autorig)
- [ ] Skeleton FBX or armature saved

## WARN Criteria (log but don't block)
- [ ] Bone count at lower end of expected range
- [ ] Primary tool failed, fallback tool used
- [ ] No bilateral symmetry detected (asymmetric skeleton)
- [ ] Some bones have zero-length (head == tail)
- [ ] Hierarchy depth > 15 (very deep chain)

## FAIL Criteria (block advancement)
- [ ] No skeleton produced (all tools failed)
- [ ] Bone count outside expected range by >50%
- [ ] Multiple root bones (disconnected hierarchy)
- [ ] Skeleton report missing

## Validation Method
```bash
python -c "
import json, sys
asset_id = 'ASSET_ID'
try:
    with open(f'pipelines/autorig-ralph/output/skeleton/{asset_id}_skeleton-report.json') as f:
        data = json.load(f)
    bones = data.get('bone_count', 0)
    assert bones > 0, 'Zero bones'
    assert data.get('has_root', False), 'No root bone'
    assert not data.get('orphan_bones', [True]), 'Orphan bones exist'
    print(f'PASS: {bones} bones via {data.get(\"tool_used\", \"unknown\")}')
except Exception as e:
    print(f'FAIL: {e}')
    sys.exit(1)
"
```
