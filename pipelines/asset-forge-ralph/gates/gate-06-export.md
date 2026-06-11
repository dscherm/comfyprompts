# Quality Gate 6: EXPORT (Final Gate)

## PASS Criteria (ALL must pass)
- [ ] `output/final/model.glb` exists and is >10KB
- [ ] `output/final/model.fbx` exists and is >10KB
- [ ] `output/final/model.stl` exists and is >1KB
- [ ] GLB has valid glTF header (magic bytes: 0x46546C67)
- [ ] FBX has valid header (starts with "Kaydara FBX Binary" or valid ASCII FBX header)
- [ ] STL has valid binary header (80 bytes + 4-byte triangle count)
- [ ] STL dimensions are in millimeters (typical range 10-500mm for character models, not 0.01-0.5 which indicates meter units)
- [ ] GLB preserves animations from Stage 5 (if asset is animated)
- [ ] `ASSET-MANIFEST.md` exists with complete documentation
- [ ] File sizes are reasonable (GLB and FBX within 2x of each other, STL smaller since geometry-only)

## WARN Criteria (log but don't block)
- [ ] Total export package >200MB (very large asset)
- [ ] FBX file is >3x the size of GLB (may have duplicate data or uncompressed textures)
- [ ] STL file is >50MB (very high polygon count for printing)
- [ ] Individual animation clip GLBs are missing (combined GLB exists but per-clip files do not)
- [ ] FBX animation track count does not match GLB animation count (some clips lost in conversion)

## FAIL Criteria (block -- re-run Stage 6)
- [ ] Any required export file is missing (GLB, FBX, or STL)
- [ ] Any export file is corrupt (invalid header, zero bytes)
- [ ] STL is in meter units (dimensions <1.0 in all axes -- forgot mm conversion)
- [ ] GLB lost all animations during final copy (animated source but static export)
- [ ] FBX conversion failed entirely (Blender export error)
- [ ] `ASSET-MANIFEST.md` is missing or empty
- [ ] Mesh geometry differs significantly between GLB and FBX exports (conversion error)

## Validation Method

### File existence and size check
```bash
echo "=== Export files ==="
for f in model.glb model.fbx model.stl; do
  path="pipelines/asset-forge-ralph/output/final/$f"
  if [ -f "$path" ]; then
    size=$(stat --printf="%s" "$path")
    echo "$f: ${size} bytes ($(( size / 1024 ))KB)"
  else
    echo "FAIL: $f missing"
  fi
done

echo "=== Manifest ==="
if [ -f "pipelines/asset-forge-ralph/output/final/ASSET-MANIFEST.md" ]; then
  lines=$(wc -l < "pipelines/asset-forge-ralph/output/final/ASSET-MANIFEST.md")
  echo "ASSET-MANIFEST.md: ${lines} lines"
else
  echo "FAIL: ASSET-MANIFEST.md missing"
fi
```

### GLB header validation
```bash
xxd -l 4 pipelines/asset-forge-ralph/output/final/model.glb
# Expected: 6746 6c54 (glTF)
```

### STL unit validation (critical)
```bash
"C:/Program Files/Blender Foundation/Blender 5.0/blender.exe" \
  --background --python - <<'PYTHON' -- STL_PATH
import bpy, sys

argv = sys.argv[sys.argv.index("--") + 1:]
stl_path = argv[0]

bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete()

bpy.ops.wm.stl_import(filepath=stl_path)

for obj in bpy.data.objects:
    if obj.type == 'MESH':
        dims = obj.dimensions
        print(f"STL dimensions: {dims.x:.2f} x {dims.y:.2f} x {dims.z:.2f}")
        max_dim = max(dims)
        if max_dim < 1.0:
            print("FAIL: Dimensions suggest meter units (max dim < 1.0)")
            print("Expected millimeters: typical character model is 50-300mm tall")
        elif max_dim > 5000:
            print("WARN: Very large dimensions (>5m in mm) -- verify scale is correct")
        else:
            print(f"PASS: Dimensions appear to be in millimeters (max: {max_dim:.1f}mm)")
PYTHON
```

### FBX animation preservation check
```bash
"C:/Program Files/Blender Foundation/Blender 5.0/blender.exe" \
  --background --python - <<'PYTHON' -- FBX_PATH
import bpy, sys

argv = sys.argv[sys.argv.index("--") + 1:]
fbx_path = argv[0]

bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete()

bpy.ops.import_scene.fbx(filepath=fbx_path)

armatures = [obj for obj in bpy.data.objects if obj.type == 'ARMATURE']
actions = bpy.data.actions

print(f"Armatures: {len(armatures)}")
print(f"Actions (animation clips): {len(actions)}")
for action in actions:
    frames = int(action.frame_range[1] - action.frame_range[0])
    print(f"  {action.name}: {frames} frames")

if not actions and armatures:
    print("WARN: FBX has armature but no animation clips")
PYTHON
```

## Pipeline Completion

When this gate passes, ALL 6 gates have passed. The pipeline is complete.

1. Verify all 6 stages in `pipeline-state.json` have `gate_passed: true`
2. Verify `ASSET-MANIFEST.md` has all sections filled in
3. Output: `<promise>ASSET FORGE COMPLETE</promise>`

## Gate Result Output

Write to `output/gate-06-result.json`:
```json
{
  "stage": "6-export",
  "result": "PASS|WARN|FAIL",
  "checks": [
    { "name": "glb_exists", "passed": true, "detail": "model.glb exists, 8.5MB" },
    { "name": "fbx_exists", "passed": true, "detail": "model.fbx exists, 12.1MB" },
    { "name": "stl_exists", "passed": true, "detail": "model.stl exists, 3.2MB" },
    { "name": "glb_valid", "passed": true, "detail": "Valid glTF header" },
    { "name": "fbx_valid", "passed": true, "detail": "Valid FBX header" },
    { "name": "stl_units", "passed": true, "detail": "STL dimensions: 45 x 180 x 35 mm (millimeters confirmed)" },
    { "name": "glb_animations", "passed": true, "detail": "3 animation tracks preserved" },
    { "name": "fbx_animations", "passed": true, "detail": "3 animation clips in FBX" },
    { "name": "manifest_exists", "passed": true, "detail": "ASSET-MANIFEST.md exists, 87 lines" }
  ],
  "warnings": [],
  "blocking_errors": [],
  "recommendation": "All exports valid -- pipeline complete"
}
```
