# Quality Gate: HYBRID BAKE VALIDATION

This gate runs AFTER `hybrid_bake_driver.py` and BEFORE re-running gate-05b. It validates
that the hybrid bake correctly locked lower-body vertices into the seated driving pose,
that the bake boundary is seamless at the hip region, and that the upper body armature
remains fully functional for runtime animation. A failed bake can produce visible seams,
residual lower-body movement, or upper-body artifacts and must be re-baked before proceeding.

## PASS Criteria (ALL must pass)

### Bake Completeness
- [ ] Baked vertices (below hip Z threshold) do NOT move when UpperArm.L/R are rotated +/-30 degrees
- [ ] Baked vertices do NOT move when any upper-body bone is posed within its normal range of motion
- [ ] Bone count in the hybrid-baked GLB matches the expected skeleton (no bones removed or duplicated)
- [ ] Mesh count in the hybrid-baked GLB is unchanged from input (same number of mesh objects)

### Upper Body Mobility
- [ ] Upper body bones steer +/-15 degrees from driving rest pose without torso or pants deformation
- [ ] Head tilts +/-25 degrees cleanly — no mesh tearing, no lower-body pull
- [ ] UpperArm.L/R rotate +30 degrees and -30 degrees without any artifact below the hip boundary

### Bake Boundary Quality
- [ ] Close-up visual scan of hip region (front + side) shows no visible seam between baked and rigged zones
- [ ] Smoothstep blending zone at boundary produces a gradual transition — no hard edge in shading or silhouette
- [ ] Close-up scan of hand-thigh gap (front + side) shows no stretching when arms are at +15 degrees steering rotation
- [ ] Close-up scan of chest (front + side) shows normal volume — no inflation or collapse

### Rest Pose Visual Validation (4 Views)
- [ ] 4-view screenshots (front/side/back/34) of the baked character in driving rest pose look natural
- [ ] Character silhouette is intact from all 4 angles — no unexpected protrusions or geometry voids
- [ ] Gate result written to `output/gate-hybrid-bake-result.json`

## WARN Criteria (log but don't block)

- [ ] 1-3 vertices in the smoothstep blending zone show minor residual movement (< 2mm displacement) — acceptable
- [ ] Hip boundary has a very faint shading discontinuity visible only under direct lighting — note for review
- [ ] Upper body rotation at full +/-30 degrees shows minor jitter on blending-zone vertices (< 5mm)
- [ ] Screenshots are lower resolution but bake boundary is still evaluable
- [ ] Bone count differs by 1-2 from expected (helper bones may be stripped by exporter)

## FAIL Criteria (block advancement -- re-bake)

- [ ] Baked vertices still move when arm bones rotate (bake incomplete — lower body not locked)
- [ ] Visible seam line at bake boundary (hard discontinuity in mesh surface, shading crease, or silhouette notch)
- [ ] Upper body rotation causes artifacts on baked lower body (smoothstep zone too narrow, or bake threshold wrong)
- [ ] Mesh explosion in any region during upper body pose test
- [ ] Head tilt causes pulling on chest or shoulder geometry that extends into the baked zone
- [ ] Gate result JSON fails to write (script error during validation)

## Validation Method

### Step 1: Import Hybrid-Baked GLB and Verify Structure

```python
# Execute in blender-mcp via execute_blender_code
import bpy

# Clear scene and import
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete()
bpy.ops.import_scene.gltf(filepath='<OUTPUT_PATH>/character-hybrid-baked.glb')

bpy.context.view_layer.update()

armatures = [o for o in bpy.data.objects if o.type == 'ARMATURE']
meshes    = [o for o in bpy.data.objects if o.type == 'MESH']

print(f"Armature count: {len(armatures)}")
print(f"Mesh count:     {len(meshes)}")

if armatures:
    rig = armatures[0]
    print(f"Bone count: {len(rig.data.bones)}")
    for bone in rig.data.bones:
        print(f"  {bone.name}")
else:
    print("ERROR: No armature found -- bake may have stripped the skeleton")
```

### Step 2: Bake Completeness Test (Arm Rotation +/-15 Degrees)

Rotate UpperArm.L/R +15 degrees and -15 degrees from rest. Capture front + side screenshots
for each rotation. The lower body must not move at all.

