# Backpressure Gate 5A: SKELETON-TO-MESH ALIGNMENT

This gate runs BEFORE gate-05-rig.md. It verifies that the auto-rigged skeleton
is correctly aligned inside the mesh volume before proceeding to animation work.
A misaligned skeleton cannot produce usable animations and must be re-rigged.

## PASS Criteria (ALL must pass)
- [ ] All 4 alignment screenshots saved to `output/rigged/alignment-{view}.png`
- [ ] Front view: all major bone chains visible inside the mesh silhouette
- [ ] Side view: bones are centered within mesh depth (not floating forward/behind)
- [ ] Back view: left/right bone positions mirror each other symmetrically
- [ ] Top view: arm bones track along the mesh arm volumes, leg bones track along leg volumes
- [ ] Spine chain runs vertically through the torso center in both front and side views
- [ ] Leg bones are contained within the leg mesh volumes
- [ ] Arm bones are contained within the arm mesh volumes
- [ ] Head bone is positioned inside the head mesh volume
- [ ] Gate result written to `output/gate-05-alignment-result.json`

## WARN Criteria (log but don't block)
- [ ] Minor bone endpoints slightly outside mesh surface (tip of finger/toe bones)
- [ ] Spine chain is slightly off-center (within ~5% of mesh width)
- [ ] Foot/hand bones are small and difficult to verify visually
- [ ] One view screenshot failed to render but other 3 views pass clearly
- [ ] Bone names are non-standard but placement is visually correct

## FAIL Criteria (block advancement -- redo rigging)
- [ ] Any entire bone chain is completely outside the mesh (e.g., spine floating beside torso)
- [ ] Skeleton scale is mismatched: skeleton is noticeably taller or shorter than mesh
- [ ] Skeleton pose does not match mesh pose (T-pose skeleton on A-pose mesh, or vice versa)
- [ ] Head bone is outside the head mesh (floating above or to the side)
- [ ] Leg bones pass through empty space beside the legs rather than inside the legs
- [ ] Arm bones are behind the mesh entirely or floating in front of it
- [ ] All 4 screenshots are blank or failed to render

## Validation Method

### Step 1: Enable X-Ray and Position Viewport

Use blender-mcp to set up the scene for alignment inspection. X-ray mode lets
bones show through the mesh surface so alignment can be judged visually.

```python
# Execute in blender-mcp via execute_blender_code
import bpy, os

output_dir = "pipelines/character-ralph/output/rigged"
os.makedirs(output_dir, exist_ok=True)

# Set render settings for screenshot
scene = bpy.context.scene
scene.render.resolution_x = 800
scene.render.resolution_y = 800
scene.render.image_settings.file_format = 'PNG'

# Make all armature layers visible and enable x-ray on all armatures
for obj in bpy.data.objects:
    if obj.type == 'ARMATURE':
        obj.show_in_front = True  # X-ray: bones draw through mesh
        obj.data.display_type = 'OCTAHEDRAL'

# Ensure all mesh objects are visible
for obj in bpy.data.objects:
    if obj.type == 'MESH':
        obj.hide_viewport = False
```

### Step 2: Capture Front View

```python
# Execute in blender-mcp via execute_blender_code
import bpy

# Set 3D viewport to FRONT orthographic
for area in bpy.context.screen.areas:
    if area.type == 'VIEW_3D':
        for space in area.spaces:
            if space.type == 'VIEW_3D':
                space.region_3d.view_perspective = 'ORTHO'
                # Front view = looking along -Y axis
                bpy.ops.view3d.view_axis(type='FRONT', align_active=False)
                break

scene = bpy.context.scene
scene.render.filepath = "pipelines/character-ralph/output/rigged/alignment-front.png"
bpy.ops.render.opengl(write_still=True)
```

Then call `get_viewport_screenshot()` and visually inspect:
- Head bone is within the head/neck silhouette
- Spine runs vertically through the center of the torso
- Upper arm and forearm bones are inside the arm silhouette
- Upper leg and lower leg bones are inside the leg silhouette
- No bone chain is entirely outside the body outline

### Step 3: Capture Side View

```python
# Execute in blender-mcp via execute_blender_code
import bpy

for area in bpy.context.screen.areas:
    if area.type == 'VIEW_3D':
        for space in area.spaces:
            if space.type == 'VIEW_3D':
                space.region_3d.view_perspective = 'ORTHO'
                # Right side view = looking along -X axis
                bpy.ops.view3d.view_axis(type='RIGHT', align_active=False)
                break

scene = bpy.context.scene
scene.render.filepath = "pipelines/character-ralph/output/rigged/alignment-side.png"
bpy.ops.render.opengl(write_still=True)
```

Then call `get_viewport_screenshot()` and visually inspect:
- Spine chain runs through the center of the torso depth (not behind the back or in front of chest)
- Leg bones are within the leg depth (not floating in front of or behind the legs)
- Head bone is centered in the head volume
- No bone chain is floating entirely in front of or behind the mesh

### Step 4: Capture Back View

```python
# Execute in blender-mcp via execute_blender_code
import bpy

for area in bpy.context.screen.areas:
    if area.type == 'VIEW_3D':
        for space in area.spaces:
            if space.type == 'VIEW_3D':
                space.region_3d.view_perspective = 'ORTHO'
                # Back view = looking along +Y axis
                bpy.ops.view3d.view_axis(type='BACK', align_active=False)
                break

scene = bpy.context.scene
scene.render.filepath = "pipelines/character-ralph/output/rigged/alignment-back.png"
bpy.ops.render.opengl(write_still=True)
```

