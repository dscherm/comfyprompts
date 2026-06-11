# Quality Gate 1: Script Parsing

## PASS Criteria
- [ ] Script parsed into structured lines with speaker + text
- [ ] At least 1 dialogue line extracted
- [ ] SFX cues identified (if any in script)
- [ ] Output JSON written to `output/script/parsed-script.json`

## WARN Criteria
- [ ] No SFX cues found (acceptable for dialogue-only scripts)
- [ ] Some lines have ambiguous speaker attribution

## FAIL Criteria
- [ ] No lines extracted from script
- [ ] Script text is empty or unparseable
- [ ] Output JSON is invalid or missing
