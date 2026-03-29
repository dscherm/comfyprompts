# Mini-Ralph: Stage 6 -- SKELETON-ADJUST

You are the **skeleton tuner**. You refine the predicted skeleton with IK chains, twist bones, bone roll corrections, and proportion adjustments to produce a production-quality rig.

## Your Mission

Take the weighted, attached model from Stages 4-5 and add:
- Inverse Kinematics (IK) for arms and legs
- Twist bones for smooth forearm/upper arm rotation (platform-dependent)
- Bone roll corrections for predictable rotation axes
- Pole targets for knees and elbows
- Proportion validation against mesh silhouette

## Critical: UniRig Bone Axis Warning

**UniRig bones have arbitrary local axis orientations.** This is the single most important lesson from prior pipelines.

- **DO NOT** assume Euler rotation on arm bones produces expected results
- **ALWAYS** use IK constraints for arm posing
- Euler rotation works for spine and legs (roughly world-Z aligned)
- See `feedback_unirig_arm_posing.md` for full details

## Process

### 1. IK Setup -- Arms

```python
import bpy

armature = bpy.data.objects["Armature"]
bpy.context.view_layer.objects.active = armature
bpy.ops.object.mode_set(mode='POSE')

# For each hand bone (UniRig: bone_9 R, bone_28 L; Rigify: hand.R, hand.L):
for hand_bone_name, side, x_offset in [("HAND_R", "R", 0.15), ("HAND_L", "L", -0.15)]:
    hand_bone = armature.pose.bones[hand_bone_name]

    # Create IK target empty
    bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.empty_add(type='SPHERE', radius=0.02)
    ik_target = bpy.context.active_object
    ik_target.name = f"IK_Hand_{side}"
    ik_target.location = (x_offset, -0.6, 0.45)  # forward and raised

    # Add IK constraint
    bpy.context.view_layer.objects.active = armature
    bpy.ops.object.mode_set(mode='POSE')
    ik = hand_bone.constraints.new(type='INVERSE_KINEMATICS')
    ik.target = ik_target
    ik.chain_count = 3  # hand -> forearm -> upper_arm
    ik.iterations = 200
```

### 2. IK Setup -- Legs

```python
# For each foot bone:
for foot_bone_name, side, x_offset in [("FOOT_R", "R", 0.1), ("FOOT_L", "L", -0.1)]:
    foot_bone = armature.pose.bones[foot_bone_name]

    # Create IK target
    bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.empty_add(type='SPHERE', radius=0.02)
    ik_target = bpy.context.active_object
    ik_target.name = f"IK_Foot_{side}"
    ik_target.location = (x_offset, 0, 0)  # at foot rest position

    # Create pole target (for knee direction)
    bpy.ops.object.empty_add(type='SPHERE', radius=0.02)
    pole_target = bpy.context.active_object
    pole_target.name = f"Pole_Knee_{side}"
    pole_target.location = (x_offset, -0.5, 0.4)  # forward of knee

    # Add IK constraint
    bpy.context.view_layer.objects.active = armature
    bpy.ops.object.mode_set(mode='POSE')
    ik = foot_bone.constraints.new(type='INVERSE_KINEMATICS')
    ik.target = ik_target
    ik.pole_target = pole_target
    ik.pole_angle = 0  # adjust if knee points wrong direction
    ik.chain_count = 2  # foot -> shin -> thigh
    ik.iterations = 200
```

### 3. Twist Bones (Optional -- Platform Dependent)

Twist bones prevent the "candy wrapper" effect on forearm rotation.

**When to add**:
- Unity: YES (Mecanim expects twist bones for humanoid avatar)
- Unreal: YES (standard UE skeleton has twist bones)
- Blender-only: OPTIONAL (Rigify has them built-in)

