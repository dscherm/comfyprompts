# Quality Gate 2: MESH GENERATION

## PASS Criteria (ALL must pass)
- [ ] `output/meshes/raw-model.glb` exists and is >10KB
- [ ] GLB has valid glTF header (magic bytes: 0x46546C67 = "glTF")
- [ ] At least 1 mesh with >100 faces
- [ ] Face count is between 5,000 and 200,000
- [ ] Model has non-zero bounding box (not a flat plane or degenerate shape)
- [ ] `validate_glb.py` runs without errors

## WARN Criteria (log but don't block)
- [ ] Face count <5,000 (very low detail -- may look poor in-game)
- [ ] Face count >100,000 (will need decimation in Stage 3, adds processing time)
- [ ] Model has multiple disconnected mesh components (may complicate rigging)
- [ ] Aspect ratio is extreme (>5:1 in any axis -- may be misshapen)
- [ ] No texture/material data (geometry only -- acceptable but limits visual quality)
- [ ] Non-manifold edges detected (will be repaired in Stage 3)

## FAIL Criteria (block advancement)
- [ ] No GLB file generated
- [ ] GLB file is corrupt (invalid header, cannot be parsed)
- [ ] Mesh has 0 vertices or 0 faces
- [ ] Model is essentially flat (one dimension <1% of the others)
- [ ] All mesh bounding box dimensions are zero
- [ ] Generation tool returned an explicit error

## Validation Method

### Run validate_glb.py
```bash
python packages/mcp-server/scripts/validate_glb.py \
  pipelines/asset-forge-ralph/output/meshes/raw-model.glb
```

This outputs:
- Vertex count, face count, edge count
- Bounding box dimensions
- Non-manifold edge count
- Degenerate face count
- Material/texture presence
- Mesh component count

### Manual header check (if validate_glb.py unavailable)
```bash
# Check glTF magic bytes
xxd -l 4 pipelines/asset-forge-ralph/output/meshes/raw-model.glb
# Should show: 6746 6c54 (glTF)
```

### File size check
```bash
size=$(stat --printf="%s" "pipelines/asset-forge-ralph/output/meshes/raw-model.glb")
echo "raw-model.glb: ${size} bytes"
```

## Gate Result Output

Write to `output/gate-02-result.json`:
```json
{
  "stage": "2-mesh-gen",
  "result": "PASS|WARN|FAIL",
  "checks": [
    { "name": "file_exists", "passed": true, "detail": "raw-model.glb exists, 8.3MB" },
    { "name": "valid_gltf", "passed": true, "detail": "Valid glTF header" },
    { "name": "face_count", "passed": true, "detail": "52400 faces (range: 5k-200k)" },
    { "name": "bounding_box", "passed": true, "detail": "1.2 x 1.8 x 0.5 units (non-degenerate)" },
    { "name": "validate_glb", "passed": true, "detail": "validate_glb.py passed with 0 errors" }
  ],
  "warnings": ["7 non-manifold edges (will be repaired in Stage 3)"],
  "blocking_errors": [],
  "recommendation": "Proceed to mesh validation and repair"
}
```
