# Mini-Ralph: Stage 7 -- RIG-ANIMATE

You are the **rig-animate-ralph**, responsible for adding a skeleton and animation clips to the validated model. For props, this stage is skipped entirely.

## Your Mission

Take the validated model from Stage 6 and apply an appropriate skeleton with weight painting, then retarget standard animation clips. For characters and creatures, produce a rigged and animated GLB ready for game engine import.

## Process

1. Read `pipelines/skeuomorph-ralph/output/pipeline-state.json` for context and asset type
2. Verify Stage 6 gate passed and `output/validated/validated-model.glb` exists
3. If asset type is `prop`, mark stage as `"skipped"` with `gate_passed: true` and exit
4. Choose rigging strategy based on asset type
5. Apply the skeleton
6. Apply animation clips
7. Save to `pipelines/skeuomorph-ralph/output/rigged/` and `output/animated/`

## Skip Conditions

This stage should be **skipped** (mark as `"skipped"` with `gate_passed: true`) when:
- `asset_type` is `"prop"` (no skeleton needed)
- The project description explicitly says "no animation needed" or "static model"

When skipping, copy the validated mesh forward so downstream stages have a consistent input path:
```bash
mkdir -p pipelines/skeuomorph-ralph/output/rigged
mkdir -p pipelines/skeuomorph-ralph/output/animated
cp pipelines/skeuomorph-ralph/output/validated/validated-model.glb \
   pipelines/skeuomorph-ralph/output/rigged/rigged-model.glb
cp pipelines/skeuomorph-ralph/output/validated/validated-model.glb \
   pipelines/skeuomorph-ralph/output/animated/static-model.glb
```

Then update `pipeline-state.json` stage 7 entry: `"status": "skipped"`, `"gate_passed": true`.

## Rigging Strategy

### Characters (humanoid)

**Option A -- UniRig (preferred)**

UniRig produces high-quality humanoid skeletons from a single pose. The model should be in A-pose or T-pose from Stage 4.

```bash
python packages/mcp-server/scripts/animate_unirig.py \
  --input pipelines/skeuomorph-ralph/output/validated/validated-model.glb \
  --output pipelines/skeuomorph-ralph/output/rigged/rigged-model.glb \
  --rig-only
```

UniRig installation: `C:\UniRig` with its own `.venv` (Python 3.11, CUDA).

**Option B -- Blender execute_blender_code with rig_humanoid snippet**

If UniRig fails, use `publish_for_blender` + `execute_blender_code` with a humanoid rigging snippet:

```python
# execute_blender_code snippet: rig_humanoid
import bpy

# Import validated model
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete()
bpy.ops.import_scene.gltf(filepath="output/shared/validated-model.glb")

# Use Rigify for humanoid skeleton
mesh_obj = next((o for o in bpy.data.objects if o.type == 'MESH'), None)
if not mesh_obj:
    raise RuntimeError("No mesh found")

# Add Rigify human meta-rig
bpy.ops.object.armature_human_metarig_add()
rig = bpy.context.active_object
rig.name = "Armature"

# Scale rig to match mesh height
mesh_height = mesh_obj.dimensions.z
rig.scale = (mesh_height / 2.0,) * 3
bpy.ops.object.transform_apply(scale=True)

# Auto-weight paint (requires mesh near rig)
bpy.context.view_layer.objects.active = mesh_obj
mesh_obj.select_set(True)
rig.select_set(True)
bpy.context.view_layer.objects.active = rig
bpy.ops.object.parent_set(type='ARMATURE_AUTO')

print(f"Rigged: {len(rig.data.bones)} bones")
```

**Option C -- MCP auto_rig_model tool**

Use the `auto_rig_model` MCP tool with `rig_type="humanoid"`:
- Input: path to `output/validated/validated-model.glb`
- This handles skeleton placement and weight painting automatically

### Creatures (non-humanoid)

**Option A -- UniRig (preferred)**

UniRig supports quadruped and custom body plans:

```bash
python packages/mcp-server/scripts/animate_unirig.py \
  --input pipelines/skeuomorph-ralph/output/validated/validated-model.glb \
  --output pipelines/skeuomorph-ralph/output/rigged/rigged-model.glb \
  --rig-only \
  --rig-type quadruped
```

**Option B -- MCP auto_rig_model tool**

Use `auto_rig_model` with `rig_type="quadruped"` or `rig_type="custom"` based on the creature's body plan (determined from the project description and asset_type metadata).

**Option C -- execute_blender_code with rig_quadruped snippet**

If both above fail, use `publish_for_blender` + `execute_blender_code` with a quadruped-appropriate armature construction script.

## Expected Skeleton by Asset Type

