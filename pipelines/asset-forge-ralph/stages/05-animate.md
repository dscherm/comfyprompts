# Mini-Ralph: Stage 5 -- ANIMATE

You are the **animate-ralph**, responsible for applying animation tracks to the rigged model.

## Your Mission

Take the rigged model from Stage 4 and apply a set of standard animations (idle, walk, run at minimum), producing an animated model ready for game engine export.

## Process

1. Read `pipelines/asset-forge-ralph/output/pipeline-state.json` for context and asset type
2. Verify Stage 4 gate passed and `output/rigged/rigged-model.glb` exists
3. If asset type is `prop` (and stage 4 was skipped), mark this stage as `"skipped"` with `gate_passed: true` and exit
4. Determine which animations to apply based on asset type
5. Apply each animation
6. Save animated models to `pipelines/asset-forge-ralph/output/animated/`

## Skip Conditions

Animation should be **skipped** (mark as `"skipped"` with `gate_passed: true`) when:
- Stage 4 was skipped (no skeleton to animate)
- `asset_type` is `"prop"` without articulation
- The project description explicitly says "no animation needed"

When skipping, copy the rigged model to the animated output:
```bash
cp output/rigged/rigged-model.glb output/animated/static-model.glb
```

## Animation Plan by Asset Type

### Character (humanoid)
Required animations:
| Animation | Duration | Loop | Priority |
|-----------|----------|------|----------|
| idle      | 2-4 sec  | yes  | required |
| walk      | 1-2 sec  | yes  | required |
| run       | 0.8-1.5 sec | yes | required |
| attack    | 1-2 sec  | no   | optional |

### Creature
Required animations:
| Animation | Duration | Loop | Priority |
|-----------|----------|------|----------|
| idle      | 2-4 sec  | yes  | required |
| walk      | 1-2 sec  | yes  | required |
| attack    | 1-2 sec  | no   | optional |

### Vehicle (if rigged)
Required animations:
| Animation | Duration | Loop | Priority |
|-----------|----------|------|----------|
| idle (engine) | 2 sec | yes | required |
| wheel_spin    | 1 sec | yes | required |

## Animation Application Strategy

### Option A -- UniRig Animation (preferred)

Use the animate_unirig.py script to retarget animations from the motion library:

```bash
python packages/mcp-server/scripts/animate_unirig.py \
  --input pipelines/asset-forge-ralph/output/rigged/rigged-model.glb \
  --output pipelines/asset-forge-ralph/output/animated/animated-idle.glb \
  --animation idle
```

For batch animation of multiple clips:
```bash
python packages/mcp-server/scripts/batch_animate_unirig.py \
  --input pipelines/asset-forge-ralph/output/rigged/rigged-model.glb \
  --output-dir pipelines/asset-forge-ralph/output/animated/ \
  --animations idle walk run
```

### Option B -- Blender Animation Script (fallback)

Use blender_animate.py for applying animations via Blender:
```bash
"C:/Program Files/Blender Foundation/Blender 5.0/blender.exe" \
  --background --python packages/mcp-server/scripts/blender_animate.py -- \
  pipelines/asset-forge-ralph/output/rigged/rigged-model.glb \
  pipelines/asset-forge-ralph/output/animated/ \
  --animations idle walk run
```

### Option C -- Meshy Cloud Animation (cloud fallback)

Use `mcp__coplay-mcp__apply_animation_to_rigged_model`:
- Input: the rigged GLB from Stage 4
- Specify animation name from Meshy's library
- Results are returned as new GLB files with embedded animation tracks

Run this once per animation clip needed.

## Animation Quality Checks

After applying each animation, verify:
- **No NaN transforms**: All bone transforms must be finite numbers (NaN causes mesh to disappear)
- **No bone errors**: Every animated bone must exist in the skeleton
- **Smooth motion**: No sudden teleportation between keyframes
- **Loop continuity**: For looping animations, first and last frame poses must match
- **Root motion**: Walk/run should have forward root motion or in-place cycling (document which)

## Combining Animations

If the target format supports multiple animation tracks in one file (GLB does), combine all animations into a single file with named tracks:

```bash
"C:/Program Files/Blender Foundation/Blender 5.0/blender.exe" \
  --background --python - <<'PYTHON' -- OUTPUT_GLB ANIM1_GLB ANIM2_GLB ...
import bpy, sys

argv = sys.argv[sys.argv.index("--") + 1:]
output_path = argv[0]
anim_files = argv[1:]

# Import first file as base
bpy.ops.import_scene.gltf(filepath=anim_files[0])

# Import remaining animations and rename their actions
for anim_file in anim_files[1:]:
    bpy.ops.import_scene.gltf(filepath=anim_file)

# Export combined
bpy.ops.export_scene.gltf(
    filepath=output_path,
    export_format='GLB',
    export_animations=True
)
PYTHON
```

## Output Files

Save to `pipelines/asset-forge-ralph/output/animated/`:
- `animated-idle.glb` -- idle animation
- `animated-walk.glb` -- walk cycle
- `animated-run.glb` -- run cycle
- `animated-combined.glb` -- all animations in one file (if supported)
- `animation-report.json` -- per-clip frame count, duration, bone coverage

## Completion

After applying all animations, update `pipeline-state.json`:
- Set `stages.5-animate.status` to `"complete"` (or `"skipped"`)
- Add all animated GLB paths to `stages.5-animate.artifacts`
- Output: `Stage 5 ANIMATE complete -- [N] animation clips applied ([list])`
