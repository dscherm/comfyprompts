# Quality Gate 3: FRAME INTERPOLATION

## PASS Criteria (ALL must pass)
- [ ] At least 1 interpolated clip exists in `output/interpolated/`
- [ ] Every interpolated clip is a valid video file >100KB
- [ ] Every interpolated clip has more frames than its source clip (frame count increased)
- [ ] `output/interpolated/interpolation-log.json` exists and is valid JSON
- [ ] Number of interpolated clips matches number of source clips from Stage 2

## WARN Criteria (log but don't block)
- [ ] Any clip was interpolated at a lower multiplier than requested (e.g., 2x instead of 3x)
- [ ] Any clip was skipped (copied from source without interpolation) due to artifacts
- [ ] Interpolated clip file size is smaller than source (unusual, may indicate quality loss)
- [ ] Output frame rate differs from `video_config.target_fps` by more than 5fps
- [ ] `artifacts_detected` is true for any clip in the interpolation log

## FAIL Criteria (block advancement)
- [ ] No interpolated clips generated at all
- [ ] More than 50% of clips failed interpolation
- [ ] Interpolated clips have FEWER frames than source (regression)
- [ ] All interpolated clips are 0 bytes or corrupt
- [ ] RIFE model not found (`rife47.pth` missing) and no fallback succeeded

## Validation Method

Compare frame counts between source and interpolated clips:
```python
import json, os

interp_dir = "pipelines/video-ralph/output/interpolated"
log_path = os.path.join(interp_dir, "interpolation-log.json")

assert os.path.exists(log_path), "interpolation-log.json missing"
with open(log_path) as f:
    log = json.load(f)

for clip in log["clips"]:
    filepath = os.path.join("pipelines/video-ralph/output", clip["output_clip"])
    assert os.path.exists(filepath), f"{clip['output_clip']} missing"
    size = os.path.getsize(filepath)
    assert size > 100 * 1024, f"{clip['output_clip']} too small: {size} bytes"
    assert clip["output_frame_count"] > clip["input_frame_count"], \
        f"Scene {clip['scene_number']}: output frames ({clip['output_frame_count']}) <= input ({clip['input_frame_count']})"
    assert clip["status"] == "success", f"Scene {clip['scene_number']} failed"
```

## Gate Result Output

Write to `output/gate-03-result.json`:
```json
{
  "stage": "3-interpolate",
  "result": "PASS|WARN|FAIL",
  "checks": [
    { "name": "interpolated_exist", "passed": true, "detail": "5/5 clips interpolated" },
    { "name": "frame_count_increased", "passed": true, "detail": "All clips: 41 -> ~102 frames (2.5x)" },
    { "name": "file_sizes", "passed": true, "detail": "All >100KB (min: 2.8MB, max: 7.1MB)" },
    { "name": "no_severe_artifacts", "passed": true, "detail": "No clips flagged for artifacts" },
    { "name": "interpolation_log", "passed": true, "detail": "All clips status=success" }
  ],
  "warnings": [],
  "blocking_errors": [],
  "recommendation": "Proceed to audio generation"
}
```
