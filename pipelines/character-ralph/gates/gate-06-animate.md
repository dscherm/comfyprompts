# Quality Gate 6: ANIMATE

## PASS Criteria (ALL must pass)
- [ ] At least 3 animation files exist in `output/animated/`: idle, walk, run
- [ ] Each animation GLB is >50KB and contains animation data
- [ ] No mesh explosion in animations (vertices stay connected)

## WARN Criteria (log but don't block)
- [ ] Attack animation missing (acceptable for non-combat characters)
- [ ] Animation loop seam visible (start/end pose mismatch)
- [ ] Animation duration outside expected range

## FAIL Criteria (block advancement)
- [ ] Fewer than 2 animation files generated
- [ ] Animation files are corrupt or contain no keyframes
- [ ] Mesh is severely broken during animation playback

## Validation Method

### Animation file check
```bash
anim_dir="pipelines/character-ralph/output/animated"
for anim in anim-idle.glb anim-walk.glb anim-run.glb anim-attack.glb; do
  if [ -f "$anim_dir/$anim" ]; then
    size=$(stat --printf="%s" "$anim_dir/$anim")
    echo "$anim: ${size} bytes"
    if [ "$size" -lt 51200 ]; then
      echo "  WARNING: Animation file small, may lack keyframe data"
    fi
  else
    echo "$anim: MISSING ($([ "$anim" = "anim-attack.glb" ] && echo 'optional' || echo 'required'))"
  fi
done
```

### Gate Result Format
Write to `output/gate-06-result.json`:
```json
{
  "stage": "6-animate",
  "result": "PASS|WARN|FAIL",
  "checks": [
    { "name": "animation_count", "passed": true, "detail": "3/3 required animations present" },
    { "name": "animation_validity", "passed": true, "detail": "All GLBs contain keyframe data" },
    { "name": "no_mesh_explosion", "passed": true, "detail": "Mesh intact during playback" }
  ],
  "warnings": [],
  "blocking_errors": [],
  "recommendation": "Proceed to packaging (Stage 7)"
}
```
