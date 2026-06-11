# Backpressure Gate 4B: PRE-RIG MESH SEPARATION

This gate runs AFTER Stage 4 mesh split (via `mesh_split_by_region.py`) and BEFORE
Stage 5 (rigging). It verifies that the character GLB contains separate body-region
mesh objects so that auto-weighting cannot cause weight bleeding between regions.
Separate mesh objects are the primary defense against hand-thigh intersection in
the seated kart driving pose.

## Input

The gate validates `output/3d/character-split.glb` which must contain multiple
mesh objects produced by `scripts/mesh_split_by_region.py`.

## Split Algorithm Reference

The split script (`mesh_split_by_region.py`) uses these boundaries:

1. **Head**: horizontal cut at 83% of character height
2. **Arms**: vertical cuts at armpit X width (torso outer edge at 58-65% height),
   only above armpit Z height (52% of character height). Arms are extracted FIRST.
3. **Legs**: 45-degree angled cut from hip center (42% height) outward, capped at
   armpit X width so it doesn't reach arm territory
4. **Torso**: everything remaining after head, arms, and legs are extracted

Key details:
- Arm X boundary is measured at the narrowest torso point at armpit height (58-65% Z)
- Arm Z lower bound is at 52% height (armpit level) — below this, outer-X faces are hips, not arms
- Leg 45-degree angle means: at center X, cut at 42% height; moving outward, cut rises 1:1
- The leg angle is capped at the armpit X distance to avoid intersecting with arm territory

## PASS Criteria (ALL must pass)

### Object Structure Checks
- [ ] GLB contains at least 5 named mesh objects: `body_head`, `body_torso`, `body_arm_L`, `body_arm_R`, `body_legs`
- [ ] Each object has >100 vertices (no empty or trivial objects)
- [ ] `body_arm_L` and `body_arm_R` each have >300 vertices (full arm including hand)
- [ ] `body_legs` has >1500 vertices (both legs including feet)

### Region Boundary Checks
- [ ] Arm objects have NO vertices below armpit Z height (52% of character height) — arms don't extend into hip/leg territory
- [ ] Leg object has NO vertices above hip_center_z + armpit_x_distance — legs don't extend into shoulder territory
- [ ] No arm object vertex is within 2cm (X distance) of any leg object vertex — hand-thigh clearance

### Close-Up Visual Validation (blender-mcp screenshots)
Color each region with distinct material colors and take screenshots:
- [ ] **Full body front** — all 5 regions visible with distinct colors, no color mixing
- [ ] **Left shoulder close-up** — arm (blue) starts at armpit, torso (orange) keeps shoulder
- [ ] **Right shoulder close-up** — same for right side
- [ ] **Hip front close-up** — torso (orange) at belt, legs (grey) below, no arm color on legs
- [ ] **Hip side close-up** — clean torso-to-leg boundary, no arm fragments

Each screenshot saved to `output/3d/split-{view}.png`.

- [ ] Gate result written to `output/gate-04b-mesh-separation-result.json`

## WARN Criteria (log but don't block)
- [ ] Arm/torso vertex count ratio is unusual (arms < 5% or > 40% of total — may indicate bad split)
- [ ] Mesh has additional objects beyond the 5 expected (accessories, debris — acceptable)
- [ ] Minor asymmetry between arm_L and arm_R vertex counts (>2x difference)

## FAIL Criteria (block advancement — return to Stage 4 mesh split)
- [ ] GLB contains fewer than 3 mesh objects (split did not produce separate regions)
- [ ] Any arm object has vertices below hip height (arm region bleeds into legs)
- [ ] Arm and leg objects have vertices within 1cm of each other (hand-thigh overlap risk)
- [ ] Any expected region object is missing or has <50 vertices
- [ ] Visual screenshots show color mixing between regions (faces assigned to wrong region)

## Validation Method

### Step 1: Import and Identify Regions

Use blender-mcp to load the mesh and run bmesh island detection.

