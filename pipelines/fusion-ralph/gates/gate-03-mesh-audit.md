# Quality Gate 3: MESH AUDIT

## PASS Criteria (ALL must pass)
- [ ] `output/validated/audit-report.json` exists and is valid JSON
- [ ] Audit report `overall` field is "PASS" or "WARN" (not "FAIL")
- [ ] No critical checks failed (file_integrity, non_empty_mesh)
- [ ] Bounding box fits within declared build volume (or can be split in Stage 5)

## WARN Criteria (log but don't block)
- [ ] Non-manifold edges detected (repairable in Stage 4)
- [ ] Overhangs >45deg on >40% of surface (will need supports or splitting)
- [ ] Wall thickness below minimum in some regions (repairable in Stage 4)
- [ ] Self-intersections detected (repairable but may need manual intervention)

## FAIL Criteria (block advancement — re-run Stage 2)
- [ ] Audit report `overall` is "FAIL"
- [ ] File integrity check failed (corrupt mesh)
- [ ] Mesh is fundamentally unprintable (all walls <0.5mm, no solid volume)
- [ ] Mesh has >50% degenerate faces (generation quality too low)

## Gate Logic
- If FAIL on geometry quality → re-trigger Stage 2 with modified generation parameters
- If WARN on repairables → advance to Stage 4 with repair instructions
- If PASS clean → advance to Stage 4 (still runs standard prep)
