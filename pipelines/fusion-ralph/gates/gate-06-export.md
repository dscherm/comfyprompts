# Quality Gate 6: EXPORT (Final Gate)

## PASS Criteria (ALL must pass)
- [ ] All part STL files exist in `output/final/` and are >1KB
- [ ] Each STL has valid header (binary STL: 80-byte header + triangle count)
- [ ] Triangle counts match source GLB face counts (no data loss)
- [ ] Each STL is watertight (slicer-ready)
- [ ] Dimensions in STL match prepared model dimensions (unit conversion correct)
- [ ] `BUILD-MANIFEST.md` exists with complete bill of materials
- [ ] `FUSION-IMPORT-GUIDE.md` exists
- [ ] `export-report.json` exists with all validation results

## WARN Criteria (log but don't block)
- [ ] Total package size >100MB (large print job)
- [ ] Any single STL >50MB (may be slow in Fusion)
- [ ] Fusion mesh-to-BRep likely to fail (>10k faces per part)

## FAIL Criteria (block — re-run Stage 6)
- [ ] Any STL file missing or corrupt
- [ ] STL has zero triangles
- [ ] Dimensions wildly different from source (>5% deviation = unit error)
- [ ] BUILD-MANIFEST.md missing critical fields
- [ ] STL not watertight (open edges introduced during conversion)

## Final Validation
```bash
# Quick STL validation
for stl in pipelines/fusion-ralph/output/final/*.stl; do
  # Check binary STL: 80 header + 4 bytes triangle count + (50 * count) + 2
  size=$(stat --printf="%s" "$stl")
  echo "$stl: $size bytes"
done
```

## Pipeline Completion
When this gate passes:
1. All 6 gates have passed
2. BUILD-MANIFEST.md is the single source of truth for the print job
3. STL files are ready for Fusion 360 import or direct slicer use
4. Output: `<promise>PIPELINE COMPLETE</promise>`