```python
# Execute in blender-mcp via execute_blender_code
import bpy
import bmesh
from mathutils import Vector

# Clear scene and import the character mesh
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete()
bpy.ops.import_scene.gltf(
    filepath='pipelines/character-ralph/output/3d/character.glb'
)

# Identify the main mesh object
mesh_obj = next((o for o in bpy.data.objects if o.type == 'MESH'), None)
if not mesh_obj:
    print("ERROR: No mesh found after import")
else:
    bb = mesh_obj.bound_box
    world_bb = [mesh_obj.matrix_world @ Vector(c) for c in bb]
    min_z = min(v.z for v in world_bb)
    max_z = max(v.z for v in world_bb)
    max_x = max(abs(v.x) for v in world_bb)
    print(f"Mesh bounds: min_z={min_z:.3f}, max_z={max_z:.3f}, max_x={max_x:.3f}")
    # Hip height: ~40% up from feet
    hip_z = min_z + (max_z - min_z) * 0.40
    # Shoulder width: ~60% of half bounding box X
    shoulder_x = max_x * 0.60
    print(f"Derived: hip_z={hip_z:.3f}, shoulder_x={shoulder_x:.3f}")
```

### Step 2: Arm-Body Separation Check (bmesh island detection)

```python
# Execute in blender-mcp via execute_blender_code
import bpy
import bmesh
from mathutils import Vector

mesh_obj = next((o for o in bpy.data.objects if o.type == 'MESH'), None)
bpy.context.view_layer.objects.active = mesh_obj

# Build bmesh from the mesh
bm = bmesh.new()
bm.from_mesh(mesh_obj.data)
bm.verts.ensure_lookup_table()
bm.edges.ensure_lookup_table()
bm.faces.ensure_lookup_table()

# Compute bounds in world space
world_bb = [mesh_obj.matrix_world @ Vector(c) for c in mesh_obj.bound_box]
min_z = min(v.z for v in world_bb)
max_z = max(v.z for v in world_bb)
max_x = max(abs(v.x) for v in world_bb)

hip_z     = min_z + (max_z - min_z) * 0.40
chest_z   = min_z + (max_z - min_z) * 0.55
shoulder_x = max_x * 0.55

# Tag arm verts: X beyond shoulder_x, Z between hip and head (above hip, below top)
arm_verts = set()
torso_verts = set()
leg_verts = set()

for v in bm.verts:
    wco = mesh_obj.matrix_world @ v.co
    if abs(wco.x) > shoulder_x and hip_z < wco.z < max_z:
        arm_verts.add(v.index)
    elif wco.z > hip_z:
        torso_verts.add(v.index)
    else:
        leg_verts.add(v.index)

print(f"Arm verts: {len(arm_verts)}, Torso verts: {len(torso_verts)}, Leg verts: {len(leg_verts)}")

# Check for bridging faces: faces that have vertices in BOTH arm and torso regions
bridging_arm_torso = 0
for face in bm.faces:
    face_vert_idxs = {v.index for v in face.verts}
    in_arm   = face_vert_idxs & arm_verts
    in_torso = face_vert_idxs & torso_verts
    if in_arm and in_torso:
        bridging_arm_torso += 1

print(f"Bridging faces (arm<->torso): {bridging_arm_torso}")

# Check for bridging faces: arm verts touching leg/pants verts
bridging_arm_leg = 0
for face in bm.faces:
    face_vert_idxs = {v.index for v in face.verts}
    in_arm = face_vert_idxs & arm_verts
    in_leg = face_vert_idxs & leg_verts
    if in_arm and in_leg:
        bridging_arm_leg += 1

print(f"Bridging faces (arm<->leg): {bridging_arm_leg}")
bm.free()
```

### Step 3: Hand-Leg Clearance Check