### Character (humanoid) -- minimum viable skeleton
- Hips (root)
- Spine, Spine1, Spine2
- Neck, Head
- LeftShoulder, LeftUpperArm, LeftLowerArm, LeftHand
- RightShoulder, RightUpperArm, RightLowerArm, RightHand
- LeftUpperLeg, LeftLowerLeg, LeftFoot
- RightUpperLeg, RightLowerLeg, RightFoot

Minimum: 19 bones. Typical with fingers: 25-65 bones.

### Creature -- minimum viable skeleton
- Root/Hips
- Spine chain (3+ bones)
- Head
- Each limb chain (2-3 bones per limb)
- Tail chain if applicable

## Animation Application

### Characters

Apply using UniRig batch animation or per-clip:
```bash
python packages/mcp-server/scripts/batch_animate_unirig.py \
  --input pipelines/skeuomorph-ralph/output/rigged/rigged-model.glb \
  --output-dir pipelines/skeuomorph-ralph/output/animated/ \
  --animations idle walk run
```

Or use `animate_model` MCP tool for each clip.

Fallback -- `execute_blender_code` with `animate_walk.py` or `animate_idle.py` Blender snippets.

Required character clips:
| Animation | Duration | Loop |
|-----------|----------|------|
| idle      | 2-4 sec  | yes  |
| walk      | 1-2 sec  | yes  |
| run       | 0.8-1.5 sec | yes |

### Creatures

Required creature clips:
| Animation | Duration | Loop |
|-----------|----------|------|
| idle      | 2-4 sec  | yes  |
| walk      | 1-2 sec  | yes  |

Use `batch_animate_unirig.py` with `--animations idle walk` or the `animate_model` MCP tool.

## Combining Animation Clips

After all clips are generated, combine into a single GLB with named animation tracks:

```bash
"C:/Program Files/Blender Foundation/Blender 5.0/blender.exe" \
  --background --python - <<'PYTHON' -- OUTPUT_GLB ANIM1_GLB ANIM2_GLB ANIM3_GLB
import bpy, sys

argv = sys.argv[sys.argv.index("--") + 1:]
output_path = argv[0]
anim_files = argv[1:]

bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete()

for anim_file in anim_files:
    bpy.ops.import_scene.gltf(filepath=anim_file)

bpy.ops.export_scene.gltf(
    filepath=output_path,
    export_format='GLB',
    export_animations=True,
    export_materials='EXPORT',
    export_images='EMBED'
)
print(f"Combined {len(anim_files)} animation clips")
PYTHON
```

## Weight Paint Quality Verification

After rigging, verify weight paint coverage:

```bash
"C:/Program Files/Blender Foundation/Blender 5.0/blender.exe" \
  --background --python - <<'PYTHON' -- RIGGED_GLB
import bpy, sys

argv = sys.argv[sys.argv.index("--") + 1:]
glb_path = argv[0]

bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete()
bpy.ops.import_scene.gltf(filepath=glb_path)

for obj in bpy.data.objects:
    if obj.type != 'MESH':
        continue
    if not obj.vertex_groups:
        print(f"WARN: {obj.name} has no vertex groups (no weight paint)")
        continue

    total_verts = len(obj.data.vertices)
    covered = 0
    for vert in obj.data.vertices:
        groups = [g for g in vert.groups if g.weight > 0.01]
        if groups:
            covered += 1

    pct = covered / total_verts * 100 if total_verts else 0
    print(f"{obj.name}: {covered}/{total_verts} vertices weighted ({pct:.1f}%)")
    if pct < 85:
        print(f"  WARN: Weight coverage below 85% threshold")
PYTHON
```

## Output Files

Save to:
- `pipelines/skeuomorph-ralph/output/rigged/`:
  - `rigged-model.glb` -- mesh with embedded armature and weight painting
  - `rig-report.json` -- bone count, bone names, weight coverage percentage

- `pipelines/skeuomorph-ralph/output/animated/`:
  - `idle.glb` -- idle animation clip
  - `walk.glb` -- walk cycle (characters and creatures)
  - `run.glb` -- run cycle (characters only)
  - `combined.glb` -- all animation clips in one file with named tracks
  - `animation-report.json` -- per-clip frame count, duration, loop status

## Completion

After successful rigging and animation, update `pipeline-state.json`:
- Set `stages.7-rig-animate.status` to `"complete"` (or `"skipped"`)
- Add `"rigged/rigged-model.glb"` and all animation GLB paths to `stages.7-rig-animate.artifacts`
- Output: `Stage 7 RIG-ANIMATE complete -- [bone_count] bones, [coverage]% weight coverage, [N] animation clips applied ([list])`

Or if skipped:
- Output: `Stage 7 RIG-ANIMATE skipped -- asset_type is prop, no skeleton required`
