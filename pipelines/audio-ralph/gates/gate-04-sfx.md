# Quality Gate 4: SOUND EFFECTS

## PASS Criteria (ALL must pass)
- [ ] `output/sfx/sfx-log.json` exists and is valid JSON
- [ ] At least 1 SFX file exists in `output/sfx/` (if script had SFX cues)
- [ ] Every SFX file listed in `sfx-log.json` with status "success" exists on disk and is >5KB
- [ ] Every SFX file has a duration that matches the requested duration within 50% tolerance

**Special case:** If the parsed script had zero SFX cues, this gate passes automatically with a note.

## WARN Criteria (log but don't block)
- [ ] Any SFX cue failed and could not be regenerated
- [ ] Fewer SFX files generated than cues in the script (some failed, but majority succeeded)
- [ ] Any SFX duration is very short (<1 second) when longer was expected
- [ ] Any SFX file is unusually large (>10MB, may indicate generation glitch)
- [ ] Stable Audio Open model not available (no SFX generated at all, but dialogue still works)

## FAIL Criteria (block advancement)
- [ ] `sfx-log.json` is missing or invalid JSON
- [ ] Script had SFX cues but zero SFX files were generated (complete failure)
- [ ] All SFX files are 0 bytes or corrupt
- [ ] More than 75% of SFX cues failed generation

## Validation Method

```python
import json, os

sfx_dir = "pipelines/audio-ralph/output/sfx"
log_path = os.path.join(sfx_dir, "sfx-log.json")

assert os.path.exists(log_path), "sfx-log.json missing"
with open(log_path) as f:
    log = json.load(f)

# Load parsed script to check expected cue count
with open("pipelines/audio-ralph/output/script/parsed-script.json") as f:
    parsed = json.load(f)
expected_cues = sum(1 for l in parsed["lines"] if l["type"] == "sfx")

if expected_cues == 0:
    print("No SFX cues in script -- gate passes automatically")
else:
    assert log["total_generated"] > 0, "No SFX files generated"
    failure_rate = log["total_failed"] / (log["total_generated"] + log["total_failed"])
    assert failure_rate < 0.75, f"Too many SFX failures: {failure_rate:.0%}"

    for cue in log["cues"]:
        if cue["status"] == "success":
            filepath = os.path.join(sfx_dir, cue["output_file"])
            assert os.path.exists(filepath), f"{cue['output_file']} missing"
            size = os.path.getsize(filepath)
            assert size > 5 * 1024, f"{cue['output_file']} too small: {size} bytes"
```

## Gate Result Output

Write to `output/gate-04-result.json`:
```json
{
  "stage": "4-sfx",
  "result": "PASS|WARN|FAIL",
  "checks": [
    { "name": "sfx_log_exists", "passed": true, "detail": "sfx-log.json valid" },
    { "name": "sfx_files_generated", "passed": true, "detail": "5/5 SFX cues generated" },
    { "name": "file_sizes", "passed": true, "detail": "All >5KB (min: 41KB, max: 312KB)" },
    { "name": "durations_valid", "passed": true, "detail": "All within 50% of requested duration" }
  ],
  "warnings": [],
  "blocking_errors": [],
  "recommendation": "Proceed to final mix"
}
```
