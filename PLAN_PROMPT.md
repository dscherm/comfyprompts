# PLAN_PROMPT.md — ComfyPrompts Codebase Analysis

## Context

@CLAUDE.md

## Your Task — Read-Only Analysis

**DO NOT modify any code.** This is a read-only analysis pass.

You will analyze the ComfyPrompts codebase to discover issues, gaps, and improvements.
Output a prioritized list in `fix_plan.md`.

## Analysis Steps

### 1. Run Tests
```bash
pytest -x --tb=short -q
```
Record: total tests, passed, failed, errors, warnings.

### 2. Search for Issues

Scan the codebase for:
- **TODOs and FIXMEs** — `grep -rn "TODO\|FIXME\|HACK\|XXX" packages/ blender/`
- **Placeholder implementations** — Functions with `pass`, `raise NotImplementedError`, empty returns
- **Broken imports** — Modules that fail to import
- **Spec drift** — Code that contradicts CLAUDE.md conventions
- **Test gaps** — Source modules without corresponding test files
- **Hardcoded paths** — Windows-specific paths (`C:\`, `D:\`) that should use env vars
- **Missing error handling** — API calls without try/except, HTTP calls without timeouts
- **Stale workflows** — Parametric workflows referencing models that don't exist in ComfyUI

### 3. Check Integration Points
- SDK exports match what MCP server and Prompter import
- Blender addon class prefixes are correct (COMFYUI_OT_ vs COMFY_OT_)
- ComfyUI URL configuration flows through correctly
- Workflow PARAM_* placeholders all have meta.json definitions

### 4. Output fix_plan.md

Write `fix_plan.md` with this format:

```markdown
# fix_plan.md — ComfyPrompts Issues

## CRITICAL (broken tests, crashes, missing deps)
- [ ] Issue description — file:line, evidence

## HIGH (placeholders, spec drift, integration gaps)
- [ ] Issue description — file:line, evidence

## MEDIUM (TODOs, test gaps, quality improvements)
- [ ] Issue description — file:line, evidence

## LOW (style, docs, minor cleanup)
- [ ] Issue description — file:line, evidence
```

### 5. Signal

When analysis is complete: `<promise>PLAN_COMPLETE</promise>`
