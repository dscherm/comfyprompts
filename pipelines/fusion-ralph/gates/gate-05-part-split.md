# Quality Gate 5: PART SPLIT & JOINTS

## PASS Criteria (ALL must pass)
- [ ] All part files exist in `output/parts/` and are valid GLBs
- [ ] `output/parts/assembly-guide.json` exists and is valid JSON
- [ ] Each part fits within the declared build volume individually
- [ ] Each part is manifold (watertight) independently
- [ ] Joint features present: pins/holes have correct dimensions with tolerance
- [ ] Clearance between mating surfaces >= print_specs.tolerance_mm
- [ ] Assembly guide specifies print orientation for each part

## WARN Criteria (log but don't block)
- [ ] A part has >50% overhangs (may need supports, but printable)
- [ ] Joint pin count <2 per face (may allow rotation — consider adding more)
- [ ] Part is very thin in one axis (<5mm — handle with care when printing)
- [ ] More than 6 parts total (complex assembly, verify necessity)

## FAIL Criteria (block — re-run Stage 5)
- [ ] Any part exceeds build volume
- [ ] Any part is non-manifold (split introduced open edges)
- [ ] Joint tolerances are wrong (clearance <0.1mm or >1mm for FDM)
- [ ] Parts don't geometrically fit together (boolean errors)
- [ ] Assembly guide missing or references nonexistent files
- [ ] No split performed when model exceeds build volume (mandatory split missed)

## Special Case: No Split Needed
If the model fits build volume and has acceptable overhangs:
- Gate passes with single part
- Assembly guide shows 1 part, no joints
- This is valid — not all models need splitting
