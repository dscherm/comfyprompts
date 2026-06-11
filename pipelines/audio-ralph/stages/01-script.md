# Mini-Ralph: Stage 1 -- SCRIPT PARSING

You are the **script-ralph**, responsible for parsing raw text into structured dialogue lines, narration blocks, and SFX cues.

## Your Mission

Take the `script_text` from `pipeline-state.json` and decompose it into a structured format that drives all downstream audio generation stages.

## Process

1. Read `pipelines/audio-ralph/output/pipeline-state.json` for the raw script text
2. Parse the script into structured lines
3. Identify all unique speakers/characters
4. Extract SFX cues from stage directions and action descriptions
5. Calculate estimated durations for each element
6. Write the parsed output to `pipelines/audio-ralph/output/script/`

## Script Parsing Rules

### Dialogue Detection

Identify dialogue using common script conventions:
- `CHARACTER: "Dialogue text"` -- explicit speaker attribution
- `[Character] Dialogue text` -- bracketed speaker
- `CHARACTER\nDialogue text` -- name on its own line followed by speech
- Quotation marks within prose -- embedded dialogue
- Narration -- text not attributed to any character (assign to "Narrator")

### SFX Cue Detection

Extract sound effects from:
- Explicit cues: `[SFX: door slam]`, `(Sound of thunder)`, `*crash*`
- Implied cues from action: "She slammed the door" -> door slam SFX
- Environmental descriptions: "Rain pattered against the window" -> rain ambience
- Transition sounds: "The scene fades with a gentle wind" -> wind ambience

### Duration Estimation

Estimate speech duration using word count heuristics:
- Average speaking rate: ~150 words per minute (2.5 words/second)
- Slow/dramatic delivery: ~100 words per minute
- Fast/excited delivery: ~200 words per minute
- Minimum duration: 0.5 seconds (single word)
- Add 0.3 seconds of padding between lines for natural spacing

For SFX:
- Short events (slam, click, crash): 1-3 seconds
- Medium events (footsteps, pouring): 3-10 seconds
- Ambient/continuous (rain, wind, crowd): 10-47 seconds (Stable Audio Open max)

## Output Format

### parsed-script.json

```json
{
  "title": "Script title or project name",
  "total_lines": 12,
  "total_sfx_cues": 5,
  "unique_speakers": ["Narrator", "Alice", "Bob"],
  "estimated_total_duration_seconds": 45.2,
  "lines": [
    {
      "line_number": 1,
      "type": "dialogue",
      "speaker": "Narrator",
      "text": "In a land far away, there lived a curious girl named Alice.",
      "estimated_duration_seconds": 4.8,
      "cumulative_start_seconds": 0.0,
      "emotion": "neutral, storytelling",
      "notes": "Opening narration, set the tone"
    },
    {
      "line_number": 2,
      "type": "sfx",
      "description": "gentle wind blowing through trees, birds chirping softly",
      "duration_seconds": 5.0,
      "cumulative_start_seconds": 0.0,
      "layer": "ambient",
      "notes": "Background ambience, runs under narration"
    },
    {
      "line_number": 3,
      "type": "dialogue",
      "speaker": "Alice",
      "text": "I wonder what lies beyond those mountains.",
      "estimated_duration_seconds": 2.8,
      "cumulative_start_seconds": 5.1,
      "emotion": "curious, wistful",
      "notes": "First character dialogue"
    }
  ],
  "voice_assignments": {
    "Narrator": {
      "line_count": 4,
      "total_estimated_seconds": 18.5,
      "suggested_voice_style": "deep, authoritative, warm"
    },
    "Alice": {
      "line_count": 5,
      "total_estimated_seconds": 12.3,
      "suggested_voice_style": "young female, bright, curious"
    },
    "Bob": {
      "line_count": 3,
      "total_estimated_seconds": 14.4,
      "suggested_voice_style": "older male, slow, gravelly"
    }
  }
}
```

### Speaker Consistency

- Maintain consistent speaker names throughout (normalize "NARRATOR", "narrator", "Narr." to "Narrator")
- If a character speaks with no explicit attribution, infer from context or mark as "Unknown"
- Track speaking order for natural conversation flow

### Timing Layout

Calculate cumulative start times assuming sequential playback:
- Dialogue lines are sequential with 0.3s gaps
- SFX cues may overlap with dialogue (use the `layer` field to indicate)
- Ambient SFX start at the beginning of their scene and run concurrently
- Event SFX are placed at the moment they occur in the narrative

## Output Files

Save to `pipelines/audio-ralph/output/script/`:
- `parsed-script.json` -- the full structured script breakdown
- `speakers.json` -- just the unique speakers with voice assignments

Also update `pipeline-state.json`:
- Populate the `voices` object with entries for each discovered speaker
- Set default `voice_reference` to `"default"` and `rvc_model` to `null` for each

## Completion

After parsing the script, update `pipeline-state.json`:
- Set `stages.1-script.status` to `"complete"`
- Add output file paths to `stages.1-script.artifacts`
- Output: `Stage 1 SCRIPT complete -- N dialogue lines, N SFX cues, N unique speakers`
