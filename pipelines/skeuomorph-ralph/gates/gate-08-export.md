# Quality Gate 8: EXPORT (Final Gate)

## PASS Criteria (ALL must pass)
- [ ] `output/final/game/model.glb` exists and is >10KB
- [ ] `output/final/render/model.glb` exists and is >10KB
- [ ] Both GLBs have valid glTF headers (magic bytes: 0x46546C67)
- [ ] At least 1 texture file exists under `output/final/game/textures/`
- [ ] `output/final/SKEUOMORPH-MANIFEST.md` exists and is non-empty (>20 lines)
- [ ] Manifest contains all required sections: Project, Material Palette, Output Files, Mesh Statistics, Generation Tools Used
- [ ] `export-report.json` exists
- [ ] If "print" was in `output_targets`: `output/final/print/model.stl` exists and STL dimensions are in millimeter range (>1.0 in at least one axis)
- [ ] If "fbx" was in `output_targets`: `output/final/game/model.fbx` exists and is >10KB
- [ ] Requested format files that were not generated are accounted for in `export-report.json` with a reason

## WARN Criteria (log but don't block)
- [ ] Total export package exceeds 500MB (very large asset)
- [ ] FBX is >3x the size of GLB (may have duplicate or uncompressed texture data)
- [ ] STL exceeds 100MB (very high polygon count for printing)
- [ ] Individual animation clip GLBs are missing but combined GLB has animations
- [ ] Render GLB is smaller than game GLB (unexpected -- render should be same or higher fidelity)
- [ ] Manifest Material Palette section lists fewer materials than `pipeline-state.json`.`material_palette`

## FAIL Criteria (block -- re-run Stage 8)
- [ ] `output/final/game/model.glb` is missing or corrupt
- [ ] `output/final/render/model.glb` is missing or corrupt
- [ ] Either GLB has an invalid glTF header
- [ ] `SKEUOMORPH-MANIFEST.md` is missing or has <10 lines (empty/partial)
- [ ] Manifest is missing the Material Palette section (core purpose of this pipeline)
- [ ] STL was requested but dimensions are <1.0 in all axes (meter units, not mm -- conversion failed)
- [ ] FBX was requested but export failed entirely
- [ ] No textures under `output/final/game/textures/` (PBR texture extraction failed)
- [ ] Mesh data is absent in the game GLB (0 faces -- export produced empty file)

## Validation Method

### File existence and size check
```bash
echo "=== Required exports ==="
for path in \
  "pipelines/skeuomorph-ralph/output/final/game/model.glb" \
  "pipelines/skeuomorph-ralph/output/final/render/model.glb" \
  "pipelines/skeuomorph-ralph/output/final/SKEUOMORPH-MANIFEST.md"; do
  if [ -f "$path" ]; then
    size=$(stat --printf="%s" "$path")
    echo "PASS: $path -- ${size} bytes ($(( size / 1024 ))KB)"
  else
    echo "FAIL: $path missing"
  fi
done

echo ""
echo "=== Textures ==="
count=$(ls pipelines/skeuomorph-ralph/output/final/game/textures/*.png 2>/dev/null | wc -l)
echo "Extracted textures: ${count}"
if [ "$count" -eq "0" ]; then
  echo "FAIL: No textures extracted"
fi

echo ""
echo "=== Optional exports (check output_targets) ==="
for path in \
  "pipelines/skeuomorph-ralph/output/final/print/model.stl" \
  "pipelines/skeuomorph-ralph/output/final/game/model.fbx"; do
  if [ -f "$path" ]; then
    size=$(stat --printf="%s" "$path")
    echo "PRESENT: $path -- ${size} bytes"
  else
    echo "ABSENT: $path (check if in output_targets)"
  fi
done
```

### GLB header validation
```bash
for glb in \
  pipelines/skeuomorph-ralph/output/final/game/model.glb \
  pipelines/skeuomorph-ralph/output/final/render/model.glb; do
  echo -n "$glb header: "
  xxd -l 4 "$glb" 2>/dev/null || echo "MISSING"
done
# Expected: 6746 6c54 (glTF)
```

