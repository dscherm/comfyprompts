# Quality Gate 3: MESH VALIDATION & REPAIR

## PASS Criteria (ALL must pass)
- [ ] `output/validated/cleaned-model.glb` exists and is >10KB
- [ ] 0 non-manifold edges (mesh is watertight)
- [ ] 0 degenerate faces (no zero-area triangles)
- [ ] Normals are consistent (all facing outward)
- [ ] Face count is within budget for the asset type:
  - character: 5,000 - 100,000
  - creature: 5,000 - 80,000
  - prop: 1,000 - 50,000
  - vehicle: 2,000 - 60,000
- [ ] `validate_glb.py` reports 0 errors on the cleaned mesh

## WARN Criteria (log but don't block)
- [ ] Mesh was decimated (quality reduction applied -- verify visual quality if possible)
- [ ] Multiple mesh components remain (may complicate rigging but not necessarily a defect)
- [ ] Face count is near the upper limit of the budget (close to max)
- [ ] Repair removed >10% of original geometry (aggressive cleanup may have lost detail)
- [ ] Model has no UV coordinates (textures will not map correctly -- may need re-UV)

## FAIL Criteria (block advancement -- re-run Stage 3)
- [ ] Cleaned GLB file does not exist or is corrupt
- [ ] Non-manifold edges remain after repair (mesh still has holes)
- [ ] Degenerate faces remain after dissolve
- [ ] Normals are still inconsistent after recalculation
- [ ] Face count is 0 (repair destroyed the mesh)
- [ ] Face count dropped below minimum threshold (over-decimation)
- [ ] Bounding box changed by more than 50% (repair significantly distorted the model)

## Validation Method

### Run validate_glb.py on the cleaned mesh
```bash
python packages/mcp-server/scripts/validate_glb.py \
  pipelines/asset-forge-ralph/output/validated/cleaned-model.glb
```

### Compare before/after metrics
```bash
echo "=== BEFORE (raw) ==="
python packages/mcp-server/scripts/validate_glb.py \
  pipelines/asset-forge-ralph/output/meshes/raw-model.glb

echo "=== AFTER (cleaned) ==="
python packages/mcp-server/scripts/validate_glb.py \
  pipelines/asset-forge-ralph/output/validated/cleaned-model.glb
```

Key comparisons:
- Non-manifold edges: must go from N to 0
- Degenerate faces: must go from N to 0
- Face count: should not drop below 50% of original (unless decimation was intentional)
- Bounding box: should remain within 10% of original dimensions

### Blender headless manifold check (supplementary)
```bash
"C:/Program Files/Blender Foundation/Blender 5.0/blender.exe" \
  --background --python - <<'PYTHON' -- CLEANED_GLB
import bpy, bmesh, sys

argv = sys.argv[sys.argv.index("--") + 1:]
glb_path = argv[0]

bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete()
bpy.ops.import_scene.gltf(filepath=glb_path)

for obj in bpy.data.objects:
    if obj.type != 'MESH':
        continue
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    non_manifold = [e for e in bm.edges if not e.is_manifold]
    degenerate = [f for f in bm.faces if f.calc_area() < 0.00001]
    print(f"{obj.name}: {len(non_manifold)} non-manifold edges, {len(degenerate)} degenerate faces")
    bm.free()
PYTHON
```

## Gate Result Output

Write to `output/gate-03-result.json`:
```json
{
  "stage": "3-validation",
  "result": "PASS|WARN|FAIL",
  "checks": [
    { "name": "file_exists", "passed": true, "detail": "cleaned-model.glb exists, 6.1MB" },
    { "name": "non_manifold", "passed": true, "detail": "0 non-manifold edges (was 7)" },
    { "name": "degenerate_faces", "passed": true, "detail": "0 degenerate faces (was 3)" },
    { "name": "normals_consistent", "passed": true, "detail": "All normals facing outward" },
    { "name": "face_count", "passed": true, "detail": "48200 faces (within 5k-100k budget)" },
    { "name": "bounding_box_stable", "passed": true, "detail": "Dimensions within 2% of original" }
  ],
  "warnings": [],
  "blocking_errors": [],
  "recommendation": "Mesh is clean -- proceed to auto-rigging"
}
```
