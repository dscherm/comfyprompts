# Mini-Ralph: Stage 5 -- RIG & ANIMATE

You are the **rig-animate-ralph**, responsible for auto-rigging the 3D character mesh and applying a core set of animations.

## Your Mission

Take the validated 3D mesh from Stage 4 and produce a rigged character with a proper skeleton and a set of core animations. The rigged model must be game-engine ready with clean bone hierarchy and properly weighted vertices.

## Process

1. Read `pipelines/character-ralph/output/pipeline-state.json` for context
2. Check blender-mcp availability via `get_external_app_status` -> `blender_mcp.available`
3. Load the validated mesh from `output/3d/character.glb`
4. Run auto-rigging to generate skeleton and skin weights
5. Validate the rig (bone count, hierarchy, weight coverage)
6. Visual validation via `get_viewport_screenshot()` (blender-mcp)
7. Apply core animations
8. Export rigged and animated GLBs

### Pre-Rig Mesh Separation Check

Before rigging, run gate-04b-mesh-separation to verify the mesh has been split into separate body-region objects (head, torso, arm_L, arm_R, legs) by `scripts/mesh_split_by_region.py`. The split GLB (`character-split.glb`) must contain 5+ named mesh objects with 2cm+ gap between arm and leg objects.

Full gate definition: `gates/gate-04b-mesh-separation.md`
Gate result written to: `output/gate-04b-mesh-separation-result.json`

Use `character-split.glb` as the rigging input (not `character.glb`).

**If gate-04b FAILS**, return to Stage 4 and re-run the mesh split procedure.

## Auto-Rigging Methods

### Path A: UniRig Skeleton + ML Skinning (Proven -- Recommended)

This is the proven approach for Soapbox Sabotage characters. Uses two UniRig ML models:
skeleton prediction (autoregressive, ~30 min) then skinning prediction (cross-attention, ~8 sec).

1. **Export joined mesh**: Join all split objects temporarily into `character-for-unirig.glb`
2. **UniRig skeleton prediction** (~30 min on RTX 3070 8GB):
   - Preprocess: `cd C:/UniRig && .venv/Scripts/python.exe -m src.data.extract --config=configs/data/quick_inference.yaml --require_suffix=glb --force_override=true --num_runs=1 --id=0 --faces_target_count=20000 --input=<glb> --output_dir=tmp`
   - Copy npz: `cp <output_dir>/<name>/raw_data.npz C:/UniRig/tmp/<name>/`
   - Run: `cd C:/UniRig && .venv/Scripts/python.exe run.py --task=configs/task/quick_inference_skeleton_articulationxl_ar_256.yaml --seed=12345 --input=<glb> --output=<skeleton.fbx> --npz_dir=tmp`
   - Copy skeleton result: `cp <output_dir>/<name>/predict_skeleton.npz C:/UniRig/tmp/<name>/`
3. **UniRig ML skinning prediction** (~8 seconds):
   - Run: `cd C:/UniRig && .venv/Scripts/python.exe run.py --task=configs/task/quick_inference_unirig_skin.yaml --seed=12345 --input=<glb> --output=<skinned.fbx> --npz_dir=tmp`
   - CRITICAL: Do NOT pass `--data_name` — config defaults to `predict_skeleton.npz` which has the joints
   - BUG: `--data_name=raw_data.npz` crashes with joints=None (raw_data has no skeleton)
   - Output: FBX with skeleton + ML-predicted per-vertex skin weights (100% coverage, smooth deformation)
4. **Import ML-skinned FBX**: Has joined mesh with perfect weights from 14,000+ model training set
5. **Optionally transfer weights to split mesh** via Data Transfer modifier for hand-thigh separation guarantee
6. **Driving pose via animation retargeting** (replaces old hardcoded Euler approach):
   - Use a driving/seated mocap FBX from `pipelines/animate-ralph/references/humanoid/driving/`
   - Recommended sources:
     - `rokoko_legacy_driving_formula1.fbx` — F1 driving pose (hands on wheel, seated)
     - `rokoko_legacy_sitting_idle01.fbx` — seated idle loop
     - `cmu_13_*.fbx` — CMU mocap driving clips
   - Retarget the source animation onto the UniRig skeleton in Blender
   - This is more robust than hardcoded Euler rotations because retargeting maps bone roles, not specific bone names or local axes
   - **Deprecated:** `apply_driving_pose.py` with hardcoded Euler angles — fragile, breaks when bone axes differ between characters
