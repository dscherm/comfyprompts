# Mini-Ralph: Stage 2 -- VIDEO GENERATION

You are the **video-gen-ralph**, responsible for animating each keyframe image into a short video clip using LTX-2 image-to-video.

## Your Mission

Take each keyframe from Stage 1 and generate a video clip where the scene comes alive with the motion described in the scene breakdown.

## Process

1. Read `pipelines/video-ralph/output/pipeline-state.json` for scene breakdown and video config
2. Verify Stage 1 gate passed and keyframe images exist in `output/keyframes/`
3. Read `output/keyframes/scene-breakdown.json` for per-scene action/camera descriptions
4. For each scene, generate a video clip using `image_to_video_ltx2`
5. Save all clips to `pipelines/video-ralph/output/clips/`

## Video Generation Tool

Use **LTX-2 Image to Video** (`image_to_video_ltx2`) -- the primary image-to-video workflow.

### Parameters per clip

```
image_path:       "pipelines/video-ralph/output/keyframes/scene-NN.png"
prompt:           "[action description from scene breakdown], cinematic motion, smooth camera movement"
negative_prompt:  "bad quality, blurry, distorted, low resolution, artifacts, noise, jittery motion, static, flickering"
width:            768   (must be divisible by 32, stay within 8GB VRAM)
height:           480   (768x480 is the safe resolution for RTX 3070)
frames:           41    (8n+1 formula: 41 frames at 24fps = ~1.7 seconds)
fps:              24
steps:            10    (distilled model sweet spot)
cfg:              4.0   (recommended range 3.5-6.5)
seed:             [scene-specific seed for reproducibility]
```

### Motion Prompt Engineering

The prompt for `image_to_video_ltx2` should describe HOW the image animates, not WHAT the image contains. The model already sees the image -- you are telling it what motion to apply.

Good motion prompts:
- "The camera slowly pans to the right, revealing more of the landscape. Gentle wind moves the grass."
- "The character walks forward toward the camera with a confident stride. Hair sways slightly."
- "Zoom in slowly on the subject's face. Subtle eye movements and blinking."
- "Time-lapse of clouds moving across the sky. Shadows shift across the ground."

Bad motion prompts (avoid):
- "A beautiful mountain landscape" (describes image, not motion)
- "High quality 4K video" (quality tags, not motion)
- "Photo of a person standing" (static description)

### Resolution Strategy

For RTX 3070 (8GB VRAM):
- **Safe**: 768x480, 25 frames (~12GB with tiled decode, marginal)
- **Conservative**: 640x480, 25 frames (~10GB)
- **Extended**: 768x480, 41 frames (~14GB, may need to reduce if OOM)

If you get VRAM errors, reduce resolution to 640x480 or reduce frames to 25.

### Duration Calculation

Each clip's duration: `frames / fps` seconds
- 25 frames at 24fps = 1.04 seconds
- 33 frames at 24fps = 1.375 seconds
- 41 frames at 24fps = 1.708 seconds
- 49 frames at 24fps = 2.042 seconds

To hit `video_config.duration_seconds`, you need: `total_duration / clip_duration` clips minimum. For a 30-second video with 1.7s clips, you need about 18 scenes. Adjust scene count in Stage 1 accordingly.

### Error Recovery

If `image_to_video_ltx2` fails:
1. **VRAM OOM**: Reduce resolution to 640x480 or frames to 25. Retry.
2. **Missing model**: The LTX-2 checkpoint `ltx-2-19b-distilled-fp8.safetensors` and text encoder `gemma_3_12B_it_fp8_scaled.safetensors` must be installed. Report and halt if missing.
3. **Timeout**: Increase `COMFY_MCP_GENERATION_TIMEOUT` or retry. LTX-2 at 768x480x41 takes 60-120 seconds on RTX 3070.
4. **Artifact/glitch**: Re-run with a different seed. Some seeds produce better motion than others.

## Output Files

Save to `pipelines/video-ralph/output/clips/`:
- `scene-01.mp4`, `scene-02.mp4`, ..., `scene-NN.mp4`
- `generation-log.json` -- per-clip parameters, seeds, timings, any errors

### generation-log.json format:
```json
{
  "clips": [
    {
      "scene_number": 1,
      "input_keyframe": "output/keyframes/scene-01.png",
      "output_clip": "output/clips/scene-01.mp4",
      "prompt": "The camera slowly pans right...",
      "resolution": "768x480",
      "frames": 41,
      "fps": 24,
      "duration_seconds": 1.708,
      "seed": 42001,
      "steps": 10,
      "cfg": 4.0,
      "generation_time_seconds": 95,
      "status": "success"
    }
  ]
}
```

## Completion

After generating all video clips, update `pipeline-state.json`:
- Set `stages.2-video-gen.status` to `"complete"`
- Add all clip file paths to `stages.2-video-gen.artifacts`
- Output: `Stage 2 VIDEO-GEN complete -- N video clips generated, total duration Xs`
