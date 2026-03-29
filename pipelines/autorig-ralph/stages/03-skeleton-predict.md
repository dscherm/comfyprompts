# Mini-Ralph: Stage 3 -- SKELETON-PREDICT

You are the **skeleton architect**. You use ML-based skeleton prediction to generate an accurate bone hierarchy for the preprocessed mesh, with a cascading fallback chain.

## Your Mission

Generate an accurate skeleton for the current asset using the best available tool. The skeleton must have correct bone placement, proper hierarchy, and appropriate bone count for the body type.

## Tool Cascade

Try tools in priority order. If one fails, proceed to the next.

### Tool A: UniRig (Primary -- Best for humanoids and creatures)

**Prerequisites**:
- UniRig installed at `C:/UniRig`
- Python 3.11 venv at `C:/UniRig/.venv/Scripts/python.exe`
- RTX 3070 with ~7GB VRAM free (close ComfyUI first!)

**Step 1: Preprocess mesh for UniRig**
```bash
cd C:/UniRig
.venv/Scripts/python.exe -m src.data.extract \
  --input "D:/Projects/comfyui-toolchain/pipelines/autorig-ralph/output/analysis/{asset-id}_preprocessed.glb"
```
This creates `raw_data.npz` in a temp directory.

**Step 2: Copy NPZ to UniRig workspace**
```bash
mkdir -p C:/UniRig/tmp/{asset-id}
cp /path/to/raw_data.npz C:/UniRig/tmp/{asset-id}/
```

**Step 3: Run skeleton prediction**
```bash
cd C:/UniRig
.venv/Scripts/python.exe run.py \
  --task=configs/task/quick_inference_skeleton_articulationxl_ar_256.yaml \
  --input C:/UniRig/tmp/{asset-id}/raw_data.npz
```
- Duration: 15-30 minutes on RTX 3070
- Output: FBX with predicted skeleton

**Step 4: Import and validate skeleton**
- Import the UniRig FBX into Blender via blender-mcp
- Delete the FBX mesh (keep only the armature)
- Verify bone count is within expected range for body type
- Check hierarchy is connected (no orphan bones)

### Tool B: Rigify (Fallback 1 -- Humanoids with standard proportions)

Use when UniRig fails or is unavailable.

**Via blender-mcp `execute_blender_code`**:
```python
import bpy

# Enable Rigify addon
bpy.ops.preferences.addon_enable(module='rigify')

# Add human metarig
bpy.ops.object.armature_human_metarig_add()
metarig = bpy.context.active_object

# Scale and position metarig to fit the mesh
mesh_obj = bpy.data.objects["MESH_NAME"]
mesh_dims = mesh_obj.dimensions
mesh_loc = mesh_obj.location

# Scale metarig to match mesh height
metarig_height = metarig.dimensions.z
scale_factor = mesh_dims.z / metarig_height
metarig.scale = (scale_factor, scale_factor, scale_factor)
bpy.ops.object.transform_apply(scale=True)

# Align metarig to mesh center
metarig.location = mesh_loc
metarig.location.z = 0  # feet on ground

# Generate the rig from metarig
bpy.context.view_layer.objects.active = metarig
bpy.ops.pose.rigify_generate()
```

Then fine-tune bone positions using landmark data from Stage 2.

### Tool C: Meshy Cloud (Fallback 2 -- Any textured mesh)

Use when both UniRig and Rigify fail.

**Via coplay-mcp**:
```
auto_rig_3d_model(model_path="path/to/mesh.glb")
```
- Requires Unity Editor running
- Mesh must have textures (geometry-only may fail)
- Returns rigged GLB with skeleton + weights (skip Stage 4 if weights are good)

### Tool D: Headless blender_autorig.py (Last resort)

```bash
"C:/Program Files/Blender Foundation/Blender 5.0/blender.exe" \
  --background --python packages/mcp-server/scripts/blender_autorig.py \
  -- "{mesh_path}" "{rig_type}" '{"auto_weights": true}'
```

## Skeleton Validation

After prediction, validate via blender-mcp:

```python
import bpy, json

armature = bpy.data.objects["Armature"]  # or predicted name
bones = armature.data.bones

validation = {
    "bone_count": len(bones),
    "root_bone": bones[0].name if bones else None,
    "hierarchy_depth": 0,  # max chain length
    "has_left_right_symmetry": False,
    "orphan_bones": [],  # bones with no parent and not root
    "leaf_bones": [b.name for b in bones if len(b.children) == 0],
    "bone_names": [b.name for b in bones]
}

# Check expected range
expected = {"biped_rigify": (50, 80), "quadruped_spine": (40, 60), "creature_custom": (20, 100)}
bone_range = expected.get(skeleton_type, (10, 200))
validation["in_expected_range"] = bone_range[0] <= len(bones) <= bone_range[1]

print("SKELETON_VALIDATION:" + json.dumps(validation))
```

## Skeleton Alignment

Ensure the skeleton root aligns with the mesh:
- Root bone (hips/pelvis) at mesh center of mass
- Spine chain along mesh vertical center line
- Feet bones at mesh lowest point
- Shoulder bones at mesh widest point above midline

If misaligned, adjust via `execute_blender_code` in Edit Mode.

## Output Files

- `output/skeleton/{asset-id}_skeleton.blend` -- Blender file with skeleton
- `output/skeleton/{asset-id}_skeleton.fbx` -- Standalone skeleton export
- `output/skeleton/{asset-id}_skeleton-report.json` -- Validation report

## Completion

Update `pipeline-state.json`:
- Set `stages.3-skeleton-predict.status` to `"complete"`
- Record which tool was used: `rigging_strategy.tool_used = "unirig|rigify|meshy|autorig"`
- Output: `Stage 3 SKELETON-PREDICT complete -- {bone_count} bones via {tool}, type: {skeleton_type}`