```python
# Execute in blender-mcp via execute_blender_code
import bpy
import bmesh
from mathutils import Vector

mesh_obj = next((o for o in bpy.data.objects if o.type == 'MESH'), None)
bm = bmesh.new()
bm.from_mesh(mesh_obj.data)
bm.verts.ensure_lookup_table()

world_bb = [mesh_obj.matrix_world @ Vector(c) for c in mesh_obj.bound_box]
min_z = min(v.z for v in world_bb)
max_z = max(v.z for v in world_bb)
max_x = max(abs(v.x) for v in world_bb)

hip_z      = min_z + (max_z - min_z) * 0.40
shoulder_x = max_x * 0.55

# Hand verts: arm region at the lowest Z in the arm zone
arm_verts_co = []
for v in bm.verts:
    wco = mesh_obj.matrix_world @ v.co
    if abs(wco.x) > shoulder_x and hip_z < wco.z < max_z:
        arm_verts_co.append(wco)

if arm_verts_co:
    hand_z_threshold = min(v.z for v in arm_verts_co) + (max_z - min_z) * 0.10
    hand_verts = [v for v in arm_verts_co if v.z <= hand_z_threshold]

    leg_verts_co = [
        mesh_obj.matrix_world @ v.co
        for v in bm.verts
        if (mesh_obj.matrix_world @ v.co).z <= hip_z
    ]

    if hand_verts and leg_verts_co:
        min_gap = float('inf')
        for hv in hand_verts:
            for lv in leg_verts_co:
                dist = (hv - lv).length
                if dist < min_gap:
                    min_gap = dist
        # Convert Blender meters to cm
        min_gap_cm = min_gap * 100
        print(f"Hand-leg minimum gap: {min_gap_cm:.2f}cm (threshold: 0.5cm)")
    else:
        print("Could not compute hand-leg gap: empty region")
else:
    print("No arm vertices detected in bounding box region")

bm.free()
```

### Step 4: Island Count After Hypothetical Separation

```python
# Execute in blender-mcp via execute_blender_code
import bpy
import bmesh
from mathutils import Vector

mesh_obj = next((o for o in bpy.data.objects if o.type == 'MESH'), None)
bm = bmesh.new()
bm.from_mesh(mesh_obj.data)
bm.verts.ensure_lookup_table()
bm.edges.ensure_lookup_table()
bm.faces.ensure_lookup_table()

world_bb = [mesh_obj.matrix_world @ Vector(c) for c in mesh_obj.bound_box]
min_z = min(v.z for v in world_bb)
max_z = max(v.z for v in world_bb)
max_x = max(abs(v.x) for v in world_bb)
hip_z      = min_z + (max_z - min_z) * 0.40
shoulder_x = max_x * 0.55

# Tag arm verts for hypothetical disconnection
arm_vert_set = set()
for v in bm.verts:
    wco = mesh_obj.matrix_world @ v.co
    if abs(wco.x) > shoulder_x and hip_z < wco.z < max_z:
        arm_vert_set.add(v.index)

# Delete bridging edges between arm and non-arm regions (in a copy)
edges_to_delete = []
for e in bm.edges:
    v_idxs = {v.index for v in e.verts}
    in_arm     = bool(v_idxs & arm_vert_set)
    in_non_arm = bool(v_idxs - arm_vert_set)
    if in_arm and in_non_arm:
        edges_to_delete.append(e)

bmesh.ops.delete(bm, geom=edges_to_delete, context='EDGES')

# Count connected islands
bm.verts.ensure_lookup_table()
visited = set()
islands = 0

def flood(v_idx):
    stack = [bm.verts[v_idx]]
    while stack:
        vert = stack.pop()
        if vert.index in visited:
            continue
        visited.add(vert.index)
        for edge in vert.link_edges:
            other = edge.other_vert(vert)
            if other.index not in visited:
                stack.append(other)

for v in bm.verts:
    if v.index not in visited:
        flood(v.index)
        islands += 1

print(f"Island count after arm separation: {islands} (expected >= 3: body, arm_L, arm_R)")
bm.free()
```

### Step 5: Close-Up Visual Bleed Scan

