# Quality Gate 1: PORTRAIT

## PASS Criteria (ALL must pass)
- [ ] `output/portrait/portrait.png` exists
- [ ] Image file is a valid PNG and >100KB (not blank or corrupt)
- [ ] Image shows a character portrait (face/bust visible)
- [ ] Subject matches the character description (verify via `caption_image` -- name, gender, key features should align)
- [ ] Image quality is acceptable (not severely blurry, not obviously deformed)

## WARN Criteria (log but don't block)
- [ ] Background is not clean/simple (may cause issues for downstream style transfer)
- [ ] Expression does not match character personality
- [ ] Seed file missing (`portrait-seed.txt`) -- reproducibility lost
- [ ] Caption file missing (`portrait-caption.txt`) -- validation less reliable

## FAIL Criteria (block advancement)
- [ ] No portrait image generated at all
- [ ] Image is blank, corrupt, or <10KB
- [ ] Image shows completely wrong subject (wrong gender, non-humanoid when humanoid expected, etc.)
- [ ] Image is severely deformed (multiple faces, broken anatomy, unrecognizable)
- [ ] Image has no discernible face or character

## Validation Method

### File check
```bash
portrait="pipelines/character-ralph/output/portrait/portrait.png"
if [ -f "$portrait" ]; then
  size=$(stat --printf="%s" "$portrait")
  echo "portrait.png: ${size} bytes"
  if [ "$size" -lt 102400 ]; then
    echo "FAIL: Image too small (<100KB), likely blank or corrupt"
  else
    echo "PASS: File exists with reasonable size"
  fi
else
  echo "FAIL: portrait.png does not exist"
fi
```

### Content check
Use `caption_image` on the portrait and compare the caption against the character description from `pipeline-state.json`. The caption should mention:
- Correct gender
- Key distinguishing features (hair color, distinctive marks, etc.)
- Portrait/bust framing
- Art style consistent with `style_config`

### Gate Result Format
Write to `output/gate-01-result.json`:
```json
{
  "stage": "1-portrait",
  "result": "PASS|WARN|FAIL",
  "checks": [
    { "name": "file_exists", "passed": true, "detail": "portrait.png exists, 245KB" },
    { "name": "file_size", "passed": true, "detail": "245KB > 100KB minimum" },
    { "name": "subject_match", "passed": true, "detail": "Caption mentions [key features]" },
    { "name": "quality_check", "passed": true, "detail": "No deformations detected" }
  ],
  "warnings": [],
  "blocking_errors": [],
  "recommendation": "Proceed to fullbody stage"
}
```
