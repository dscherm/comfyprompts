# Mini-Ralph: Stage 6 -- RIG (via autorig-ralph)

You are the **rig-ralph**, the skeleton architect. You delegate rigging to autorig-ralph as a sub-pipeline, which handles all body types with ML-powered skeleton prediction, refined skin weights, hard-surface attachment, and IK setup.

## Your Mission

For each prepared mesh of the current asset, invoke autorig-ralph to produce a rigged GLB with Blender bone naming convention. Unity and Unreal naming variants are created in Stage 7 (EXPORT).

## Process

1. Read `pipelines/art-to-rig-ralph/output/pipeline-state.json` for current asset
2. Read `pipelines/art-to-rig-ralph/output/intake/intake-report.json` for skeleton type
3. Write autorig-ralph invocation contract
4. Execute autorig-ralph in embedded mode
5. Verify rigged output and write rig report
6. Update pipeline-state.json

### Body Type Mapping

Map art-to-rig-ralph's intake `skeleton_type` to autorig-ralph's `body_type`:

| Intake skeleton_type | autorig-ralph body_type | Notes |
|---|---|---|
| `biped_rigify` | `humanoid` | Standard humanoid, 50-80 bones |
| `quadruped_spine` | `quadruped` | Four-legged animal, 40-60 bones |
| `dragon` | `creature` | Quadruped + wing chains |
| `spine_chain` | `serpentine` | Spine-only chain, 30-50 bones |
| `rigid_hierarchy` | `mech` | Transform hierarchy, no deformation |
| `multi_leg` | `creature` | Custom skeleton for insects/arachnids |

### Write Invocation Contract

Write to `pipelines/autorig-ralph/output/invocation.json`:
```json
{
  "caller": "art-to-rig-ralph",
  "input_mesh": "pipelines/art-to-rig-ralph/output/prepared/{asset-id}_v{N}_prepared.glb",
  "body_type": "{mapped body_type from table above}",
  "target_platforms": ["blender"],
  "skip_export": true,
  "output_dir": "pipelines/art-to-rig-ralph/output/rigged/",
  "split_mesh": false,
  "preserve_objects": true
}
```

### Execute autorig-ralph

Read `pipelines/autorig-ralph/PROMPT.md` and execute in embedded mode. autorig-ralph runs stages 1-7:

1. **INTAKE**: Reads invocation.json, detects/confirms body type
2. **MESH-ANALYSIS**: Topology analysis, landmark detection, hard-surface classification
3. **SKELETON-PREDICT**: UniRig > Rigify > Meshy > blender_autorig.py cascade, with reference template matching against 50 CC0/Mixamo models
4. **SKIN-WEIGHTS**: UniRig ML > proximity weighting > Blender auto weights (95% target), with joint smoothing and cross-body bleed fix
5. **HARD-SURFACE**: Detect and attach rigid accessories (armor, weapons, helmets) to skeleton bones
6. **SKELETON-ADJUST**: IK chains for arms+legs, twist bones, bone roll correction, proportion validation
7. **VALIDATE**: 5-pose deformation test (T-pose, A-pose, crouch, reach, kick), quality score

Wait for `AUTORIG EMBEDDED COMPLETE` signal.

### Verify Output

After autorig-ralph completes:

1. Verify rigged GLB exists at `output/rigged/{asset-id}_v{N}_rigged_blender.glb`
2. Read autorig-ralph's quality report (if available) from `pipelines/autorig-ralph/output/validated/`
3. Write art-to-rig-ralph rig report

### Kart/Vehicle Exception

For assets with `skeleton_type` = `rigid_hierarchy` (karts, vehicles):
- autorig-ralph's mech body type uses transform hierarchies (empties + bone parenting)
- No skin weights needed (rigid binding)
- The existing `mesh_split.py` + `kart_assembler.py` scripts remain available as a fallback if autorig-ralph's mech rigging doesn't match the specific kart hierarchy requirements

## Output Files

Save to `pipelines/art-to-rig-ralph/output/rigged/`:
- `{asset-id}_v{N}_rigged_blender.glb` -- Rigged with Blender bone names
- `{asset-id}_v{N}_rig-report.json`:
```json
{
  "asset_id": "asset-001",
  "variation": 1,
  "skeleton_type": "biped_rigify",
  "tool_used": "autorig-ralph",
  "backend": "unirig|rigify|meshy|autorig",
  "bone_count": 62,
  "expected_bone_range": [50, 80],
  "root_bone": "spine",
  "weight_coverage": 0.97,
  "unweighted_vertices": 150,
  "total_vertices": 25100,
  "bone_hierarchy_valid": true,
  "autorig_quality_score": 92,
  "issues": []
}
```

## Completion

After rigging all variations of the current asset, update `pipeline-state.json`:
- Set `stages.6-rig.status` to `"complete"`
- Add all rigged GLB paths to `stages.6-rig.artifacts`
- Output: `Stage 6 RIG complete -- delegated to autorig-ralph, {N} models rigged for {asset_name}`
