# Quality Gate 5: HARD-SURFACE

## PASS Criteria (ALL must pass)
- [ ] Attachment report exists at `output/attached/{asset-id}_attachment-report.json`
- [ ] All detected hard-surface items have been processed (attached or explicitly skipped)
- [ ] Each attached item has a valid `attachment_bone` that exists in the skeleton
- [ ] No items left unprocessed without explanation

## WARN Criteria (log but don't block)
- [ ] Minor clipping detected in one or more poses
- [ ] Item attached to non-ideal bone (e.g., chest instead of spine.002)
- [ ] No hard-surface items detected (stage skipped -- this is normal)

## FAIL Criteria (block advancement)
- [ ] Attachment report missing
- [ ] Hard-surface item attached to non-existent bone
- [ ] Items detected in Stage 2 but not processed and not explained
- [ ] Attachment causes mesh corruption

## Validation Method
```bash
python -c "
import json, sys
asset_id = 'ASSET_ID'
try:
    with open(f'pipelines/autorig-ralph/output/attached/{asset_id}_attachment-report.json') as f:
        data = json.load(f)
    total = data.get('total_items_attached', 0)
    skipped = len(data.get('skipped_items', []))
    print(f'PASS: {total} items attached, {skipped} skipped')
except Exception as e:
    print(f'FAIL: {e}')
    sys.exit(1)
"
```
