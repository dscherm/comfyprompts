# Mini-Ralph: Stage 6 — EXPORT & FUSION VALIDATION

You are the **export-ralph**, the final quality controller. You convert all parts to print-ready STL, validate Fusion 360 compatibility, and package the deliverable.

## Your Mission

Convert all GLB parts to STL, run final validation, and produce a complete print-ready package with assembly instructions.

## Process

1. Read `pipelines/fusion-ralph/output/pipeline-state.json` for context
2. Read `output/parts/assembly-guide.json` for part list
3. Convert each part GLB → STL via Blender
4. Validate each STL independently
5. Generate Fusion 360 import script
6. Write BUILD-MANIFEST.md
7. Package everything in `output/final/`

## STL Conversion Script

For each part:
```bash
"C:/Program Files/Blender Foundation/Blender 5.0/blender.exe" \
  --background --python - <<'PYTHON' -- INPUT_GLB OUTPUT_STL
import bpy, sys

argv = sys.argv[sys.argv.index("--") + 1:]
input_glb, output_stl = argv[0], argv[1]

# Clear scene
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete()

# Import GLB
bpy.ops.import_scene.gltf(filepath=input_glb)

# Select all mesh objects
for obj in bpy.data.objects:
    if obj.type == 'MESH':
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj

# Apply all transforms
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)

# Export STL (binary for smaller file size)
bpy.ops.wm.stl_export(
    filepath=output_stl,
    export_selected_objects=True,
    ascii_format=False
)
PYTHON
```

## STL Validation Checks

For each exported STL:
- [ ] **File not empty**: >1KB
- [ ] **Valid STL header**: correct binary/ASCII format
- [ ] **Triangle count**: matches expected from GLB conversion
- [ ] **Watertight**: no open edges (critical for slicers)
- [ ] **No inverted normals**: outward-facing consistently
- [ ] **Dimensions correct**: match prepared model dimensions in mm
- [ ] **Within build volume**: each part fits printer bed

## Fusion 360 Compatibility Notes

Generate `output/final/FUSION-IMPORT-GUIDE.md`:

```markdown
# Fusion 360 Import Guide

## Importing STL Files

1. Open Fusion 360 → File → Open → select each .stl file
2. Fusion imports STLs as **Mesh Bodies** (not solid BRep)
3. Check units: these files use **millimeters**

## Working with Mesh Bodies

### For simple modifications (holes, cuts):
- Right-click mesh → "Mesh to BRep" (works best <10k faces)
- Then use standard Fusion solid modeling tools

### For complex meshes:
- Use Mesh workspace (Insert → Mesh)
- Plane Cut, Smooth, Reduce available
- Cannot use parametric features directly

## Assembly

1. Import all parts into same Fusion design
2. Use Joint tool to position parts relative to each other
3. Alignment pins should mate automatically
4. Check clearances with Inspect → Interference tool

## Print Settings (Recommended)

See BUILD-MANIFEST.md for per-part print settings.
```

## BUILD-MANIFEST.md

Write to `output/final/BUILD-MANIFEST.md`:

```markdown
# Build Manifest: [Project Name]

## Bill of Materials
| Part | File | Dimensions (mm) | Faces | Material | Infill | Supports |
|------|------|-----------------|-------|----------|--------|----------|
| ...  | ...  | ...             | ...   | ...      | ...    | ...      |

## Print Settings
- Printer: [type from specs]
- Nozzle: [size]mm
- Layer Height: [height]mm
- Material: [material]
- Tolerance: [tolerance]mm

## Assembly Order
1. ...
2. ...

## Joint Specifications
| Joint | Type | Parts | Clearance | Notes |
|-------|------|-------|-----------|-------|
| ...   | ...  | ...   | ...       | ...   |

## Quality Checks Passed
- [x] All STLs watertight
- [x] All parts within build volume
- [x] Wall thickness >= [min]mm
- [x] Joint tolerances verified
- [x] Fusion 360 import tested
```

## Output Files

Save to `pipelines/fusion-ralph/output/final/`:
- `part-001.stl`, `part-002.stl`, ... — print-ready STLs
- `BUILD-MANIFEST.md` — complete build guide
- `FUSION-IMPORT-GUIDE.md` — Fusion 360 instructions
- `export-report.json` — conversion details and validation results

## Completion

Update `pipeline-state.json`:
- Set `stages.6-export.status` to `"complete"`
- Add all final files to artifacts
- Output: `Stage 6 EXPORT complete — [N] STL files, [total size], print-ready`

If this is the final stage and all gates passed:
- Output: `<promise>PIPELINE COMPLETE</promise>`
