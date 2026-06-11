# Quality Gate 1: KEYFRAME

## PASS Criteria (ALL must pass)
- [ ] At least 1 keyframe image exists in `output/keyframes/`
- [ ] Every keyframe PNG is >50KB (not blank or corrupt)
- [ ] `output/keyframes/scene-breakdown.json` exists and is valid JSON
- [ ] Scene breakdown has at least 1 scene entry with `description`, `action`, and `output_file`
- [ ] Each listed `output_file` in the breakdown actually exists on disk
- [ ] All keyframe images have the correct aspect ratio for the target resolution (within 5% tolerance of 16:9 for 1280x720)

## WARN Criteria (log but don't block)
- [ ] Fewer than 3 keyframes generated (very short video, may lack variety)
- [ ] Any keyframe is <100KB (may be low detail or partially rendered)
- [ ] Scene durations do not sum to within 20% of `video_config.duration_seconds`
- [ ] Inconsistent resolution across keyframes (some 1024x576, some 768x512)
- [ ] Scene breakdown missing `camera` or `duration_seconds` fields (Stage 2 can infer defaults)

## FAIL Criteria (block advancement)
- [ ] No keyframe images generated at all
- [ ] All keyframes are blank, corrupt, or <10KB
- [ ] `scene-breakdown.json` is missing or invalid JSON
- [ ] Scene breakdown has 0 scenes
- [ ] Keyframe images are wrong format (not PNG or not a valid image)

## Validation Method

Check each keyframe file exists and has reasonable size:
```python
import json, os

keyframe_dir = "pipelines/video-ralph/output/keyframes"
breakdown_path = os.path.join(keyframe_dir, "scene-breakdown.json")

# Check breakdown exists
assert os.path.exists(breakdown_path), "scene-breakdown.json missing"
with open(breakdown_path) as f:
    breakdown = json.load(f)

assert len(breakdown["scenes"]) > 0, "No scenes in breakdown"

# Check each keyframe
for scene in breakdown["scenes"]:
    filepath = os.path.join(keyframe_dir, scene["output_file"])
    assert os.path.exists(filepath), f"{scene['output_file']} missing"
    size = os.path.getsize(filepath)
    assert size > 50 * 1024, f"{scene['output_file']} too small: {size} bytes"
```

## Gate Result Output

Write to `output/gate-01-result.json`:
```json
{
  "stage": "1-keyframe",
  "result": "PASS|WARN|FAIL",
  "checks": [
    { "name": "breakdown_exists", "passed": true, "detail": "scene-breakdown.json valid, 5 scenes" },
    { "name": "keyframes_exist", "passed": true, "detail": "5/5 keyframe PNGs found" },
    { "name": "keyframe_sizes", "passed": true, "detail": "All >50KB (min: 187KB, max: 342KB)" },
    { "name": "aspect_ratio", "passed": true, "detail": "All 16:9 (1024x576)" }
  ],
  "warnings": [],
  "blocking_errors": [],
  "recommendation": "Proceed to video generation"
}
```
