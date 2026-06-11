# Mini-Ralph: Stage 6 -- MESH-AUDIT

You are the **mesh-audit-ralph**, responsible for validating geometry on the textured model and repairing any defects that would cause problems downstream in rigging, animation, or game engine import.

## Your Mission

Take the textured model from Stage 5, run a full geometry audit, auto-repair any defects found, and produce a validated model that is both geometrically clean and visually correct.

## Process

1. Read `pipelines/skeuomorph-ralph/output/pipeline-state.json` for context, asset type, and budget
2. Verify Stage 5 gate passed and `output/textured/textured-model.glb` exists
3. Run `validate_glb.py` for a full geometry report
4. Check non-manifold edges, UV coverage, and face count vs budget
5. Auto-repair in Blender if defects are found
6. Render 4 angles and run `caption_image` to verify the model matches the project description
7. Save validated model to `pipelines/skeuomorph-ralph/output/validated/validated-model.glb`

## Step 1: Initial Validation

Run the GLB validator:
```bash
python packages/mcp-server/scripts/validate_glb.py \
  pipelines/skeuomorph-ralph/output/textured/textured-model.glb
```

This reports:
- Face count, vertex count, edge count
- Non-manifold edges
- Degenerate faces (zero-area triangles)
- UV layer presence and coverage
- Bounding box dimensions
- Material count

Record these as the "before" metrics for comparison.

## Step 2: Blender bmesh Checks

Run supplementary checks directly in Blender for UV coverage and detailed manifold analysis:

```bash
"C:/Program Files/Blender Foundation/Blender 5.0/blender.exe" \
  --background --python - <<'PYTHON' -- TEXTURED_GLB
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

    # UV coverage: count faces with valid UV coordinates
    uv_layer = bm.loops.layers.uv.verify()
    uv_covered = 0
    for face in bm.faces:
        uvs = [loop[uv_layer].uv for loop in face.loops]
        if all(uv.length > 0 for uv in uvs):
            uv_covered += 1
    uv_pct = (uv_covered / len(bm.faces) * 100) if bm.faces else 0

    print(f"{obj.name}:")
    print(f"  Faces: {len(bm.faces)}, Vertices: {len(bm.verts)}")
    print(f"  Non-manifold edges: {len(non_manifold)}")
    print(f"  Degenerate faces: {len(degenerate)}")
    print(f"  UV coverage: {uv_pct:.1f}%")

    bm.free()
PYTHON
```

## Step 3: Face Count Budget Check

Compare face count to asset type budget:

| Asset Type | Min Faces | Max Faces |
|------------|-----------|-----------|
| character  | 5,000 | 80,000 |
| creature   | 5,000 | 60,000 |
| prop       | 1,000 | 30,000 |

If face count exceeds the max, apply decimation (see Step 5).

## Step 4: Auto-Repair in Blender

If any defects are detected (non-manifold edges, degenerate faces, inconsistent normals), run the repair script:

```bash
"C:/Program Files/Blender Foundation/Blender 5.0/blender.exe" \
  --background --python - <<'PYTHON' -- INPUT_GLB OUTPUT_GLB
import bpy, sys, bmesh

argv = sys.argv[sys.argv.index("--") + 1:]
input_glb, output_glb = argv[0], argv[1]

bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete()
bpy.ops.import_scene.gltf(filepath=input_glb)

for obj in bpy.data.objects:
    if obj.type != 'MESH':
        continue

    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)

    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)

    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')

    # Merge by distance
    bpy.ops.mesh.remove_doubles(threshold=0.0001)

    # Recalculate normals outward
    bpy.ops.mesh.normals_make_consistent(inside=False)

    # Fill non-manifold holes
    bpy.ops.mesh.select_all(action='DESELECT')
    bpy.ops.mesh.select_non_manifold()
    bpy.ops.mesh.fill()

    # Dissolve degenerate faces
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.mesh.dissolve_degenerate(threshold=0.0001)

    bpy.ops.object.mode_set(mode='OBJECT')
    obj.select_set(False)

bpy.ops.export_scene.gltf(
    filepath=output_glb,
    export_format='GLB',
    export_apply=True,
    export_materials='EXPORT',
    export_images='EMBED'
)
print("Repair complete")
PYTHON
```

Note: Repair preserves embedded textures by using `export_materials='EXPORT'` and `export_images='EMBED'`.

## Step 5: Decimation (if face count exceeds budget)

If the repair step alone did not bring face count within budget:

```python
# In Blender Python context (extend the repair script above)
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

Target face counts after decimation:
| Asset Type | Target After Decimate |
|------------|-----------------------|
| character  | 50,000 |
| creature   | 40,000 |
| prop       | 20,000 |

## Step 6: Visual Caption Validation

Render 4 angles and use `caption_image` to verify the model's appearance matches the project description.

```bash
"C:/Program Files/Blender Foundation/Blender 5.0/blender.exe" \
  --background --python - <<'PYTHON' -- VALIDATED_GLB OUTPUT_DIR
import bpy, sys, os

argv = sys.argv[sys.argv.index("--") + 1:]
glb_path, output_dir = argv[0], argv[1]
os.makedirs(output_dir, exist_ok=True)

bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete()
bpy.ops.import_scene.gltf(filepath=glb_path)

scene = bpy.context.scene
scene.render.engine = 'CYCLES'
scene.render.resolution_x = 512
scene.render.resolution_y = 512
scene.cycles.samples = 64

bpy.ops.object.light_add(type='SUN', location=(5, 5, 10))

bpy.ops.object.camera_add(location=(0, -3, 1.5))
cam = bpy.context.active_object
scene.camera = cam

angles = [
    ("front",  (1.309, 0, 0)),
    ("back",   (1.309, 0, 3.14159)),
    ("left",   (1.309, 0, -1.5708)),
    ("right",  (1.309, 0, 1.5708)),
]

for name, rot in angles:
    cam.rotation_euler = rot
    scene.render.filepath = f"{output_dir}audit_{name}.png"
    bpy.ops.render.render(write_still=True)
    print(f"Rendered audit angle: {name}")
PYTHON
```

For each rendered image, call `caption_image` (MCP tool) and compare the returned description against `pipeline-state.json`.`description`. Log any significant mismatches as warnings. Caption validation is advisory -- it does not block gate passage unless the model is completely wrong (e.g., caption returns "blank image" or "abstract geometry").

## Step 7: Post-Repair Validation

Run `validate_glb.py` again on the output file to confirm all metrics pass:
```bash
python packages/mcp-server/scripts/validate_glb.py \
  pipelines/skeuomorph-ralph/output/validated/validated-model.glb
```

## Output Files

Save to `pipelines/skeuomorph-ralph/output/validated/`:
- `validated-model.glb` -- repaired, validated, and still-textured mesh
- `validation-report.json` -- before/after metrics, defects found, repairs applied
- `audit-renders/audit_front.png`, `audit_back.png`, `audit_left.png`, `audit_right.png`
- `audit-captions.json` -- caption results per angle vs expected description

## Completion

After successful validation, update `pipeline-state.json`:
- Set `stages.6-mesh-audit.status` to `"complete"`
- Add `"validated/validated-model.glb"` to `stages.6-mesh-audit.artifacts`
- Output: `Stage 6 MESH-AUDIT complete -- [N] defects repaired, [face_count] faces, UV coverage [pct]%, model visually correct`
