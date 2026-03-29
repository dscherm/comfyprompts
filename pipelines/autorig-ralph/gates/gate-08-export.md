# Quality Gate 8: EXPORT

## PASS Criteria (ALL must pass)
- [ ] Asset manifest exists at `output/final/{asset-id}/manifest.json`
- [ ] Blender GLB export exists and file size > 0
- [ ] Unity FBX export exists and file size > 0
- [ ] Unreal FBX export exists and file size > 0
- [ ] GLB re-import validation passes (armature + mesh present)
- [ ] pipeline-state.json updated (stage complete, batch progress advanced)

## WARN Criteria (log but don't block)
- [ ] One platform export file smaller than expected (<50KB)
- [ ] Bone names in FBX don't perfectly match platform convention (manual mapping needed)
- [ ] Export includes extra objects (empties, IK targets) that could be cleaned

## FAIL Criteria (block advancement)
- [ ] Any export file missing or zero-size
- [ ] GLB re-import finds no armature
- [ ] GLB re-import finds no mesh
- [ ] Asset manifest missing or invalid JSON
- [ ] Batch state not updated

## Validation Method
```bash
python -c "
import json, sys, os
asset_id = 'ASSET_ID'
try:
    base = f'pipelines/autorig-ralph/output/final/{asset_id}'
    with open(f'{base}/manifest.json') as f:
        data = json.load(f)
    exports = data.get('exports', {})
    for platform, filename in exports.items():
        path = f'{base}/{filename}'
        assert os.path.exists(path), f'{platform} export missing: {path}'
        assert os.path.getsize(path) > 0, f'{platform} export empty: {path}'
    print(f'PASS: {len(exports)} exports for {data.get(\"name\", asset_id)}')
except Exception as e:
    print(f'FAIL: {e}')
    sys.exit(1)
"
```
