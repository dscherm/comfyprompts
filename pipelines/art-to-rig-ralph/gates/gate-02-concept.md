# Quality Gate 2: CONCEPT ART

## PASS Criteria (ALL must pass)
- [ ] At least 1 front view image exists per variation in `output/concept/`
- [ ] Each image is a valid PNG, >50KB (not blank or corrupt)
- [ ] Image filenames follow convention: `{asset-id}_v{N}_front.png`
- [ ] Number of images matches `variations_requested` for the current asset
- [ ] Images are at least 512x512 pixels (sufficient for 3D generation)

## WARN Criteria (log but don't block)
- [ ] Missing side view for complex body types (quadruped_winged, serpentine, insect)
- [ ] Images have visible background despite `generate_transparent` approach
- [ ] Some variations look visually identical (same seed or minimal variation)
- [ ] Image resolution below 1024x1024 (higher resolution improves 3D quality)
- [ ] Subject appears cropped at edges (head/feet/wings cut off)
- [ ] Subject is very small in frame (<30% of image area)

## FAIL Criteria (block -- re-run Stage 2)
- [ ] No images generated at all for the current asset
- [ ] All images are blank, corrupt, or <10KB
- [ ] Subject is completely wrong (e.g., landscape instead of character)
- [ ] Style completely mismatches the intake style profile
- [ ] More than 50% of requested variations failed to generate
- [ ] All images show the subject in a pose that will fail rigging (e.g., running, jumping, fighting)

## Validation Method
```bash
# Check concept images for current asset
python -c "
import json, os, sys
from pathlib import Path

concept_dir = Path('pipelines/art-to-rig-ralph/output/concept')
state = json.load(open('pipelines/art-to-rig-ralph/output/pipeline-state.json'))
intake = json.load(open('pipelines/art-to-rig-ralph/output/intake/intake-report.json'))
asset_id = state['batch_progress']['current_asset_id']
asset = next(a for a in intake['assets'] if a['id'] == asset_id)
expected = asset.get('variations_requested', 1)

found = list(concept_dir.glob(f'{asset_id}_v*_front.png'))
valid = [f for f in found if f.stat().st_size > 50000]

print(f'Asset: {asset_id}')
print(f'Expected variations: {expected}')
print(f'Found images: {len(found)}')
print(f'Valid images (>50KB): {len(valid)}')

if len(valid) >= expected:
    print('PASS')
elif len(valid) > 0:
    print(f'WARN: only {len(valid)}/{expected} valid images')
else:
    print('FAIL: no valid images')
    sys.exit(1)
"
```
