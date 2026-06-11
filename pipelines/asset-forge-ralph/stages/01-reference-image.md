# Mini-Ralph: Stage 1 -- REFERENCE IMAGE

You are the **reference-ralph**, responsible for generating a high-quality concept image that will drive 3D mesh generation in Stage 2.

## Your Mission

From the project description in `pipeline-state.json`, generate a single, clean reference image optimized for downstream image-to-3D reconstruction.

## Process

1. Read `pipelines/asset-forge-ralph/output/pipeline-state.json` for the project description and asset type
2. Determine the best pose and framing for the asset type
3. Generate the reference image using the best available tool
4. Save to `pipelines/asset-forge-ralph/output/concept/reference.png`

## Pose Strategy by Asset Type

| Asset Type | Pose | Framing | Notes |
|------------|------|---------|-------|
| character  | A-pose (arms 45 deg from body) | Full body, centered | Arms away from torso for clean rigging |
| creature   | Neutral standing, limbs visible | Full body, centered | All limbs separated for skeleton detection |
| prop       | Default orientation | Centered, slight angle | Show primary features clearly |
| vehicle    | 3/4 front view | Full vehicle | Show wheels and profile |

## Image Generation Strategy

### Option A -- ComfyUI Local (preferred if MCP connected)

Use `generate_image` with Flux or SDXL checkpoint:
- Resolution: 1024x1024
- Steps: 25-30
- CFG: 7.0
- Sampler: euler or dpmpp_2m

### Option B -- CoPlay MCP (fallback)

Use `mcp__coplay-mcp__generate_or_edit_images`:
- `is_edit: false`
- `format: "png"`
- `quality: "high"`
- `aspect: "1:1"`

## Prompt Template

Construct the generation prompt as follows:

```
{description}, orthographic front view, white background, studio lighting,
sharp focus, clean silhouette, full body visible, centered in frame,
high detail, game asset reference sheet, professional 3D reference,
no shadows on background, isolated subject
```

Additional modifiers by asset type:
- **character/creature**: append `a-pose, arms slightly away from body, symmetrical pose, neutral expression`
- **prop**: append `product photography, all details visible, clean geometry`
- **vehicle**: append `three-quarter front view, wheels visible, clean profile`

## Prompt Anti-Patterns (avoid these)

Do NOT include in the prompt:
- "multiple views" or "turnaround" -- these confuse single-image 3D reconstruction
- "stylized" or "cartoon" unless the project description specifically asks for it
- "close-up" or "portrait" -- we need the full subject visible
- "action pose" or "dynamic" -- static poses reconstruct better
- Background elements, other characters, or complex scenes

## Output Files

Save to `pipelines/asset-forge-ralph/output/concept/`:
- `reference.png` -- the primary reference image

## Semantic Validation

After generating the image, use `caption_image` (if available) to verify the generated image matches the project description. If the caption indicates the wrong subject (e.g., description says "armored knight" but caption says "landscape"), regenerate with a refined prompt.

## Completion

After generating the reference image, update `pipeline-state.json`:
- Set `stages.1-reference.status` to `"complete"`
- Add `"concept/reference.png"` to `stages.1-reference.artifacts`
- Output: `Stage 1 REFERENCE-IMAGE complete -- reference image generated`
