# Quality Gate: Kart Assembly (Character-in-Kart Validation)

## Purpose

This backpressure gate validates that each character is correctly scaled, positioned, and posed inside their assigned kart. It runs AFTER assembly and BEFORE final export. A failure triggers re-assembly with adjusted parameters.

## PASS Criteria (ALL must pass)

### Scale Check
- [ ] Character's head is visible above the kart body (not buried inside or floating above)
- [ ] Character's shoulders are within the kart side panels (not clipping through or floating outside)
- [ ] Character fills the seat area proportionally (not comically small or oversized)
- [ ] Character's torso height is between 40%-70% of the kart's total height

### Position Check
- [ ] Character's hips are aligned with the Seat empty (within 5cm tolerance)
- [ ] Character is centered left-right in the kart (within 3cm of kart center X)
- [ ] Character is NOT floating above the kart (feet/legs should be at or below seat level)
- [ ] Character is NOT clipping through the kart floor

### Driving Pose Check
- [ ] Upper legs are bent forward ~90 degrees (seated position)
- [ ] Lower legs are bent ~90 degrees (feet at pedal area)
- [ ] Arms are reaching forward toward the steering column area
- [ ] Hands are at approximately steering wheel height (within 15cm of SteeringColumn empty)
- [ ] Head is upright and facing forward (not drooping or tilted severely)
- [ ] Spine has slight forward lean (driving posture, not rigid upright)

### Visual Validation (4 Views)
- [ ] **Front view**: Character visible in driver seat, head above kart body, centered
- [ ] **Side view**: Seated posture visible, arms reaching forward, legs bent
- [ ] **3/4 view**: Character looks like a driver in a kart (natural driving appearance)
- [ ] **Top view**: Character centered in seat area, arms pointing toward steering column

## WARN Criteria (log but don't block)

- [ ] Hands not precisely at steering wheel position (cosmetic, acceptable for first pass)
- [ ] Slight mesh interpenetration between character and kart (< 2cm overlap)
- [ ] Character pose looks stiff (procedural animation, not mocap)
- [ ] No textures on character mesh (geometry-only rigged model)

## FAIL Criteria (block export, re-assemble)

- [ ] Character is invisible (buried inside kart or off-screen)
- [ ] Character is floating significantly above kart (> 10cm gap)
- [ ] Character is not in seated position (standing, lying down, or T-pose)
- [ ] Character scale is obviously wrong (tiny speck or giant clipping through everything)
- [ ] Arms are pointing backward or straight down (not reaching for steering)
- [ ] Severe mesh explosion or vertex scattering visible
- [ ] Character is rotated incorrectly (facing backward or sideways)

## Validation Method

### Step 1: Render 4 Views
For each assembled character-kart pair, render viewport screenshots:

```python
# In Blender (via blender-mcp or headless)
views = [
    ("FRONT", "front"),
    ("RIGHT", "side"),
    ("BACK", "back"),
    # Plus a 3/4 view with custom rotation
]

for view_axis, view_name in views:
    bpy.ops.view3d.view_axis(type=view_axis)
    bpy.ops.view3d.view_all()
    bpy.context.scene.render.filepath = f"output/{char_id}_in_{kart_id}_{view_name}.png"
    bpy.ops.render.opengl(write_still=True)
```

### Step 2: Geometric Validation
Programmatically check:

```python
# Character bounding box vs kart bounding box
char_bb = get_character_bounds(armature)
kart_bb = get_kart_bounds(kart_root)

# Scale ratio: character height should be 40-70% of kart height
scale_ratio = char_bb.height / kart_bb.height
assert 0.4 <= scale_ratio <= 0.7, f"Scale ratio {scale_ratio:.2f} out of range"

# Hips distance from Seat
hips_pos = armature.matrix_world @ hips_bone.head_local
seat_pos = seat_empty.matrix_world.translation
dist = (hips_pos - seat_pos).length
assert dist < 0.1, f"Hips {dist:.3f}m from seat (max 0.1m)"

# Hands distance from SteeringColumn
for hand_bone in [hand_l, hand_r]:
    hand_pos = armature.matrix_world @ hand_bone.head_local
    steer_dist = (hand_pos - steering_pos).length
    assert steer_dist < 0.3, f"Hand {steer_dist:.3f}m from steering (max 0.3m)"
```

### Step 3: Pose Angle Validation
Check bone rotations are within expected ranges:

```python
expected_poses = {
    "UpperLeg": {"x_range": (-100, -70)},   # bent forward ~90
    "LowerLeg": {"x_range": (70, 110)},     # bent ~90
    "UpperArm": {"x_range": (-85, -50)},    # reaching forward
    "LowerArm": {"x_range": (-55, -20)},    # bent for wheel
    "Spine":    {"x_range": (-20, 0)},      # slight forward lean
    "Head":     {"x_range": (5, 25)},       # looking forward/up
}
```

## Remediation

If gate **FAILS**, adjust parameters and re-assemble:

| Symptom | Cause | Fix |
|---------|-------|-----|
| Character too small | `character_scale` too low | Increase scale (try 0.4-0.5) |
| Character too large | `character_scale` too high | Decrease scale (try 0.25-0.35) |
| Floating above kart | Z-offset too high | Reduce seat Z offset |
| Buried in kart | Z-offset too low or scale too large | Adjust Z offset, reduce scale |
| Arms not reaching wheel | Arm rotation insufficient | Increase UpperArm rx to -80° |
| Not seated | Hip rotation wrong | Check UpperLeg rx = -90° |
| Facing wrong way | Character imported rotated | Apply rotation correction before posing |

## Gate Result Format

Write to `output/{char_id}_gate_result.json`:
```json
{
  "character_id": "player",
  "kart_id": "player_kart",
  "result": "PASS|WARN|FAIL",
  "scale_ratio": 0.55,
  "hips_seat_distance": 0.03,
  "hand_steering_distance": [0.15, 0.16],
  "pose_angles": {
    "UpperLeg.L": -90.0,
    "LowerLeg.L": 90.0,
    "UpperArm.L": -70.0
  },
  "screenshots": [
    "player_in_kart_front.png",
    "player_in_kart_side.png",
    "player_in_kart_34.png",
    "player_in_kart_top.png"
  ],
  "warnings": [],
  "blocking_errors": [],
  "recommendation": "Assembly passes visual and geometric checks"
}
```
