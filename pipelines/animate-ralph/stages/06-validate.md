# Mini-Ralph: Stage 6 -- VALIDATE

Test imports, verify loops, check bone compatibility across platforms.

## Process

1. For each exported file, validate:
   - FBX/GLB file integrity (valid headers, parseable)
   - Animation data present (keyframe count > 0)
   - Bone names match target platform convention
   - Clip duration matches spec
   - Loop clips: first/last frame delta < 0.001 per channel
2. For Unity exports: verify Mecanim avatar compatibility
3. For Unreal exports: verify skeleton hierarchy matches UE conventions
4. Write validation report

## Validation Checks

### File Integrity
- File exists and > 10KB
- Valid FBX/glTF magic bytes
- Parseable by Blender reimport

### Animation Data
- At least one action/animation clip
- Clip has keyframes on expected bones
- Duration within 10% of spec target
- Frame rate matches spec (default 30fps)

### Loop Quality (for looping clips)
- Import the clip
- Compare bone transforms at frame 0 vs last frame
- Maximum delta per bone per channel < 0.001
- Visual inspection: no visible pop at loop point

### Platform Compatibility
- Unity: bone names match Mecanim mapping
- Unreal: bone names match UE skeleton template
- Root bone exists and is named correctly per platform

## Output

Write validation report to `output/final/{model_id}_validation.json`:
```json
{
  "model_id": "model_id",
  "clips_validated": 5,
  "clips_passed": 5,
  "clips_warned": 0,
  "clips_failed": 0,
  "platforms_tested": ["unity", "unreal", "blender"],
  "details": [...]
}
```

## Completion

If all validations pass:
- Write `output/final/ANIMATION-MANIFEST.md`
- Update pipeline-state.json
- Output: `Stage 6 VALIDATE complete -- {N} clips validated for {model_name}, all platforms OK`
