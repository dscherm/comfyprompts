# Memories — ComfyPrompts

Cross-iteration learnings. Categorized, tagged, dated.
Each memory is 1-3 sentences with evidence (file paths, values, commands).

## Patterns

<!-- Codebase conventions, API behaviors, authority patterns -->

## Decisions

<!-- Architectural choices with rationale, especially "why NOT" -->

## Fixes

<!-- Bug solutions, especially multi-attempt fixes with root causes -->

- **mem-20260326-001** [bug] WorkflowManager defaults to `packages/mcp-server/workflows` but parametric workflows live at repo-root `workflows/mcp/`. Test `test_workflows_directory_exists` fails. Env var `COMFY_MCP_WORKFLOW_DIR` can override. Tags: workflow, path, mcp-server

## Context

<!-- Domain knowledge future iterations need -->