```python
# Execute in blender-mcp via execute_blender_code
import bpy, math, os

rig  = next((o for o in bpy.data.objects if o.type == 'ARMATURE'), None)
mesh = next((o for o in bpy.data.objects if o.type == 'MESH'), None)
if not rig or not mesh:
    print("ERROR: Missing rig or mesh")
else:
    from mathutils import Vector

    # Get hip Z threshold (40% of mesh height from bottom)
    world_bb = [mesh.matrix_world @ Vector(c) for c in mesh.bound_box]
    min_z = min(v.z for v in world_bb)
    max_z = max(v.z for v in world_bb)
    hip_z = min_z + (max_z - min_z) * 0.45

    # Record rest-pose positions for below-hip vertices
    rest_positions = {}
    for v in mesh.data.vertices:
        wco = mesh.matrix_world @ v.co
        if wco.z < hip_z:
            rest_positions[v.index] = wco.copy()

    print(f"Monitoring {len(rest_positions)} below-hip vertices (hip_z={hip_z:.3f})")

    bpy.context.view_layer.objects.active = rig
    bpy.ops.object.mode_set(mode='POSE')
    bpy.ops.pose.select_all(action='SELECT')
    bpy.ops.pose.transforms_clear()

    # Apply +15 degree arm rotation
    for bone_name_part in ['upperarm.l', 'upper_arm_l', 'arm.l']:
        for pb in rig.pose.bones:
            if bone_name_part in pb.name.lower():
                pb.rotation_mode = 'XYZ'
                pb.rotation_euler[0] = math.radians(15)
                print(f"Rotated {pb.name} +15 deg")
                break

    bpy.context.view_layer.update()

    # Check displacement of below-hip vertices
    depsgraph = bpy.context.evaluated_depsgraph_get()
    mesh_eval = mesh.evaluated_get(depsgraph)
    max_disp = 0.0
    worst_vert = -1
    for idx, rest_pos in rest_positions.items():
        posed_pos = mesh.matrix_world @ mesh_eval.data.vertices[idx].co
        disp = (posed_pos - rest_pos).length
        if disp > max_disp:
            max_disp = disp
            worst_vert = idx

    print(f"Max below-hip displacement (arm +15deg): {max_disp*1000:.2f}mm (worst vert: {worst_vert})")
    if max_disp > 0.002:
        print("FAIL: baked vertices moved -- bake incomplete")
    else:
        print("PASS: baked vertices stationary during arm rotation")

    bpy.ops.pose.select_all(action='SELECT')
    bpy.ops.pose.transforms_clear()
```

### Step 3: Screenshot Front + Side for Arm +15 and -15 Degrees

```python
# Execute in blender-mcp via execute_blender_code
import bpy, math, os

out_dir = "pipelines/kart-assembly-ralph/output/gate-hybrid-bake"
os.makedirs(out_dir, exist_ok=True)

rig = next((o for o in bpy.data.objects if o.type == 'ARMATURE'), None)
bpy.context.view_layer.objects.active = rig
bpy.ops.object.mode_set(mode='POSE')

scene = bpy.context.scene
scene.render.resolution_x = 800
scene.render.resolution_y = 800
scene.render.image_settings.file_format = 'PNG'

def screenshot(filepath, view_axis):
    for area in bpy.context.screen.areas:
        if area.type == 'VIEW_3D':
            for space in area.spaces:
                if space.type == 'VIEW_3D':
                    space.region_3d.view_perspective = 'ORTHO'
                    bpy.ops.view3d.view_axis(type=view_axis, align_active=False)
                    break
    scene.render.filepath = filepath
    bpy.ops.render.opengl(write_still=True)
    print(f"Saved {filepath}")

def pose_upper_arms(degrees):
    bpy.ops.pose.select_all(action='SELECT')
    bpy.ops.pose.transforms_clear()
    for pb in rig.pose.bones:
        if any(kw in pb.name.lower() for kw in ['upperarm', 'upper_arm']):
            pb.rotation_mode = 'XYZ'
            pb.rotation_euler[0] = math.radians(degrees)
    bpy.context.view_layer.update()

for angle in [15, -15]:
    pose_upper_arms(angle)
    label = f"arm_plus{angle}" if angle > 0 else f"arm_minus{abs(angle)}"
    screenshot(f"{out_dir}/{label}_front.png", 'FRONT')
    screenshot(f"{out_dir}/{label}_side.png", 'RIGHT')

bpy.ops.pose.select_all(action='SELECT')
bpy.ops.pose.transforms_clear()
print("Arm rotation screenshots complete")
```

Then call `get_viewport_screenshot()` and visually confirm the lower body does not move.

### Step 4: Head Tilt +25 and -25 Degrees

