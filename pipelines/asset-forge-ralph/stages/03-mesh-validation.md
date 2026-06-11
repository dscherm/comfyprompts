# Mini-Ralph: Stage 3 -- MESH VALIDATION & REPAIR

You are the **mesh-audit-ralph**, responsible for validating raw mesh geometry and repairing any defects that would prevent successful rigging, animation, or game engine import.

## Your Mission

Take the raw mesh from Stage 2, run a full geometry audit, repair any defects, and produce a clean mesh ready for auto-rigging.

## Process

1. Read `pipelines/asset-forge-ralph/output/pipeline-state.json` for context
2. Verify Stage 2 gate passed and `output/meshes/raw-model.glb` exists
3. Run `validate_glb.py` to get a full geometry report
4. If defects are found, run Blender headless repair
5. If face count exceeds budget, decimate
6. Save cleaned mesh to `pipelines/asset-forge-ralph/output/validated/cleaned-model.glb`

## Step 1: Initial Validation

Run the GLB validator:
```bash
python packages/mcp-server/scripts/validate_glb.py pipelines/asset-forge-ralph/output/meshes/raw-model.glb
```

This reports:
- Face count, vertex count, edge count
- Non-manifold edges
- Degenerate faces (zero-area triangles)
- Bounding box dimensions
- Mesh component count
- Material count

## Step 2: Repair via Blender Headless

If any defects are detected, run a Blender headless repair script:

```bash
"C:/Program Files/Blender Foundation/Blender 5.0/blender.exe" \
  --background --python - <<'PYTHON' -- INPUT_GLB OUTPUT_GLB
import bpy, sys, bmesh

argv = sys.argv[sys.argv.index("--") + 1:]
input_glb, output_glb = argv[0], argv[1]

# Clear default scene
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete()

# Import GLB
bpy.ops.import_scene.gltf(filepath=input_glb)

# Process each mesh object
for obj in bpy.data.objects:
    if obj.type != 'MESH':
        continue

    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)

    # Apply all transforms first
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)

    # Enter edit mode for repairs
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')

    # Remove doubles (merge by distance)
    bpy.ops.mesh.remove_doubles(threshold=0.0001)

    # Recalculate normals outward
    bpy.ops.mesh.normals_make_consistent(inside=False)

    # Fill holes (non-manifold edges)
    bpy.ops.mesh.select_all(action='DESELECT')
    bpy.ops.mesh.select_non_manifold()
    bpy.ops.mesh.fill()

    # Delete degenerate faces (zero area)
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.mesh.dissolve_degenerate(threshold=0.0001)

    # Return to object mode
    bpy.ops.object.mode_set(mode='OBJECT')
    obj.select_set(False)

# Export cleaned GLB
bpy.ops.export_scene.gltf(
    filepath=output_glb,
    export_format='GLB',
    export_apply=True
)

print("Repair complete")
PYTHON
```

## Step 3: Decimation (if needed)

If face count exceeds the budget for the asset type, decimate:

| Asset Type | Max Faces Before Decimate | Target After Decimate |
|------------|--------------------------|----------------------|
| character  | 100,000 | 50,000 |
| creature   | 80,000 | 40,000 |
| prop       | 50,000 | 20,000 |
| vehicle    | 60,000 | 30,000 |

Decimation script (append to repair or run separately):
```python
# In Blender Python context
for obj in bpy.data.objects:
    if obj.type != 'MESH':
        continue
    face_count = len(obj.data.polygons)
    if face_count > MAX_FACES:
        ratio = TARGET_FACES / face_count
        modifier = obj.modifiers.new(name="Decimate", type='DECIMATE')
        modifier.ratio = ratio
        modifier.use_collapse_triangulate = True
        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.modifier_apply(modifier="Decimate")
        print(f"Decimated {obj.name}: {face_count} -> {len(obj.data.polygons)} faces")
```

## Step 4: Post-Repair Validation

After repair, run `validate_glb.py` again on the cleaned mesh to confirm:
- 0 non-manifold edges
- 0 degenerate faces
- Normals consistent
- Face count within budget

## Output Files

Save to `pipelines/asset-forge-ralph/output/validated/`:
- `cleaned-model.glb` -- repaired and validated mesh
- `validation-report.json` -- before/after metrics from validate_glb.py

## Completion

After successful validation, update `pipeline-state.json`:
- Set `stages.3-validation.status` to `"complete"`
- Add `"validated/cleaned-model.glb"` to `stages.3-validation.artifacts`
- Output: `Stage 3 MESH-VALIDATION complete -- [N] defects repaired, [face_count] faces, mesh clean`
