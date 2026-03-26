# PROMPT.md — ComfyPrompts: Blender + ComfyUI AI Pipeline

## Context

@.ralph/pending_tasks.md
@.ralph/recent_activity.md
@.ralph/memories.md
@.ralph/gate_failure.md
@.ralph/human_note.md
@CLAUDE.md

Source code: `packages/`. Tests: `packages/*/tests/`. Workflows: `workflows/`.
Blender addons: `blender/`. ComfyUI installation: `C:\Users\Teacher\ComfyUI`.

## Your Task — 8-Phase Sequence

Follow these phases in order. ONE task per iteration.

### Phase 1: Orient

- Read pending tasks (above). Your task is the FIRST one listed.
- Read recent activity to understand what was just completed.
- Read memories for cross-iteration context.
- **If gate_failure.md is non-empty, FIX THE GATE FAILURE before starting any new task.**
- If human_note.md has content, follow those instructions.

### Phase 2: Search

- Before writing any code, search the codebase for existing implementations.
- Do not duplicate code that already exists. Extend or modify it instead.
- Use subagents for parallel codebase searches when helpful.
- Check both `blender/comfyui_tools/` and `blender/comfyui_mcp_tools/` before adding Blender operators.

### Phase 3: Implement

- Follow the task's `steps` array from pending_tasks.md.
- Full implementations only — no placeholders, no stubs, no TODOs.
- If the task cannot be completed, signal BLOCKED (see Phase 8).

### Phase 4: Verify

- Run targeted tests for the modules you changed:
  ```
  pytest packages/<package>/tests/ -v
  ```
- If you touched shared code (SDK client, config, credentials), run the full suite:
  ```
  pytest -x --tb=short -q
  ```
- If you touched Blender addon code, verify syntax:
  ```
  python -c "import py_compile; py_compile.compile('blender/<addon>/__init__.py')"
  ```

### Phase 5: Record

- Add an entry to `activity.md`:
  ```
  ## YYYY-MM-DD - Task N: Brief Title

  **Goal:** What was being accomplished

  **Changes Made:**
  - `file.py`: Description of change (specific values)

  **Verification:**
  - `pytest command` -- N passed, 0 failures

  **Status:** COMPLETE
  ```
- If you learned something non-obvious, add it to `.ralph/memories.md` with a unique ID
  (`mem-YYYYMMDD-NNN`), evidence, and tags.
- If you discovered new issues, add them as new JSON task blocks at the end of `plan.md`
  with appropriate priority.

### Phase 6: Mark

- In `plan.md`, find the JSON block for the task you completed.
- Change `"passes": false` to `"passes": true`.

### Phase 7: Commit

- Stage specific files by name. **NEVER use `git add -A` or `git add .`.**
  ```
  git add packages/sdk/src/file.py tests/test_file.py plan.md activity.md
  ```
- Commit with a structured message:
  ```
  type: brief description

  - Specific change 1
  - Specific change 2

  Verified: pytest command -- N passed, 0 failures
  ```
  Where `type` is: feat, fix, test, chore, refactor, docs.
- **NEVER push to remote.**

### Phase 8: Signal

- If ALL pending tasks are done: output `<promise>COMPLETE</promise>`
- If you cannot proceed (missing deps, unclear spec, needs human): output `<promise>BLOCKED</promise>`
- If you completed work but aren't confident: output `<promise>NEEDS_REVIEW</promise>`
- Otherwise: output nothing (the harness will start the next iteration).

## Rules

- **ONE task per iteration. Only one.**
- Fix gate failures before new work.
- No placeholders, stubs, or TODOs.
- For bugs you notice but don't fix, add them to `plan.md` as priority 1 tasks.
- Use parallel subagents for file search, but only 1 subagent for running tests.
- L-sized tasks (8-15 files): decompose into sequential subtasks in plan.md.
- XL-sized tasks (>15 files): output `<promise>SPAWN_REQUESTED</promise>`.

## Integration Notes

- **Blender MCP** is installed and available — the `comfyui_mcp_tools` addon communicates
  via MCP HTTP to the `comfyui-mcp` server.
- **ComfyUI** is at `C:\Users\Teacher\ComfyUI` — check models, custom nodes, and outputs there.
- **Two Blender addons** exist with different backends — don't conflate them.
  `comfyui_tools` uses Flask API (port 5050), `comfyui_mcp_tools` uses MCP.
- **SDK is shared** — both MCP server and Prompter depend on it. Changes to SDK must be
  tested across both consumers.

## Stack

- **SDK**: Python (comfyui-agent-sdk) — shared client, assets, defaults
- **MCP Server**: Python FastMCP — 40+ tools for AI generation
- **Prompter**: Python Tkinter + Flask — GUI and REST API
- **Blender Addons**: Python (Blender's bundled Python, no pip deps, urllib only)
- **Workflows**: JSON parametric templates with .meta.json sidecars
- **ComfyUI**: Local installation at C:\Users\Teacher\ComfyUI
- **Testing**: pytest, pytest-asyncio
