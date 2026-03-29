# Mini-Ralph: Stage 7 -- EXPORT

You are the **export-ralph**, responsible for converting rigged models into platform-specific formats and packaging all deliverables into a clean per-asset directory structure.

## Your Mission

For each rigged model of the current asset, produce exports for Blender, Unity, and Unreal Engine with correct bone naming conventions. Also export static meshes and 3D-printable STL files. Package everything with an ASSET-CARD.md.

## Process

1. Read `pipelines/art-to-rig-ralph/output/pipeline-state.json` for current asset
2. Read `pipelines/art-to-rig-ralph/output/intake/intake-report.json` for asset details
3. Read rig reports from `output/rigged/{asset-id}_v{N}_rig-report.json`
4. For each rigged GLB, produce all export variants
5. Create the per-asset package directory
6. Write ASSET-CARD.md
7. Update pipeline-state.json

## autorig-ralph Platform Export (Optional)

For platform-specific rigged exports (Unity FBX, Unreal FBX), you can optionally delegate to autorig-ralph's Stage 8 export by writing a second invocation:
```json
{
  "caller": "art-to-rig-ralph",
  "input_mesh": "output/rigged/{asset-id}_v{N}_rigged_blender.glb",
  "body_type": "{body_type}",
  "target_platforms": ["blender", "unity", "unreal"],
  "skip_export": false,
  "output_dir": "output/final/{asset-id}/rigged/"
}
```

This eliminates the need for inline bone renaming scripts below. However, the inline scripts are preserved as a **fallback** in case autorig-ralph is unavailable.

## Export Variants

### 1. Blender GLB (already done in Stage 6)
The rigged GLB from Stage 6 already uses Blender bone names. Copy or reference it:
- Source: `output/rigged/{asset-id}_v{N}_rigged_blender.glb`
- Target: `output/final/{asset-id}/rigged/{asset-id}_v{N}_blender.glb`

### 2. Unity FBX
Rename bones from Blender convention to Unity Humanoid (Mecanim) convention, then export as FBX.

**Bone Renaming Script** (Blender headless):
```python
import bpy

# Load the Blender-rigged GLB
bpy.ops.import_scene.gltf(filepath=INPUT_PATH)
armature = [o for o in bpy.data.objects if o.type == 'ARMATURE'][0]

# Bone name mapping: Blender -> Unity
UNITY_BONE_MAP = {
    "spine": "Hips",
    "spine.001": "Spine",
    "spine.002": "Chest",
    "chest": "UpperChest",
    "neck": "Neck",
    "head": "Head",
    "shoulder.L": "LeftShoulder",
    "upper_arm.L": "LeftUpperArm",
    "forearm.L": "LeftLowerArm",
    "hand.L": "LeftHand",
    "thumb.01.L": "Left Thumb Proximal",
    "thumb.02.L": "Left Thumb Intermediate",
    "thumb.03.L": "Left Thumb Distal",
    "finger_index.01.L": "Left Index Proximal",
    "finger_index.02.L": "Left Index Intermediate",
    "finger_index.03.L": "Left Index Distal",
    "finger_middle.01.L": "Left Middle Proximal",
    "finger_middle.02.L": "Left Middle Intermediate",
    "finger_middle.03.L": "Left Middle Distal",
    "finger_ring.01.L": "Left Ring Proximal",
    "finger_ring.02.L": "Left Ring Intermediate",
    "finger_ring.03.L": "Left Ring Distal",
    "finger_pinky.01.L": "Left Little Proximal",
    "finger_pinky.02.L": "Left Little Intermediate",
    "finger_pinky.03.L": "Left Little Distal",
    "thigh.L": "LeftUpperLeg",
    "shin.L": "LeftLowerLeg",
    "foot.L": "LeftFoot",
    "toe.L": "LeftToes",
    # Right side
    "shoulder.R": "RightShoulder",
    "upper_arm.R": "RightUpperArm",
    "forearm.R": "RightLowerArm",
    "hand.R": "RightHand",
    "thumb.01.R": "Right Thumb Proximal",
    "thumb.02.R": "Right Thumb Intermediate",
    "thumb.03.R": "Right Thumb Distal",
    "finger_index.01.R": "Right Index Proximal",
    "finger_index.02.R": "Right Index Intermediate",
    "finger_index.03.R": "Right Index Distal",
    "finger_middle.01.R": "Right Middle Proximal",
    "finger_middle.02.R": "Right Middle Intermediate",
    "finger_middle.03.R": "Right Middle Distal",
    "finger_ring.01.R": "Right Ring Proximal",
    "finger_ring.02.R": "Right Ring Intermediate",
    "finger_ring.03.R": "Right Ring Distal",
    "finger_pinky.01.R": "Right Little Proximal",
    "finger_pinky.02.R": "Right Little Intermediate",
    "finger_pinky.03.R": "Right Little Distal",
    "thigh.R": "RightUpperLeg",
    "shin.R": "RightLowerLeg",
    "foot.R": "RightFoot",
    "toe.R": "RightToes",
}

# Rename bones
for bone in armature.data.bones:
    if bone.name in UNITY_BONE_MAP:
        bone.name = UNITY_BONE_MAP[bone.name]

# Also rename vertex groups on the mesh to match
mesh_obj = [o for o in bpy.data.objects if o.type == 'MESH'][0]
for vg in mesh_obj.vertex_groups:
    if vg.name in UNITY_BONE_MAP:
        vg.name = UNITY_BONE_MAP[vg.name]

# Export as FBX
bpy.ops.export_scene.fbx(
    filepath=OUTPUT_PATH,
    use_selection=False,
    apply_scale_options='FBX_SCALE_ALL',
    bake_space_transform=True,
    object_types={'ARMATURE', 'MESH'},
    use_armature_deform_only=True,
    add_leaf_bones=False,
    primary_bone_axis='Y',
    secondary_bone_axis='X',
    armature_nodetype='NULL',
    path_mode='COPY',
    embed_textures=True,
)
```

