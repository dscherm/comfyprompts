# Mini-Ralph: Stage 5 -- RENDER

Set up camera and render the final scene.

## Process

1. **Camera placement** via `execute_blender_code`:
   - Position per scene plan or auto-frame all objects
   - Set focal length, depth of field if appropriate
2. **Render settings** via `execute_blender_code`:
   - Engine: EEVEE for fast preview, Cycles for quality
   - Resolution: 1920x1080 (default) or per spec
   - Samples: 128 (EEVEE) or 256 (Cycles)
   - Denoising: enabled
3. **Preview**: `get_viewport_screenshot()` for quick check
4. **Render**: Execute render to file via `execute_blender_code`
5. Save to `output/renders/`

## Render Code Pattern

```python
import bpy

scene = bpy.context.scene
scene.render.engine = 'BLENDER_EEVEE_NEXT'
scene.render.resolution_x = 1920
scene.render.resolution_y = 1080
scene.render.filepath = "//output/renders/scene_render.png"
scene.render.image_settings.file_format = 'PNG'

# Render
bpy.ops.render.render(write_still=True)
```

## Completion

Update pipeline-state.json. Output: `Stage 5 RENDER complete -- rendered at {resolution}`
