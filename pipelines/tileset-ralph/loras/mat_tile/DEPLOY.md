# mat_tile — deploy receipt

- **Deployed:** 2026-07-17
- **Checkpoint:** `D:\Projects\ComfyUI\models\loras\style\mat_tile.safetensors`
  (final 1500-step checkpoint from `E:\ai-training\sdxl-output\mat_tile\`, TX2)
- **Sidecar:** `mat_tile.txt` — trigger `mat_tile`, **strength 0.6** single-pass
  (user verdict, TX3); wood uses the two-pass recipe (untiled at 0.8 →
  img2img denoise 0.35 with tiling; spec §6c)
- **Workflow:** `workflows/mcp/generate_texture_tile.json` — LoraLoader wired
  (PARAM_STR_LORA_NAME / PARAM_FLOAT_LORA_STRENGTH, inert at 0.0 by default);
  params documented in the .meta.json
- **Known limitation:** cobblestone-class prompts regress at strength ≥0.8
  (lilac plaster-bleed, eval/mat_tile_grid.md) — stay at 0.6
- **Smoke test:** rendered via the MCP server's WorkflowManager
  (`apply_workflow_overrides` on the registered workflow — the engine
  `generate_game_tileset` calls) with lora_name=style/mat_tile.safetensors,
  strength 0.6 against live ComfyUI: 22 s, **edge MAD 2.74% < 5%**
  (`eval/mat_tile_grid/tx4_smoke_manager_path.png`). Deviation note: the
  comfyui-mcp MCP transport wasn't connected in the deploying session, so the
  smoke exercised the identical code path one layer below the tool transport.
- **Provenance:** `mat_tile_manifest.md` (55 CC0 Poly Haven sources,
  user-approved dataset)
