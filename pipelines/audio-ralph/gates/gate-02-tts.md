# Quality Gate 2: TEXT-TO-SPEECH

## PASS Criteria (ALL must pass)
- [ ] At least 1 TTS audio file exists in `output/tts/`
- [ ] Every TTS audio file listed in `tts-log.json` exists on disk
- [ ] Every TTS audio file is >10KB (not empty or corrupt)
- [ ] Every TTS audio file has a duration >0.5 seconds
- [ ] `output/tts/tts-log.json` exists and is valid JSON
- [ ] Number of successful files matches number of dialogue lines in parsed script

## WARN Criteria (log but don't block)
- [ ] Any line required retries (may indicate text formatting issues)
- [ ] Any TTS duration differs from estimated by >50% (speech rate variance)
- [ ] Total generated duration differs from estimated total by >30%
- [ ] Any file is unusually large (>5MB for a single line, may indicate a generation glitch)
- [ ] 1-2 lines failed but were successfully regenerated

## FAIL Criteria (block advancement)
- [ ] No TTS files generated at all
- [ ] More than 50% of dialogue lines failed generation
- [ ] All TTS files are 0 bytes or corrupt
- [ ] `tts-log.json` is missing or invalid JSON
- [ ] F5-TTS engine not available (TTS-Audio-Suite custom nodes not installed)
- [ ] Any TTS file is pure silence (0 amplitude throughout)

## Validation Method

```python
import json, os

tts_dir = "pipelines/audio-ralph/output/tts"
log_path = os.path.join(tts_dir, "tts-log.json")

assert os.path.exists(log_path), "tts-log.json missing"
with open(log_path) as f:
    log = json.load(f)

assert log["total_generated"] > 0, "No TTS files generated"
failed_ratio = log["total_failed"] / (log["total_generated"] + log["total_failed"])
assert failed_ratio < 0.5, f"Too many failures: {log['total_failed']}/{log['total_generated'] + log['total_failed']}"

for line in log["lines"]:
    if line["status"] == "success":
        filepath = os.path.join(tts_dir, line["output_file"])
        assert os.path.exists(filepath), f"{line['output_file']} missing"
        size = os.path.getsize(filepath)
        assert size > 10 * 1024, f"{line['output_file']} too small: {size} bytes"
        assert line["duration_seconds"] > 0.5, f"Line {line['line_number']} too short: {line['duration_seconds']}s"
```

## Gate Result Output

Write to `output/gate-02-result.json`:
```json
{
  "stage": "2-tts",
  "result": "PASS|WARN|FAIL",
  "checks": [
    { "name": "tts_log_exists", "passed": true, "detail": "tts-log.json valid" },
    { "name": "files_generated", "passed": true, "detail": "8/8 lines generated successfully" },
    { "name": "file_sizes", "passed": true, "detail": "All >10KB (min: 32KB, max: 178KB)" },
    { "name": "durations", "passed": true, "detail": "All >0.5s (range: 1.2-4.8s)" },
    { "name": "no_failures", "passed": true, "detail": "0 failures, 0 retries" }
  ],
  "warnings": [],
  "blocking_errors": [],
  "recommendation": "Proceed to voice cloning"
}
```
