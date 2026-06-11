# Quality Gate 5: COMPOSITE

## PASS Criteria (ALL must pass)
- [ ] `output/final/final-video.mp4` exists and is >500KB
- [ ] Final video is a valid MP4 container (has both video and audio streams, or video-only if all audio failed)
- [ ] Final video duration is within 20% of `video_config.duration_seconds`
- [ ] Final video has the correct resolution matching `video_config.resolution`
- [ ] `output/final/PRODUCTION-MANIFEST.md` exists and documents the full production
- [ ] Video stream frame rate matches `video_config.target_fps` (60fps default, 5fps tolerance)

## WARN Criteria (log but don't block)
- [ ] Final video has no audio stream (silent video -- all audio generation failed)
- [ ] Audio and video are out of sync by >0.5 seconds at any point
- [ ] Final video duration differs from sum of scene durations by >2 seconds
- [ ] Some scenes were composited at different resolutions (letterboxing may be visible)
- [ ] Music bed was omitted from the mix
- [ ] Lip-sync was planned but not applied
- [ ] `clip-list.txt` or `video-only.mp4` intermediate files are missing (compositing may have used an alternative method)

## FAIL Criteria (block advancement)
- [ ] `output/final/final-video.mp4` does not exist
- [ ] Final video is 0 bytes or an invalid/corrupt container
- [ ] Final video has 0 duration or 0 frames
- [ ] Final video resolution is 0x0 or completely wrong (e.g., 100x100 when 1280x720 expected)
- [ ] `PRODUCTION-MANIFEST.md` is missing
- [ ] No video stream present in the container

## Validation Method

Verify the final video using ffprobe (if available) or file size heuristics:
```bash
# Check video metadata
ffprobe -v error -show_entries format=duration,size -show_entries stream=codec_type,width,height,r_frame_rate -of json output/final/final-video.mp4
```

```python
import json, os

final_dir = "pipelines/video-ralph/output/final"
video_path = os.path.join(final_dir, "final-video.mp4")
manifest_path = os.path.join(final_dir, "PRODUCTION-MANIFEST.md")

# File existence and size
assert os.path.exists(video_path), "final-video.mp4 missing"
assert os.path.getsize(video_path) > 500 * 1024, "final-video.mp4 too small"
assert os.path.exists(manifest_path), "PRODUCTION-MANIFEST.md missing"

# Load pipeline state for expected values
with open("pipelines/video-ralph/output/pipeline-state.json") as f:
    state = json.load(f)

expected_duration = state["video_config"]["duration_seconds"]
# Duration check would require ffprobe -- log as warning if unavailable
```

## Sync Verification

If ffprobe is available, check audio/video alignment:
```bash
# Get video duration
video_dur=$(ffprobe -v error -show_entries format=duration -of csv=p=0 output/final/final-video.mp4)

# Get audio duration (if audio stream exists)
audio_dur=$(ffprobe -v error -select_streams a:0 -show_entries stream=duration -of csv=p=0 output/final/final-video.mp4)

echo "Video: ${video_dur}s, Audio: ${audio_dur}s"
# Difference should be <0.5s
```

## Gate Result Output

Write to `output/gate-05-result.json`:
```json
{
  "stage": "5-composite",
  "result": "PASS|WARN|FAIL",
  "checks": [
    { "name": "final_video_exists", "passed": true, "detail": "final-video.mp4 exists, 12.4MB" },
    { "name": "valid_container", "passed": true, "detail": "MP4 with H.264 video + AAC audio" },
    { "name": "duration", "passed": true, "detail": "30.6s (target: 30s, within 20% tolerance)" },
    { "name": "resolution", "passed": true, "detail": "1280x720 matches config" },
    { "name": "frame_rate", "passed": true, "detail": "60fps matches target" },
    { "name": "audio_sync", "passed": true, "detail": "Video/audio duration delta: 0.1s" },
    { "name": "manifest", "passed": true, "detail": "PRODUCTION-MANIFEST.md written" }
  ],
  "warnings": [],
  "blocking_errors": [],
  "recommendation": "Pipeline complete"
}
```