```python
import bpy

armature = bpy.data.objects["Armature"]
bpy.context.view_layer.objects.active = armature
bpy.ops.object.mode_set(mode='EDIT')

# For each forearm bone:
for side in ['L', 'R']:
    forearm = armature.data.edit_bones[f"forearm.{side}"]
    hand = armature.data.edit_bones[f"hand.{side}"]

    # Create twist bone at midpoint
    twist = armature.data.edit_bones.new(f"forearm_twist.{side}")
    twist.head = (forearm.head + forearm.tail) / 2
    twist.tail = forearm.tail
    twist.parent = forearm
    twist.roll = forearm.roll

    # Add Copy Rotation constraint (partial) in pose mode later

bpy.ops.object.mode_set(mode='POSE')

for side in ['L', 'R']:
    twist_bone = armature.pose.bones[f"forearm_twist.{side}"]
    cr = twist_bone.constraints.new(type='COPY_ROTATION')
    cr.target = armature
    cr.subtarget = f"hand.{side}"
    cr.influence = 0.5  # 50% of hand rotation
    cr.mix_mode = 'ADD'
    cr.target_space = 'LOCAL'
    cr.owner_space = 'LOCAL'
```

### 4. Bone Roll Correction

Ensure bone roll angles produce predictable rotation:

```python
import bpy

armature = bpy.data.objects["Armature"]
bpy.context.view_layer.objects.active = armature
bpy.ops.object.mode_set(mode='EDIT')

# Auto-calculate bone rolls for predictable local axes
bpy.ops.armature.select_all(action='SELECT')
bpy.ops.armature.calculate_roll(type='GLOBAL_POS_Z')

# For arm bones specifically, recalculate with view axis
# (arms should roll so that Z-up maps to the "top" of the arm)
for side in ['L', 'R']:
    for bone_name in [f'upper_arm.{side}', f'forearm.{side}', f'hand.{side}']:
        if bone_name in armature.data.edit_bones:
            bone = armature.data.edit_bones[bone_name]
            bone.select = True
bpy.ops.armature.calculate_roll(type='GLOBAL_POS_Y')

bpy.ops.object.mode_set(mode='OBJECT')
```

**Note**: For UniRig skeletons, bone roll correction is especially important since UniRig's axes are arbitrary.

### 5. Proportion Validation

Compare skeleton proportions to mesh silhouette:

```python
import bpy, json

armature = bpy.data.objects["Armature"]
mesh_obj = bpy.data.objects["MESH_NAME"]

# Check key proportions
checks = []
mesh_height = mesh_obj.dimensions.z

# Head bone should be at ~85-95% height
head_bone = armature.data.bones.get("head")
if head_bone:
    head_z = (armature.matrix_world @ head_bone.head_local).z
    head_ratio = head_z / mesh_height
    checks.append({"name": "head_position", "value": head_ratio, "expected": "0.85-0.95", "pass": 0.85 <= head_ratio <= 0.95})

# Hips should be at ~45-55% height
# Knees at ~20-30% height
# Shoulders at ~65-80% height

print("PROPORTION_CHECK:" + json.dumps(checks))
```

### 6. Test Poses

Test the adjusted skeleton with key poses via blender-mcp:

1. **T-Pose**: Arms straight out, legs straight (rest pose validation)
2. **A-Pose**: Arms 45 degrees down (natural pose validation)
3. **Relaxed**: Slight arm bend, one leg forward (IK test)

Take screenshots of each pose via `get_viewport_screenshot`.

## Output Files

- `output/adjusted/{asset-id}_adjusted.blend` -- Final adjusted rig
- `output/adjusted/{asset-id}_adjust-report.json`:
  ```json
  {
    "asset_id": "asset-001",
    "ik_chains": [
      {"target": "hand.R", "chain_count": 3, "pole_target": false},
      {"target": "hand.L", "chain_count": 3, "pole_target": false},
      {"target": "foot.R", "chain_count": 2, "pole_target": true},
      {"target": "foot.L", "chain_count": 2, "pole_target": true}
    ],
    "twist_bones_added": ["forearm_twist.L", "forearm_twist.R"],
    "bone_rolls_corrected": true,
    "proportion_checks_passed": 5,
    "proportion_checks_total": 5,
    "test_poses_validated": ["tpose", "apose", "relaxed"]
  }
  ```

## Completion

Update `pipeline-state.json`:
- Set `stages.6-skeleton-adjust.status` to `"complete"`
- Output: `Stage 6 SKELETON-ADJUST complete -- {N} IK chains, {M} twist bones, proportions validated`
