# Quality Gate 4: MESH GENERATION

## PASS Criteria (ALL must pass)
- [ ] GLB file exists for each variation of the current asset in `output/meshes/`
- [ ] Each GLB is >100KB (not empty or corrupt)
- [ ] Each GLB has valid glTF header (starts with correct magic bytes or valid JSON)
- [ ] Face count is between 5,000 and 200,000 for each mesh
- [ ] Bounding box is non-degenerate (no axis has zero length)
- [ ] Generation log JSON exists for each variation

## WARN Criteria (log but don't block)
- [ ] Low face count (<10,000) -- may lack detail for rigging, but still processable
- [ ] High face count (>100,000) -- will need aggressive decimation in Stage 5
- [ ] Fallback tool was used instead of primary (Hunyuan3D v2.5)
- [ ] Floating geometry visible (disconnected mesh islands) -- fixable in Stage 5
- [ ] Mesh has obvious topology issues (long thin triangles, uneven distribution)
- [ ] Some variations used different generation tools (quality may be inconsistent)

## FAIL Criteria (block -- re-run Stage 4 or go back to Stage 3)
- [ ] No GLB files generated for the current asset
- [ ] All GLB files are corrupt or <10KB
- [ ] All meshes have 0 faces (empty geometry)
- [ ] All generation tools failed (entire fallback chain exhausted)
- [ ] Mesh is inside-out (all normals inverted -- visible as completely black in viewer)
- [ ] Generated mesh bears no resemblance to the source image (wrong subject)

## Validation Method
```bash
# Validate GLB files
python -c "
import json, os, sys
from pathlib import Path

mesh_dir = Path('pipelines/art-to-rig-ralph/output/meshes')
state = json.load(open('pipelines/art-to-rig-ralph/output/pipeline-state.json'))
asset_id = state['batch_progress']['current_asset_id']

glbs = list(mesh_dir.glob(f'{asset_id}_v*_raw.glb'))
logs = list(mesh_dir.glob(f'{asset_id}_v*_gen-log.json'))

print(f'Asset: {asset_id}')
print(f'GLB files: {len(glbs)}')
print(f'Log files: {len(logs)}')

valid = 0
for glb in glbs:
    size = glb.stat().st_size
    if size > 100000:
        valid += 1
        print(f'  {glb.name}: {size/1024:.0f}KB - OK')
    else:
        print(f'  {glb.name}: {size/1024:.0f}KB - TOO SMALL')

for log_path in logs:
    log = json.load(open(log_path))
    faces = log.get('face_count', 0)
    tool = log.get('tool_used', 'unknown')
    print(f'  {log_path.name}: {faces} faces, tool: {tool}')
    if faces < 5000:
        print(f'    WARN: very low face count')
    elif faces > 200000:
        print(f'    WARN: very high face count')

if valid > 0:
    print('PASS')
else:
    print('FAIL: no valid GLB files')
    sys.exit(1)
"
```

Also run the GLB validator if available:
```bash
python packages/mcp-server/scripts/validate_glb.py pipelines/art-to-rig-ralph/output/meshes/{asset-id}_v1_raw.glb
```
