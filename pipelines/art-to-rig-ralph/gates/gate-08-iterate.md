# Quality Gate 8: ITERATE

## PASS Criteria -- Batch Loop (advance to next asset)
When assets remain unprocessed:
- [ ] Current asset is fully exported (Gate 7 passed)
- [ ] Intake report updated: current asset status set to `"complete"`
- [ ] Pipeline state updated: `current_asset_id` set to next pending asset
- [ ] Pipeline state updated: stages 2-7 reset to `"pending"` for next asset
- [ ] Iteration count has not exceeded max_iterations

## PASS Criteria -- Batch Complete (pipeline done)
When all assets are processed:
- [ ] All assets in intake report have status `"complete"`
- [ ] `output/final/BATCH-MANIFEST.md` exists and contains all assets
- [ ] Every asset has a complete `output/final/{asset-id}/` directory
- [ ] Variation comparison report exists (if any asset had >1 variation)
- [ ] `batch_progress.completed_assets` equals `batch_progress.total_assets`

## WARN Criteria (log but don't block)
- [ ] Some variations flagged as quality outliers (>20 points below best)
- [ ] Style drift detected across batch (early assets look different from late assets)
- [ ] Some assets used fallback generation tools while others used primary
- [ ] Iteration count >35 (approaching limit)
- [ ] One asset required more than 5 iterations of any single stage (difficult subject)

## FAIL Criteria (block -- investigate)
- [ ] Less than 50% of assets completed and iteration count >40 (will not finish)
- [ ] Current asset has failed the same stage 3+ times consecutively (stuck loop)
- [ ] BATCH-MANIFEST.md is missing when all assets should be complete
- [ ] Pipeline state is inconsistent (completed_assets count does not match actual)
- [ ] Iteration limit reached (50) with assets still pending

## Validation Method
```bash
python -c "
import json, sys
from pathlib import Path

state = json.load(open('pipelines/art-to-rig-ralph/output/pipeline-state.json'))
intake = json.load(open('pipelines/art-to-rig-ralph/output/intake/intake-report.json'))

total = len(intake['assets'])
completed = sum(1 for a in intake['assets'] if a.get('status') == 'complete')
iteration = state.get('iteration', 0)
max_iter = state.get('max_iterations', 50)

print(f'Assets: {completed}/{total} complete')
print(f'Iterations: {iteration}/{max_iter}')

if completed < total:
    remaining = total - completed
    remaining_assets = [a['id'] for a in intake['assets'] if a.get('status') != 'complete']
    print(f'Remaining: {remaining_assets}')

    if iteration > 40 and completed < total * 0.5:
        print('FAIL: approaching iteration limit with <50% complete')
        sys.exit(1)
    else:
        print(f'PASS (loop): advancing to next asset')
else:
    manifest = Path('pipelines/art-to-rig-ralph/output/final/BATCH-MANIFEST.md')
    if manifest.exists():
        print('PASS (complete): all assets done, manifest exists')
    else:
        print('WARN: all assets done but BATCH-MANIFEST.md missing')

    # Check all final directories exist
    for asset in intake['assets']:
        asset_dir = Path(f'pipelines/art-to-rig-ralph/output/final/{asset[\"id\"]}')
        if asset_dir.exists():
            print(f'  {asset[\"id\"]}: directory exists')
        else:
            print(f'  {asset[\"id\"]}: MISSING directory')
"
```
