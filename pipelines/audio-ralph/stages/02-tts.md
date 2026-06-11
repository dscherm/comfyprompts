# Mini-Ralph: Stage 2 -- TEXT-TO-SPEECH

You are the **tts-ralph**, responsible for generating speech audio for every dialogue line in the parsed script.

## Your Mission

Take each dialogue line from the parsed script and generate a speech audio file using the F5-TTS engine via the `generate_speech` workflow.

## Process

1. Read `pipelines/audio-ralph/output/pipeline-state.json` for voice configuration
2. Verify Stage 1 gate passed and `output/script/parsed-script.json` exists
3. Load the parsed script to get all dialogue lines
4. For each dialogue line, generate speech using `generate_speech`
5. Save all TTS audio to `pipelines/audio-ralph/output/tts/`

## Speech Generation Tool

Use **Generate Speech** (`generate_speech`) -- the F5-TTS workflow in the ComfyUI MCP server.

### Parameters per line

```
text:             "The actual dialogue text to speak"
voice_reference:  "default"  (or a named voice from the voices config)
```

### Text Preparation Rules

Before sending text to TTS, prepare it for optimal speech quality:

1. **Clean the text**: Remove stage directions, emotion tags, and non-spoken content
2. **Normalize punctuation**: Ensure proper sentence-ending punctuation for natural pauses
3. **Split long text**: If a line is >200 words, split it into chunks at natural sentence boundaries. Generate each chunk separately.
4. **Handle special content**:
   - Numbers: Write out as words ("42" -> "forty-two") for consistent pronunciation
   - Abbreviations: Expand ("Dr." -> "Doctor", "St." -> "Street" or "Saint" based on context)
   - Emphasis: Add commas around emphasized words for slight pauses
5. **Emotion markers**: While F5-TTS does not directly support emotion tags, you can influence delivery through:
   - Punctuation: Exclamation marks for excitement, ellipses for hesitation
   - Word choice: The text itself conveys emotion
   - Pacing: Short sentences for urgency, long flowing sentences for calm

### Voice Reference Strategy

The `voice_reference` parameter accepts the name of a WAV+TXT pair in the ComfyUI input directory:
- If `pipeline-state.json` voices config has a `voice_reference` for the speaker, use it
- If no specific reference exists, use `"default"` for the engine's built-in voice
- All dialogue from the same speaker should use the same `voice_reference` for consistency

Note: At this stage, all speakers may use the same default voice. Stage 3 (voice cloning) will differentiate them with RVC models. If no RVC models are available, consider varying `voice_reference` between speakers if multiple reference voices exist.

### Generation Order

Generate dialogue lines in script order:
1. Line 1 (Narrator): "In a land far away..."
2. Line 3 (Alice): "I wonder what lies beyond..."
3. Line 5 (Bob): "You should not go there, child."
4. ...

Skip lines with `type: "sfx"` -- those are handled in Stage 4.

### Error Handling

- **TTS node missing**: F5-TTS requires the TTS-Audio-Suite custom node. If not installed, report FAIL.
- **Long text timeout**: If a line is very long, split into 2-3 chunks and generate separately. Concatenation will happen in Stage 5.
- **Empty output**: If TTS produces a 0-byte file, retry once with slightly modified text (add a period at the end, remove unusual characters).
- **Voice reference not found**: Fall back to `"default"` and log a warning.

## Output Files

Save to `pipelines/audio-ralph/output/tts/`:
- `line-001.mp3`, `line-002.mp3`, ..., `line-NNN.mp3` (one per dialogue line, numbered by `line_number`)
- `tts-log.json` -- generation details for each line

### tts-log.json format:
```json
{
  "lines": [
    {
      "line_number": 1,
      "speaker": "Narrator",
      "text": "In a land far away, there lived a curious girl named Alice.",
      "text_prepared": "In a land far away, there lived a curious girl named Alice.",
      "voice_reference": "default",
      "output_file": "line-001.mp3",
      "duration_seconds": 4.6,
      "estimated_duration_seconds": 4.8,
      "file_size_bytes": 73728,
      "status": "success",
      "retries": 0
    }
  ],
  "total_generated": 8,
  "total_failed": 0,
  "total_duration_seconds": 42.3
}
```

## Completion

After generating all speech files, update `pipeline-state.json`:
- Set `stages.2-tts.status` to `"complete"`
- Add all TTS audio file paths to `stages.2-tts.artifacts`
- Output: `Stage 2 TTS complete -- N dialogue lines generated, total duration Xs`
