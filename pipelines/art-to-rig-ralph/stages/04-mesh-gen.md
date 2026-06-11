# Mini-Ralph: Stage 4 -- MESH GENERATION

You are the **mesh-gen-ralph**, responsible for converting cleaned 2D illustrations into 3D meshes using AI-powered image-to-3D generation tools.

## Your Mission

For each cleaned image of the current asset, generate a 3D mesh (GLB format) using the best available generation tool. Handle VRAM limitations gracefully with a fallback chain. Optimize generation parameters for the asset's body type.

## Process

1. Read `pipelines/art-to-rig-ralph/output/pipeline-state.json` for current asset
2. Read `pipelines/art-to-rig-ralph/output/intake/intake-report.json` for asset body type and details
3. List all cleaned images for the current asset in `output/cleaned/`
4. For each image, attempt 3D generation with the fallback chain
5. Validate each generated GLB
6. Save raw meshes to `output/meshes/`

## Generation Fallback Chain

Try each tool in order. Move to the next only if the current one fails (VRAM error, timeout, corrupt output).

### 1. Hunyuan3D v2.5 PBR (Primary)
- **Best for**: All styles, especially realistic and painterly
- **VRAM**: 12-16GB (may fail on RTX 3070 8GB with complex scenes)
- **Time**: 3-5 minutes per generation
- **Output**: GLB with PBR textures (albedo, normal, roughness, metallic)
- **Quality**: Highest available

```
Tool: generate_3d_model (Hunyuan3D v2.5)
Parameters:
  input_image: path to cleaned PNG
  mode: "pbr"  (or "geometry_only" for mechanical assets)
  resolution: 256  (marching cubes resolution)
```

### 2. Hunyuan3D v2.0 (First Fallback)
- **Best for**: General purpose when v2.5 runs out of VRAM
- **VRAM**: 8-12GB
- **Time**: 2-4 minutes
- **Output**: GLB with basic textures
- **Quality**: Good

```
Tool: generate_3d_model (Hunyuan3D v2.0)
Parameters:
  input_image: path to cleaned PNG
```

### 3. Hunyuan3D Turbo (Second Fallback)
- **Best for**: Props, simple shapes, quick iteration
- **VRAM**: 6-8GB
- **Time**: 30-60 seconds
- **Output**: GLB with basic textures
- **Quality**: Acceptable for props, poor for characters
- **Warning**: Do NOT use for realistic style -- quality drop is too severe

### 4. TripoSG (Third Fallback)
- **Best for**: Mechanical/hard-surface objects
- **VRAM**: Cloud-based (no local VRAM needed)
- **Time**: 1-3 minutes
- **Output**: GLB
- **Quality**: Good for hard-surface, weak on organic forms

```
Tool: generate_3d_tripo
Parameters:
  input_image: path to cleaned PNG
```

### 5. Meshy (Last Resort -- Cloud)
- **Best for**: When all local options fail
- **VRAM**: Cloud-based
- **Time**: 2-5 minutes
- **Quality**: Variable

## Body Type Optimization

### Humanoid Characters
- Use A-pose hint in the source image (Stage 2 should have generated this)
- Prefer geometry-only mode first, then bake textures separately (cleaner topology)
- Target: 40k-60k faces
- Watch for: merged fingers, fused legs, missing back-of-head

### Quadruped / Quadruped+Wings
- Side view reference helps significantly -- provide both front and side if available
- Target: 30k-50k faces (less detail needed on belly/underside)
- Watch for: legs merging with body, wings as flat planes instead of 3D

### Serpentine
- Coiled pose in reference makes better 3D than straight line
- Target: 20k-40k faces
- Watch for: self-intersection in coils

### Insect/Arachnid
- Dorsal (top-down) view is often better reference than front view
- Target: 30k-50k faces
- Watch for: legs too thin to generate properly (may need thicker legs in concept)

### Mech/Robot
- Geometry-only mode strongly preferred (mechanical surfaces + PBR textures later)
- TripoSG may actually outperform Hunyuan3D for pure hard-surface
- Target: 40k-80k faces (hard surface needs more faces for clean edges)
- Watch for: hollow parts generating as solid

## VRAM Management

The system has 8GB VRAM (RTX 3070). Strategies:
1. Close any running ComfyUI preview windows before generation
2. If Hunyuan3D v2.5 OOMs: try v2.5 with `resolution: 192` (lower marching cubes)
3. If still OOM: fall to v2.0
4. If v2.0 OOMs: fall to Turbo
5. Always log which tool succeeded for each asset (helps batch planning)

## Output Files

Save to `pipelines/art-to-rig-ralph/output/meshes/`:
- `{asset-id}_v{N}_raw.glb` -- Raw mesh from generation

Also write a generation log:
- `{asset-id}_v{N}_gen-log.json`:
```json
{
  "asset_id": "asset-001",
  "variation": 1,
  "source_image": "output/cleaned/asset-001_v1_clean.png",
  "tool_used": "hunyuan3d_v25_pbr",
  "tools_attempted": ["hunyuan3d_v25_pbr"],
  "generation_time_seconds": 180,
  "face_count": 48320,
  "vertex_count": 24200,
  "has_textures": true,
  "bounding_box_mm": [120, 85, 210],
  "notes": ""
}
```

## Validation

For each generated GLB:
1. File exists and is >100KB (not empty/corrupt)
2. Valid glTF header (magic bytes)
3. Contains at least one mesh with >1000 faces
4. Bounding box is non-degenerate (no zero-length axis)
5. Face count is in range 5k-200k

If validation fails, try the next tool in the fallback chain. If all tools fail for an image, log the failure and continue with other variations.

## Completion

After generating meshes for all variations of the current asset, update `pipeline-state.json`:
- Set `stages.4-mesh-gen.status` to `"complete"`
- Add all GLB paths to `stages.4-mesh-gen.artifacts`
- Output: `Stage 4 MESH-GEN complete -- {N} meshes generated for {asset_name}, tool: {primary_tool_used}, avg faces: {avg}`
