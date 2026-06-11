# Backpressure Gate 5B: POST-RIG DEFORMATION

This gate runs AFTER auto-weighting and BEFORE animation work. It verifies that
the rig can pose the character without mesh distortion, vertex bleeding between
body regions, or mesh explosion. A rig that causes the torso/pants to deform
when arms move has arm bone weights bleeding across body regions and must be
corrected before animations are applied.

## PASS Criteria (ALL must pass)

### Numeric Checks
- [ ] Seated pose test: no vertex moves more than 150% of the relevant bone length from its rest position
- [ ] Arm raise test: viewport screenshot confirms torso/pants are NOT visibly deformed during UpperArm.L -90° rotation
- [ ] No mesh explosion: all vertices remain within 2x the character's rest-pose bounding box after posing
- [ ] Weight isolation: no vertex below hip height has weight > 0.1 in any arm bone vertex group

### Full-Body Visual Check (4 views)
- [ ] Visual 4-view check (front/side/back/top) saved to `output/rigged/deform-{view}.png`

### Close-Up Posed Bleed Scan (ALL zones must pass)
After applying the driving pose (seated, arms forward), zoom into each joint/contact zone and render from 2 angles. This catches subtle mesh bleeding that numeric checks miss — e.g., a small patch of torso vertices stretching toward the arm, or pants geometry pulled by hand bones.

**Required inspection zones (in driving pose):**
- [ ] **Left hand / left thigh** — zoom to posed Hand.L position, front + side: hand mesh must NOT drag pants vertices with it
- [ ] **Right hand / right thigh** — same for Hand.R
- [ ] **Left armpit (posed)** — zoom to posed UpperArm.L, front + side: no torso mesh stretching toward raised arm
- [ ] **Right armpit (posed)** — same for UpperArm.R
- [ ] **Hip crease (seated)** — zoom to Hips, front + side: seated leg bend must not create mesh artifacts (interpenetration OK, stretching NOT OK)
- [ ] **Left knee (bent)** — zoom to posed LowerLeg.L, front + side: knee bend should deform cleanly
- [ ] **Right knee (bent)** — same for LowerLeg.R
- [ ] **Chest/belly** — zoom to Chest bone, front + side: torso must maintain original volume (no inflation or collapse from arm/leg poses)

Each close-up saved to `output/rigged/deform-closeup-{zone}-{angle}.png` and logged in gate result.

**How to evaluate:**
- **PASS**: posed mesh deforms smoothly at the joint, no geometry from another body region is pulled
- **FAIL**: visible stretching of torso/pants when only arms moved, or hand geometry dragging a trail of vertices from the hip area
- **WARN**: minor interpenetration at deep bends (knee into thigh) — acceptable for game use but note it

- [ ] Gate result written to `output/gate-05b-deformation-result.json`

## WARN Criteria (log but don't block)
- [ ] Max displacement is 120-150% of bone length in seated pose (borderline -- note for review)
- [ ] One or two vertices below hip have arm weight 0.05-0.1 (minor bleed, low visual impact)
- [ ] Visual check screenshots are low resolution but readable
- [ ] Mesh has slightly unusual proportions making displacement thresholds less precise
- [ ] Missing `deform-back.png` but front/side/top pass visual inspection

## FAIL Criteria (block advancement -- go to Remediation)
- [ ] Any vertex moves more than 150% of bone length during seated pose
- [ ] Torso or pants mesh visibly deforms during arm raise (screenshot shows bulging/stretching away from body)
- [ ] Any vertex lands outside 2x rest-pose bounding box after posing (mesh explosion)
- [ ] Any vertex below hip height has arm bone weight > 0.1 (weight bleeding into pants region)
- [ ] All 4 deformation screenshots fail to render or are blank

## Validation Method

### Step 1: Apply Seated Driving Pose and Measure Displacement

