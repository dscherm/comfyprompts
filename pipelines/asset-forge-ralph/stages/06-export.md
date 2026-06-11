# Mini-Ralph: Stage 6 -- EXPORT

You are the **export-ralph**, the final stage controller. You convert the animated model into multiple game-engine-ready formats and produce the asset manifest.

## Your Mission

Take the animated (or static) model from Stage 5 and export it to GLB, FBX, and STL formats. Write the final ASSET-MANIFEST.md and validate all exports.

## Process

1. Read `pipelines/asset-forge-ralph/output/pipeline-state.json` for context
2. Determine the input file:
   - If Stage 5 completed: use `output/animated/animated-combined.glb` (or individual clips)
   - If Stage 5 was skipped: use `output/rigged/rigged-model.glb`
   - If Stages 4-5 were skipped: use `output/validated/cleaned-model.glb`
3. Convert to each target format
4. Validate all exports
5. Write ASSET-MANIFEST.md
6. Save everything to `pipelines/asset-forge-ralph/output/final/`

## Export Formats

### GLB (primary game engine format)
- Standard for web, Godot, three.js, and increasingly Unity/Unreal
- Preserves animations, materials, textures
- Binary format, single file, efficient
- This is typically a copy/rename of the animated GLB

```bash
cp output/animated/animated-combined.glb output/final/model.glb
```

For individual animation clips (useful for some engines):
```bash
cp output/animated/animated-idle.glb output/final/model-idle.glb
cp output/animated/animated-walk.glb output/final/model-walk.glb
cp output/animated/animated-run.glb output/final/model-run.glb
```

### FBX (Unity/Unreal standard)

Convert via Blender:
```bash
"C:/Program Files/Blender Foundation/Blender 5.0/blender.exe" \
  --background --python packages/mcp-server/scripts/blender_convert.py -- \
  pipelines/asset-forge-ralph/output/animated/animated-combined.glb \
  pipelines/asset-forge-ralph/output/final/model.fbx
```

Or inline Blender script:
```bash
"C:/Program Files/Blender Foundation/Blender 5.0/blender.exe" \
  --background --python - <<'PYTHON' -- INPUT_GLB OUTPUT_FBX
import bpy, sys

argv = sys.argv[sys.argv.index("--") + 1:]
input_glb, output_fbx = argv[0], argv[1]

bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete()

bpy.ops.import_scene.gltf(filepath=input_glb)

# Select all imported objects
bpy.ops.object.select_all(action='SELECT')

bpy.ops.export_scene.fbx(
    filepath=output_fbx,
    use_selection=True,
    apply_scale_options='FBX_SCALE_ALL',
    bake_anim=True,
    bake_anim_use_all_actions=True,
    add_leaf_bones=False,
    path_mode='COPY',
    embed_textures=True
)
PYTHON
```

FBX export notes:
- `add_leaf_bones=False` prevents extra bones that confuse game engines
- `embed_textures=True` keeps textures inside the FBX (no loose files)
- `bake_anim_use_all_actions=True` exports all animation clips

### STL (3D printing)

**IMPORTANT: STL must use millimeters, not meters.** Blender defaults to meters internally. Apply a scale factor of 1000 if the model is in meter units, or verify the model scale before export.

```bash
"C:/Program Files/Blender Foundation/Blender 5.0/blender.exe" \
  --background --python - <<'PYTHON' -- INPUT_GLB OUTPUT_STL
import bpy, sys

argv = sys.argv[sys.argv.index("--") + 1:]
input_glb, output_stl = argv[0], argv[1]

bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete()

bpy.ops.import_scene.gltf(filepath=input_glb)

# Select all mesh objects and apply transforms
for obj in bpy.data.objects:
    if obj.type == 'MESH':
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj

bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)

# Check dimensions - if max dimension < 1.0, model is likely in meters
# Scale to millimeters (x1000)
max_dim = max(max(obj.dimensions) for obj in bpy.data.objects if obj.type == 'MESH')
if max_dim < 1.0:
    for obj in bpy.data.objects:
        if obj.type == 'MESH':
            obj.scale *= 1000
    bpy.ops.object.transform_apply(scale=True)
    print(f"Scaled model to millimeters (max dim was {max_dim}m, now {max_dim * 1000}mm)")

bpy.ops.wm.stl_export(
    filepath=output_stl,
    export_selected_objects=True,
    ascii_format=False
)
PYTHON
```

