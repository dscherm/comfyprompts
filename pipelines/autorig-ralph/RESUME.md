# AutoRig Ralph -- Resume Point (2026-03-29)

## What Was Done This Session

### Pipeline Created (4 commits)
1. **autorig-ralph pipeline** -- 8-stage ML auto-rigging with 50 reference meshes
2. **Integration** -- character-ralph (7 stages) + art-to-rig-ralph delegate rigging to autorig-ralph
3. **animate-ralph** -- animation reference library (2,937 files) + autorig→animate handoff
4. **Batch script** -- `batch_generate_characters.py` for all 10 Soapbox Sabotage characters

### UniRig Run Completed
- Skeleton prediction: 29 min, output at `pipelines/autorig-ralph/output/skeleton/player_skeleton.fbx`
- Skin weights: 4 sec, output at `pipelines/autorig-ralph/output/weighted/player_skinned.fbx`
- Quality score: 100/100 (51 bones, 100% weight coverage)

### Current Blocker: Driving Pose Distortion
The character mesh from Hunyuan3D has **49,000 disconnected triangle islands** (every face is a separate island). This causes tearing and distortion when posing. Multiple approaches tried (IK, Euler, DAMPED_TRACK, matrix manipulation) -- all produce leg distortion because the mesh topology is broken.

## What Needs To Happen Next

### 1. Fix the mesh FIRST (before posing)
The `character-clean.glb` has 147k verts but all disconnected. Need to:
```python
# In Blender (via blender-mcp):
import bpy, bmesh

# Import the clean mesh
bpy.ops.import_scene.gltf(filepath='D:/Projects/comfyui-toolchain/pipelines/character-ralph/output/3d/character-clean.glb')

# Select the mesh
obj = [o for o in bpy.data.objects if o.type == 'MESH'][0]
bpy.context.view_layer.objects.active = obj

# Enter edit mode and merge vertices
bpy.ops.object.mode_set(mode='EDIT')
bpy.ops.mesh.select_all(action='SELECT')
bpy.ops.mesh.remove_doubles(threshold=0.001)  # merge close verts
bpy.ops.mesh.normals_make_consistent(inside=False)  # fix normals
bpy.ops.object.mode_set(mode='OBJECT')

# Check: should go from 49k islands to 1-5 islands
```

### 2. Re-run UniRig on the cleaned mesh
After merge, export cleaned mesh as GLB and re-run:
```bash
# Extract
cd C:/UniRig && .venv/Scripts/python.exe -m src.data.extract \
  --config=configs/data/quick_inference.yaml --require_suffix=glb \
  --force_override=true --num_runs=1 --id=0 --time=0 \
  --faces_target_count=20000 --input=<cleaned.glb> --output_dir=tmp

# Skeleton (~30 min)
cd C:/UniRig && .venv/Scripts/python.exe run.py \
  --task=configs/task/quick_inference_skeleton_articulationxl_ar_256.yaml \
  --seed=12345 --input=<cleaned.glb> \
  --output=<skeleton.fbx> --npz_dir=tmp

# Skin weights (~4 sec)
cd C:/UniRig && .venv/Scripts/python.exe run.py \
  --task=configs/task/quick_inference_unirig_skin.yaml \
  --seed=12345 --input=<cleaned.glb> \
  --output=<skinned.fbx> --npz_dir=tmp
```

### 3. Apply driving pose
Use `pipelines/autorig-ralph/scripts/apply_driving_pose.py` which:
- Auto-detects bone roles from hierarchy
- Renames UniRig bone_XX to standard names (upperleg.l, lowerleg.l, etc.)
- Applies the proven kart-assembly Euler rotations (-90/+90 for legs)
- Keyframes as "DrivingPose" animation

### 4. Use blender-mcp for visual validation
With blender-mcp connected, import the GLB and take screenshots:
```
blender-mcp: execute_blender_code(code="bpy.ops.import_scene.gltf(filepath='...')")
blender-mcp: get_viewport_screenshot()
```

## Key File Locations

| File | Purpose |
|------|---------|
| `pipelines/character-ralph/output/3d/character-clean.glb` | Original Hunyuan3D mesh (147k verts, BROKEN - 49k islands) |
| `pipelines/character-ralph/output/3d/character-for-unirig.glb` | Joined mesh sent to UniRig |
| `pipelines/autorig-ralph/output/skeleton/player_skeleton.fbx` | UniRig skeleton (51 bones) |
| `pipelines/autorig-ralph/output/weighted/player_skinned.fbx` | UniRig skinned mesh (10.5k verts, ML weights) |
| `pipelines/character-ralph/output/rigged/character-driving-pose.glb` | Current (BROKEN) driving pose attempt |
| `pipelines/autorig-ralph/scripts/apply_driving_pose.py` | Driving pose script (rename bones + Euler) |
| `pipelines/character-ralph/scripts/resplit_mesh.py` | Mesh split script (may not be needed if mesh is fixed) |
| `pipelines/character-ralph/scripts/batch_generate_characters.py` | Batch gen for all 10 characters |
| `C:/Users/scher/Downloads/animation references/` | Downloaded animation packs (Rokoko, Quaternius, RancidMilk CMU) |
| `C:/Users/scher/Downloads/downloaded rigged models/` | Downloaded rigged reference meshes |

## Pipeline State

```
character-ralph: Stages 1-5 complete, Stage 6 (ANIMATE) pending
autorig-ralph: Embedded run complete (score 100/100)
kart-assembly-ralph: Waiting for fixed character-rigged-split.glb
```

## Prompt To Resume

```
Read pipelines/autorig-ralph/RESUME.md for context. We left off trying to fix
the driving pose on The Rookie character. The root problem is the Hunyuan3D mesh
has 49,000 disconnected triangle islands causing tearing when posed.

Use blender-mcp to:
1. Import character-clean.glb and merge vertices (remove_doubles threshold=0.001)
2. Verify mesh is now 1-5 connected islands (not 49k)
3. Re-export as cleaned GLB
4. Re-run UniRig skeleton + skin prediction on the cleaned mesh
5. Apply driving pose using apply_driving_pose.py
6. Take viewport screenshots to validate

The blender-mcp tools (execute_blender_code, get_viewport_screenshot) should
be available. Check with get_external_app_status first.
```

## Session Commits (10 total)

| Commit | Description |
|--------|-------------|
| `6856dd6` | autorig-ralph pipeline + 50 reference meshes |
| `35d72f3` | Integration into character-ralph (7 stages) + art-to-rig-ralph |
| `59d4b44` | Animation reference library + autorig→animate handoff |
| `3e2292d` | Animation organizer script + gitignores |
| `889bd09` | Driving animation keyword fix |
| `f1051dc` | Mesh resplit, driving pose, batch character scripts |
| `292144e` | Auto-detect bone roles (fixed left leg detection) |
| `8e21b4c` | IK for all limbs (fixed leg bowing) |
| `14ef4a2` | Keyframe-based bake (fixed mesh tearing from new_from_object) |
| Currently unstaged | Latest apply_driving_pose.py (rename bones + Euler approach) |
