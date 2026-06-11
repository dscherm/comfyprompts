# Quality Gate 2: MATERIAL-SCAN

## PASS Criteria (ALL must pass)
- [ ] `output/materials/material-palette.json` exists and is valid JSON
- [ ] `materials` array has at least 1 entry
- [ ] Every entry has a non-empty `name` field
- [ ] Every entry has `estimated_pbr` with both `metallic` and `roughness` values (numbers in [0.0, 1.0])
- [ ] Every entry where `mask_path` is non-null has the referenced file existing on disk
- [ ] Every entry where `crop_path` is non-null has the referenced file existing on disk

## WARN Criteria (log but don't block)
- [ ] Only 1 material identified (subject may have more regions that were missed)
- [ ] More than 6 materials identified (may cause downstream texture generation to be slow)
- [ ] Any material has `"pbr_source": "default"` (no keyword match -- PBR values are estimated)
- [ ] `overall_caption` is missing or very short (<20 characters)
- [ ] All `mask_path` entries are null (segmentation failed entirely -- will limit per-region texturing quality)
- [ ] Any mask file exists but is under 1KB (likely blank mask)

## FAIL Criteria (block advancement)
- [ ] `output/materials/material-palette.json` does not exist
- [ ] File is not valid JSON
- [ ] `materials` array is empty or missing
- [ ] Any material entry is missing both `name` and `region_description` (unidentifiable region)
- [ ] Any `estimated_pbr.metallic` or `estimated_pbr.roughness` value is outside [0.0, 1.0]
- [ ] A non-null `mask_path` points to a file that does not exist on disk
- [ ] A non-null `crop_path` points to a file that does not exist on disk

## Validation Method

### File existence and JSON validity
```bash
file="pipelines/skeuomorph-ralph/output/materials/material-palette.json"
if [ -f "$file" ]; then
  python -c "import json; d=json.load(open('$file')); print('JSON valid, material count:', len(d.get('materials', [])))"
else
  echo "FAIL: material-palette.json does not exist"
fi
```

### PBR value range check
```python
import json, os
palette = json.load(open("pipelines/skeuomorph-ralph/output/materials/material-palette.json"))
base = "pipelines/skeuomorph-ralph"
errors = []
warnings = []

for mat in palette.get("materials", []):
    mid = mat.get("id", "?")
    pbr = mat.get("estimated_pbr", {})
    m = pbr.get("metallic")
    r = pbr.get("roughness")
    if m is None or not (0.0 <= m <= 1.0):
        errors.append(f"FAIL: {mid} metallic={m} out of range")
    if r is None or not (0.0 <= r <= 1.0):
        errors.append(f"FAIL: {mid} roughness={r} out of range")
    for key in ("mask_path", "crop_path"):
        val = mat.get(key)
        if val is not None and not os.path.exists(os.path.join(base, val)):
            errors.append(f"FAIL: {mid} {key}='{val}' does not exist")
    if mat.get("pbr_source") == "default":
        warnings.append(f"WARN: {mid} used default PBR values (no keyword match)")

for e in errors: print(e)
for w in warnings: print(w)
if not errors:
    print(f"PASS: all {len(palette['materials'])} materials have valid PBR values and file references")
```

### Mask file size check
```bash
for mask in pipelines/skeuomorph-ralph/output/materials/masks/*.png; do
  size=$(stat --printf="%s" "$mask")
  if [ "$size" -lt 1024 ]; then
    echo "WARN: $mask is only ${size} bytes (may be blank mask)"
  else
    echo "OK: $mask is ${size} bytes"
  fi
done
```

## Gate Result Output

Write to `output/gate-02-result.json`:
```json
{
  "stage": "2-material-scan",
  "result": "PASS|WARN|FAIL",
  "checks": [
    { "name": "file_exists", "passed": true, "detail": "material-palette.json exists" },
    { "name": "valid_json", "passed": true, "detail": "JSON parsed successfully" },
    { "name": "materials_non_empty", "passed": true, "detail": "3 material(s) identified" },
    { "name": "pbr_values_valid", "passed": true, "detail": "All metallic/roughness in [0.0, 1.0]" },
    { "name": "mask_files_exist", "passed": true, "detail": "3/3 mask files exist on disk" },
    { "name": "crop_files_exist", "passed": true, "detail": "3/3 crop files exist on disk" }
  ],
  "warnings": ["mat-003 used default PBR values (keyword not matched)"],
  "blocking_errors": [],
  "recommendation": "Proceed to concept forge"
}
```