After the structural checks pass, perform a zoomed-in visual inspection of every
bleed-risk zone. This catches cases where geometry is technically on separate islands
but visually overlaps or nearly touches, which will cause weight bleed after rigging.

```python
# Execute in blender-mcp via execute_blender_code
import bpy, math, os
from mathutils import Vector, Euler

mesh_obj = next((o for o in bpy.data.objects if o.type == 'MESH'), None)
out_dir = "pipelines/character-ralph/output/3d"
os.makedirs(out_dir, exist_ok=True)

# Derive bone reference positions from mesh bounds
bb = [mesh_obj.matrix_world @ Vector(c) for c in mesh_obj.bound_box]
min_z = min(v.z for v in bb)
max_z = max(v.z for v in bb)
max_x = max(abs(v.x) for v in bb)
h = max_z - min_z

# Approximate bone positions for camera targeting
zones = {
    "hand-L":       Vector(( max_x*0.5, 0, min_z + h*0.35)),
    "hand-R":       Vector((-max_x*0.5, 0, min_z + h*0.35)),
    "armpit-L":     Vector(( max_x*0.4, 0, min_z + h*0.72)),
    "armpit-R":     Vector((-max_x*0.4, 0, min_z + h*0.72)),
    "elbow-L":      Vector(( max_x*0.5, 0, min_z + h*0.55)),
    "elbow-R":      Vector((-max_x*0.5, 0, min_z + h*0.55)),
    "hip-crease":   Vector(( 0,         0, min_z + h*0.45)),
}

# Camera angles: front (looking along -Y) and side (looking along -X)
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
                        r3d.view_distance = 0.35  # tight zoom
                        r3d.view_rotation = rotation
                break

        filepath = os.path.join(out_dir, f"bleed-scan-{zone_name}-{angle_name}.png")
        bpy.context.scene.render.filepath = filepath
        bpy.context.scene.render.resolution_x = 600
        bpy.context.scene.render.resolution_y = 600
        bpy.ops.render.opengl(write_still=True)

print(f"Bleed scan: {len(zones) * len(angles)} close-up screenshots saved")
```

**How to evaluate each screenshot:**
- If you see two distinct mesh surfaces with a visible gap between them: **PASS**
- If you see mesh faces from arm region blending seamlessly into torso/leg region: **FAIL** — bridging faces remain
- If you see two surfaces touching with zero gap but no shared faces: **WARN** — weight bleed risk is high, consider increasing the gap by scaling the arm island slightly inward
- Pay special attention to the hand-thigh zone: this is where the character's resting pose places the hands directly against the pants, and is the #1 failure point

### Step 6: Write Gate Result

```python
# Execute in blender-mcp via execute_blender_code
import json, os

# Populate from the checks above -- fill in actual values
result = {
    "stage": "4b-mesh-separation",
    "gate": "gate-04b-mesh-separation",
    "result": "PASS",  # or "FAIL"
    "checks": [
        {
            "name": "arm_body_separation_L",
            "passed": True,
            "detail": "Left arm has no shared faces with torso"
        },
        {
            "name": "arm_body_separation_R",
            "passed": True,
            "detail": "Right arm has no shared faces with torso"
        },
        {
            "name": "hand_leg_clearance",
            "passed": True,
            "detail": "Min gap: 1.2cm (threshold: 0.5cm)"
        },
        {
            "name": "mesh_islands_after_cut",
            "passed": True,
            "detail": "3 islands: body, arm_L, arm_R"
        }
    ],
    "warnings": [],
    "blocking_errors": [],
    "recommendation": "Mesh separation verified -- proceed to gate-05-alignment and rigging"
}

output_path = "pipelines/character-ralph/output/gate-04b-mesh-separation-result.json"
os.makedirs(os.path.dirname(output_path), exist_ok=True)
with open(output_path, "w") as f:
    json.dump(result, f, indent=2)
print(json.dumps(result, indent=2))
```

## Remediation if FAIL

If any check fails, the mesh must be physically cut before rigging can proceed:

