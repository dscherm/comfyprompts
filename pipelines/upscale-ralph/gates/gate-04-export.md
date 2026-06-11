# Quality Gate 4: EXPORT (Final Gate)

## PASS Criteria (ALL must pass)
- [ ] Export directories exist under `output/exports/` for each configured preset
- [ ] Each preset directory contains one export per enhanced image
- [ ] All exported files are valid images (correct format per preset, >1KB)
- [ ] Exported dimensions match preset specifications (within 1px tolerance for rounding)
- [ ] File sizes are within preset limits (e.g., web_optimized <= 500KB, instagram <= 8MB)
- [ ] `output/exports/export-log.json` exists with entries for all exports
- [ ] `output/final/EXPORT-MANIFEST.md` exists with complete export listing

## WARN Criteria (log but don't block)
- [ ] Any export required aggressive quality reduction to meet file size limits
- [ ] Crop mode caused significant content loss for any preset (extreme aspect ratio mismatch)
- [ ] Print export DPI metadata could not be set (some viewers may ignore embedded DPI)
- [ ] Total export package size exceeds 500MB (large delivery)
- [ ] Watermark was configured but watermark image was not set (exports are unwatermarked)

## FAIL Criteria (block advancement)
- [ ] Any preset directory is empty (no exports for that platform)
- [ ] Any exported file is corrupt or zero bytes
- [ ] Exported dimensions are wildly wrong (>10% deviation from preset spec)
- [ ] More than 20% of individual exports failed
- [ ] `export-log.json` is missing or malformed
- [ ] `EXPORT-MANIFEST.md` is missing
- [ ] Print exports are not at full resolution (print quality compromised)

## Dimension Verification

Check each preset against its specification:
| Preset | Expected Width | Expected Height | Tolerance |
|--------|---------------|-----------------|-----------|
| instagram_square | 1080 | 1080 | +/- 1px |
| instagram_story | 1080 | 1920 | +/- 1px |
| twitter_banner | 1500 | 500 | +/- 1px |
| twitter_post | 1200 | 675 | +/- 1px |
| print_300dpi | varies (original aspect) | varies | must be >= enhanced resolution |
| web_optimized | <= 2048 long edge | <= 2048 long edge | long edge exactly 2048 or smaller |
| youtube_thumbnail | 1280 | 720 | +/- 1px |

## Validation Method
```bash
# Check export directories exist and have files
for preset in instagram_square twitter_banner print_300dpi web_optimized; do
  dir="pipelines/upscale-ralph/output/exports/$preset"
  if [ -d "$dir" ]; then
    count=$(ls -1 "$dir" | wc -l)
    echo "$preset: $count files"
  else
    echo "$preset: DIRECTORY MISSING"
  fi
done

# Verify manifest and log
for f in "output/exports/export-log.json" "output/final/EXPORT-MANIFEST.md"; do
  path="pipelines/upscale-ralph/$f"
  if [ -f "$path" ]; then
    echo "$f: OK"
  else
    echo "$f: MISSING"
  fi
done
```

## Gate Result Output
Write to `output/gate-04-result.json`:
```json
{
  "stage": "4-export",
  "result": "PASS|WARN|FAIL",
  "checks": [
    { "name": "preset_dirs_exist", "passed": true, "detail": "4/4 preset directories present" },
    { "name": "all_exports_present", "passed": true, "detail": "20/20 exports generated (5 images x 4 presets)" },
    { "name": "files_valid", "passed": true, "detail": "All exports valid and >1KB" },
    { "name": "dimensions_correct", "passed": true, "detail": "All exports match preset dimensions" },
    { "name": "file_sizes_within_limits", "passed": true, "detail": "All exports within platform size limits" },
    { "name": "export_log_exists", "passed": true, "detail": "export-log.json present" },
    { "name": "manifest_exists", "passed": true, "detail": "EXPORT-MANIFEST.md present and complete" }
  ],
  "warnings": [],
  "blocking_errors": [],
  "recommendation": "All exports complete and validated"
}
```

## Pipeline Completion
When this gate passes:
1. All 4 gates have passed
2. EXPORT-MANIFEST.md is the single source of truth for the delivery
3. Export directories contain ready-to-upload files for each platform
4. Output: `<promise>UPSCALE COMPLETE</promise>`