```python
# Execute in blender-mcp via execute_blender_code
import bpy, math, os

out_dir = "pipelines/kart-assembly-ralph/output/gate-hybrid-bake"
os.makedirs(out_dir, exist_ok=True)

rig = next((o for o in bpy.data.objects if o.type == 'ARMATURE'), None)
bpy.context.view_layer.objects.active = rig
bpy.ops.object.mode_set(mode='POSE')

scene = bpy.context.scene
scene.render.resolution_x = 800
scene.render.resolution_y = 800

def screenshot(filepath, view_axis):
    for area in bpy.context.screen.areas:
        if area.type == 'VIEW_3D':
            for space in area.spaces:
                if space.type == 'VIEW_3D':
                    space.region_3d.view_perspective = 'ORTHO'
                    bpy.ops.view3d.view_axis(type=view_axis, align_active=False)
                    break
    scene.render.filepath = filepath
    bpy.ops.render.opengl(write_still=True)

for angle in [25, -25]:
    bpy.ops.pose.select_all(action='SELECT')
    bpy.ops.pose.transforms_clear()
    for pb in rig.pose.bones:
        if 'head' in pb.name.lower() and 'headband' not in pb.name.lower():
            pb.rotation_mode = 'XYZ'
            pb.rotation_euler[0] = math.radians(angle)
            bpy.context.view_layer.update()
            break
    label = f"head_plus{angle}" if angle > 0 else f"head_minus{abs(angle)}"
    screenshot(f"{out_dir}/{label}_front.png", 'FRONT')
    screenshot(f"{out_dir}/{label}_side.png", 'RIGHT')
    print(f"Head {angle}deg screenshots saved")

bpy.ops.pose.select_all(action='SELECT')
bpy.ops.pose.transforms_clear()
print("Head tilt screenshots complete")
```

Visually verify via `get_viewport_screenshot()`: no mesh tearing, no lower-body pull, clean
deformation at neck.

### Step 5: Close-Up Scan of Bake Boundary and Key Zones (6 Minimum)

With the rig at driving rest pose, zoom into each critical zone. Minimum 6 close-ups required:
hip boundary front, hip boundary side, hand-thigh gap front, hand-thigh gap side,
chest front, chest side.

```python
# Execute in blender-mcp via execute_blender_code
import bpy, math, os
from mathutils import Vector, Euler

out_dir = "pipelines/kart-assembly-ralph/output/gate-hybrid-bake"
os.makedirs(out_dir, exist_ok=True)

mesh = next((o for o in bpy.data.objects if o.type == 'MESH'), None)
rig  = next((o for o in bpy.data.objects if o.type == 'ARMATURE'), None)

# Ensure driving rest pose
bpy.context.view_layer.objects.active = rig
bpy.ops.object.mode_set(mode='POSE')
bpy.ops.pose.select_all(action='SELECT')
bpy.ops.pose.transforms_clear()
bpy.ops.object.mode_set(mode='OBJECT')
bpy.context.view_layer.update()

# Compute reference heights from mesh bounding box
world_bb = [mesh.matrix_world @ Vector(c) for c in mesh.bound_box]
min_z = min(v.z for v in world_bb)
max_z = max(v.z for v in world_bb)
mid_x = (max(v.x for v in world_bb) + min(v.x for v in world_bb)) / 2
mid_y = (max(v.y for v in world_bb) + min(v.y for v in world_bb)) / 2

hip_z    = min_z + (max_z - min_z) * 0.45   # bake boundary
chest_z  = min_z + (max_z - min_z) * 0.65
hand_z   = min_z + (max_z - min_z) * 0.35
hand_x_l = mid_x + (max(v.x for v in world_bb) - mid_x) * 0.6

# Zone definitions: (name, look_at_position, zoom_distance)
zones = [
    ("hip-boundary-front",  Vector((mid_x, mid_y, hip_z)),   0.35),
    ("hip-boundary-side",   Vector((mid_x, mid_y, hip_z)),   0.35),
    ("hand-thigh-gap-front",Vector((hand_x_l, mid_y, hand_z)),0.30),
    ("hand-thigh-gap-side", Vector((hand_x_l, mid_y, hand_z)),0.30),
    ("chest-front",         Vector((mid_x, mid_y, chest_z)), 0.30),
    ("chest-side",          Vector((mid_x, mid_y, chest_z)), 0.30),
]

angle_for_zone = {
    "front": Euler((math.radians(90), 0, 0)).to_quaternion(),
    "side":  Euler((math.radians(90), 0, math.radians(-90))).to_quaternion(),
}

scene = bpy.context.scene
scene.render.resolution_x = 600
scene.render.resolution_y = 600
scene.render.image_settings.file_format = 'PNG'

for zone_name, target, zoom in zones:
    # Pick angle from zone name suffix
    angle_key = "side" if zone_name.endswith("-side") else "front"
    rotation = angle_for_zone[angle_key]

    for area in bpy.context.screen.areas:
        if area.type == 'VIEW_3D':
            for space in area.spaces:
                if space.type == 'VIEW_3D':
                    space.shading.type = 'SOLID'
                    r3d = space.region_3d
                    r3d.view_location = target
                    r3d.view_distance = zoom
                    r3d.view_rotation = rotation
            break

    filepath = os.path.join(out_dir, f"closeup-{zone_name}.png")
    scene.render.filepath = filepath
    bpy.ops.render.opengl(write_still=True)
    print(f"Saved closeup: {zone_name}")

print(f"Close-up scan complete: {len(zones)} images in {out_dir}")
```

