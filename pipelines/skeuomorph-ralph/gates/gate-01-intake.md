# Quality Gate 1: INTAKE

## PASS Criteria (ALL must pass)
- [ ] `output/intake/intake-report.json` exists
- [ ] `mode` field is one of `"A"`, `"B"`, `"C"`, or `"D"`
- [ ] `asset_type` field is one of `"character"`, `"creature"`, or `"prop"`
- [ ] `primary_image` field is set and the referenced file exists on disk
- [ ] `input_files` array is non-empty
- [ ] File is valid JSON (parseable without errors)

## WARN Criteria (log but don't block)
- [ ] `project_description` is empty or very short (<10 characters) -- downstream prompts will be generic
- [ ] Mode B detected but fewer than 3 frames extracted from video (very short clip)
- [ ] Mode C detected but `material_reference_files` array is empty (may have misclassified)
- [ ] `output_targets` array is missing or empty (will default to `["game"]`)
- [ ] `mode_rationale` field is absent (makes debugging harder)
- [ ] Mode D with 3D file but conversion to GLB failed (original format may still work downstream)
- [ ] Mode D with vector file but rasterization produced image below 512x512
- [ ] URL download was attempted but `yt-dlp` was not available (social media URL skipped)
- [ ] One or more URL downloads failed but other inputs remain valid

## FAIL Criteria (block advancement)
- [ ] `output/intake/intake-report.json` does not exist
- [ ] File is not valid JSON
- [ ] `mode` field is missing or has an unrecognized value (must be A, B, C, or D)
- [ ] `asset_type` field is missing or has an unrecognized value
- [ ] `primary_image` is set but the file it points to does not exist on disk
- [ ] `input_files` is empty or missing (nothing to process downstream)

## Validation Method

### File existence and JSON validity
```bash
file="pipelines/skeuomorph-ralph/output/intake/intake-report.json"
if [ -f "$file" ]; then
  python -c "import json; d=json.load(open('$file')); print('JSON valid'); print('mode:', d.get('mode')); print('asset_type:', d.get('asset_type')); print('primary_image:', d.get('primary_image'))"
else
  echo "FAIL: intake-report.json does not exist"
fi
```

### Primary image exists
```bash
primary=$(python -c "import json; print(json.load(open('pipelines/skeuomorph-ralph/output/intake/intake-report.json')).get('primary_image',''))")
if [ -f "pipelines/skeuomorph-ralph/$primary" ]; then
  echo "PASS: primary_image exists at $primary"
else
  echo "FAIL: primary_image '$primary' does not exist on disk"
fi
```

### Mode and asset_type validation
```python
import json
report = json.load(open("pipelines/skeuomorph-ralph/output/intake/intake-report.json"))
valid_modes = {"A", "B", "C", "D"}
valid_types = {"character", "creature", "prop"}
if report.get("mode") not in valid_modes:
    print(f"FAIL: invalid mode '{report.get('mode')}' -- must be A, B, or C")
if report.get("asset_type") not in valid_types:
    print(f"FAIL: invalid asset_type '{report.get('asset_type')}' -- must be character, creature, or prop")
if report.get("mode") in valid_modes and report.get("asset_type") in valid_types:
    print("PASS: mode and asset_type are valid")
```

## Gate Result Output

Write to `output/gate-01-result.json`:
```json
{
  "stage": "1-intake",
  "result": "PASS|WARN|FAIL",
  "checks": [
    { "name": "file_exists", "passed": true, "detail": "intake-report.json exists" },
    { "name": "valid_json", "passed": true, "detail": "JSON parsed successfully" },
    { "name": "valid_mode", "passed": true, "detail": "mode=A (valid)" },
    { "name": "valid_asset_type", "passed": true, "detail": "asset_type=character (valid)" },
    { "name": "primary_image_exists", "passed": true, "detail": "input/reference.jpg exists on disk" },
    { "name": "input_files_non_empty", "passed": true, "detail": "1 input file(s) registered" }
  ],
  "warnings": [],
  "blocking_errors": [],
  "recommendation": "Proceed to material scan"
}
```
