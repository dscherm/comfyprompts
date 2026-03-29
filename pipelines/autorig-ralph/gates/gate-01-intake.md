# Quality Gate 1: INTAKE

## PASS Criteria (ALL must pass)
- [ ] `output/intake/intake-report.json` exists and is valid JSON
- [ ] At least 1 asset defined in the `assets` array
- [ ] Each asset has: `id`, `name`, `mesh_path`, `body_type`, `skeleton_type`
- [ ] `body_type` is one of: humanoid, quadruped, creature, mech, serpentine
- [ ] `rigging_strategy` has `primary_tool` and `fallback_chain`
- [ ] `tool_availability` section present with at least one tool available
- [ ] `pipeline-state.json` initialized with correct asset count
- [ ] Input mesh file(s) exist at specified path(s)

## WARN Criteria (log but don't block)
- [ ] UniRig not available (fallback chain will be used)
- [ ] blender-mcp not available (headless fallback only)
- [ ] Mesh has >100k vertices (may be slow to process)
- [ ] Body type detected as "creature" (custom skeleton, less predictable)
- [ ] Mesh has existing armature (will be replaced)

## FAIL Criteria (block advancement)
- [ ] `intake-report.json` does not exist or is invalid JSON
- [ ] No assets defined
- [ ] Input mesh file does not exist
- [ ] No rigging tools available (all unavailable)
- [ ] Mesh format unsupported

## Validation Method
```bash
python -c "
import json, sys, os
try:
    with open('pipelines/autorig-ralph/output/intake/intake-report.json') as f:
        data = json.load(f)
    assert len(data.get('assets', [])) > 0, 'No assets'
    for a in data['assets']:
        assert all(k in a for k in ('id','name','mesh_path','body_type','skeleton_type')), f'Missing fields: {a.get(\"id\")}'
        assert a['body_type'] in ('humanoid','quadruped','creature','mech','serpentine'), f'Bad body_type: {a[\"body_type\"]}'
        assert os.path.exists(a['mesh_path']), f'Mesh not found: {a[\"mesh_path\"]}'
    strategy = data.get('rigging_strategy', {})
    assert strategy.get('primary_tool'), 'No primary tool'
    tools = data.get('tool_availability', {})
    assert any(tools.values()), 'No tools available'
    print(f'PASS: {len(data[\"assets\"])} assets, primary: {strategy[\"primary_tool\"]}')
except Exception as e:
    print(f'FAIL: {e}')
    sys.exit(1)
"
```