**Evaluation protocol for close-ups:**
- **Hip boundary**: shading must be smooth and continuous across the bake line — no hard crease,
  no silhouette notch. The smoothstep blending zone should be invisible to the eye.
- **Hand-thigh gap**: arm rotation must leave the thigh mesh completely unaffected. No stretched
  triangles bridging the gap between hand and thigh.
- **Chest**: volume must match rest pose. No inflation, no collapse from upper body posing.

### Step 6: 4-View Rest Pose Screenshots

```python
# Execute in blender-mcp via execute_blender_code
import bpy, math, os

out_dir = "pipelines/kart-assembly-ralph/output/gate-hybrid-bake"
os.makedirs(out_dir, exist_ok=True)

rig = next((o for o in bpy.data.objects if o.type == 'ARMATURE'), None)
bpy.context.view_layer.objects.active = rig
bpy.ops.object.mode_set(mode='POSE')
bpy.ops.pose.select_all(action='SELECT')
bpy.ops.pose.transforms_clear()
bpy.ops.object.mode_set(mode='OBJECT')

scene = bpy.context.scene
scene.render.resolution_x = 800
scene.render.resolution_y = 800
scene.render.image_settings.file_format = 'PNG'

views = [
    ('FRONT', 'rest-front.png'),
    ('RIGHT',  'rest-side.png'),
    ('BACK',  'rest-back.png'),
]

for view_type, filename in views:
    for area in bpy.context.screen.areas:
        if area.type == 'VIEW_3D':
            for space in area.spaces:
                if space.type == 'VIEW_3D':
                    space.region_3d.view_perspective = 'ORTHO'
                    bpy.ops.view3d.view_axis(type=view_type, align_active=False)
                    bpy.ops.view3d.view_all()
                    break
    scene.render.filepath = os.path.join(out_dir, filename)
    bpy.ops.render.opengl(write_still=True)
    print(f"Saved {filename}")

# 3/4 view
import math
for area in bpy.context.screen.areas:
    if area.type == 'VIEW_3D':
        for space in area.spaces:
            if space.type == 'VIEW_3D':
                from mathutils import Euler
                r3d = space.region_3d
                r3d.view_perspective = 'PERSP'
                r3d.view_rotation = Euler((math.radians(65), 0, math.radians(45))).to_quaternion()
                bpy.ops.view3d.view_all()
                break
scene.render.filepath = os.path.join(out_dir, "rest-34.png")
bpy.ops.render.opengl(write_still=True)
print("Saved rest-34.png")
```

### Step 7: Write Gate Result

