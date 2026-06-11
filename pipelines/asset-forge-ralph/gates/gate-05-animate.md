# Quality Gate 5: ANIMATION

## Stage Skipped Handling
If `stages.5-animate.status` is `"skipped"` (prop or unrigged asset), this gate automatically passes. Verify that a model file exists in `output/animated/` (should be a copy of the rigged or cleaned mesh).

## PASS Criteria (ALL must pass for animated assets)
- [ ] At least one animated GLB exists in `output/animated/`
- [ ] Each animated GLB is >10KB and has valid glTF header
- [ ] Each animation has at least 10 keyframes (not a static pose masquerading as animation)
- [ ] No NaN or Infinity values in any bone transforms (would cause mesh disappearance)
- [ ] All animated bones exist in the skeleton (no references to missing bones)
- [ ] Animation duration is >0.5 seconds (not a single-frame "animation")
- [ ] Required animations present based on asset type:
  - character: idle, walk, run (minimum 3)
  - creature: idle, walk (minimum 2)
  - vehicle: idle or wheel_spin (minimum 1)

## WARN Criteria (log but don't block)
- [ ] Only required animations present (no optional attack/jump/etc.)
- [ ] Animation is very short (<1 second for a loop -- may look unnatural)
- [ ] Animation is very long (>10 seconds for a loop -- unusually long cycle)
- [ ] Root bone has large translation offsets (may cause character to fly off-screen in engine)
- [ ] Some bones are not animated (static bones -- may be intentional for face/fingers)
- [ ] Loop discontinuity: first and last frame poses differ by >5 degrees on any bone

## FAIL Criteria (block advancement -- re-run Stage 5)
- [ ] No animated GLB files generated
- [ ] Any animation file is corrupt or invalid
- [ ] NaN or Infinity detected in bone transforms (critical rendering bug)
- [ ] Animation references bones not in the skeleton (will crash some engines)
- [ ] All keyframes are identical (no actual motion -- just a static pose)
- [ ] Required animations missing (e.g., character has no idle)
- [ ] Animation tool returned an explicit error
- [ ] Mesh geometry deformed beyond recognition (extreme bone transforms)

## Validation Method

### Blender headless animation check
```bash
"C:/Program Files/Blender Foundation/Blender 5.0/blender.exe" \
  --background --python - <<'PYTHON' -- ANIMATED_GLB
import bpy, sys, math

argv = sys.argv[sys.argv.index("--") + 1:]
glb_path = argv[0]

bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete()
bpy.ops.import_scene.gltf(filepath=glb_path)

# Find armature
armatures = [obj for obj in bpy.data.objects if obj.type == 'ARMATURE']
if not armatures:
    print("FAIL: No armature found")
    sys.exit(1)

armature = armatures[0]
bone_names = set(b.name for b in armature.data.bones)

# Check all actions (animations)
actions = bpy.data.actions
if not actions:
    print("FAIL: No animations found")
    sys.exit(1)

for action in actions:
    frame_start = action.frame_range[0]
    frame_end = action.frame_range[1]
    frame_count = int(frame_end - frame_start)
    duration = frame_count / 24.0  # Assume 24fps default

    print(f"Animation: {action.name}")
    print(f"  Frames: {frame_count} ({frame_start}-{frame_end})")
    print(f"  Duration: {duration:.2f}s")

    # Check for NaN in keyframes
    nan_count = 0
    for fcurve in action.fcurves:
        for kp in fcurve.keyframe_points:
            if math.isnan(kp.co[0]) or math.isnan(kp.co[1]):
                nan_count += 1
            if math.isinf(kp.co[0]) or math.isinf(kp.co[1]):
                nan_count += 1

    if nan_count > 0:
        print(f"  FAIL: {nan_count} NaN/Inf values in keyframes")
    else:
        print(f"  NaN check: PASS")

    # Check bone references
    animated_bones = set()
    for fcurve in action.fcurves:
        if fcurve.data_path.startswith("pose.bones"):
            bone_name = fcurve.data_path.split('"')[1]
            animated_bones.add(bone_name)

    missing = animated_bones - bone_names
    if missing:
        print(f"  FAIL: Animation references missing bones: {missing}")
    else:
        print(f"  Bone references: PASS ({len(animated_bones)} bones animated)")

    # Check for actual motion (not all keyframes identical)
    has_motion = False
    for fcurve in action.fcurves:
        values = [kp.co[1] for kp in fcurve.keyframe_points]
        if len(set(round(v, 4) for v in values)) > 1:
            has_motion = True
            break

    if not has_motion:
        print(f"  FAIL: No actual motion detected (all keyframes identical)")
    else:
        print(f"  Motion check: PASS")
PYTHON
```

### Per-file validation
Run the above check on each animated GLB:
```bash
for f in pipelines/asset-forge-ralph/output/animated/animated-*.glb; do
  echo "=== Checking $f ==="
  "C:/Program Files/Blender Foundation/Blender 5.0/blender.exe" \
    --background --python check_animation.py -- "$f"
done
```

## Gate Result Output

Write to `output/gate-05-result.json`:
```json
{
  "stage": "5-animate",
  "result": "PASS|WARN|FAIL",
  "checks": [
    { "name": "idle_exists", "passed": true, "detail": "animated-idle.glb exists, 2.1MB" },
    { "name": "walk_exists", "passed": true, "detail": "animated-walk.glb exists, 1.8MB" },
    { "name": "run_exists", "passed": true, "detail": "animated-run.glb exists, 1.5MB" },
    { "name": "no_nan", "passed": true, "detail": "0 NaN/Inf values across all clips" },
    { "name": "bone_refs_valid", "passed": true, "detail": "All animated bones exist in skeleton" },
    { "name": "has_motion", "passed": true, "detail": "All clips contain actual motion" },
    { "name": "min_keyframes", "passed": true, "detail": "All clips have >10 keyframes" }
  ],
  "warnings": ["Loop discontinuity on walk cycle: 3.2 degree hip offset at loop point"],
  "blocking_errors": [],
  "recommendation": "Animations look good -- proceed to export"
}
```
