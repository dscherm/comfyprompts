# Quality Gate 3: VOICE CLONING

## PASS Criteria (ALL must pass)
- [ ] At least 1 audio file exists in `output/voiced/`
- [ ] Every dialogue line has a corresponding file in `output/voiced/` (either cloned or passthrough)
- [ ] Every voiced file is >5KB (not empty or corrupt)
- [ ] `output/voiced/voice-clone-log.json` exists and is valid JSON
- [ ] Number of voiced files matches number of TTS files from Stage 2

## WARN Criteria (log but don't block)
- [ ] All lines are passthrough (no RVC models available, voice cloning skipped entirely)
- [ ] Any RVC model referenced in voices config was not found (fallback to passthrough for that speaker)
- [ ] Any voiced file has significantly different duration from its TTS source (>30% difference)
- [ ] Fewer speakers were cloned than configured (some RVC models failed)
- [ ] `method` is `"passthrough"` for all lines (no voice differentiation achieved)

## FAIL Criteria (block advancement)
- [ ] No voiced files generated at all
- [ ] `voice-clone-log.json` is missing or invalid JSON
- [ ] More than 50% of voiced files are 0 bytes or corrupt
- [ ] Voiced files have drastically wrong durations (<0.1s or >10x the TTS source)
- [ ] Total processed count in log does not match expected dialogue line count

## Validation Method

```python
import json, os

voiced_dir = "pipelines/audio-ralph/output/voiced"
log_path = os.path.join(voiced_dir, "voice-clone-log.json")

assert os.path.exists(log_path), "voice-clone-log.json missing"
with open(log_path) as f:
    log = json.load(f)

assert log["total_processed"] > 0, "No lines processed"

for line in log["lines"]:
    filepath = os.path.join(voiced_dir, os.path.basename(line["output_file"]))
    assert os.path.exists(filepath), f"{line['output_file']} missing"
    size = os.path.getsize(filepath)
    assert size > 5 * 1024, f"{line['output_file']} too small: {size} bytes"
    assert line["status"] == "success", f"Line {line['line_number']} failed: {line.get('error', 'unknown')}"

# Cross-check with TTS log
tts_log_path = os.path.join("pipelines/audio-ralph/output/tts", "tts-log.json")
with open(tts_log_path) as f:
    tts_log = json.load(f)
tts_success_count = sum(1 for l in tts_log["lines"] if l["status"] == "success")
assert log["total_processed"] == tts_success_count, \
    f"Mismatch: {log['total_processed']} voiced vs {tts_success_count} TTS files"
```

## Gate Result Output

Write to `output/gate-03-result.json`:
```json
{
  "stage": "3-voice-clone",
  "result": "PASS|WARN|FAIL",
  "checks": [
    { "name": "voice_clone_log_exists", "passed": true, "detail": "voice-clone-log.json valid" },
    { "name": "files_exist", "passed": true, "detail": "8/8 voiced files present" },
    { "name": "file_sizes", "passed": true, "detail": "All >5KB" },
    { "name": "count_matches_tts", "passed": true, "detail": "8 voiced = 8 TTS (match)" }
  ],
  "warnings": ["All lines passthrough -- no RVC models configured"],
  "blocking_errors": [],
  "recommendation": "Proceed to SFX generation"
}
```
