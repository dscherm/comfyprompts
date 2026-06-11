# Quality Gate 5: FINAL MIX

## PASS Criteria (ALL must pass)
- [ ] `output/final/final-mix.mp3` exists and is >50KB
- [ ] Final mix is a valid audio file (MP3 or WAV, decodable)
- [ ] Final mix total duration is within 30% of the estimated total from `parsed-script.json`
- [ ] `output/final/AUDIO-MANIFEST.md` exists and documents the production
- [ ] `output/final/mix-instructions.json` exists (for manual editing reference)

## WARN Criteria (log but don't block)
- [ ] Final mix has no background music (ACE-Step unavailable)
- [ ] Final mix has no SFX (Stable Audio Open unavailable or no cues in script)
- [ ] Any audio track was omitted from the mix (could not be layered)
- [ ] Peak amplitude exceeds -1 dBFS (near clipping)
- [ ] Silence gaps longer than 3 seconds detected (may feel unnatural)
- [ ] `final-mix.wav` lossless version was not generated
- [ ] ffmpeg was not available, mix-instructions.json provided instead of actual mix

## FAIL Criteria (block advancement)
- [ ] `output/final/final-mix.mp3` does not exist
- [ ] Final mix is 0 bytes or an invalid/corrupt audio file
- [ ] Final mix duration is 0 seconds
- [ ] `AUDIO-MANIFEST.md` is missing
- [ ] No dialogue tracks were included in the mix (silence-only output)

## Validation Method

```python
import json, os

final_dir = "pipelines/audio-ralph/output/final"
mix_path = os.path.join(final_dir, "final-mix.mp3")
manifest_path = os.path.join(final_dir, "AUDIO-MANIFEST.md")
instructions_path = os.path.join(final_dir, "mix-instructions.json")

# File existence
assert os.path.exists(mix_path), "final-mix.mp3 missing"
assert os.path.getsize(mix_path) > 50 * 1024, "final-mix.mp3 too small"
assert os.path.exists(manifest_path), "AUDIO-MANIFEST.md missing"
assert os.path.exists(instructions_path), "mix-instructions.json missing"

# Duration check (if ffprobe available)
# ffprobe -v error -show_entries format=duration -of csv=p=0 output/final/final-mix.mp3

# Cross-check with script estimate
with open("pipelines/audio-ralph/output/script/parsed-script.json") as f:
    parsed = json.load(f)
expected_duration = parsed["estimated_total_duration_seconds"]
# Actual duration should be within 30% of expected
```

If ffprobe is available:
```bash
duration=$(ffprobe -v error -show_entries format=duration -of csv=p=0 output/final/final-mix.mp3)
echo "Final mix duration: ${duration}s"

# Check for clipping
peak=$(ffmpeg -i output/final/final-mix.mp3 -af "volumedetect" -f null /dev/null 2>&1 | grep max_volume)
echo "Peak: $peak"
```

## Gate Result Output

Write to `output/gate-05-result.json`:
```json
{
  "stage": "5-mix",
  "result": "PASS|WARN|FAIL",
  "checks": [
    { "name": "final_mix_exists", "passed": true, "detail": "final-mix.mp3 exists, 1.8MB" },
    { "name": "valid_audio", "passed": true, "detail": "Valid MP3, 192kbps stereo" },
    { "name": "duration", "passed": true, "detail": "46.1s (expected: 45.2s, within 30% tolerance)" },
    { "name": "manifest", "passed": true, "detail": "AUDIO-MANIFEST.md written" },
    { "name": "mix_instructions", "passed": true, "detail": "mix-instructions.json written" },
    { "name": "no_clipping", "passed": true, "detail": "Peak at -3.2 dBFS" }
  ],
  "warnings": ["Music bed not included (ACE-Step unavailable)"],
  "blocking_errors": [],
  "recommendation": "Pipeline complete"
}
```