Then call `get_viewport_screenshot()` and visually inspect:
- Left arm bones (from back: appear on right side of image) mirror right arm bones
- Left leg bones mirror right leg bones
- Spine is centered, not offset to one side
- Both shoulders are at the same height

### Step 5: Capture Top View

```python
# Execute in blender-mcp via execute_blender_code
import bpy

for area in bpy.context.screen.areas:
    if area.type == 'VIEW_3D':
        for space in area.spaces:
            if space.type == 'VIEW_3D':
                space.region_3d.view_perspective = 'ORTHO'
                # Top view = looking down -Z axis
                bpy.ops.view3d.view_axis(type='TOP', align_active=False)
                break

scene = bpy.context.scene
scene.render.filepath = "pipelines/character-ralph/output/rigged/alignment-top.png"
bpy.ops.render.opengl(write_still=True)
```

Then call `get_viewport_screenshot()` and visually inspect:
- Arm bones spread outward into the arm volumes (not crossing the torso)
- Leg bones drop down into the leg footprint (not between the legs or outside them)
- Spine is centered on the torso footprint

### Step 6: Write Gate Result

```python
# Execute in blender-mcp via execute_blender_code
import json, os

result = {
    "stage": "5a-alignment",
    "gate": "gate-05-alignment",
    "result": "PASS",  # or "WARN" or "FAIL"
    "screenshots": {
        "front":  "output/rigged/alignment-front.png",
        "side":   "output/rigged/alignment-side.png",
        "back":   "output/rigged/alignment-back.png",
        "top":    "output/rigged/alignment-top.png"
    },
    "checks": [
        { "name": "front_spine_aligned",    "passed": True,  "detail": "Spine chain runs through torso center" },
        { "name": "front_arms_inside",      "passed": True,  "detail": "Arm bones inside arm silhouette" },
        { "name": "front_legs_inside",      "passed": True,  "detail": "Leg bones inside leg silhouette" },
        { "name": "front_head_inside",      "passed": True,  "detail": "Head bone inside head volume" },
        { "name": "side_bones_centered",    "passed": True,  "detail": "Bones centered in mesh depth" },
        { "name": "back_symmetry",          "passed": True,  "detail": "L/R bones mirror correctly" },
        { "name": "top_arms_aligned",       "passed": True,  "detail": "Arm bones track into arm volumes" },
        { "name": "top_legs_aligned",       "passed": True,  "detail": "Leg bones track into leg volumes" },
        { "name": "scale_match",            "passed": True,  "detail": "Skeleton height matches mesh height" },
        { "name": "pose_match",             "passed": True,  "detail": "Skeleton and mesh are in matching pose" }
    ],
    "warnings": [],
    "blocking_errors": [],
    "recommendation": "Alignment verified -- proceed to gate-05-rig"
}

output_path = "pipelines/character-ralph/output/gate-05-alignment-result.json"
os.makedirs(os.path.dirname(output_path), exist_ok=True)
with open(output_path, "w") as f:
    json.dump(result, f, indent=2)
print(json.dumps(result, indent=2))
```

### Common Failure Modes and Remediation

| Symptom | Likely Cause | Fix |
|---------|-------------|-----|
| Skeleton taller than mesh | Scale not applied before rigging | Apply mesh scale in Blender, re-rig |
| Spine floating beside torso | Metarig placed at wrong origin | Delete armature, re-add metarig at mesh center |
| T-pose skeleton on A-pose mesh | Wrong template used | Use A-pose metarig template or adjust arm angle before generating rig |
| Legs outside leg volumes | Metarig hip width wrong | Adjust metarig leg bone positions to match mesh hip width, regenerate |
| Head bone above mesh | Metarig head bone height wrong | Scale metarig spine to match mesh torso height before generating |
| Asymmetric arms/legs | Mesh is asymmetric OR weight of metarig off-center | Check mesh for asymmetry; if mesh is symmetric, re-place metarig at exact world origin |

### Gate Result Format

Write to `output/gate-05-alignment-result.json`:
```json
{
  "stage": "5a-alignment",
  "gate": "gate-05-alignment",
  "result": "PASS|WARN|FAIL",
  "screenshots": {
    "front": "output/rigged/alignment-front.png",
    "side":  "output/rigged/alignment-side.png",
    "back":  "output/rigged/alignment-back.png",
    "top":   "output/rigged/alignment-top.png"
  },
  "checks": [
    { "name": "front_spine_aligned",  "passed": true,  "detail": "Spine chain runs through torso center" },
    { "name": "front_arms_inside",    "passed": true,  "detail": "Arm bones inside arm silhouette" },
    { "name": "front_legs_inside",    "passed": true,  "detail": "Leg bones inside leg silhouette" },
    { "name": "front_head_inside",    "passed": true,  "detail": "Head bone inside head volume" },
    { "name": "side_bones_centered",  "passed": true,  "detail": "Bones centered in mesh depth" },
    { "name": "back_symmetry",        "passed": true,  "detail": "L/R bones mirror correctly" },
    { "name": "top_arms_aligned",     "passed": true,  "detail": "Arm bones track into arm volumes" },
    { "name": "top_legs_aligned",     "passed": true,  "detail": "Leg bones track into leg volumes" },
    { "name": "scale_match",          "passed": true,  "detail": "Skeleton height matches mesh height" },
    { "name": "pose_match",           "passed": true,  "detail": "Skeleton and mesh are in matching pose" }
  ],
  "warnings": [],
  "blocking_errors": [],
  "recommendation": "Alignment verified -- proceed to gate-05-rig"
}
```
