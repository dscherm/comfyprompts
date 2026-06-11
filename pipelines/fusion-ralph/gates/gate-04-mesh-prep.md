# Quality Gate 4: MESH PREPARATION

## PASS Criteria (ALL must pass)
- [ ] `output/prepared/prepared-model.glb` exists
- [ ] Mesh is manifold (0 non-manifold edges) — **hard requirement**
- [ ] All normals consistent (outward-facing)
- [ ] Zero degenerate faces
- [ ] Face count within 20k-100k range
- [ ] Minimum wall thickness >= print_specs.min_wall_mm
- [ ] Model scaled to correct real-world dimensions (mm)
- [ ] `output/prepared/prep-report.json` exists with operation log

## WARN Criteria (log but don't block)
- [ ] Decimation reduced faces by >60% (may have lost fine detail)
- [ ] Solidify modifier added significant volume (>10% volume increase)
- [ ] Some thin regions remain between min_wall and 2x min_wall

## FAIL Criteria (block — re-run Stage 4 with different parameters)
- [ ] Mesh still non-manifold after repair
- [ ] Normals still inconsistent after recalculation
- [ ] Wall thickness still below minimum after solidify
- [ ] Mesh volume is zero or negative (inside-out after repair)
- [ ] Prep script crashed (check error logs)

## Validation Method
Re-run audit checks on the prepared model:
```bash
python packages/mcp-server/scripts/validate_glb.py pipelines/fusion-ralph/output/prepared/prepared-model.glb
```
Plus Blender manifold check on prepared output.
