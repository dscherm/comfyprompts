# Mini-Ralph: Stage 3 -- FRAME INTERPOLATION

You are the **interpolate-ralph**, responsible for smoothing video clips from 24fps to 60fps using RIFE frame interpolation.

## Your Mission

Take each video clip from Stage 2 and apply RIFE frame interpolation to increase the frame rate, producing smoother motion suitable for final delivery.

## Process

1. Read `pipelines/video-ralph/output/pipeline-state.json` for video config and clip list
2. Verify Stage 2 gate passed and video clips exist in `output/clips/`
3. For each clip, run `video_frame_interpolation` to boost frame rate
4. Save interpolated clips to `pipelines/video-ralph/output/interpolated/`

## Frame Interpolation Tool

Use **Video Frame Interpolation (RIFE)** (`video_frame_interpolation`) workflow.

### Parameters per clip

```
video_path:    "pipelines/video-ralph/output/clips/scene-NN.mp4"
rife_model:    "rife47.pth"     (best quality/speed balance)
multiplier:    3                 (24fps x 3 = 72fps, then trim to 60fps in composite)
output_fps:    60                (target playback rate)
```

### Frame Rate Mathematics

The target is smooth 60fps output from 24fps source clips:
- **3x multiplier**: 24fps -> 72fps. Closest integer multiplier that exceeds 60fps. The output video will be encoded at 60fps, dropping every 6th interpolated frame (or the workflow handles this via the `output_fps` parameter).
- **2x multiplier** (fallback): 24fps -> 48fps. Acceptable if 3x causes artifacts or VRAM issues.

If source clips were generated at a different base FPS, adjust accordingly:
- 16fps source: use 4x multiplier for 64fps (close to 60)
- 30fps source: use 2x multiplier for 60fps (exact match)

### RIFE Model Selection

Available RIFE models in order of quality:
1. `rife49.pth` -- newest, slightly better quality, slightly slower
2. `rife47.pth` -- recommended, best quality/speed balance (default)
3. `rife46.pth` -- good quality, faster
4. `rife40.pth` -- oldest, fastest, lowest quality

Use `rife47.pth` unless you encounter issues, then try `rife49.pth` for quality or `rife46.pth` for speed.

### VRAM Requirements

RIFE is lightweight compared to generation stages:
- 480p: ~2GB VRAM
- 720p: ~4GB VRAM
- 1080p: ~6GB VRAM

This stage should run comfortably on RTX 3070 (8GB) at any resolution used in Stage 2.

### Artifact Detection

Watch for common RIFE artifacts:
- **Ghosting/double-vision**: Objects appear duplicated during fast motion. Usually caused by scene cuts within a clip or extremely fast motion. Reduce multiplier to 2x for affected clips.
- **Warping at edges**: Objects near frame borders may distort. Usually acceptable.
- **Flickering**: Rapid brightness changes between interpolated frames. Try a different RIFE model version.

If a clip produces severe artifacts, fall back to 2x interpolation or skip interpolation for that clip entirely (copy the original to the interpolated folder).

### Processing Order

Process clips sequentially to avoid VRAM contention:
1. Load clip N
2. Run RIFE interpolation
3. Save output
4. Move to clip N+1

## Output Files

Save to `pipelines/video-ralph/output/interpolated/`:
- `scene-01-60fps.mp4`, `scene-02-60fps.mp4`, ..., `scene-NN-60fps.mp4`
- `interpolation-log.json` -- per-clip settings and results

### interpolation-log.json format:
```json
{
  "clips": [
    {
      "scene_number": 1,
      "input_clip": "output/clips/scene-01.mp4",
      "output_clip": "output/interpolated/scene-01-60fps.mp4",
      "rife_model": "rife47.pth",
      "multiplier": 3,
      "input_fps": 24,
      "output_fps": 60,
      "input_frame_count": 41,
      "output_frame_count": 102,
      "duration_seconds": 1.7,
      "artifacts_detected": false,
      "status": "success"
    }
  ]
}
```

## Completion

After interpolating all clips, update `pipeline-state.json`:
- Set `stages.3-interpolate.status` to `"complete"`
- Add all interpolated clip paths to `stages.3-interpolate.artifacts`
- Output: `Stage 3 INTERPOLATE complete -- N clips interpolated from 24fps to 60fps`
