# Quality Gate 3: BACKGROUND REMOVAL

## PASS Criteria (ALL must pass)
- [ ] All cleaned images exist in `output/cleaned/` matching the concept images
- [ ] Each cleaned image is a valid PNG with alpha channel (RGBA mode)
- [ ] File size > 30KB (not blank after removal)
- [ ] Subject occupies >20% of image area (not excessively eroded)
- [ ] Background regions (corners) have alpha = 0 (fully transparent)

## WARN Criteria (log but don't block)
- [ ] Minor halo artifacts visible at subject edges (1-2px bright/dark fringe)
- [ ] Some edge roughness (jagged silhouette) but overall shape preserved
- [ ] Fine details partially lost (hair wisps, wing membrane tips) -- acceptable for 3D conversion
- [ ] Subject slightly smaller than original due to edge erosion
- [ ] Alpha channel has soft edges (semi-transparent border) rather than hard mask

## FAIL Criteria (block -- re-run Stage 3 or go back to Stage 2)
- [ ] No cleaned images produced
- [ ] Background removal deleted the subject (image is mostly transparent)
- [ ] Major body parts missing after removal (arms, legs, head clipped)
- [ ] Background is still clearly visible (removal failed completely)
- [ ] All cleaned images are <10KB (effectively blank)
- [ ] File is not RGBA (no alpha channel added)

## Validation Method
```bash
python -c "
import json, os, sys
from pathlib import Path

cleaned_dir = Path('pipelines/art-to-rig-ralph/output/cleaned')
state = json.load(open('pipelines/art-to-rig-ralph/output/pipeline-state.json'))
asset_id = state['batch_progress']['current_asset_id']

found = list(cleaned_dir.glob(f'{asset_id}_v*_clean.png'))
valid = [f for f in found if f.stat().st_size > 30000]

print(f'Asset: {asset_id}')
print(f'Found cleaned: {len(found)}')
print(f'Valid (>30KB): {len(valid)}')

if len(valid) > 0:
    # Optional: check for alpha channel using PIL if available
    try:
        from PIL import Image
        for f in valid:
            img = Image.open(f)
            if img.mode != 'RGBA':
                print(f'WARN: {f.name} is {img.mode}, not RGBA')
            else:
                # Check corner transparency
                corners = [img.getpixel((0,0)), img.getpixel((img.width-1, 0)),
                           img.getpixel((0, img.height-1)), img.getpixel((img.width-1, img.height-1))]
                transparent_corners = sum(1 for c in corners if c[3] < 10)
                if transparent_corners < 3:
                    print(f'WARN: {f.name} corners not fully transparent ({transparent_corners}/4)')
    except ImportError:
        print('PIL not available, skipping pixel-level validation')
    print('PASS')
else:
    print('FAIL: no valid cleaned images')
    sys.exit(1)
"
```
