# Quality Gate 4: 3D CONVERT

## PASS Criteria (ALL must pass)
- [ ] `output/3d/character.glb` exists and is >100KB
- [ ] GLB file is valid (parseable, correct header)
- [ ] Mesh is manifold (no non-manifold edges, no open boundaries)
- [ ] Face count is within range: 10,000 - 200,000
- [ ] Bounding box dimensions are reasonable for a humanoid (height 1.0 - 3.0 meters)
- [ ] Mesh has no degenerate faces (zero-area triangles)

## WARN Criteria (log but don't block)
- [ ] Face count above 100,000 (may need decimation for game use but rigging can proceed)
- [ ] No texture/material data in the GLB (rigging still works, visual quality reduced)
- [ ] Pose is not clearly A-pose or T-pose (rigging may produce lower quality)
- [ ] Minor non-manifold issues (1-5 edges -- often fixable during rigging)
- [ ] Missing validation-report.json
- [ ] Bounding box proportions unusual (very wide or very thin)

## FAIL Criteria (block advancement)
- [ ] No GLB file generated
- [ ] GLB file is corrupt or unparseable
- [ ] Mesh has zero faces or zero vertices
- [ ] Severe non-manifold geometry (>50 non-manifold edges)
- [ ] Mesh is not recognizable as a humanoid character
- [ ] Bounding box is degenerate (zero volume, or absurdly large >100m)
- [ ] Face count below 1,000 (insufficient geometry for rigging)

## Validation Method

### GLB validation script
```bash
python packages/mcp-server/scripts/validate_glb.py \
  pipelines/character-ralph/output/3d/character.glb
```

The script checks:
- File format validity
- Vertex and face counts
- Non-manifold edge detection
- Bounding box dimensions
- Material/texture presence

### Blender validation (if validate_glb.py unavailable)
```bash
"C:/Program Files/Blender Foundation/Blender 5.0/blender.exe" \
  --background --python - <<'PYTHON' -- INPUT_GLB
import bpy, sys, json

argv = sys.argv[sys.argv.index("--") + 1:]
input_glb = argv[0]

bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete()
bpy.ops.import_scene.gltf(filepath=input_glb)

report = {"valid": True, "meshes": []}
for obj in bpy.data.objects:
    if obj.type == 'MESH':
        mesh = obj.data
        report["meshes"].append({
            "name": obj.name,
            "vertices": len(mesh.vertices),
            "faces": len(mesh.polygons),
            "dimensions": list(obj.dimensions)
        })

print(json.dumps(report, indent=2))
PYTHON
```

### Dimension check
For a humanoid character:
- Height (Y or Z depending on up-axis): 1.5 - 2.5 meters
- Width (X): 0.3 - 1.5 meters
- Depth (Z or Y): 0.2 - 1.0 meters

### Gate Result Format
Write to `output/gate-04-result.json`:
```json
{
  "stage": "4-3d-convert",
  "result": "PASS|WARN|FAIL",
  "checks": [
    { "name": "file_exists", "passed": true, "detail": "character.glb exists, 4.2MB" },
    { "name": "glb_valid", "passed": true, "detail": "Valid GLB header, parseable" },
    { "name": "manifold", "passed": true, "detail": "0 non-manifold edges" },
    { "name": "face_count", "passed": true, "detail": "48320 faces (range: 10k-200k)" },
    { "name": "dimensions", "passed": true, "detail": "1.78m height, reasonable humanoid proportions" },
    { "name": "textures", "passed": true, "detail": "1 material with albedo texture" }
  ],
  "warnings": [],
  "blocking_errors": [],
  "recommendation": "Proceed to rigging"
}
```
