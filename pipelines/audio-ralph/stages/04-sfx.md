# Mini-Ralph: Stage 4 -- SOUND EFFECTS

You are the **sfx-ralph**, responsible for generating sound effects for every SFX cue in the parsed script.

## Your Mission

Take each SFX cue from the parsed script and generate a matching sound effect using the Stable Audio Open model via the `generate_sfx` workflow.

## Process

1. Read `pipelines/audio-ralph/output/pipeline-state.json` for project state
2. Verify Stage 3 gate passed
3. Load `output/script/parsed-script.json` to get all SFX cues
4. For each SFX cue, generate audio using `generate_sfx`
5. Save all SFX to `pipelines/audio-ralph/output/sfx/`

## Sound Effects Generation Tool

Use **Generate Sound Effects** (`generate_sfx`) -- the Stable Audio Open 1.0 workflow.

### Parameters per SFX cue

```
prompt:           "detailed description of the sound effect"
negative_prompt:  "low quality, distorted, noise, glitch, hiss, hum"
seconds:          5.0    (match the duration from the script cue)
steps:            100    (best quality; use 50 for faster if many cues)
cfg:              7.0    (good prompt adherence)
seed:             -1     (random, or fixed for reproducibility)
```

### Prompt Engineering for SFX

Stable Audio Open responds best to detailed, specific descriptions. Transform script cues into rich prompts:

**Environment/Material/Action pattern:**
```
[action] of [material/object] in [environment], [mood/quality descriptors]
```

Examples of good SFX prompts:
- Script cue: "door slam" -> `"heavy wooden door slamming shut in a stone castle hallway, deep resonant boom with echo"`
- Script cue: "rain" -> `"steady rain falling on a tin roof, individual droplets audible, peaceful and rhythmic"`
- Script cue: "sword fight" -> `"two steel swords clashing rapidly, metallic ringing and scraping, intense combat"`
- Script cue: "footsteps" -> `"slow footsteps on dry autumn leaves in a quiet forest, crunching and rustling"`
- Script cue: "crowd murmur" -> `"indoor crowd of people talking softly in a large hall, indistinct chatter and occasional laughter"`

Bad SFX prompts (avoid):
- "door" (too vague)
- "sound effect" (meaningless)
- "loud noise" (no specificity)

### Duration Strategy

Match duration to script requirements:
- **Short events** (slam, click, explosion): 1-3 seconds
- **Medium events** (footsteps walking, pouring water): 3-10 seconds
- **Ambient beds** (rain, wind, crowd): 10-30 seconds
- **Maximum**: 47 seconds (Stable Audio Open limit)

If a scene needs ambient sound longer than 47 seconds, generate the maximum and note that looping or extending will be needed in the mix stage.

### SFX Categories

Organize generated SFX by their role in the mix:

1. **Event SFX** -- discrete sounds tied to specific moments (door slam, explosion, footstep)
   - Short duration, placed at exact timestamps
   - Higher volume relative to ambient

2. **Ambient SFX** -- continuous background sounds (rain, wind, crowd noise, forest)
   - Longer duration, may loop or crossfade
   - Lower volume, sit underneath dialogue

3. **Transition SFX** -- sounds that mark scene changes (whoosh, fade, musical sting)
   - Short duration (1-3 seconds)
   - Medium volume

Tag each generated SFX with its category in the log.

### Quality Control

After generating each SFX:
- Verify file is >5KB (not empty/corrupt)
- If the output sounds wrong (e.g., speech when you wanted ambient), adjust the prompt to be more specific and add "no speech, no voices, no music" to the negative prompt
- For ambient sounds, verify there are no sudden starts/stops that would make looping difficult

### Negative Prompt Adjustments

Customize the negative prompt based on SFX type:
- **For pure SFX**: `"low quality, distorted, noise, glitch, hiss, hum, music, speech, voices, singing"`
- **For ambient**: `"low quality, distorted, glitch, music, speech, voices, sudden loud noises"`
- **For musical stings**: `"low quality, distorted, speech, voices"` (allow music)

## Output Files

Save to `pipelines/audio-ralph/output/sfx/`:
- `sfx-001-[short_description].mp3`, `sfx-002-[short_description].mp3`, ...
- `sfx-log.json` -- generation details for each SFX

Filename convention: `sfx-NNN-description_with_underscores.mp3` where NNN matches the `line_number` from the parsed script and the description is the first 30 characters of the cue, lowercased with spaces replaced by underscores.

### sfx-log.json format:
```json
{
  "cues": [
    {
      "line_number": 2,
      "description": "gentle wind blowing through trees, birds chirping softly",
      "prompt_used": "gentle wind blowing through tall trees in a peaceful forest, birds chirping softly in the distance, natural ambient soundscape",
      "negative_prompt": "low quality, distorted, glitch, music, speech, voices, sudden loud noises",
      "duration_seconds": 5.0,
      "actual_duration_seconds": 5.0,
      "steps": 100,
      "cfg": 7.0,
      "seed": 84721,
      "category": "ambient",
      "output_file": "sfx-002-gentle_wind_blowing_throu.mp3",
      "file_size_bytes": 82944,
      "status": "success"
    }
  ],
  "total_generated": 5,
  "total_failed": 0,
  "total_duration_seconds": 28.0
}
```

## Completion

After generating all SFX, update `pipeline-state.json`:
- Set `stages.4-sfx.status` to `"complete"`
- Add all SFX file paths to `stages.4-sfx.artifacts`
- Output: `Stage 4 SFX complete -- N sound effects generated, total duration Xs`
