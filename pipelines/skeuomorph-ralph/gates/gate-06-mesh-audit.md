# Quality Gate 6: MESH-AUDIT

## PASS Criteria (ALL must pass)
- [ ] `output/validated/validated-model.glb` exists and is >10KB
- [ ] 0 non-manifold edges (mesh is watertight)
- [ ] 0 degenerate faces (no zero-area triangles)
- [ ] UV coverage is >90% (less than 10% of faces missing UV coordinates)
- [ ] Face count is within budget for the asset type:
  - character: 5,000 - 80,000
  - creature: 5,000 - 60,000
  - prop: 1,000 - 30,000
- [ ] `validate_glb.py` reports 0 errors on the validated mesh
- [ ] Materials and embedded textures are preserved in the validated GLB (material count matches Stage 5)
- [ ] `validation-report.json` exists with before/after metrics

## WARN Criteria (log but don't block)
- [ ] Mesh was decimated (quality reduction applied -- check visual quality in audit renders)
- [ ] UV coverage is between 90-95% (passing but slightly below ideal)
- [ ] Repair removed >10% of original geometry
- [ ] Multiple disconnected mesh components remain
- [ ] Face count is near the upper budget limit
- [ ] Caption validation returned a description that partially differs from expected (e.g., material descriptions match but pose differs)
- [ ] Bounding box changed by more than 10% from the textured model (repair distorted proportions)

## FAIL Criteria (block advancement -- re-run Stage 6)
- [ ] Validated GLB does not exist or is corrupt
- [ ] Non-manifold edges remain after repair
- [ ] Degenerate faces remain after dissolve
- [ ] Face count is 0 (repair destroyed the mesh)
- [ ] UV coverage is <60% (model will not texture correctly downstream)
- [ ] Materials were lost during repair/export (0 material slots in validated GLB)
- [ ] Caption validation returned "blank image" or "no recognizable object" for all 4 angles
- [ ] Face count dropped below minimum threshold (over-decimation)

## Validation Method

### File existence and size
```bash
echo "=== Validated GLB ==="
if [ -f "pipelines/skeuomorph-ralph/output/validated/validated-model.glb" ]; then
  size=$(stat --printf="%s" "pipelines/skeuomorph-ralph/output/validated/validated-model.glb")
  echo "validated-model.glb: ${size} bytes ($(( size / 1024 ))KB)"
else
  echo "FAIL: validated-model.glb missing"
fi
```

### Before/After comparison
```bash
echo "=== BEFORE (textured) ==="
python packages/mcp-server/scripts/validate_glb.py \
  pipelines/skeuomorph-ralph/output/textured/textured-model.glb

echo "=== AFTER (validated) ==="
python packages/mcp-server/scripts/validate_glb.py \
  pipelines/skeuomorph-ralph/output/validated/validated-model.glb
```

Key comparisons:
- Non-manifold edges: must go from N to 0
- Degenerate faces: must go from N to 0
- Face count: should not drop below 50% of original unless decimation was intentional and documented
- Bounding box: must remain within 15% of original dimensions

### UV coverage check via Blender
```bash
"C:/Program Files/Blender Foundation/Blender 5.0/blender.exe" \
  --background --python - <<'PYTHON' -- VALIDATED_GLB
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

    uv_layer = bm.loops.layers.uv.verify()
    uv_covered = 0
    for face in bm.faces:
        uvs = [loop[uv_layer].uv for loop in face.loops]
        if all(uv.length > 0 for uv in uvs):
            uv_covered += 1
    uv_pct = (uv_covered / len(bm.faces) * 100) if bm.faces else 0

    non_manifold = [e for e in bm.edges if not e.is_manifold]

    print(f"{obj.name}:")
    print(f"  UV coverage: {uv_pct:.1f}% ({'PASS' if uv_pct >= 90 else 'FAIL'})")
    print(f"  Non-manifold edges: {len(non_manifold)} ({'PASS' if len(non_manifold) == 0 else 'FAIL'})")
    print(f"  Face count: {len(bm.faces)}")

    bm.free()
PYTHON
```

### Material preservation check
```bash
"C:/Program Files/Blender Foundation/Blender 5.0/blender.exe" \
  --background --python - <<'PYTHON' -- VALIDATED_GLB
import bpy, sys

argv = sys.argv[sys.argv.index("--") + 1:]
glb_path = argv[0]

bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete()
bpy.ops.import_scene.gltf(filepath=glb_path)

for obj in bpy.data.objects:
    if obj.type != 'MESH':
        continue
    mat_names = [s.material.name for s in obj.material_slots if s.material]
    print(f"{obj.name}: {len(mat_names)} materials -- {mat_names}")
    if len(mat_names) == 0:
        print(f"FAIL: {obj.name} has no materials -- textures lost during repair")
PYTHON
```

### Caption check (advisory)

Read `output/validated/audit-captions.json` and compare each caption against the expected description from `pipeline-state.json`.`description`. Log mismatches as warnings. Only block on completely blank or unrecognizable results.

## Gate Result Output

Write to `output/gate-06-result.json`:
```json
{
  "stage": "6-mesh-audit",
  "result": "PASS|WARN|FAIL",
  "checks": [
    { "name": "file_exists", "passed": true, "detail": "validated-model.glb exists, 13.8MB" },
    { "name": "non_manifold", "passed": true, "detail": "0 non-manifold edges (was 4)" },
    { "name": "degenerate_faces", "passed": true, "detail": "0 degenerate faces (was 1)" },
    { "name": "uv_coverage", "passed": true, "detail": "94.2% UV coverage (above 90% threshold)" },
    { "name": "face_count", "passed": true, "detail": "42600 faces (within 5k-80k budget for character)" },
    { "name": "materials_preserved", "passed": true, "detail": "4 material slots preserved from Stage 5" },
    { "name": "caption_validation", "passed": true, "detail": "front: armored warrior (matches), back: armored figure (matches)" }
  ],
  "warnings": [
    "Face count dropped 12% due to degenerate face removal -- within acceptable range"
  ],
  "blocking_errors": [],
  "recommendation": "Geometry clean, materials preserved -- proceed to rigging"
}
```
