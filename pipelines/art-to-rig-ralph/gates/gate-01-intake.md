# Quality Gate 1: INTAKE

## PASS Criteria (ALL must pass)
- [ ] `output/intake/intake-report.json` exists and is valid JSON
- [ ] At least 1 asset defined in the `assets` array
- [ ] Each asset has: `id`, `name`, `description`, `body_type`, `skeleton_type`
- [ ] `style_profile` has a `primary_style` that maps to a known style (cartoon, comic, dark_fantasy, high_fantasy, hard_scifi, cyberpunk, realistic, pencil, oil_painting, watercolor, digital_painting, pixel_art, art_nouveau, art_deco, custom)
- [ ] `style_profile` has `prompt_suffix` and `negative_prompt` (for prompt engineering)
- [ ] `background_approach` is one of: `generate_transparent`, `remove_after`
- [ ] `total_assets` > 0 and matches length of `assets` array
- [ ] All `body_type` values map to valid `skeleton_type` entries
- [ ] `pipeline-state.json` has been updated with batch_progress and style_profile

## WARN Criteria (log but don't block)
- [ ] No reference images provided (`reference_images` is empty) -- relying on text description only
- [ ] Asset description is shorter than 20 characters (may produce generic results)
- [ ] `custom` body type used without detailed skeleton description in notes
- [ ] Variations count > 5 for any single asset (will use many iterations)
- [ ] Total generations > 20 (pipeline may approach iteration limit)

## FAIL Criteria (block advancement)
- [ ] `intake-report.json` does not exist or is invalid JSON
- [ ] No assets defined (empty `assets` array)
- [ ] No style profile determined (missing `primary_style`)
- [ ] `background_approach` not set or invalid value
- [ ] Asset has `body_type` that cannot be mapped to any skeleton type
- [ ] PRD is empty or unreadable

## Validation Method
```bash
# Check file exists and is valid JSON
python -c "
import json, sys
try:
    with open('pipelines/art-to-rig-ralph/output/intake/intake-report.json') as f:
        data = json.load(f)
    assert len(data.get('assets', [])) > 0, 'No assets defined'
    assert data.get('style_profile', {}).get('primary_style'), 'No style'
    assert data.get('background_approach') in ('generate_transparent', 'remove_after'), 'Bad bg approach'
    for asset in data['assets']:
        assert all(k in asset for k in ('id', 'name', 'body_type', 'skeleton_type')), f'Missing fields in {asset.get(\"id\", \"unknown\")}'
    print(f'PASS: {len(data[\"assets\"])} assets, style: {data[\"style_profile\"][\"primary_style\"]}')
except Exception as e:
    print(f'FAIL: {e}')
    sys.exit(1)
"
```