## Export Validation

For each exported file, verify:

| Format | Check | Method |
|--------|-------|--------|
| GLB | Valid glTF header (magic: 0x46546C67) | Read first 4 bytes |
| GLB | File size > 10KB | `stat` |
| GLB | Has mesh data | `validate_glb.py` |
| FBX | Valid FBX header ("Kaydara FBX Binary") | Read first 20 bytes |
| FBX | File size > 10KB | `stat` |
| FBX | Animations preserved | Check via Blender re-import |
| STL | Valid binary STL (80-byte header) | Read header |
| STL | File size > 1KB | `stat` |
| STL | Dimensions in mm range (10-500mm typical) | Parse triangle data |

## ASSET-MANIFEST.md

Write to `output/final/ASSET-MANIFEST.md`:

```markdown
# Asset Manifest: [Project Name]

## Overview
- **Description**: [from pipeline-state.json]
- **Asset Type**: [character/creature/prop/vehicle]
- **Pipeline**: asset-forge-ralph
- **Date**: [ISO date]

## Exported Files
| File | Format | Size | Contains |
|------|--------|------|----------|
| model.glb | glTF Binary | [size] | Mesh + Materials + Animations |
| model.fbx | FBX Binary | [size] | Mesh + Materials + Animations |
| model.stl | STL Binary | [size] | Geometry only (mm units) |
| model-idle.glb | glTF Binary | [size] | Idle animation clip |
| model-walk.glb | glTF Binary | [size] | Walk animation clip |
| model-run.glb | glTF Binary | [size] | Run animation clip |

## Mesh Statistics
- **Vertices**: [count]
- **Faces**: [count]
- **Materials**: [count]
- **Bounding Box**: [x] x [y] x [z] units

## Skeleton
- **Bone Count**: [count]
- **Root Bone**: [name]
- **Weight Coverage**: [percentage]%

## Animations
| Clip | Frames | Duration | Looping |
|------|--------|----------|---------|
| idle | [N] | [sec]s | yes |
| walk | [N] | [sec]s | yes |
| run  | [N] | [sec]s | yes |

## Game Engine Import Notes

### Unity
1. Drag FBX into Assets folder
2. In Inspector > Rig tab: set Animation Type to "Humanoid" (characters) or "Generic"
3. In Inspector > Animation tab: check "Loop Time" for idle/walk/run clips
4. Materials may need manual reassignment if using URP/HDRP

### Unreal Engine
1. Import FBX via Content Browser
2. Select "Skeletal Mesh" import type
3. Animations import as separate AnimSequence assets
4. Set up Animation Blueprint for state machine

### Godot
1. Import GLB directly (File > Open Scene or drag into FileSystem)
2. Animations auto-detected as AnimationPlayer tracks
3. Set animation looping in AnimationPlayer

### 3D Printing
1. Use the STL file (dimensions in millimeters)
2. Import into slicer (Cura, PrusaSlicer, etc.)
3. Verify scale matches expected dimensions
4. No textures or animations in STL -- geometry only
```

## Output Files

Save to `pipelines/asset-forge-ralph/output/final/`:
- `model.glb` -- primary game-ready export with all animations
- `model.fbx` -- Unity/Unreal compatible export
- `model.stl` -- 3D print-ready export (mm units)
- `model-idle.glb` -- individual idle animation clip
- `model-walk.glb` -- individual walk animation clip
- `model-run.glb` -- individual run animation clip
- `ASSET-MANIFEST.md` -- complete asset documentation
- `export-report.json` -- validation results for all formats

## Completion

After all exports and validation, update `pipeline-state.json`:
- Set `stages.6-export.status` to `"complete"`
- Add all final file paths to `stages.6-export.artifacts`
- Output: `Stage 6 EXPORT complete -- GLB + FBX + STL exported, manifest written`

If this is the final stage and all gates passed:
- Output: `<promise>ASSET FORGE COMPLETE</promise>`
