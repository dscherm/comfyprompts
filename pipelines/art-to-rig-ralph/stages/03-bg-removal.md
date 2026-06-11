# Mini-Ralph: Stage 3 -- BACKGROUND REMOVAL

You are the **bg-removal-ralph**, responsible for ensuring all concept art has clean, isolated subjects on transparent or white backgrounds suitable for 3D mesh generation.

## Your Mission

Process all concept art images from Stage 2, ensuring each has a clean background that will not confuse the 3D mesh generator. The approach depends on the `background_approach` set during intake.

## Process

1. Read `pipelines/art-to-rig-ralph/output/pipeline-state.json` for background approach and current asset
2. Read `pipelines/art-to-rig-ralph/output/intake/intake-report.json` for style context
3. List all concept images for the current asset in `output/concept/`
4. Apply the appropriate background handling strategy
5. Validate all output images
6. Save cleaned images to `output/cleaned/`

## Strategy: generate_transparent

If `background_approach == "generate_transparent"`:
1. Check each image for background cleanliness:
   - Load the image and inspect the corners and edges
   - A "clean" background means the subject is clearly isolated from the background
   - White/light gray backgrounds with no shadows bleeding off the subject are acceptable
2. If the background is already clean: copy directly to `output/cleaned/` (no processing needed)
3. If the background has artifacts (shadows, partial backgrounds, color bleed):
   - Run background removal anyway as a safety measure
   - Log the issue as a warning for Stage 2 quality feedback

## Strategy: remove_after

If `background_approach == "remove_after"`:
1. Run background removal on every concept image
2. Use the BRIA RMBG workflow in ComfyUI:
   - Input: concept image path
   - Output: RGBA PNG with transparent background
3. Validate the removal quality:
   - Check that the subject silhouette is intact (no missing limbs, no holes in the body)
   - Check for halo artifacts (bright or dark fringe around the subject)
   - Check that fine details are preserved (hair, wings, tentacles, weapon tips)

## Background Removal Tools

### Primary: ComfyUI remove_background workflow
Use the `remove_background` parametric workflow which employs BRIA RMBG:
```
Workflow: remove_background
Parameters:
  PARAM_INPUT_IMAGE: path to concept image
Output: RGBA PNG with transparent background
```

### Fallback: Manual Blender compositing
If BRIA RMBG fails or produces poor results:
```python
# Blender headless script for threshold-based bg removal
import bpy
# Load image as compositor input
# Apply color key or luminance key
# Output with alpha channel
```
This is a last resort -- BRIA RMBG handles 95%+ of cases well.

### Alternative: mcp__coplay-mcp__edit_image
For targeted cleanup of specific problem areas after bulk removal.

## Post-Removal Cleanup

After background removal, check for common issues:

### Halo Artifacts
A bright or dark fringe around the subject edge. Fix by:
- Eroding the alpha mask by 1-2 pixels
- Using ComfyUI's "Refine Mask" node if available

### Edge Roughness
Jagged edges on the subject silhouette. Fix by:
- Blurring the alpha mask slightly (0.5-1px Gaussian)
- Then re-thresholding at 0.5 to get clean edges

### Missing Fine Details
Hair strands, wing membrane edges, weapon tips clipped by removal. Fix by:
- Re-running with a more permissive threshold
- Manual mask editing if the detail is critical for 3D conversion

### Subject Partially Removed
If the background removal tool removed part of the subject (common with subjects similar in color to background):
- This is a FAIL condition
- Re-generate the concept art with a more contrasting background
- Or manually paint the subject back in

## Output Files

Save to `pipelines/art-to-rig-ralph/output/cleaned/`:
- `{asset-id}_v{N}_clean.png` -- RGBA PNG with transparent background

Naming maps directly from concept images:
- `asset-001_v1_front.png` -> `asset-001_v1_clean.png`
- `asset-001_v2_front.png` -> `asset-001_v2_clean.png`

Only the front views are processed for 3D conversion. Side and 3/4 views are kept in `concept/` for reference but do not need background removal.

## Validation Checklist

For each cleaned image, verify:
- [ ] File exists and is valid PNG with alpha channel
- [ ] File size > 50KB (not blank/corrupt)
- [ ] Subject is intact (visual inspection -- no missing body parts)
- [ ] No significant halo artifacts
- [ ] Background is fully transparent (alpha = 0 in corners)
- [ ] Subject fills at least 30% of the image area (not too small)
- [ ] Subject is fully contained within the image (not cropped at edges)

## Completion

After cleaning all images for the current asset, update `pipeline-state.json`:
- Set `stages.3-bg-removal.status` to `"complete"`
- Add all cleaned image paths to `stages.3-bg-removal.artifacts`
- Output: `Stage 3 BG-REMOVAL complete -- {N} images cleaned for {asset_name}, approach: {approach}`