```python
# Execute in blender-mcp via execute_blender_code
import bpy
import math
from mathutils import Vector

# Find the rig
rig = next((o for o in bpy.data.objects if o.type == 'ARMATURE'), None)
if not rig:
    print("ERROR: No armature found in scene")
else:
    bpy.context.view_layer.objects.active = rig
    bpy.ops.object.mode_set(mode='POSE')

    # Record rest-pose bone lengths for thresholds
    bone_lengths = {}
    for bone in rig.pose.bones:
        bone_lengths[bone.name] = bone.length

    # Clear any existing pose
    bpy.ops.pose.select_all(action='SELECT')
    bpy.ops.pose.transforms_clear()

    # Apply seated driving pose
    # UpperLeg: -90 degrees (X rotation, legs forward/down)
    # LowerLeg: +90 degrees (X rotation, shin forward)
    # UpperArm: -70 degrees (Z rotation, arms out)
    pose_targets = {
        'UpperLeg_L': ('rotation_euler', 0, math.radians(-90)),
        'UpperLeg_R': ('rotation_euler', 0, math.radians(-90)),
        'LowerLeg_L': ('rotation_euler', 0, math.radians(90)),
        'LowerLeg_R': ('rotation_euler', 0, math.radians(90)),
        'UpperArm_L': ('rotation_euler', 2, math.radians(-70)),
        'UpperArm_R': ('rotation_euler', 2, math.radians(70)),
    }

    for bone_name, (prop, axis, value) in pose_targets.items():
        # Try common naming variants
        for variant in [bone_name, bone_name.replace('_L', '.L').replace('_R', '.R'),
                        bone_name.lower(), 'DEF-' + bone_name]:
            pbone = rig.pose.bones.get(variant)
            if pbone:
                pbone.rotation_mode = 'XYZ'
                rot = list(pbone.rotation_euler)
                rot[axis] = value
                pbone.rotation_euler = rot
                print(f"Posed {variant}: axis={axis}, value={math.degrees(value):.1f}deg")
                break

    bpy.context.view_layer.update()
    print("Seated pose applied. Evaluating displacement...")
```

### Step 2: Measure Maximum Vertex Displacement Against Bone Length

```python
# Execute in blender-mcp via execute_blender_code
import bpy
from mathutils import Vector

rig  = next((o for o in bpy.data.objects if o.type == 'ARMATURE'), None)
mesh = next((o for o in bpy.data.objects if o.type == 'MESH'), None)
if not rig or not mesh:
    print("ERROR: Missing rig or mesh")
else:
    # Get rest-pose vertex positions (from the original mesh data in local space)
    rest_positions = {v.index: mesh.matrix_world @ v.co for v in mesh.data.vertices}

    # Force dependency graph evaluation to get posed positions
    depsgraph = bpy.context.evaluated_depsgraph_get()
    mesh_eval = mesh.evaluated_get(depsgraph)
    posed_positions = {v.index: mesh.matrix_world @ v.co for v in mesh_eval.data.vertices}

    max_displacement = 0.0
    worst_vert = -1
    for idx in rest_positions:
        disp = (posed_positions[idx] - rest_positions[idx]).length
        if disp > max_displacement:
            max_displacement = disp
            worst_vert = idx

    # Reference bone length: average of UpperLeg bones
    ref_length = 0.0
    ref_count = 0
    for bone in rig.pose.bones:
        if 'upperleg' in bone.name.lower() or 'thigh' in bone.name.lower():
            ref_length += bone.length
            ref_count += 1
    if ref_count:
        ref_length /= ref_count
    else:
        ref_length = 0.4  # Fallback: 40cm in Blender units

    ratio = max_displacement / ref_length if ref_length > 0 else 0
    print(f"Max displacement: {max_displacement*100:.2f}cm, bone_length_ref: {ref_length*100:.2f}cm")
    print(f"Displacement ratio: {ratio:.2f}x (threshold: 1.5x)")
    print(f"Worst vertex index: {worst_vert}")
    if ratio > 1.5:
        print("FAIL: displacement exceeds 150% of bone length")
    elif ratio > 1.2:
        print("WARN: displacement 120-150% of bone length")
    else:
        print("PASS: displacement within acceptable range")
```

### Step 3: Arm Raise Test with Viewport Screenshot

