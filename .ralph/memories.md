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

- **mem-20260326-002** [context] ComfyUI 0.16.4 at C:\Users\Teacher\ComfyUI has only SD1.5 checkpoints (v1-5-pruned-emaonly, dreamshaper_8, 512-inpainting-ema) and one LoRA (blindbox_V1Mix). No ControlNets, no custom nodes. Most workflows reference flux1-dev-fp8.safetensors (not installed). Only basic_api_test could work with installed models but its JSON hardcodes flux1-dev-fp8 too. COMFYUI_OUTPUT_ROOT is NOT SET. Tags: comfyui, models, gap-analysis

- **mem-20260326-003** [context] basic_api_test.meta.json says checkpoint is `v1-5-pruned-emaonly.ckpt` but actual basic_api_test.json hardcodes `flux1-dev-fp8.safetensors` — meta/json mismatch. Tags: workflow, bug, basic_api_test