### Identify and delete bridging faces in edit mode

```python
# Execute in blender-mcp via execute_blender_code
import bpy
import bmesh
from mathutils import Vector

mesh_obj = next((o for o in bpy.data.objects if o.type == 'MESH'), None)
bpy.context.view_layer.objects.active = mesh_obj

# Switch to edit mode for visual inspection
bpy.ops.object.mode_set(mode='EDIT')
bpy.ops.mesh.select_all(action='DESELECT')

# Switch back to object mode to use bmesh programmatically
bpy.ops.object.mode_set(mode='OBJECT')

bm = bmesh.new()
bm.from_mesh(mesh_obj.data)
bm.verts.ensure_lookup_table()
bm.faces.ensure_lookup_table()

world_bb = [mesh_obj.matrix_world @ Vector(c) for c in mesh_obj.bound_box]
min_z = min(v.z for v in world_bb)
max_z = max(v.z for v in world_bb)
max_x = max(abs(v.x) for v in world_bb)
hip_z      = min_z + (max_z - min_z) * 0.40
shoulder_x = max_x * 0.55

arm_vert_set = set()
for v in bm.verts:
    wco = mesh_obj.matrix_world @ v.co
    if abs(wco.x) > shoulder_x and hip_z < wco.z < max_z:
        arm_vert_set.add(v.index)

# Delete faces that bridge arm-to-body gap
bridging_faces = [
    f for f in bm.faces
    if ({v.index for v in f.verts} & arm_vert_set) and
       ({v.index for v in f.verts} - arm_vert_set)
]
print(f"Deleting {len(bridging_faces)} bridging faces")
bmesh.ops.delete(bm, geom=bridging_faces, context='FACES')

bm.to_mesh(mesh_obj.data)
bm.free()
mesh_obj.data.update()
print("Bridging faces deleted. Optionally fill holes in arm and body separately.")
```

After deletion, export the cleaned mesh:

```python
# Execute in blender-mcp via execute_blender_code
import bpy, os

output_dir = "pipelines/character-ralph/output/3d"
os.makedirs(output_dir, exist_ok=True)

bpy.ops.export_scene.gltf(
    filepath=f"{output_dir}/character-clean.glb",
    export_format='GLB',
    export_animations=False
)
print(f"Exported cleaned mesh to {output_dir}/character-clean.glb")
```

Then re-run the gate against `character-clean.glb`. Once the gate passes, Stage 5
must use `character-clean.glb` as input rather than the original `character.glb`.

### Common Failure Modes and Remediation

| Symptom | Likely Cause | Fix |
|---------|-------------|-----|
| Arms fused to torso (1 island) | AI mesh gen welded arm seam | Delete bridging faces, fill holes, re-export |
| Hand touching pants | Arms too low in bind pose or mesh gen artifact | Delete bridging faces in elbow-to-wrist zone |
| No arm verts detected | Character has no arm geometry (robe/cloak) | Mark WARN if intentional, re-check bounding box thresholds |
| Many islands (>10) | Fragmented mesh from 3D gen | Check WARN, ensure each fragment has correct bone region |

### Gate Result Format

Write to `output/gate-04b-mesh-separation-result.json`:
```json
{
  "stage": "4b-mesh-separation",
  "gate": "gate-04b-mesh-separation",
  "result": "PASS|FAIL",
  "checks": [
    {"name": "arm_body_separation_L", "passed": true, "detail": "Left arm has no shared faces with torso"},
    {"name": "arm_body_separation_R", "passed": true, "detail": "Right arm has no shared faces with torso"},
    {"name": "hand_leg_clearance",    "passed": true, "detail": "Min gap: 1.2cm"},
    {"name": "mesh_islands_after_cut","passed": true, "detail": "3 islands: body, arm_L, arm_R"}
  ],
  "warnings": [],
  "blocking_errors": [],
  "recommendation": "Mesh separation verified -- proceed to gate-05-alignment and rigging"
}
```
