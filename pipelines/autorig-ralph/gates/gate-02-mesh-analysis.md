# Quality Gate 2: MESH-ANALYSIS

## PASS Criteria (ALL must pass)
- [ ] `output/analysis/{asset-id}_topology.json` exists with valid mesh stats
- [ ] `output/analysis/{asset-id}_landmarks.json` exists (humanoid/quadruped) or skipped (mech)
- [ ] `output/analysis/{asset-id}_regions.json` exists with body/hard-surface classification
- [ ] `output/analysis/{asset-id}_preprocessed.glb` exists (cleaned mesh for skeleton prediction)
- [ ] Zero isolated vertices in preprocessed mesh
- [ ] All normals consistent (no flipped faces)
- [ ] Mesh is manifold or non-manifold edges < 1% of total

## WARN Criteria (log but don't block)
- [ ] Non-manifold edges > 0 but < 1%
- [ ] Face count > 80k (may slow skeleton prediction)
- [ ] Many loose parts detected (>10 separate mesh islands)
- [ ] No hard-surface items detected (Stage 5 will skip)
- [ ] Landmark detection confidence low for some joints

## FAIL Criteria (block advancement)
- [ ] Topology report missing
- [ ] Preprocessed mesh missing or empty (0 vertices)
- [ ] Mesh has >50% non-manifold edges (severely broken)
- [ ] Mesh has 0 faces after cleanup

## Validation Method
```bash
python -c "
import json, sys, os
asset_id = 'ASSET_ID'  # replace at runtime
try:
    topo_path = f'pipelines/autorig-ralph/output/analysis/{asset_id}_topology.json'
    with open(topo_path) as f:
        topo = json.load(f)
    assert topo.get('vertices', 0) > 0, 'Zero vertices'
    assert topo.get('faces', 0) > 0, 'Zero faces'
    prep_path = f'pipelines/autorig-ralph/output/analysis/{asset_id}_preprocessed.glb'
    assert os.path.exists(prep_path), 'Preprocessed mesh missing'
    print(f'PASS: {topo[\"vertices\"]} verts, {topo[\"faces\"]} faces')
except Exception as e:
    print(f'FAIL: {e}')
    sys.exit(1)
"
```
