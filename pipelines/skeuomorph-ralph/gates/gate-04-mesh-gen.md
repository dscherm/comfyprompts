# Quality Gate 4: MESH-GEN

## PASS Criteria (ALL must pass)
- [ ] `output/meshes/raw-model.glb` exists and is >10KB
- [ ] GLB has valid glTF magic bytes (`glTF` = 0x46546C67 at bytes 0-3)
- [ ] Mesh contains at least 1 mesh primitive with >100 faces
- [ ] Total face count is between 5,000 and 200,000
- [ ] Model has a non-degenerate bounding box (no single axis dimension is zero)
- [ ] `output/meshes/generation-log.json` exists and is valid JSON

## WARN Criteria (log but don't block)
- [ ] Face count is below 5,000 (very low detail -- may look poor in-game; consider re-running at higher resolution)
- [ ] Face count exceeds 100,000 (will require decimation in Stage 6 -- adds time)
- [ ] `generation-log.json` indicates fallback level >= 2 (geometry-only -- Stage 5 will have to do full texturing)
- [ ] Model has multiple disconnected mesh components (may complicate rigging in Stage 7)
- [ ] Aspect ratio in any axis exceeds 5:1 (model may be misshapen)
- [ ] No material or texture data present (acceptable at fallback level >= 2, otherwise unexpected)
- [ ] Non-manifold edges detected (will be repaired in Stage 6)
- [ ] `generation_time_seconds` in log exceeds 300 seconds (pipeline may time out on retries)

## FAIL Criteria (block advancement)
- [ ] `output/meshes/raw-model.glb` does not exist
- [ ] GLB file is under 1KB (corrupt or empty output)
- [ ] Invalid glTF magic bytes (not a valid GLB file)
- [ ] Mesh has 0 vertices or 0 faces
- [ ] Model bounding box is entirely zero (degenerate flat plane)
- [ ] `generation-log.json` contains `"errors"` with non-empty content and `output/meshes/raw-model.glb` is missing (tool reported failure and no file was produced)

## Validation Method

### Run validate_glb.py
```bash
python packages/mcp-server/scripts/validate_glb.py \
  pipelines/skeuomorph-ralph/output/meshes/raw-model.glb
```

This outputs vertex count, face count, edge count, bounding box dimensions, non-manifold edge count, degenerate face count, material/texture presence, and mesh component count.

### Manual GLB header check (if validate_glb.py unavailable)
```bash
# Check glTF magic bytes -- should show: 6746 6c54 (little-endian "glTF")
xxd -l 4 pipelines/skeuomorph-ralph/output/meshes/raw-model.glb
```

### File size check
```bash
file="pipelines/skeuomorph-ralph/output/meshes/raw-model.glb"
if [ -f "$file" ]; then
  size=$(stat --printf="%s" "$file")
  echo "raw-model.glb: ${size} bytes"
  if [ "$size" -lt 10240 ]; then
    echo "FAIL: File under 10KB, likely corrupt or empty"
  fi
else
  echo "FAIL: raw-model.glb does not exist"
fi
```

### Generation log check
```python
import json
log = json.load(open("pipelines/skeuomorph-ralph/output/meshes/generation-log.json"))
print("Tool used:", log.get("tool_used"))
print("Fallback level:", log.get("fallback_level", 0))
print("Texture deferred:", log.get("texture_deferred", False))
errors = log.get("errors", [])
if errors:
    print(f"WARN: {len(errors)} error(s) recorded in generation log")
    for e in errors:
        print(" -", e)
else:
    print("PASS: no errors in generation log")
```

### Bounding box non-degeneracy check
```python
# After running validate_glb.py, verify bounding box dimensions
# All three axes (X, Y, Z) must be > 0.001 units
# If any axis is 0.0, the model is a flat plane or degenerate point cloud
```

## Gate Result Output

Write to `output/gate-04-result.json`:
```json
{
  "stage": "4-mesh-gen",
  "result": "PASS|WARN|FAIL",
  "checks": [
    { "name": "file_exists", "passed": true, "detail": "raw-model.glb exists, 9.1MB" },
    { "name": "valid_gltf", "passed": true, "detail": "Valid glTF magic bytes confirmed" },
    { "name": "face_count", "passed": true, "detail": "58200 faces (range: 5k-200k)" },
    { "name": "bounding_box", "passed": true, "detail": "1.1 x 1.9 x 0.6 units (non-degenerate)" },
    { "name": "generation_log", "passed": true, "detail": "generation-log.json valid, fallback_level=0" },
    { "name": "validate_glb", "passed": true, "detail": "validate_glb.py passed with 0 errors" }
  ],
  "warnings": ["12 non-manifold edges detected (will be repaired in Stage 6)"],
  "blocking_errors": [],
  "recommendation": "Proceed to PBR texturing"
}
```
