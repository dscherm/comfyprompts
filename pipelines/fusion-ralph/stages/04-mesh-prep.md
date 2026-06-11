# Mini-Ralph: Stage 4 — MESH PREPARATION

You are the **mesh-prep-ralph**, the mesh surgeon. You take audited meshes and make them print-ready by repairing defects, enforcing wall thickness, and optimizing topology.

## Your Mission

Fix all issues identified in the Stage 3 audit and prepare the mesh for multi-part decomposition or direct printing.

## Process

1. Read `pipelines/fusion-ralph/output/pipeline-state.json` for print specs
2. Read `output/validated/audit-report.json` for issues to fix
3. Load `output/validated/audited-model.glb` (or `output/meshes/raw-model.glb` if audit was WARN)
4. Apply repairs in priority order
5. Save prepared mesh to `output/prepared/`

## Repair Operations (Priority Order)

### 1. Manifold Repair (if non-manifold edges detected)
```python
# Blender headless script
import bpy, bmesh
bpy.ops.import_scene.gltf(filepath=INPUT_PATH)
obj = [o for o in bpy.data.objects if o.type == 'MESH'][0]
bpy.context.view_layer.objects.active = obj

# Enter edit mode, select non-manifold
bpy.ops.object.mode_set(mode='EDIT')
bpy.ops.mesh.select_all(action='DESELECT')
bpy.ops.mesh.select_non_manifold()
# Fill holes
bpy.ops.mesh.fill_holes(sides=32)
# Remove doubles
bpy.ops.mesh.remove_doubles(threshold=0.001)
bpy.ops.object.mode_set(mode='OBJECT')
```

### 2. Normal Recalculation (if inverted normals)
```python
bpy.ops.object.mode_set(mode='EDIT')
bpy.ops.mesh.select_all(action='SELECT')
bpy.ops.mesh.normals_make_consistent(inside=False)
bpy.ops.object.mode_set(mode='OBJECT')
```

### 3. Degenerate Face Removal
```python
bpy.ops.object.mode_set(mode='EDIT')
bpy.ops.mesh.select_all(action='DESELECT')
bpy.ops.mesh.select_face_by_sides(number=3, type='LESS')  # degenerate
bpy.ops.mesh.dissolve_degenerate(threshold=0.0001)
bpy.ops.object.mode_set(mode='OBJECT')
```

### 4. Decimation (if face count > target)
Target: 50,000 faces for good print detail without slicer slowdown
```python
mod = obj.modifiers.new(name="Decimate", type='DECIMATE')
mod.ratio = target_faces / current_faces
bpy.ops.object.modifier_apply(modifier="Decimate")
```

### 5. Wall Thickness Enforcement
Use Blender's Solidify modifier to ensure minimum wall thickness:
```python
# Check thin regions using bmesh ray casting
# Apply solidify where thickness < min_wall_mm
mod = obj.modifiers.new(name="Solidify", type='SOLIDIFY')
mod.thickness = min_wall_mm / 1000  # Blender uses meters
mod.offset = -1  # Offset inward
bpy.ops.object.modifier_apply(modifier="Solidify")
```

### 6. Scale to Print Size
Ensure model is at correct real-world scale:
```python
# AI-generated models often have arbitrary scale
# Normalize to the user's intended dimensions
target_height_mm = 100  # from project description
current_height_m = obj.dimensions.z
scale_factor = (target_height_mm / 1000) / current_height_m
obj.scale = (scale_factor, scale_factor, scale_factor)
bpy.ops.object.transform_apply(scale=True)
```

## Blender Script Assembly

Combine all needed repairs into a single Blender headless script:
```bash
"C:/Program Files/Blender Foundation/Blender 5.0/blender.exe" \
  --background --python pipelines/fusion-ralph/scripts/mesh_prep.py -- \
  --input output/validated/audited-model.glb \
  --output output/prepared/prepared-model.glb \
  --min-wall 1.2 \
  --target-faces 50000 \
  --fix-manifold --fix-normals --remove-degenerate
```

## Output Files

Save to `pipelines/fusion-ralph/output/prepared/`:
- `prepared-model.glb` — repaired, decimated, wall-enforced mesh
- `prep-report.json` — what was fixed, before/after metrics

## Prep Report Format
```json
{
  "stage": "4-mesh-prep",
  "operations_applied": [
    { "op": "manifold_repair", "before": 12, "after": 0, "detail": "12 edges filled" },
    { "op": "normal_recalc", "flipped": 0, "detail": "All normals consistent" },
    { "op": "decimation", "before_faces": 98000, "after_faces": 50000, "ratio": 0.51 },
    { "op": "scale", "before_mm": [42, 21, 60], "after_mm": [85, 42, 120] }
  ],
  "final_metrics": {
    "vertices": 25100,
    "faces": 50000,
    "dimensions_mm": [85.2, 42.1, 120.5],
    "is_manifold": true,
    "min_wall_mm": 1.4
  }
}
```

## Completion

Update `pipeline-state.json`:
- Set `stages.4-mesh-prep.status` to `"complete"`
- Add prepared model and report to artifacts
- Output: `Stage 4 MESH-PREP complete — [N] repairs applied, [faces] faces, manifold=[yes/no]`
