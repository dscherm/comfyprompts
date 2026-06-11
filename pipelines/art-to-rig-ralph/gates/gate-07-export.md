# Quality Gate 7: EXPORT

## PASS Criteria (ALL must pass)
- [ ] Per-asset directory exists at `output/final/{asset-id}/`
- [ ] Blender GLB exists: `rigged/{asset-id}_v{N}_blender.glb`
- [ ] Unity FBX exists: `rigged/{asset-id}_v{N}_unity.fbx`
- [ ] Unreal FBX exists: `rigged/{asset-id}_v{N}_unreal.fbx`
- [ ] Static GLB exists: `mesh/{asset-id}_v{N}_static.glb`
- [ ] Print STL exists: `mesh/{asset-id}_v{N}_print.stl`
- [ ] Front artwork exists: `artwork/{asset-id}_v{N}_front.png`
- [ ] Cleaned artwork exists: `artwork/{asset-id}_v{N}_clean.png`
- [ ] `ASSET-CARD.md` exists and contains all required sections
- [ ] All export files are >10KB (not empty/corrupt)
- [ ] At least one full set of exports exists per asset (v1 at minimum)

## WARN Criteria (log but don't block)
- [ ] One platform FBX failed but the other two succeeded (partial platform coverage)
- [ ] STL file is significantly larger than expected (>100MB -- may be too detailed for slicing)
- [ ] FBX bone names do not exactly match platform convention (may need manual adjustment)
- [ ] Side/3-4 view artwork missing from variants directory (non-critical)
- [ ] ASSET-CARD.md is missing some optional fields (variations comparison, etc.)
- [ ] Some variations have incomplete exports (missing one format but others present)

## FAIL Criteria (block -- re-run Stage 7)
- [ ] No export directory created
- [ ] No Blender GLB export (primary format missing)
- [ ] Both Unity AND Unreal FBX exports failed (no game engine format available)
- [ ] No STL export and 3D printing was requested
- [ ] All export files are corrupt or <1KB
- [ ] ASSET-CARD.md does not exist
- [ ] Export Blender script crashed completely

## File Size Expectations
| Format | Minimum | Typical | Maximum |
|--------|---------|---------|---------|
| Blender GLB | 100KB | 2-10MB | 50MB |
| Unity FBX | 100KB | 3-15MB | 80MB |
| Unreal FBX | 100KB | 3-15MB | 80MB |
| Static GLB | 50KB | 1-5MB | 30MB |
| Print STL | 100KB | 5-20MB | 100MB |
| Artwork PNG | 50KB | 500KB-3MB | 10MB |

## Validation Method
```bash
python -c "
import json, os, sys
from pathlib import Path

state = json.load(open('pipelines/art-to-rig-ralph/output/pipeline-state.json'))
asset_id = state['batch_progress']['current_asset_id']
base = Path(f'pipelines/art-to-rig-ralph/output/final/{asset_id}')

if not base.exists():
    print(f'FAIL: directory {base} does not exist')
    sys.exit(1)

required_patterns = {
    'blender_glb': f'rigged/{asset_id}_v*_blender.glb',
    'unity_fbx': f'rigged/{asset_id}_v*_unity.fbx',
    'unreal_fbx': f'rigged/{asset_id}_v*_unreal.fbx',
    'static_glb': f'mesh/{asset_id}_v*_static.glb',
    'print_stl': f'mesh/{asset_id}_v*_print.stl',
    'front_art': f'artwork/{asset_id}_v*_front.png',
    'clean_art': f'artwork/{asset_id}_v*_clean.png',
}

results = {}
for name, pattern in required_patterns.items():
    found = list(base.glob(pattern))
    valid = [f for f in found if f.stat().st_size > 10000]
    results[name] = {'found': len(found), 'valid': len(valid)}
    status = 'OK' if len(valid) > 0 else 'MISSING'
    print(f'  {name}: {len(valid)} valid files - {status}')

# Check ASSET-CARD.md
card = base / 'ASSET-CARD.md'
if card.exists() and card.stat().st_size > 100:
    print(f'  asset_card: OK ({card.stat().st_size} bytes)')
else:
    print(f'  asset_card: MISSING or empty')

# Determine overall result
critical_missing = [k for k, v in results.items() if v['valid'] == 0]
if not critical_missing and card.exists():
    print('PASS')
elif len(critical_missing) <= 2:
    print(f'WARN: missing {critical_missing}')
else:
    print(f'FAIL: missing {critical_missing}')
    sys.exit(1)
"
```