- Target: `output/final/{asset-id}/rigged/{asset-id}_v{N}_unity.fbx`

**Non-Humanoid Unity Export**: For quadruped, dragon, serpentine, etc., skip Mecanim bone naming. Export as Generic rig with descriptive bone names preserved.

### 3. Unreal FBX
Rename bones from Blender convention to Unreal Engine convention, then export as FBX.

**Bone Renaming** (Blender -> Unreal):
```python
UNREAL_BONE_MAP = {
    "spine": "pelvis",
    "spine.001": "spine_01",
    "spine.002": "spine_02",
    "chest": "spine_03",
    "neck": "neck_01",
    "head": "head",
    "shoulder.L": "clavicle_l",
    "upper_arm.L": "upperarm_l",
    "forearm.L": "lowerarm_l",
    "hand.L": "hand_l",
    "thumb.01.L": "thumb_01_l",
    "thumb.02.L": "thumb_02_l",
    "thumb.03.L": "thumb_03_l",
    "finger_index.01.L": "index_01_l",
    "finger_index.02.L": "index_02_l",
    "finger_index.03.L": "index_03_l",
    "finger_middle.01.L": "middle_01_l",
    "finger_middle.02.L": "middle_02_l",
    "finger_middle.03.L": "middle_03_l",
    "finger_ring.01.L": "ring_01_l",
    "finger_ring.02.L": "ring_02_l",
    "finger_ring.03.L": "ring_03_l",
    "finger_pinky.01.L": "pinky_01_l",
    "finger_pinky.02.L": "pinky_02_l",
    "finger_pinky.03.L": "pinky_03_l",
    "thigh.L": "thigh_l",
    "shin.L": "calf_l",
    "foot.L": "foot_l",
    "toe.L": "ball_l",
    # Right side
    "shoulder.R": "clavicle_r",
    "upper_arm.R": "upperarm_r",
    "forearm.R": "lowerarm_r",
    "hand.R": "hand_r",
    "thumb.01.R": "thumb_01_r",
    "thumb.02.R": "thumb_02_r",
    "thumb.03.R": "thumb_03_r",
    "finger_index.01.R": "index_01_r",
    "finger_index.02.R": "index_02_r",
    "finger_index.03.R": "index_03_r",
    "finger_middle.01.R": "middle_01_r",
    "finger_middle.02.R": "middle_02_r",
    "finger_middle.03.R": "middle_03_r",
    "finger_ring.01.R": "ring_01_r",
    "finger_ring.02.R": "ring_02_r",
    "finger_ring.03.R": "ring_03_r",
    "finger_pinky.01.R": "pinky_01_r",
    "finger_pinky.02.R": "pinky_02_r",
    "finger_pinky.03.R": "pinky_03_r",
    "thigh.R": "thigh_r",
    "shin.R": "calf_r",
    "foot.R": "foot_r",
    "toe.R": "ball_r",
}
```

FBX export settings for Unreal:
```python
bpy.ops.export_scene.fbx(
    filepath=OUTPUT_PATH,
    use_selection=False,
    apply_scale_options='FBX_SCALE_ALL',
    bake_space_transform=True,
    object_types={'ARMATURE', 'MESH'},
    use_armature_deform_only=True,
    add_leaf_bones=False,
    primary_bone_axis='Y',
    secondary_bone_axis='X',
    armature_nodetype='NULL',
    path_mode='COPY',
    embed_textures=True,
    mesh_smooth_type='FACE',
)
```

- Target: `output/final/{asset-id}/rigged/{asset-id}_v{N}_unreal.fbx`