```python
# Execute in blender-mcp via execute_blender_code
import bpy, math, os

rig = next((o for o in bpy.data.objects if o.type == 'ARMATURE'), None)
bpy.context.view_layer.objects.active = rig
bpy.ops.object.mode_set(mode='POSE')

# Clear seated pose first
bpy.ops.pose.select_all(action='SELECT')
bpy.ops.pose.transforms_clear()

# Apply arm raise only: UpperArm.L rotated -90 degrees (arms forward)
for bone_name in ['UpperArm_L', 'UpperArm.L', 'upper_arm_L', 'DEF-upper_arm.L']:
    pbone = rig.pose.bones.get(bone_name)
    if pbone:
        pbone.rotation_mode = 'XYZ'
        pbone.rotation_euler[0] = math.radians(-90)
        print(f"Arm raised on {bone_name}")
        break

bpy.context.view_layer.update()

# Render front view screenshot
output_dir = "pipelines/character-ralph/output/rigged"
os.makedirs(output_dir, exist_ok=True)

scene = bpy.context.scene
scene.render.resolution_x = 800
scene.render.resolution_y = 800
scene.render.filepath = f"{output_dir}/deform-armraise-front.png"

for area in bpy.context.screen.areas:
    if area.type == 'VIEW_3D':
        for space in area.spaces:
            if space.type == 'VIEW_3D':
                space.region_3d.view_perspective = 'ORTHO'
                bpy.ops.view3d.view_axis(type='FRONT', align_active=False)
                break

bpy.ops.render.opengl(write_still=True)
print(f"Arm raise screenshot saved to {output_dir}/deform-armraise-front.png")

# Reset pose
bpy.ops.pose.select_all(action='SELECT')
bpy.ops.pose.transforms_clear()
print("Pose reset to rest position")
```

Then call `get_viewport_screenshot()` and visually verify that the torso/pants
mesh is NOT deformed (no bulging, no stretching, no geometry pulled toward the arm).

### Step 4: Bounding Box Explosion Check

```python
# Execute in blender-mcp via execute_blender_code
import bpy, math
from mathutils import Vector

rig  = next((o for o in bpy.data.objects if o.type == 'ARMATURE'), None)
mesh = next((o for o in bpy.data.objects if o.type == 'MESH'), None)

# Get rest bounding box extents
rest_bbox = [mesh.matrix_world @ Vector(c) for c in mesh.bound_box]
rest_min = Vector((min(v.x for v in rest_bbox), min(v.y for v in rest_bbox), min(v.z for v in rest_bbox)))
rest_max = Vector((max(v.x for v in rest_bbox), max(v.y for v in rest_bbox), max(v.z for v in rest_bbox)))
rest_size = rest_max - rest_min
threshold = 2.0  # 2x rest bounding box

# Apply full driving pose
bpy.context.view_layer.objects.active = rig
bpy.ops.object.mode_set(mode='POSE')
bpy.ops.pose.select_all(action='SELECT')
bpy.ops.pose.transforms_clear()

for bone_name in ['UpperLeg_L', 'UpperLeg.L', 'thigh.L']:
    pbone = rig.pose.bones.get(bone_name)
    if pbone:
        pbone.rotation_mode = 'XYZ'
        pbone.rotation_euler[0] = math.radians(-90)
        break

bpy.context.view_layer.update()

# Evaluate posed mesh
depsgraph = bpy.context.evaluated_depsgraph_get()
mesh_eval = mesh.evaluated_get(depsgraph)
posed_verts = [mesh.matrix_world @ v.co for v in mesh_eval.data.vertices]

# Check all posed verts are within 2x rest bbox
explosion_count = 0
for wco in posed_verts:
    if (abs(wco.x - (rest_min.x + rest_size.x/2)) > rest_size.x * threshold or
        abs(wco.y - (rest_min.y + rest_size.y/2)) > rest_size.y * threshold or
        abs(wco.z - (rest_min.z + rest_size.z/2)) > rest_size.z * threshold):
        explosion_count += 1

print(f"Vertices outside 2x bbox: {explosion_count} of {len(posed_verts)}")
if explosion_count > 0:
    print("FAIL: mesh explosion detected")
else:
    print("PASS: all vertices within 2x bounding box")

# Reset pose
bpy.ops.pose.select_all(action='SELECT')
bpy.ops.pose.transforms_clear()
```

### Step 5: Weight Isolation Check

