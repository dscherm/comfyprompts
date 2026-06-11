# Quality Gate 5: PBR-TEXTURING

## PASS Criteria (ALL must pass)
- [ ] `output/textured/textured-model.glb` exists and is >10KB
- [ ] At least 1 material slot is present in the textured GLB
- [ ] At least 1 albedo texture exists under `output/textured/textures/albedo/`
- [ ] Every material in `pipeline-state.json`.`material_palette` has metallic and roughness values set (not default 0/0)
- [ ] All albedo PNG files are valid images (non-zero byte size, readable header)
- [ ] GLB has valid glTF header (magic bytes: 0x46546C67)
- [ ] `texturing-report.json` exists and lists at least 1 material

## WARN Criteria (log but don't block)
- [ ] Bake resolution was downgraded to 1024x1024 due to VRAM pressure
- [ ] CPU bake fallback was used (bake time will be much longer on future runs)
- [ ] Mode C style transfer was skipped for one or more materials (reference crop missing)
- [ ] One or more materials fell back to solid color albedo (tile generation failed)
- [ ] Normal pass renders produced dark/empty images (lighting issue during Blender render)
- [ ] Upscaling was skipped for hero materials (>20% surface area) due to time constraints

## FAIL Criteria (block advancement -- re-run Stage 5)
- [ ] Textured GLB does not exist or is corrupt
- [ ] GLB has 0 material slots (materials not applied)
- [ ] No albedo textures exist (entire Pass 2 failed)
- [ ] All materials have metallic=0 and roughness=0 (PBR values not applied -- Principled BSDF nodes not set up)
- [ ] Blender bake produced all-black or all-white textures (bake target not connected)
- [ ] GLB export failed (Blender crash or export error)
- [ ] `material_palette` in pipeline-state.json is empty (Stage 2 data not read)

## Validation Method

### File existence and material count check
```bash
echo "=== Textured GLB ==="
if [ -f "pipelines/skeuomorph-ralph/output/textured/textured-model.glb" ]; then
  size=$(stat --printf="%s" "pipelines/skeuomorph-ralph/output/textured/textured-model.glb")
  echo "textured-model.glb: ${size} bytes ($(( size / 1024 ))KB)"
else
  echo "FAIL: textured-model.glb missing"
fi

echo "=== Albedo textures ==="
count=$(ls pipelines/skeuomorph-ralph/output/textured/textures/albedo/*.png 2>/dev/null | wc -l)
echo "Albedo maps found: ${count}"
if [ "$count" -eq "0" ]; then
  echo "FAIL: No albedo textures generated"
fi

echo "=== All texture maps ==="
for subdir in albedo normal roughness metallic; do
  n=$(ls "pipelines/skeuomorph-ralph/output/textured/textures/$subdir/"*.png 2>/dev/null | wc -l)
  echo "  $subdir: $n files"
done
```

### GLB header validation
```bash
xxd -l 4 pipelines/skeuomorph-ralph/output/textured/textured-model.glb
# Expected: 6746 6c54 (glTF)
```

### GLB material slot check via Blender
```bash
"C:/Program Files/Blender Foundation/Blender 5.0/blender.exe" \
  --background --python - <<'PYTHON' -- TEXTURED_GLB
import bpy, sys

argv = sys.argv[sys.argv.index("--") + 1:]
glb_path = argv[0]

bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete()
bpy.ops.import_scene.gltf(filepath=glb_path)

total_materials = 0
for obj in bpy.data.objects:
    if obj.type != 'MESH':
        continue
    mat_count = len(obj.material_slots)
    print(f"{obj.name}: {mat_count} material slot(s)")
    total_materials += mat_count

    for slot in obj.material_slots:
        if slot.material:
            mat = slot.material
            if mat.use_nodes:
                bsdf = mat.node_tree.nodes.get('Principled BSDF')
                if bsdf:
                    metallic = bsdf.inputs['Metallic'].default_value
                    roughness = bsdf.inputs['Roughness'].default_value
                    print(f"  {mat.name}: metallic={metallic:.2f}, roughness={roughness:.2f}")
                    if metallic == 0.0 and roughness == 0.0:
                        print(f"  WARN: {mat.name} has default PBR values (0/0) -- may not be set")
            else:
                print(f"  WARN: {mat.name} does not use nodes")

print(f"Total material slots across all meshes: {total_materials}")
if total_materials == 0:
    print("FAIL: No materials found in textured GLB")
PYTHON
```

### Albedo texture validity check
```bash
"C:/Program Files/Blender Foundation/Blender 5.0/blender.exe" \
  --background --python - <<'PYTHON'
import bpy, os, glob

albedo_dir = "pipelines/skeuomorph-ralph/output/textured/textures/albedo/"
png_files = glob.glob(albedo_dir + "*.png")

all_pass = True
for png_path in png_files:
    size = os.path.getsize(png_path)
    if size < 1024:
        print(f"FAIL: {os.path.basename(png_path)} is suspiciously small ({size} bytes)")
        all_pass = False
        continue
    try:
        img = bpy.data.images.load(png_path)
        w, h = img.size
        print(f"PASS: {os.path.basename(png_path)} -- {w}x{h} px, {size} bytes")
        bpy.data.images.remove(img)
    except Exception as e:
        print(f"FAIL: {os.path.basename(png_path)} could not be loaded: {e}")
        all_pass = False

if all_pass and png_files:
    print("All albedo textures valid")
elif not png_files:
    print("FAIL: No albedo textures found")
PYTHON
```

### PBR values coverage check

Read `pipeline-state.json` and verify every `material_palette` entry has `metallic` and `roughness` keys set to non-default values consistent with the PROMPT.md PBR reference table.

## Gate Result Output

Write to `output/gate-05-result.json`:
```json
{
  "stage": "5-pbr-texturing",
  "result": "PASS|WARN|FAIL",
  "checks": [
    { "name": "textured_glb_exists", "passed": true, "detail": "textured-model.glb exists, 14.2MB" },
    { "name": "glb_valid_header", "passed": true, "detail": "Valid glTF header" },
    { "name": "material_slots", "passed": true, "detail": "4 material slots (steel_plate, leather_trim, skin_face, fabric_cloak)" },
    { "name": "albedo_textures", "passed": true, "detail": "4 albedo maps generated (2048x2048 hero x2, 1024x1024 secondary x2)" },
    { "name": "pbr_values_set", "passed": true, "detail": "All materials have non-default metallic/roughness from palette" },
    { "name": "texturing_report", "passed": true, "detail": "texturing-report.json exists, 4 materials listed" }
  ],
  "warnings": [
    "fabric_cloak tile generation fell back to solid color -- style transfer reference crop missing"
  ],
  "blocking_errors": [],
  "recommendation": "PBR textures applied -- proceed to mesh audit"
}
```