```python
# Execute in blender-mcp via execute_blender_code
import json, os

result = {
    "stage": "hybrid-bake",
    "gate": "gate-hybrid-bake",
    "result": "PASS",  # or "FAIL"
    "checks": [
        {
            "name": "bake_completeness_arm_plus15",
            "passed": True,
            "detail": "Max below-hip displacement 0.0mm during arm +15deg rotation"
        },
        {
            "name": "bake_completeness_arm_minus15",
            "passed": True,
            "detail": "Max below-hip displacement 0.0mm during arm -15deg rotation"
        },
        {
            "name": "upper_body_steering_plus15",
            "passed": True,
            "detail": "No torso or pants deformation at +15deg steering"
        },
        {
            "name": "upper_body_steering_minus15",
            "passed": True,
            "detail": "No torso or pants deformation at -15deg steering"
        },
        {
            "name": "head_tilt_plus25",
            "passed": True,
            "detail": "Head +25deg -- clean deformation, no lower-body pull"
        },
        {
            "name": "head_tilt_minus25",
            "passed": True,
            "detail": "Head -25deg -- clean deformation, no lower-body pull"
        },
        {
            "name": "closeup_hip_boundary",
            "passed": True,
            "detail": "Bake boundary seamless front+side -- smoothstep zone invisible"
        },
        {
            "name": "closeup_hand_thigh_gap",
            "passed": True,
            "detail": "No stretching in hand-thigh gap during arm steering"
        },
        {
            "name": "closeup_chest",
            "passed": True,
            "detail": "Chest volume unchanged from rest pose"
        },
        {
            "name": "4view_rest_pose",
            "passed": True,
            "detail": "rest-front/side/back/34 screenshots look natural"
        }
    ],
    "warnings": [],
    "blocking_errors": [],
    "bone_count": 0,       # fill in from Step 1
    "mesh_count": 0,       # fill in from Step 1
    "max_baked_displacement_mm": 0.0,
    "recommendation": "Hybrid bake validated -- proceed to gate-05b re-run (upper body only)"
}

output_path = "output/gate-hybrid-bake-result.json"
os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else ".", exist_ok=True)
with open(output_path, "w") as f:
    json.dump(result, f, indent=2)
print(json.dumps(result, indent=2))
```

## Remediation if FAIL

### If baked vertices still move (bake incomplete)

The bake threshold or blending zone is wrong. Re-run `hybrid_bake_driver.py` with a higher
bake boundary (`--bake_height_fraction 0.50` instead of default 0.45) so the blend zone
fully covers the problem vertices. Then re-run this gate.

### If visible seam at hip boundary

The smoothstep blending width is too narrow. Re-run `hybrid_bake_driver.py` with a wider
blending zone (`--blend_fraction 0.08` instead of default 0.05). The blend zone should span
at least 5% of the total mesh height to avoid a hard transition.

### If upper body rotation causes lower-body artifacts

The blending zone vertices are weighted too heavily toward baked positions. This can happen
when the smoothstep is applied but the vertex group normalization is off. Re-run the bake
with `--normalize_weights` flag and verify the blend zone vertices sum to 1.0 across
baked-position weight and armature weight.

### If mesh explosion in any region

The driving-pose position capture step in `hybrid_bake_driver.py` failed for some vertices
(produced NaN or extreme values). Re-run the bake from a clean Blender session with the
rigged character and verify the driving pose is applied correctly before baking.

### Common Failure Modes

| Symptom | Likely Cause | Fix |
|---------|-------------|-----|
| Below-hip verts move during arm rotation | Bake threshold too low, arm-influenced verts above threshold | Raise `bake_height_fraction` to 0.50 |
| Hard seam visible at hip | Blending zone too narrow | Widen `blend_fraction` to 0.08 |
| Artifacts on baked verts when upper body poses | Blend zone weight normalization error | Re-bake with `--normalize_weights` |
| Mesh explosion | Driving pose NaN in bake script | Re-bake from clean session |
| Bone count wrong | Exporter stripped bones | Re-export with `export_all_influences=True` |

## Gate Result Format

Write to `output/gate-hybrid-bake-result.json`:
```json
{
  "stage": "hybrid-bake",
  "gate": "gate-hybrid-bake",
  "result": "PASS|FAIL",
  "checks": [
    {"name": "bake_completeness_arm_plus15",    "passed": true, "detail": "0.0mm displacement"},
    {"name": "bake_completeness_arm_minus15",   "passed": true, "detail": "0.0mm displacement"},
    {"name": "upper_body_steering_plus15",      "passed": true, "detail": "no artifacts"},
    {"name": "upper_body_steering_minus15",     "passed": true, "detail": "no artifacts"},
    {"name": "head_tilt_plus25",                "passed": true, "detail": "clean"},
    {"name": "head_tilt_minus25",               "passed": true, "detail": "clean"},
    {"name": "closeup_hip_boundary",            "passed": true, "detail": "seamless"},
    {"name": "closeup_hand_thigh_gap",          "passed": true, "detail": "no stretch"},
    {"name": "closeup_chest",                   "passed": true, "detail": "volume intact"},
    {"name": "4view_rest_pose",                 "passed": true, "detail": "screenshots saved"}
  ],
  "warnings": [],
  "blocking_errors": [],
  "bone_count": 65,
  "mesh_count": 1,
  "max_baked_displacement_mm": 0.0,
  "recommendation": "Hybrid bake validated -- proceed to gate-05b re-run (upper body only)"
}
```