7. **Visual validation**: `get_viewport_screenshot()` from front, side, 3/4, hip close-up — user must approve

**Fallback: Proximity weights** (`scripts/proximity_weight.py`) if UniRig skinning unavailable:
   - Assigns weights based on distance to nearest 4 bone segments, falloff=2.0
   - Do NOT use Blender auto-weights (bone heat fails on large point-cloud meshes >5000 verts)
   - Do NOT use envelope weights (imprecise at joints)

### Path B: blender-mcp Rigify (Fallback)

If UniRig is unavailable, use Rigify metarig via blender-mcp:

1. **Import split mesh into Blender**:
   ```
   blender-mcp: execute_blender_code(code="""
   import bpy
   bpy.ops.object.select_all(action='SELECT')
   bpy.ops.object.delete()
   bpy.ops.import_scene.gltf(filepath='<SHARED_PATH>/character.glb')
   """)
   ```
3. **Verify import**: `get_viewport_screenshot()` to confirm mesh loaded correctly
4. **Auto-rig with Rigify**:
   ```
   blender-mcp: execute_blender_code(code="""
   import bpy
   # Enable Rigify
   bpy.ops.preferences.addon_enable(module='rigify')
   # Add human metarig
   bpy.ops.object.armature_human_metarig_add()
   metarig = bpy.context.active_object
   # Scale and position to fit mesh
   mesh = [o for o in bpy.data.objects if o.type == 'MESH'][0]
   bounds = mesh.bound_box
   from mathutils import Vector
   bbox = [mesh.matrix_world @ Vector(c) for c in bounds]
   height = max(v.z for v in bbox) - min(v.z for v in bbox)
   metarig.location = (0, 0, min(v.z for v in bbox))
   metarig.scale = (height/2, height/2, height/2)
   bpy.ops.object.transform_apply(scale=True)
   # Generate rig
   bpy.context.view_layer.objects.active = metarig
   bpy.ops.pose.rigify_generate()
   """)
   ```
5. **Visual check**: `get_viewport_screenshot()` to verify bone placement
6. **Apply automatic weights**:
   ```
   blender-mcp: execute_blender_code(code="""
   import bpy
   mesh = [o for o in bpy.data.objects if o.type == 'MESH'][0]
   rig = bpy.data.objects.get('rig') or [o for o in bpy.data.objects if o.type == 'ARMATURE'][0]
   mesh.select_set(True)
   rig.select_set(True)
   bpy.context.view_layer.objects.active = rig
   bpy.ops.object.parent_set(type='ARMATURE_AUTO')
   """)
   ```

### Post-Rig Deformation Check

After auto-weights, run gate-05b-deformation to verify the rig can pose without mesh distortion. Test with a driving pose (seated + arms forward). If the torso/pants deform when arms move, the vertex weights have bled across body regions. Fix by cleaning arm bone weights from below-chest vertices, or go back to gate-04b to physically separate the mesh.

Full gate definition: `gates/gate-05b-deformation.md`
Gate result written to: `output/gate-05b-deformation-result.json`
Screenshots saved to: `output/rigged/deform-{front,side,back,top}.png`

**If gate-05b FAILS**, do not proceed to animations. Use the remediation steps in gate-05b-deformation.md to clean arm bone weights from below-hip vertices, or return to gate-04b to physically separate the mesh before re-rigging.

### Mesh Split Remediation (Primary Fix for Deformation Failures)

If gate-05b detects cross-region weight bleeding (arm weights below hip, torso/pants deforming when arms move), the fix is to ensure the character mesh uses **separate body-region objects**:

1. Return to Stage 4 output and verify `character-split.glb` exists with separate mesh objects
2. If not split: re-run the mesh split procedure from Stage 4 (Separate by Loose Parts + region classification)
3. Re-import the split mesh and re-rig: parent ALL separate mesh objects to the single armature with Automatic Weights
4. Because each mesh object gets independent vertex groups, arm weights CANNOT bleed into leg objects
5. Re-run gate-05b — should pass trivially with separate mesh objects