```python
# Execute in blender-mcp via execute_blender_code
import bpy
from mathutils import Vector

mesh = next((o for o in bpy.data.objects if o.type == 'MESH'), None)

# Get hip Z from bounding box
world_bb = [mesh.matrix_world @ Vector(c) for c in mesh.bound_box]
min_z = min(v.z for v in world_bb)
max_z = max(v.z for v in world_bb)
hip_z = min_z + (max_z - min_z) * 0.40

# Find arm bone vertex groups
arm_group_names = [
    vg.name for vg in mesh.vertex_groups
    if any(kw in vg.name.lower() for kw in ['arm', 'hand', 'forearm', 'wrist', 'elbow', 'shoulder'])
]
print(f"Arm vertex groups found: {arm_group_names}")

bleed_verts = []
weight_threshold = 0.1

for v in mesh.data.vertices:
    wco = mesh.matrix_world @ v.co
    if wco.z > hip_z:
        continue  # Only check below-hip vertices
    for g in v.groups:
        vg_name = mesh.vertex_groups[g.group].name
        if vg_name in arm_group_names and g.weight > weight_threshold:
            bleed_verts.append({
                "vert_idx": v.index,
                "group": vg_name,
                "weight": round(g.weight, 4),
                "z": round(wco.z, 4)
            })

print(f"Below-hip vertices with arm weight > {weight_threshold}: {len(bleed_verts)}")
if bleed_verts:
    print("FAIL: arm weights bleeding into pants region")
    for item in bleed_verts[:10]:
        print(f"  vert {item['vert_idx']}: {item['group']} = {item['weight']}, z={item['z']}")
else:
    print("PASS: no arm weights below hip height")
```

### Step 6: Visual 4-View Screenshots (Rest Pose)

```python
# Execute in blender-mcp via execute_blender_code
import bpy, os

output_dir = "pipelines/character-ralph/output/rigged"
os.makedirs(output_dir, exist_ok=True)

scene = bpy.context.scene
scene.render.resolution_x = 800
scene.render.resolution_y = 800
scene.render.image_settings.file_format = 'PNG'

# Make armature visible with x-ray for bone visibility
for obj in bpy.data.objects:
    if obj.type == 'ARMATURE':
        obj.show_in_front = True
        obj.data.display_type = 'STICK'

views = [
    ('FRONT', 'deform-front.png'),
    ('RIGHT',  'deform-side.png'),
    ('BACK',  'deform-back.png'),
    ('TOP',   'deform-top.png'),
]

for view_type, filename in views:
    for area in bpy.context.screen.areas:
        if area.type == 'VIEW_3D':
            for space in area.spaces:
                if space.type == 'VIEW_3D':
                    space.region_3d.view_perspective = 'ORTHO'
                    bpy.ops.view3d.view_axis(type=view_type, align_active=False)
                    break
    scene.render.filepath = f"{output_dir}/{filename}"
    bpy.ops.render.opengl(write_still=True)
    print(f"Saved {filename}")
```

Then call `get_viewport_screenshot()` for each view and visually confirm:
- Body shape is intact from all 4 angles
- No unexpected geometry protrusions or distortions
- Skeleton (in stick/x-ray mode) is positioned within the mesh volume

### Step 7: Close-Up Posed Bleed Scan

With the driving pose still applied, zoom into each joint zone and capture close-ups.
This is the most critical visual check — it reveals subtle weight bleeding that the
numeric displacement check can miss.

