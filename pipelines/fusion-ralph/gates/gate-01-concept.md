# Quality Gate 1: CONCEPT

## PASS Criteria (ALL must pass)
- [ ] At least 3 reference images exist in `output/concept/`
- [ ] Each image is a valid PNG, >50KB (not blank/corrupt)
- [ ] Front orthographic view exists (`ref-front.png`)
- [ ] At least one image has a clean/white background suitable for background removal

## WARN Criteria (log but don't block)
- [ ] Missing side view (3D gen can work from front-only, but quality drops)
- [ ] Missing detail callout sheet
- [ ] Images have strong shadows on background (may confuse bg removal)

## FAIL Criteria (block advancement)
- [ ] No images generated at all
- [ ] All images are blank, corrupt, or <10KB
- [ ] Images show completely wrong subject matter vs project description

## Validation Method
```bash
# Check files exist and have reasonable size
for f in ref-front.png ref-side.png ref-perspective.png ref-details.png; do
  if [ -f "output/concept/$f" ]; then
    size=$(stat -f%z "output/concept/$f" 2>/dev/null || stat --printf="%s" "output/concept/$f")
    echo "$f: ${size} bytes"
  else
    echo "$f: MISSING"
  fi
done
```
