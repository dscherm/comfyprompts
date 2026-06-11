# Quality Gate 2: VIDEO GENERATION

## PASS Criteria (ALL must pass)
- [ ] At least 1 video clip exists in `output/clips/`
- [ ] Every video clip is >100KB (not empty or corrupt)
- [ ] Every video clip has a duration >1.0 second
- [ ] Video clips are valid MP4 files (can be probed for metadata)
- [ ] `output/clips/generation-log.json` exists and records all generation attempts
- [ ] Number of successful clips matches number of scenes in the breakdown

## WARN Criteria (log but don't block)
- [ ] Any clip duration differs from expected by >0.5 seconds
- [ ] Any clip resolution does not match `video_config.resolution` (e.g., generated at lower res due to VRAM)
- [ ] Any clip required a retry (seed change or resolution reduction)
- [ ] Generation log records any clips that took >180 seconds (may indicate GPU bottleneck)
- [ ] 1-2 clips failed but were re-generated successfully

## FAIL Criteria (block advancement)
- [ ] No video clips generated at all
- [ ] More than 50% of clips failed generation
- [ ] Any clip is 0 bytes or an invalid video container
- [ ] Generation log reports missing model errors (`ltx-2-19b-distilled-fp8.safetensors` not found)
- [ ] All clips are static (no motion detected -- identical first and last frames)

## Validation Method

Verify each clip exists, has reasonable size, and has valid duration:
```python
import json, os

clips_dir = "pipelines/video-ralph/output/clips"
log_path = os.path.join(clips_dir, "generation-log.json")

assert os.path.exists(log_path), "generation-log.json missing"
with open(log_path) as f:
    log = json.load(f)

for clip in log["clips"]:
    filepath = os.path.join("pipelines/video-ralph/output", clip["output_clip"])
    assert os.path.exists(filepath), f"{clip['output_clip']} missing"
    size = os.path.getsize(filepath)
    assert size > 100 * 1024, f"{clip['output_clip']} too small: {size} bytes"
    assert clip["status"] == "success", f"Scene {clip['scene_number']} failed: {clip.get('error', 'unknown')}"
    assert clip["duration_seconds"] > 1.0, f"Scene {clip['scene_number']} too short: {clip['duration_seconds']}s"
```

If ffprobe is available, also verify video metadata:
```bash
for f in output/clips/scene-*.mp4; do
    duration=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$f")
    echo "$f: ${duration}s"
done
```

## Gate Result Output

Write to `output/gate-02-result.json`:
```json
{
  "stage": "2-video-gen",
  "result": "PASS|WARN|FAIL",
  "checks": [
    { "name": "clips_exist", "passed": true, "detail": "5/5 clips generated" },
    { "name": "clip_sizes", "passed": true, "detail": "All >100KB (min: 1.2MB, max: 3.8MB)" },
    { "name": "clip_durations", "passed": true, "detail": "All >1.0s (range: 1.7-1.7s)" },
    { "name": "valid_containers", "passed": true, "detail": "All valid MP4" },
    { "name": "generation_log", "passed": true, "detail": "All clips status=success" }
  ],
  "warnings": [],
  "blocking_errors": [],
  "recommendation": "Proceed to frame interpolation"
}
```