```python
# Execute in blender-mcp via execute_blender_code
import bpy, math, os
from mathutils import Vector, Euler

rig = next((o for o in bpy.data.objects if o.type == 'ARMATURE'), None)
out_dir = "pipelines/character-ralph/output/rigged"
os.makedirs(out_dir, exist_ok=True)

# Re-apply driving pose for close-up inspection
bpy.context.view_layer.objects.active = rig
bpy.ops.object.mode_set(mode='POSE')
bpy.ops.pose.select_all(action='SELECT')
bpy.ops.pose.transforms_clear()

def pose_bone(name_part, rx=0, ry=0, rz=0):
    for pb in rig.pose.bones:
        if name_part.lower() in pb.name.lower():
            pb.rotation_mode = 'XYZ'
            pb.rotation_euler = (math.radians(rx), math.radians(ry), math.radians(rz))
            return

pose_bone("upperleg.l", rx=-90)
pose_bone("upperleg.r", rx=-90)
pose_bone("lowerleg.l", rx=90)
pose_bone("lowerleg.r", rx=90)
pose_bone("spine", rx=-15)
pose_bone("chest", rx=-10)
pose_bone("shoulder.l", rz=-15)
pose_bone("shoulder.r", rz=15)
pose_bone("upperarm.l", rx=-70, rz=15)
pose_bone("upperarm.r", rx=-70, rz=-15)
pose_bone("lowerarm.l", rx=-40)
pose_bone("lowerarm.r", rx=-40)
pose_bone("hand.l", rx=-10)
pose_bone("hand.r", rx=-10)
pose_bone("head", rx=20)
pose_bone("foot.l", rx=-35)
pose_bone("foot.r", rx=-35)

bpy.ops.object.mode_set(mode='OBJECT')
bpy.context.view_layer.update()

# Get POSED bone world positions for camera targeting
bone_pos = {}
for pb in rig.pose.bones:
    bone_pos[pb.name] = rig.matrix_world @ pb.head

# Define close-up zones using posed bone positions
zones = {}
for name in ["Hand.L", "Hand.R", "UpperArm.L", "UpperArm.R",
             "Hips", "LowerLeg.L", "LowerLeg.R", "Chest"]:
    if name in bone_pos:
        zones[name.lower().replace(".", "-")] = bone_pos[name]

# Fallback: if bone names don't match, use mesh bounds
if not zones:
    mesh = next((o for o in bpy.data.objects if o.type == 'MESH'), None)
    bb = [mesh.matrix_world @ Vector(c) for c in mesh.bound_box]
    cz = (max(v.z for v in bb) + min(v.z for v in bb)) / 2
    zones = {
        "hand-l": Vector((0.3, 0, cz - 0.2)),
        "hand-r": Vector((-0.3, 0, cz - 0.2)),
        "armpit-l": Vector((0.2, 0, cz + 0.3)),
        "armpit-r": Vector((-0.2, 0, cz + 0.3)),
        "hips": Vector((0, 0, cz)),
        "knee-l": Vector((0.1, 0, cz - 0.4)),
        "chest": Vector((0, 0, cz + 0.2)),
    }

angles = {
    "front": Euler((math.radians(90), 0, 0)).to_quaternion(),
    "side":  Euler((math.radians(90), 0, math.radians(-90))).to_quaternion(),
}

for zone_name, target in zones.items():
    for angle_name, rotation in angles.items():
        for area in bpy.context.screen.areas:
            if area.type == 'VIEW_3D':
                for space in area.spaces:
                    if space.type == 'VIEW_3D':
                        space.shading.type = 'SOLID'
                        space.shading.show_xray = False
                        r3d = space.region_3d
                        r3d.view_location = target
                        r3d.view_distance = 0.4  # tight zoom
                        r3d.view_rotation = rotation
                break

        filepath = os.path.join(out_dir, f"deform-closeup-{zone_name}-{angle_name}.png")
        bpy.context.scene.render.filepath = filepath
        bpy.context.scene.render.resolution_x = 600
        bpy.context.scene.render.resolution_y = 600
        bpy.ops.render.opengl(write_still=True)

print(f"Posed bleed scan: {len(zones) * len(angles)} close-up screenshots saved")
```

**Evaluation protocol for each close-up:**
1. Open the screenshot and examine the boundary between body regions
2. Look for: stretched triangles, vertices pulled away from their region, faces that form a "bridge" between two body parts
3. Compare left vs right side — asymmetric stretching indicates uneven weight distribution
4. The chest/belly zone should look the same volume as the rest pose — any inflation means torso weights are wrong
5. At knee bends, some interpenetration (thigh into calf) is acceptable for 90° bends — but NO stretching of unrelated regions

### Step 8: Write Gate Result

```python
# Execute in blender-mcp via execute_blender_code
import json, os

result = {
    "stage": "5b-deformation",
    "gate": "gate-05b-deformation",
    "result": "PASS",  # or "FAIL"
    "checks": [
        {
            "name": "seated_pose_displacement",
            "passed": True,
            "detail": "Max displacement 0.8x bone length (threshold: 1.5x)"
        },
        {
            "name": "arm_raise_no_distortion",
            "passed": True,
            "detail": "Torso unchanged during arm raise -- screenshot verified"
        },
        {
            "name": "no_mesh_explosion",
            "passed": True,
            "detail": "All verts within 2x bbox after seated pose"
        },
        {
            "name": "weight_isolation",
            "passed": True,
            "detail": "No arm weights below hip Z"
        },
        {
            "name": "visual_front",
            "passed": True,
            "detail": "deform-front.png saved, body shape intact"
        },
        {
            "name": "visual_side",
            "passed": True,
            "detail": "deform-side.png saved, body shape intact"
        }
    ],
    "warnings": [],
    "blocking_errors": [],
    "recommendation": "Deformation verified -- proceed to animations"
}

output_path = "pipelines/character-ralph/output/gate-05b-deformation-result.json"
os.makedirs(os.path.dirname(output_path), exist_ok=True)
with open(output_path, "w") as f:
    json.dump(result, f, indent=2)
print(json.dumps(result, indent=2))
```

