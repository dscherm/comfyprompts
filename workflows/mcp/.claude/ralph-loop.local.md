---
active: true
iteration: 3
session_id: 
max_iterations: 30
completion_promise: null
started_at: "2026-03-28T13:02:28Z"
---

Soapbox Sabotage character gen-to-rig pipeline.

## Proven Mesh Pipeline Steps (from player character iteration)

### Stage 2: Fullbody Generation
- Extreme wide T-pose prompt: arms fully extended at 90deg, wide stance, visible daylight between all limbs
- 768x768 resolution (wider to accommodate T-pose)
- Negative prompt: "arms close to body, hands touching legs"

### Stage 4: 3D Generation + Cleanup + Split
1. Generate via Hunyuan3D v2.0 geometry-only (octree_resolution=256, max_faces=20000)
2. Boot fin removal: delete vertices below boot_z (15% height) that extend past calf outer X + 3cm
3. Fill holes from boot cleanup: select boundary edges, mesh.fill(), normals_make_consistent()
4. Mesh split via `scripts/mesh_split_by_region.py`:
   - Head: horizontal cut at 83% height
   - Arms: vertical cut at armpit X width (torso edge at 58-65% height), only above 52% Z (armpit height)
   - Legs: 45-degree angle from hip center (42% height), capped at armpit X distance
   - Torso: remainder
   - Extract order: head -> arms -> legs -> torso (order matters!)
5. Color-code regions and take viewport screenshots for visual validation
6. Export as character-split.glb with 5 separate mesh objects

### Stage 5: Rig with UniRig (Skeleton + ML Skinning)

**Step 1: UniRig skeleton prediction (on joined mesh, ~30 min on RTX 3070)**
1. Export the split mesh as a single joined GLB for UniRig input: `character-for-unirig.glb`
2. Preprocess: `cd C:/UniRig && .venv/Scripts/python.exe -m src.data.extract --config=configs/data/quick_inference.yaml --require_suffix=glb --force_override=true --num_runs=1 --id=0 --time=$(date) --faces_target_count=20000 --input=<joined.glb> --output_dir=tmp`
3. Copy npz: `cp <output_dir>/<name>/raw_data.npz C:/UniRig/tmp/<name>/`
4. Run skeleton prediction: `cd C:/UniRig && .venv/Scripts/python.exe run.py --task=configs/task/quick_inference_skeleton_articulationxl_ar_256.yaml --seed=12345 --input=<joined.glb> --output=<skeleton.fbx> --npz_dir=tmp`
5. Copy skeleton npz: `cp <output_dir>/<name>/predict_skeleton.npz C:/UniRig/tmp/<name>/`
6. UniRig outputs FBX with ML-predicted 52-bone skeleton aligned to actual mesh geometry

**Step 2: UniRig ML skinning prediction (~8 seconds)**
1. Run skinning: `cd C:/UniRig && .venv/Scripts/python.exe run.py --task=configs/task/quick_inference_unirig_skin.yaml --seed=12345 --input=<joined.glb> --output=<skinned.fbx> --npz_dir=tmp`
2. CRITICAL: Do NOT pass `--data_name` — let it default to `predict_skeleton.npz` from config
   - Passing `--data_name=raw_data.npz` causes joints=None crash (raw_data has no skeleton)
   - The skin config defaults to `data_name: predict_skeleton.npz` which has the predicted joints
3. Output: FBX with skeleton + ML-predicted per-vertex skin weights (100% coverage, smooth joints)
4. ML weights are dramatically better than proximity or envelope — learned from 14,000+ rigged models

**Step 3: Apply to split mesh (for hand-thigh separation)**
1. Import ML-skinned FBX into Blender via blender-mcp (has joined mesh with perfect weights)
2. Import split character GLB alongside it (5 objects: head, torso, arm_L, arm_R, legs)
3. Use Blender Data Transfer modifier to copy weights from skinned mesh to each split object
4. Parent split objects to skeleton with Armature modifier
5. Delete the joined skinned mesh — keep only split objects + skeleton
6. Each split object has ML weights but as separate objects — arm weights CANNOT bleed into legs

**Alternative (simpler but single mesh):** Use the ML-skinned FBX directly without splitting.
The ML weights are good enough that the joined mesh may not need splitting — test the driving
pose first. If hands and thighs don't intersect (wide T-pose + ML weights), splitting is optional.

**Step 4: Apply driving pose**
- Legs: Euler rotation works (bone_44/48 thigh -90X, bone_45/49 shin +90X, bone_46/50 foot -30X)
- Spine: Euler works (bone_2 -15X, bone_3 -10X, bone_4 neck +5X, bone_5 head +15X)
- Arms: DO NOT USE EULER — UniRig bone local axes are arbitrary
- Arms: Use IK constraints on hand bones targeting empty objects:
  1. Create two empties: SteeringTarget_R at (0.15, -0.6, 0.45), SteeringTarget_L at (-0.15, -0.6, 0.45)
  2. Add IK constraint to bone_9 (R hand) -> SteeringTarget_R, chain_count=3, iterations=200
  3. Add IK constraint to bone_28 (L hand) -> SteeringTarget_L, chain_count=3, iterations=200
  4. Adjust target positions to tune hand placement (X=spread, Y=forward reach, Z=height)

**Step 5: Validate**
- Take viewport screenshots (front, side, 3/4, hip close-up) — user must approve before advancing
- Check: no hand-thigh intersection, smooth knee/hip deformation, arms at steering position
- Export approved pose as GLB for kart assembly

### Kart Assembly
- Apply driving pose at assembly time via IK targets relative to kart SteeringColumn empty
- Separate mesh objects prevent intersection (if using split mesh)
- ML weights prevent deformation artifacts (if using joined mesh)

### Known Issues / Lessons Learned (from player character iteration)
1. UniRig skeleton prediction takes ~30 min on RTX 3070 8GB (near VRAM limit)
2. UniRig skinning prediction takes ~8 sec — FAST, but MUST use correct data_name
   - BUG: passing `--data_name=raw_data.npz` causes crash (joints=None)
   - FIX: omit --data_name, let config default to predict_skeleton.npz
3. Meshy auto_rig_3d_model requires Unity Editor running AND textured GLB — geometry-only fails
4. Blender bone heat weighting fails silently on mesh objects >5000 verts (0% weight coverage)
5. Blender envelope weights work but produce rough joint deformation
6. proximity_weight.py works for 100% coverage but inferior to ML weights at joints
7. Hunyuan3D generates ground-shadow artifacts as boot sole fins — must clean before split
8. Mesh split extraction order matters: head -> arms -> legs -> torso
9. UniRig bone local axes are arbitrary — Euler arm rotation produces unexpected results, use IK
10. Wide T-pose fullbody image is critical — arms down = hand-thigh intersection in 3D mesh

## Pipeline Config
- UniRig 52-bone skeleton (ML-predicted, aligned to actual mesh geometry)
- UniRig ML skin weights (cross-attention model, 8 sec inference, 100% coverage)
- IK-based arm posing (not Euler — UniRig local axes are arbitrary)
- Split mesh for hand-thigh separation guarantee (optional with ML weights)
- Custom rig_soupbox.py for barrel character
- Hybrid bake is DEPRECATED — replaced by mesh split + ML skinning
