# Mini-Ralph: Stage 6 -- REFINE

Optional AI enhancement and final polish.

## Process

1. Review the rendered image quality
2. If enhancement is needed:
   a. Use comfyui-mcp `generate_variations` or `upscale_image` on the render
   b. If texture issues are visible, regenerate specific textures and re-apply in Blender
   c. Re-render if scene changes were made
3. Save final outputs to `output/final/`
4. Write `output/final/SCENE-MANIFEST.md`

## When to Refine

- **Upscale**: If the render resolution needs to be higher than Blender rendered
- **Style transfer**: If a specific art style was requested (apply via img2img)
- **Texture fix**: If a material looks wrong in the render, fix and re-render
- **Skip**: If the render looks good, skip refinement entirely

## Scene Manifest

```markdown
# Scene: {project_name}

## Assets
| ID | Description | Source | Published Path |
|----|-------------|--------|---------------|
| chair-01 | Wooden chair | Hunyuan3D | output/shared/chair-01.glb |

## Render
- Resolution: {WxH}
- Engine: {engine}
- Samples: {N}
- Final render: output/final/scene_render.png

## Environment
- HDRI: {name}
- Lighting: 3-point
```

## Completion

Output: `<promise>SCENE COMPLETE</promise>`
