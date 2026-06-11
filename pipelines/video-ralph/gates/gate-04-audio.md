# Quality Gate 4: AUDIO

## PASS Criteria (ALL must pass)
- [ ] At least 1 audio file exists in `output/audio/`
- [ ] `output/audio/audio-timing-plan.json` exists and is valid JSON
- [ ] Every dialogue audio file listed in the timing plan exists and is >10KB
- [ ] Every dialogue audio file has a duration >0.5 seconds (not a click or silence)
- [ ] Every SFX audio file listed in the timing plan exists and is >5KB
- [ ] Audio files are valid MP3 or WAV format

## WARN Criteria (log but don't block)
- [ ] Music bed (`music-bed.mp3`) was not generated (ACE-Step unavailable)
- [ ] Music bed duration does not match total video duration (within 20% tolerance)
- [ ] Any SFX duration differs from expected by >50%
- [ ] Fewer SFX files than SFX cues in the timing plan (some failed)
- [ ] Lip-sync was planned but not applied (Wav2Lip unavailable or no suitable face clips)
- [ ] Any audio file appears to be pure silence (no detectable signal)

## FAIL Criteria (block advancement)
- [ ] No audio files generated at all
- [ ] `audio-timing-plan.json` is missing or invalid
- [ ] All dialogue lines failed generation (TTS engine error)
- [ ] All audio files are 0 bytes or corrupt
- [ ] F5-TTS model failed to load (missing nodes or models)

## Validation Method

Check all audio files referenced in the timing plan:
```python
import json, os

audio_dir = "pipelines/video-ralph/output/audio"
plan_path = os.path.join(audio_dir, "audio-timing-plan.json")

assert os.path.exists(plan_path), "audio-timing-plan.json missing"
with open(plan_path) as f:
    plan = json.load(f)

# Check dialogue
for line in plan.get("dialogue", []):
    filepath = os.path.join(audio_dir, f"dialogue-{line['scene']:02d}.mp3")
    assert os.path.exists(filepath), f"Dialogue for scene {line['scene']} missing"
    size = os.path.getsize(filepath)
    assert size > 10 * 1024, f"Dialogue for scene {line['scene']} too small: {size} bytes"

# Check SFX
for cue in plan.get("sfx", []):
    filepath = os.path.join(audio_dir, f"sfx-{cue['scene']:02d}-{cue['description'][:20].replace(' ', '_')}.mp3")
    if os.path.exists(filepath):
        size = os.path.getsize(filepath)
        assert size > 5 * 1024, f"SFX '{cue['description']}' too small: {size} bytes"
    else:
        print(f"WARNING: SFX for scene {cue['scene']} missing: {cue['description']}")

# Check music (warn-only)
music_path = os.path.join(audio_dir, "music-bed.mp3")
if not os.path.exists(music_path):
    print("WARNING: music-bed.mp3 not generated")
```

## Gate Result Output

Write to `output/gate-04-result.json`:
```json
{
  "stage": "4-audio",
  "result": "PASS|WARN|FAIL",
  "checks": [
    { "name": "timing_plan_exists", "passed": true, "detail": "audio-timing-plan.json valid" },
    { "name": "dialogue_files", "passed": true, "detail": "3/3 dialogue lines generated, all >10KB" },
    { "name": "sfx_files", "passed": true, "detail": "4/5 SFX generated (1 optional cue skipped)" },
    { "name": "audio_durations", "passed": true, "detail": "All dialogue >0.5s, SFX within expected range" },
    { "name": "valid_formats", "passed": true, "detail": "All files valid MP3" }
  ],
  "warnings": ["Music bed not generated (ACE-Step unavailable)"],
  "blocking_errors": [],
  "recommendation": "Proceed to composite (without music bed)"
}
```