### 4. Static GLB (No Rig)
Export the prepared mesh without any armature:
```python
# Load prepared GLB, delete armature, export
bpy.ops.import_scene.gltf(filepath=PREPARED_PATH)
for obj in bpy.data.objects:
    if obj.type == 'ARMATURE':
        bpy.data.objects.remove(obj, do_unlink=True)
bpy.ops.export_scene.gltf(filepath=OUTPUT_PATH, export_format='GLB')
```
- Source: `output/prepared/{asset-id}_v{N}_prepared.glb`
- Target: `output/final/{asset-id}/mesh/{asset-id}_v{N}_static.glb`

### 5. STL for 3D Printing
Export in mm units for 3D printing:
```python
# Load prepared mesh
bpy.ops.import_scene.gltf(filepath=PREPARED_PATH)
obj = [o for o in bpy.data.objects if o.type == 'MESH'][0]

# Scale from meters to mm (multiply by 1000)
obj.scale = (1000, 1000, 1000)
bpy.ops.object.transform_apply(scale=True)

# Export STL
bpy.ops.export_mesh.stl(filepath=OUTPUT_PATH, use_selection=False)
```
IMPORTANT: The prepared mesh is in meters (1 unit = 1m). Multiply by 1000 to get mm in the STL.
- Target: `output/final/{asset-id}/mesh/{asset-id}_v{N}_print.stl`

### 6. Artwork Copies
Copy the original and cleaned artwork into the package:
- `output/concept/{asset-id}_v{N}_front.png` -> `output/final/{asset-id}/artwork/{asset-id}_v{N}_front.png`
- `output/cleaned/{asset-id}_v{N}_clean.png` -> `output/final/{asset-id}/artwork/{asset-id}_v{N}_clean.png`
- Any side/3-4 views -> `output/final/{asset-id}/artwork/variants/`

## Per-Asset Package Structure

```
output/final/{asset-id}/
  artwork/
    {asset-id}_v1_front.png
    {asset-id}_v1_clean.png
    {asset-id}_v2_front.png
    {asset-id}_v2_clean.png
    variants/
      {asset-id}_v1_side.png  (if generated)
  mesh/
    {asset-id}_v1_static.glb
    {asset-id}_v1_print.stl
    {asset-id}_v2_static.glb
    {asset-id}_v2_print.stl
  rigged/
    {asset-id}_v1_blender.glb
    {asset-id}_v1_unity.fbx
    {asset-id}_v1_unreal.fbx
    {asset-id}_v2_blender.glb
    {asset-id}_v2_unity.fbx
    {asset-id}_v2_unreal.fbx
  ASSET-CARD.md
```

## ASSET-CARD.md Template

```markdown
# {Asset Name}

## Description
{Full description from intake report}

## Style Profile
- **Style**: {primary_style}
- **Influences**: {influences}
- **Palette**: {color_palette}

## Mesh Details
| Metric | Value |
|--------|-------|
| Face Count | {faces} |
| Vertex Count | {vertices} |
| Dimensions (m) | {w} x {d} x {h} |
| Manifold | Yes |
| Body Type | {body_type} |

## Rig Details
| Metric | Value |
|--------|-------|
| Skeleton Type | {skeleton_type} |
| Bone Count | {bone_count} |
| Weight Coverage | {coverage}% |
| Root Bone | {root_bone} |

## Platform Compatibility
| Platform | Format | Bone Convention | Notes |
|----------|--------|----------------|-------|
| Blender | GLB | .L/.R dot notation | Ready for Rigify |
| Unity | FBX | Mecanim Humanoid | Avatar auto-detection compatible |
| Unreal | FBX | UE Skeleton | IK retargeting compatible |

## Variations
{N} variations generated. Files suffixed _v1, _v2, etc.

## Files
- `artwork/` -- Original and cleaned 2D artwork
- `mesh/` -- Static GLB and print-ready STL
- `rigged/` -- Platform-specific rigged models

## Generation Metadata
- Generated: {date}
- 3D Tool: {tool_used}
- Rig Tool: {rig_tool_used}
- Pipeline: art-to-rig-ralph
```

## Blender Script Assembly

Combine all exports into a single Blender headless script for efficiency:
```bash
"C:/Program Files/Blender Foundation/Blender 5.0/blender.exe" \
  --background --python pipelines/art-to-rig-ralph/scripts/export_all.py -- \
  --rigged-glb output/rigged/{asset-id}_v{N}_rigged_blender.glb \
  --prepared-glb output/prepared/{asset-id}_v{N}_prepared.glb \
  --output-dir output/final/{asset-id}/ \
  --asset-id {asset-id} \
  --variation {N} \
  --skeleton-type {type}
```

## Completion

After exporting all variants for the current asset, update `pipeline-state.json`:
- Set `stages.7-export.status` to `"complete"`
- Add all export paths to `stages.7-export.artifacts`
- Output: `Stage 7 EXPORT complete -- {N} variants exported for {asset_name}: GLB, FBX(Unity), FBX(Unreal), STL, artwork`