## Remediation if FAIL

### Mesh Split (Recommended for Lower Body Bleeding)

If the deformation failure is caused by lower-body bleeding (torso/pants vertices being pulled by arm bones during driving pose), the recommended fix is the **mesh split approach**:

1. Return to Stage 4 and ensure `character-split.glb` contains separate body-region objects (torso, arm_L, arm_R, legs, head)
2. Re-rig by parenting all separate mesh objects to the armature with Automatic Weights
3. Because each mesh object has independent vertex groups, arm weights CANNOT bleed into leg/pants objects
4. Re-run this gate — cross-region bleeding should be impossible with separate objects

This approach is more reliable than weight cleaning or hybrid baking because it eliminates the possibility of cross-region weight bleeding at the mesh-object level, AND prevents geometric intersection between hands and thighs in the seated driving pose.

### If arm weights bleed into pants (weight_isolation FAIL)

```python
# Execute in blender-mcp via execute_blender_code
import bpy
from mathutils import Vector

mesh = next((o for o in bpy.data.objects if o.type == 'MESH'), None)
bpy.context.view_layer.objects.active = mesh

world_bb = [mesh.matrix_world @ Vector(c) for c in mesh.bound_box]
min_z = min(v.z for v in world_bb)
max_z = max(v.z for v in world_bb)
hip_z = min_z + (max_z - min_z) * 0.40

arm_group_names = [
    vg.name for vg in mesh.vertex_groups
    if any(kw in vg.name.lower() for kw in ['arm', 'hand', 'forearm', 'wrist', 'elbow', 'shoulder'])
]

cleaned = 0
for v in mesh.data.vertices:
    wco = mesh.matrix_world @ v.co
    if wco.z > hip_z:
        continue
    for g in v.groups:
        vg_name = mesh.vertex_groups[g.group].name
        if vg_name in arm_group_names and g.weight > 0.0:
            mesh.vertex_groups[g.group].remove([v.index])
            cleaned += 1

mesh.data.update()
print(f"Removed arm weights from {cleaned} below-hip vertex assignments")
print("Re-run weight_isolation check to confirm fix")
```

### If seated pose displacement FAILS or mesh explodes

The rig auto-weights are unusable. Two options:
1. **Go back to gate-04b**: the mesh may still be a single connected island. Physically cut the arms from the torso mesh, re-export `character-clean.glb`, and redo rigging.
2. **Redo auto-weights with envelope fallback**: delete the armature modifier, re-add it with `Envelope Weights` instead of `Automatic Weights`, then refine by hand.

### Common Failure Modes and Remediation

| Symptom | Likely Cause | Fix |
|---------|-------------|-----|
| Torso deforms when arm moves | Arm weights bleeding across mesh | Return to Stage 4, ensure mesh split into separate body objects, re-rig |
| Vertices explode during seated pose | Auto-weight assigned wrong bone influence to torso | Redo auto-weights with separate mesh objects; check each object's weights |
| Displacement > 1.5x bone length | Mesh still fused to arm (single island) | Return to gate-04b, physically separate arms into distinct objects |
| Arm bone weights found in pants | Single-island mesh caused weight bleed | Return to Stage 4 mesh split, ensure arms and legs are separate objects, re-rig |

### Gate Result Format

Write to `output/gate-05b-deformation-result.json`:
```json
{
  "stage": "5b-deformation",
  "gate": "gate-05b-deformation",
  "result": "PASS|FAIL",
  "checks": [
    {"name": "seated_pose_displacement", "passed": true, "detail": "Max displacement 0.8x bone length"},
    {"name": "arm_raise_no_distortion",  "passed": true, "detail": "Torso unchanged during arm raise"},
    {"name": "no_mesh_explosion",        "passed": true, "detail": "All verts within 2x bbox"},
    {"name": "weight_isolation",         "passed": true, "detail": "No arm weights below hip Z"},
    {"name": "visual_front",             "passed": true, "detail": "screenshot saved"},
    {"name": "visual_side",              "passed": true, "detail": "screenshot saved"}
  ],
  "warnings": [],
  "blocking_errors": [],
  "recommendation": "Deformation verified -- proceed to animations"
}
```