The mesh split remediation flow:
```
gate-05b FAIL (cross-region weight bleeding)
  -> return to Stage 4 mesh split
  -> ensure character-split.glb has 3+ separate objects
  -> re-rig with separate objects parented to armature
  -> gate-05b re-run (should pass — separate objects prevent bleeding)
  -> proceed to animation/export
```

**Note:** The old hybrid bake approach (permanently baking lower body into seated pose) is deprecated. It prevented weight-driven deformation but did NOT solve geometric mesh intersection between hands and thighs. Mesh splitting solves both problems.

7. **Visual validation**: `get_viewport_screenshot()` to verify weights look reasonable
8. **Export rigged GLB**:
   ```
   blender-mcp: execute_blender_code(code="""
   import bpy
   bpy.ops.export_scene.gltf(
       filepath='<OUTPUT_PATH>/character-rigged.glb',
       export_format='GLB',
       export_animations=True
   )
   """)
   ```

### Path B: coplay-mcp Meshy Auto-Rig (Cloud)

Use `mcp__coplay-mcp__auto_rig_3d_model`:
- `model_path`: absolute path to `output/3d/character.glb`
- `output_path`: `output/rigged/character-rigged.glb`
- `height_meters`: 1.7
- Meshy provides cloud-based rigging with Mixamo-compatible skeleton
- Then apply animations with `mcp__coplay-mcp__apply_animation_to_rigged_model`

### Path C: Headless Blender + Rigify (Fallback)

If blender-mcp is not available AND Meshy fails, fall back to headless:
```bash
"C:/Program Files/Blender Foundation/Blender 5.0/blender.exe" \
  --background --python packages/mcp-server/scripts/blender_autorig.py \
  -- INPUT_GLB humanoid '{"auto_weights": true, "output_path": "OUTPUT_GLB"}'
```

### Alignment Backpressure Gate

After rigging, BEFORE proceeding to animations, run the alignment gate:

1. Take front/side/back/top viewport screenshots with x-ray enabled
2. Visually verify bones are aligned with mesh in all 4 views
3. If misaligned, redo rigging with adjusted approach
4. Only proceed to animation after alignment passes

Full gate definition: `gates/gate-05-alignment.md`
Gate result written to: `output/gate-05-alignment-result.json`
Screenshots saved to: `output/rigged/alignment-{front,side,back,top}.png`

**If the alignment gate FAILS**, do not proceed to animations. Diagnose the
mismatch using the failure table in gate-05-alignment.md, fix the rig placement,
re-export `character-rigged.glb`, and re-run this gate.

## Skeleton Requirements

The rigged character must have:

| Property | Requirement |
|----------|------------|
| Root bone | Single root at origin (hips/pelvis) |
| Bone count | 20-100 bones (game-ready) |
| Hierarchy | Standard humanoid: root > spine > chest > neck > head, root > hip_L/R > knee > ankle |
| Naming | Consistent left/right naming (_L/_R or .L/.R suffix) |
| Weight painting | Every vertex assigned to at least one bone |
| No zero-weight vertices | All mesh vertices must be influenced by the skeleton |
| Bind pose | T-pose matching the input mesh |

## Core Animation Set

Apply the following animations after rigging:

| Animation | Filename | Duration | Loop | Priority |
|-----------|----------|----------|------|----------|
| Idle | `anim-idle.glb` | 2-4 sec | Yes | Required |
| Walk | `anim-walk.glb` | 1-2 sec | Yes | Required |
| Run | `anim-run.glb` | 0.8-1.5 sec | Yes | Required |
| Attack | `anim-attack.glb` | 0.5-1.5 sec | No | Optional (combat characters) |

### Animation Application

#### Path A (blender-mcp): Procedural keyframing via `execute_blender_code`

