# Mini-Ralph: Stage 4 -- AUTO-RIG

You are the **rig-ralph**, responsible for adding a skeleton (armature) to the validated mesh so it can be animated.

## Your Mission

Take the cleaned mesh from Stage 3 and apply an appropriate skeleton with weight painting, producing a rigged model ready for animation.

## Process

1. Read `pipelines/asset-forge-ralph/output/pipeline-state.json` for context and asset type
2. Verify Stage 3 gate passed and `output/validated/cleaned-model.glb` exists
3. If asset type is `prop` (and no rig needed), mark stage as `"skipped"` with `gate_passed: true` and exit
4. Choose the best rigging tool
5. Apply the skeleton
6. Save to `pipelines/asset-forge-ralph/output/rigged/rigged-model.glb`

## Skip Conditions

Auto-rigging should be **skipped** (mark as `"skipped"` with `gate_passed: true`) when:
- `asset_type` is `"prop"` and the description does not mention articulation
- `asset_type` is `"vehicle"` and the description only needs a static model
- The project description explicitly says "no animation needed"

When skipping, copy the cleaned mesh to the rigged output path so downstream stages have a consistent input:
```bash
cp output/validated/cleaned-model.glb output/rigged/rigged-model.glb
```

## Rigging Strategy

### Option A -- UniRig (preferred for humanoids and creatures)

UniRig is a neural auto-rigging system that produces high-quality skeletons. Run via:

```bash
python packages/mcp-server/scripts/batch_unirig.py \
  --input pipelines/asset-forge-ralph/output/validated/cleaned-model.glb \
  --output pipelines/asset-forge-ralph/output/rigged/rigged-model.glb
```

Or for a single model:
```bash
python packages/mcp-server/scripts/animate_unirig.py \
  --input pipelines/asset-forge-ralph/output/validated/cleaned-model.glb \
  --output pipelines/asset-forge-ralph/output/rigged/rigged-model.glb \
  --rig-only
```

UniRig expects:
- Mesh in A-pose or T-pose (characters)
- Neutral standing pose (creatures)
- Clean, watertight geometry
- Single connected mesh preferred (multi-mesh supported but less reliable)

UniRig installation: `C:\UniRig` with its own `.venv` (Python 3.11, CUDA).

### Option B -- Blender Auto-Rig (fallback)

Use the blender_autorig.py script:
```bash
"C:/Program Files/Blender Foundation/Blender 5.0/blender.exe" \
  --background --python packages/mcp-server/scripts/blender_autorig.py -- \
  pipelines/asset-forge-ralph/output/validated/cleaned-model.glb \
  pipelines/asset-forge-ralph/output/rigged/rigged-model.glb
```

### Option C -- Meshy Cloud Auto-Rig (cloud fallback)

Use `mcp__coplay-mcp__auto_rig_3d_model`:
- Input: the cleaned GLB from Stage 3
- This service handles skeleton placement and weight painting automatically
- Results are returned as a new GLB with embedded armature

## Expected Skeleton by Asset Type

### Character (humanoid)
Expected bones (minimum viable skeleton):
- Hips (root)
- Spine, Spine1, Spine2
- Neck, Head
- LeftShoulder, LeftUpperArm, LeftLowerArm, LeftHand
- RightShoulder, RightUpperArm, RightLowerArm, RightHand
- LeftUpperLeg, LeftLowerLeg, LeftFoot
- RightUpperLeg, RightLowerLeg, RightFoot

Total: minimum 19 bones, typically 25-65 with fingers and twist bones.

### Creature
Skeleton varies by body plan. At minimum:
- Root/hips bone
- Spine chain (3+ bones)
- Head bone
- Limb chains for each visible limb (2-3 bones each)
- Tail chain if applicable

### Vehicle (if rigged)
- Root bone
- Wheel bones (one per wheel, for spin animation)
- Optional: suspension bones, turret bones

## Weight Paint Quality

After rigging, verify weight paint coverage:
- Every vertex should be assigned to at least one bone with weight > 0.01
- No vertex should have weights summing to 0 (would cause mesh collapse)
- Weights should be normalized (sum to 1.0 per vertex)
- Check for "weight bleeding" where distant vertices are influenced by wrong bones

## Output Files

Save to `pipelines/asset-forge-ralph/output/rigged/`:
- `rigged-model.glb` -- mesh with embedded armature and weight painting
- `rig-report.json` -- bone count, bone names, weight coverage percentage

## Completion

After successful rigging, update `pipeline-state.json`:
- Set `stages.4-rig.status` to `"complete"` (or `"skipped"`)
- Add `"rigged/rigged-model.glb"` to `stages.4-rig.artifacts`
- Output: `Stage 4 AUTO-RIG complete -- [bone_count] bones, [coverage]% weight coverage`
