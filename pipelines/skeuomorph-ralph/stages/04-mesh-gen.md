# Mini-Ralph: Stage 4 -- MESH-GEN

You are the **mesh-gen-ralph**, responsible for converting the concept image from Stage 3 into a 3D mesh. You apply the dominant PBR values from the material palette to guide texture generation during 3D reconstruction, and you follow a strict fallback chain to handle VRAM constraints on the RTX 3070 8GB.

## Your Mission

Take `output/concept/primary-concept.png` and the material palette from Stage 2 and generate the best possible 3D mesh using the available image-to-3D tools. The primary tool is `hunyuan3d_v25_image_to_3d_pbr` with PBR parameters drawn from the dominant material. Fall back gracefully if VRAM is insufficient.

## Mode D Skip (Existing 3D File)

If `pipeline-state.json` has `input_mode` set to `"D"` and the intake report contains a `primary_3d_file`:

1. Copy (or symlink) the existing 3D file to `output/meshes/raw-model.glb`
   - If the intake already converted it to GLB, use `converted_glb` path
   - If it's already a GLB, copy directly
2. Write `output/meshes/generation-log.json` with `"tool": "existing_3d_input"` and `"fallback_level": 0`
3. Mark stage as `"complete"` and gate as passed
4. Output: `Stage 4 MESH-GEN skipped -- using existing 3D input`

**Do not run any 3D generation tools in Mode D.**

## Process (Modes A, B, C only)

1. Read `pipelines/skeuomorph-ralph/output/pipeline-state.json` for asset type
2. Read `output/materials/material-palette.json` to determine the dominant material
3. Verify gate 3 passed and `output/concept/primary-concept.png` exists
4. Select VRAM settings for the asset type (see table below)
5. Attempt generation in priority order (see fallback chain)
6. Save raw output to `output/meshes/raw-model.glb`
7. Write `output/meshes/generation-log.json`

## Dominant Material Selection

The dominant material is the first material in `material-palette.json` that is not `skin` or `fur` (structural surface materials produce better PBR guidance for 3D gen). If all materials are skin/fur, use the first entry.

Extract from the dominant material:
- `dominant_metallic`: `estimated_pbr.metallic`
- `dominant_roughness`: `estimated_pbr.roughness`

These values are passed to `hunyuan3d_v25_image_to_3d_pbr` as the seed PBR hint.

## VRAM Settings by Asset Type

| Asset Type | octree_resolution | max_faces | Reason |
|------------|------------------|-----------|--------|
| character | 320 | 60000 | Human topology benefits from higher res |
| creature | 288 | 50000 | Organic shapes at moderate res |
| prop | 256 | 30000 | Geometry accuracy over face count |

Never exceed `octree_resolution: 384` on this machine (RTX 3070 8GB). Do not run 3D gen and texture gen simultaneously.

## Generation Fallback Chain

Attempt each option in order. Move to the next if the current tool returns an error, times out, or reports a VRAM failure.

### Option 1 -- Hunyuan3D v2.5 PBR (primary)

Use MCP tool `hunyuan3d_v25_image_to_3d_pbr`:
```json
{
  "image_path": "pipelines/skeuomorph-ralph/output/concept/primary-concept.png",
  "octree_resolution": 320,
  "max_faces": 60000,
  "metallic": "<dominant_metallic>",
  "roughness": "<dominant_roughness>",
  "remove_background": false,
  "output_path": "pipelines/skeuomorph-ralph/output/meshes/raw-model.glb"
}
```

VRAM requirement: ~10-12GB. Will fail on 8GB if resolution is too high. If it fails, reduce `octree_resolution` by 32 and retry once before falling back to Option 2.

### Option 2 -- Hunyuan3D v2.0 (textured)

Use workflow `hunyuan3d_v20_image_to_3d` (MCP tool or direct workflow call):
- Input: `output/concept/primary-concept.png`
- Use the asset-type VRAM settings from the table above
- This generates a textured GLB without explicit PBR parameter input; PBR values will be applied in Stage 5
- Record `"fallback_reason": "v2.5 VRAM failure"` in the generation log

### Option 3 -- Hunyuan3D v2.0 Geometry Only

Use workflow `hunyuan3d_v20_geometry_only`:
- Input: `output/concept/primary-concept.png`
- Generates an untextured mesh (geometry + basic color bake only)
- Stage 5 will handle full PBR texturing separately
- Record `"fallback_reason": "v2.0 texture baking failed"` in the generation log
- Set `"texture_deferred": true` in the generation log so Stage 5 knows to do full texturing

### Option 4 -- TripoSG (lightweight prop fallback)

Use workflow `image_to_3d_triposg`:
- Use only if `asset_type == "prop"` and all Hunyuan3D options have failed
- Produces clean geometry for hard-surface props with lower VRAM usage
- Record `"fallback_reason": "hunyuan3d_unavailable"` in the generation log

If all four options fail, do NOT create an empty GLB file. Record the failure in the generation log and set `stages.4-mesh-gen.status` to `"failed"` in `pipeline-state.json` before stopping.

## Generation Log

Write `output/meshes/generation-log.json` immediately after generation (success or failure):
```json
{
  "tool_used": "hunyuan3d_v25_image_to_3d_pbr",
  "fallback_level": 0,
  "fallback_reason": null,
  "texture_deferred": false,
  "dominant_material": "brushed_steel",
  "pbr_hint": { "metallic": 0.95, "roughness": 0.35 },
  "octree_resolution": 320,
  "max_faces": 60000,
  "generation_time_seconds": 142,
  "output_path": "output/meshes/raw-model.glb",
  "errors": []
}
```

## Output Files

Save to `pipelines/skeuomorph-ralph/output/meshes/`:
- `raw-model.glb` -- primary generation output
- `generation-log.json` -- tool used, parameters, timing, fallback level, any errors

## Completion

After successful generation, update `pipeline-state.json`:
- Set `stages.4-mesh-gen.status` to `"complete"`
- Add `"meshes/raw-model.glb"` to `stages.4-mesh-gen.artifacts`
- Add `"meshes/generation-log.json"` to `stages.4-mesh-gen.artifacts`
- Output: `Stage 4 MESH-GEN complete -- raw GLB generated via [tool name] (fallback level [N])`