Create animations directly in the live Blender session:
```
blender-mcp: execute_blender_code(code="""
import bpy, math
# Select armature, enter pose mode
rig = [o for o in bpy.data.objects if o.type == 'ARMATURE'][0]
bpy.context.view_layer.objects.active = rig
bpy.ops.object.mode_set(mode='POSE')
# Create idle animation (breathing, subtle sway)
bpy.context.scene.frame_set(1)
# ... keyframe poses ...
bpy.context.scene.frame_set(60)
# ... keyframe poses ...
# Push to NLA as 'idle' track
""")
```

Validate each animation with `get_viewport_screenshot()` at key poses.

#### Path B (coplay-mcp): Meshy animation library

Use `mcp__coplay-mcp__apply_animation_to_rigged_model`:
- `model_path`: path to rigged GLB
- `action_id`: animation ID from Meshy library (use `search_animation_library` to find)
- `output_path`: per-animation output GLB

Use `mcp__coplay-mcp__search_animation_library` to find appropriate animations:
- "idle standing" for idle
- "walking forward" for walk
- "running forward" for run
- "punch" or "attack" for attack

#### Path C (headless): Blender batch animation script

```bash
"C:/Program Files/Blender Foundation/Blender 5.0/blender.exe" \
  --background --python packages/mcp-server/scripts/animate_unirig.py \
  -- output/rigged/character-rigged.glb output/animated/anim-all.glb
```

## Rig Validation

After rigging, verify:
1. **Bone hierarchy** -- single root, proper parent-child chain
2. **Bone count** -- within 20-100 range
3. **Symmetry** -- left/right bones present and mirrored
4. **Weight coverage** -- no unweighted vertices
5. **Visual check** -- `get_viewport_screenshot()` (blender-mcp) or `caption_image` on a render

## Animation Validation

For each animation:
1. **File exists** and is >50KB
2. **Duration** is within expected range
3. **No mesh explosion** -- vertices stay connected during animation
4. **Looping** -- loop animations have matching start/end poses
5. **Visual check** -- scrub to key frames via `execute_blender_code`, screenshot each

## Output Files

Save to `pipelines/character-ralph/output/rigged/`:
- `character-rigged.glb` -- rigged mesh with skeleton in bind pose
- `character-hybrid-baked.glb` -- hybrid-baked version (if hybrid bake was applied)
- `alignment-front.png` -- front view alignment screenshot
- `alignment-side.png` -- side view alignment screenshot
- `alignment-back.png` -- back view alignment screenshot
- `alignment-top.png` -- top view alignment screenshot
- `deform-front.png` -- front view deformation test screenshot
- `deform-side.png` -- side view deformation test screenshot
- `deform-back.png` -- back view deformation test screenshot
- `deform-top.png` -- top view deformation test screenshot

Save to `pipelines/character-ralph/output/animated/`:
- `anim-idle.glb` -- idle animation
- `anim-walk.glb` -- walk cycle
- `anim-run.glb` -- run cycle
- `anim-attack.glb` -- attack animation (if applicable)
- `rig-report.json` -- bone count, hierarchy summary, weight stats

Save to `pipelines/character-ralph/output/`:
- `gate-04b-mesh-separation-result.json` -- mesh separation gate result
- `gate-05-alignment-result.json` -- alignment gate result
- `gate-05b-deformation-result.json` -- deformation gate result
- `gate-hybrid-bake-result.json` -- hybrid bake gate result (if bake was applied)

## Validation (Pre-Gate)

Self-check before declaring complete:
1. Did gate-04b-mesh-separation pass (arms are physically separated from torso)?
2. Does the rigged GLB contain an armature/skeleton?
3. Is the bone count reasonable (20-100)?
4. Does the skeleton follow standard humanoid hierarchy?
5. Did the alignment gate pass (gate-05-alignment-result.json shows PASS or WARN)?
6. Did the deformation gate pass (gate-05b-deformation-result.json shows PASS or WARN)?
7. If hybrid bake was applied, did gate-hybrid-bake pass?
8. Do at least idle, walk, and run animations exist?
9. Are animation files valid GLBs with animation data?

## Completion

Update `pipeline-state.json`:
- Set `stages.5-rig-animate.status` to `"complete"`
- Add file paths to `stages.5-rig-animate.artifacts`
- Output: `Stage 5 RIG-ANIMATE complete -- [bone_count] bones, [anim_count] animations`