### GLB mesh and material check
```bash
"C:/Program Files/Blender Foundation/Blender 5.0/blender.exe" \
  --background --python - <<'PYTHON' -- GAME_GLB
import bpy, sys

argv = sys.argv[sys.argv.index("--") + 1:]
glb_path = argv[0]

bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete()
bpy.ops.import_scene.gltf(filepath=glb_path)

meshes = [o for o in bpy.data.objects if o.type == 'MESH']
armatures = [o for o in bpy.data.objects if o.type == 'ARMATURE']
actions = bpy.data.actions

if not meshes:
    print("FAIL: No mesh data in game GLB")
else:
    total_faces = sum(len(o.data.polygons) for o in meshes)
    total_mats = sum(len([s for s in o.material_slots if s.material]) for o in meshes)
    print(f"Meshes: {len(meshes)}, Total faces: {total_faces}, Materials: {total_mats}")
    if total_faces == 0:
        print("FAIL: 0 faces -- empty mesh exported")
    if total_mats == 0:
        print("FAIL: No materials -- PBR textures lost")

print(f"Armatures: {len(armatures)}")
print(f"Animation tracks: {len(actions)}")
for action in actions:
    frames = int(action.frame_range[1] - action.frame_range[0])
    print(f"  {action.name}: {frames} frames")
PYTHON
```

### STL unit validation (if print in output_targets)
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
        max_dim = max(dims)
        print(f"STL dimensions: {dims.x:.2f} x {dims.y:.2f} x {dims.z:.2f}")
        if max_dim < 1.0:
            print("FAIL: Dimensions suggest meter units -- forgot mm conversion")
        elif max_dim > 5000:
            print("WARN: Very large STL -- verify scale is intended")
        else:
            print(f"PASS: Millimeter units confirmed (max: {max_dim:.1f}mm)")
PYTHON
```

### Manifest completeness check
```bash
python - <<'PYTHON'
import re

manifest_path = "pipelines/skeuomorph-ralph/output/final/SKEUOMORPH-MANIFEST.md"

required_sections = [
    "## Project",
    "## Material Palette",
    "## Output Files",
    "## Mesh Statistics",
    "## Generation Tools Used",
]

with open(manifest_path) as f:
    content = f.read()
    lines = content.splitlines()

print(f"Manifest length: {len(lines)} lines")

for section in required_sections:
    if section in content:
        print(f"PASS: '{section}' found")
    else:
        print(f"FAIL: '{section}' missing from manifest")

# Check material palette is not empty template
if "| [material_name]" in content:
    print("WARN: Material Palette section still contains placeholder values")
PYTHON
```

## Pipeline Completion

When this gate passes, all 8 stages and gates have passed. The pipeline is complete.

1. Verify all 8 stages in `pipeline-state.json` have `gate_passed: true`
2. Verify `SKEUOMORPH-MANIFEST.md` exists with all required sections filled in
3. Output: `<promise>SKEUOMORPH COMPLETE</promise>`

## Gate Result Output

Write to `output/gate-08-result.json`:
```json
{
  "stage": "8-export",
  "result": "PASS|WARN|FAIL",
  "checks": [
    { "name": "game_glb_exists", "passed": true, "detail": "game/model.glb exists, 16.3MB" },
    { "name": "render_glb_exists", "passed": true, "detail": "render/model.glb exists, 22.1MB" },
    { "name": "game_glb_valid", "passed": true, "detail": "Valid glTF header, 42600 faces, 4 materials, 3 animation tracks" },
    { "name": "textures_extracted", "passed": true, "detail": "8 PNG textures extracted to game/textures/" },
    { "name": "stl_exists", "passed": true, "detail": "print/model.stl exists, 5.8MB" },
    { "name": "stl_units", "passed": true, "detail": "STL dimensions: 38 x 185 x 28 mm (millimeters confirmed)" },
    { "name": "fbx_exists", "passed": false, "detail": "Not requested in output_targets" },
    { "name": "manifest_exists", "passed": true, "detail": "SKEUOMORPH-MANIFEST.md exists, 94 lines" },
    { "name": "manifest_complete", "passed": true, "detail": "All 5 required sections present, 4 materials in palette" }
  ],
  "warnings": [],
  "blocking_errors": [],
  "recommendation": "All exports valid, manifest complete -- pipeline complete"
}
```
