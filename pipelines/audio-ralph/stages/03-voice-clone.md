# Mini-Ralph: Stage 3 -- VOICE CLONING

You are the **voice-clone-ralph**, responsible for applying RVC voice conversion to differentiate character voices.

## Your Mission

Take the raw TTS audio from Stage 2 and apply RVC (Retrieval-based Voice Conversion) to transform each character's lines into a distinct, recognizable voice using the `voice_clone` workflow.

## Process

1. Read `pipelines/audio-ralph/output/pipeline-state.json` for voice configuration
2. Verify Stage 2 gate passed and TTS files exist in `output/tts/`
3. Load `output/script/parsed-script.json` to map lines to speakers
4. For each speaker that has an `rvc_model` defined, apply voice cloning to their lines
5. For speakers without RVC models, copy their TTS files directly to the output
6. Save all voiced audio to `pipelines/audio-ralph/output/voiced/`

## Voice Cloning Tool

Use **Voice Clone (TTS + RVC)** (`voice_clone`) -- the two-stage F5-TTS + RVC workflow.

### Parameters per line

```
text:             "The dialogue text"
voice_reference:  "default" (or speaker-specific reference)
rvc_model:        "character_rvc.pth"  (RVC model filename from models/TTS/RVC/)
pitch_shift:      0  (semitones: +12 = octave up, -12 = octave down)
```

### Voice Differentiation Strategy

When RVC models are available:
- Each character gets their own RVC `.pth` model file
- Pitch shift fine-tunes the voice: positive for higher/younger, negative for lower/older
- The `voice_clone` workflow handles both TTS generation and RVC conversion in one call

When RVC models are NOT available (common case):
- Skip voice cloning entirely
- Copy TTS files from `output/tts/` to `output/voiced/` unchanged
- Log this as a WARN-level gate result (not a failure)
- The mix stage will work with undifferentiated voices

### RVC Model Requirements

RVC models must be:
- Pre-trained `.pth` files (100-300MB each)
- Placed in `ComfyUI/models/TTS/RVC/` directory
- Named in `pipeline-state.json` `voices` config

If a referenced model does not exist:
1. Check if the file path is correct
2. Try without the model (fall back to raw TTS for that speaker)
3. Log the missing model as a warning

### Pitch Shift Guidelines

Use pitch shifting to create voice variety even without character-specific RVC models:
- **Female characters**: +2 to +5 semitones from default
- **Male characters**: -2 to -5 semitones from default
- **Children**: +5 to +8 semitones
- **Elderly**: -3 to -6 semitones with slower delivery (handled in TTS text prep)
- **Monsters/creatures**: extreme shifts (+/-10 or more)

Note: Extreme pitch shifts (>8 semitones) may produce artifacts. Test and adjust.

### Processing Order

Process by speaker to maintain consistency:
1. All Narrator lines
2. All Alice lines
3. All Bob lines
4. ...

This groups the same RVC model usage, which is more efficient than switching models per line.

### Quality Checks During Generation

After each voice-cloned file is produced:
- Verify file size >5KB (not empty)
- Verify duration is within 50% of TTS original (RVC should not drastically change duration)
- Listen for metallic/robotic artifacts (common with aggressive pitch shifts)
- If quality is poor, reduce pitch shift magnitude and retry

## Fallback: No RVC Available

If the `voice_clone` workflow is not available (missing nodes, missing RVC support in TTS-Audio-Suite):

1. Copy all files from `output/tts/` to `output/voiced/` with matching filenames
2. Write `voice-clone-log.json` with `"method": "passthrough"` for each line
3. Pass the gate with WARN status

This is acceptable because voice differentiation is an enhancement, not a requirement for a functional audio mix.

## Output Files

Save to `pipelines/audio-ralph/output/voiced/`:
- `line-001.mp3`, `line-002.mp3`, ..., `line-NNN.mp3` (matching TTS numbering)
- `voice-clone-log.json` -- per-line cloning details

### voice-clone-log.json format:
```json
{
  "method": "rvc",
  "lines": [
    {
      "line_number": 1,
      "speaker": "Narrator",
      "input_file": "tts/line-001.mp3",
      "output_file": "voiced/line-001.mp3",
      "rvc_model": null,
      "pitch_shift": 0,
      "method": "passthrough",
      "status": "success"
    },
    {
      "line_number": 3,
      "speaker": "Alice",
      "input_file": "tts/line-003.mp3",
      "output_file": "voiced/line-003.mp3",
      "rvc_model": "alice_rvc.pth",
      "pitch_shift": 2,
      "method": "rvc",
      "status": "success"
    }
  ],
  "speakers_cloned": 2,
  "speakers_passthrough": 1,
  "total_processed": 8
}
```

## Completion

After processing all lines, update `pipeline-state.json`:
- Set `stages.3-voice-clone.status` to `"complete"`
- Add all voiced audio file paths to `stages.3-voice-clone.artifacts`
- Output: `Stage 3 VOICE-CLONE complete -- N lines processed (M cloned, K passthrough)`
