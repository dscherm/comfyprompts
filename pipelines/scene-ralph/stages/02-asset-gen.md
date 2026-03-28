# Mini-Ralph: Stage 2 -- ASSET-GEN

Generate 3D models for each asset in the scene plan using comfyui-mcp.

## Process

1. Read `output/parse/scene-plan.json` for asset list
2. For each asset:
   a. Generate 3D model via comfyui-mcp (use appropriate workflow -- Hunyuan3D for detailed, TripoSG for simple)
   b. Wait for generation to complete
   c. Publish to shared directory: `publish_for_blender(asset_id=...)`
   d. Record the published path in pipeline state
3. If a generation fails, retry once with adjusted prompt. If it fails again, log and skip.

## Choosing the Right Workflow

| Asset Type | Workflow | Notes |
|-----------|---------|-------|
| Organic/detailed | Hunyuan3D v2.0 | Best for characters, animals, plants |
| Hard surface | TripoSG | Good for furniture, vehicles, architecture |
| Simple props | Either | Small objects, quick generation |

## Output

For each asset:
- Published GLB in `output/shared/{asset-id}.glb`
- Asset record in pipeline-state.json

## Completion

Update pipeline-state.json. Output: `Stage 2 ASSET-GEN complete -- {N}/{total} assets generated`
