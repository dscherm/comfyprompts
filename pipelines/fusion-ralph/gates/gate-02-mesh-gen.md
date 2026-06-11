# Quality Gate 2: MESH GENERATION

## PASS Criteria (ALL must pass)
- [ ] `output/meshes/raw-model.glb` exists and is >10KB
- [ ] GLB has valid header (magic bytes: 0x46546C67 = "glTF")
- [ ] At least 1 mesh with >100 faces
- [ ] Model has non-zero bounding box (not a flat plane or degenerate shape)

## WARN Criteria (log but don't block)
- [ ] Face count <5,000 (very low detail, may look blocky when printed)
- [ ] Face count >150,000 (will slow down downstream processing)
- [ ] Model has multiple disconnected mesh components (may need manual review)
- [ ] Aspect ratio is extreme (>5:1 in any axis — may be misshapen)

## FAIL Criteria (block advancement)
- [ ] No GLB file generated
- [ ] GLB file corrupt (invalid header)
- [ ] Mesh has 0 vertices or 0 faces
- [ ] Model is essentially flat (one dimension <1% of the others)
- [ ] Generation tool returned an error

## Validation Method
Run `validate_glb.py` and check the report:
```bash
python packages/mcp-server/scripts/validate_glb.py pipelines/fusion-ralph/output/meshes/raw-model.glb
```
