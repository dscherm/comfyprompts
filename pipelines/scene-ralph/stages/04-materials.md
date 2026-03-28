# Mini-Ralph: Stage 4 -- MATERIALS

Apply materials and environment lighting using both MCP servers.

## Process

1. **HDRI Environment** (blender-mcp):
   - Search Poly Haven: `search_polyhaven_assets(asset_type="hdris", categories="indoor|outdoor|studio")`
   - Download and apply: `download_polyhaven_asset(asset_id=..., asset_type="hdris")`

2. **Object Materials** (blender-mcp + comfyui-mcp):
   - For objects with material hints, search Poly Haven textures:
     `search_polyhaven_assets(asset_type="textures", categories="wood|metal|fabric")`
   - For custom textures, generate via comfyui-mcp:
     `generate_image(prompt="seamless {material} texture, tileable, PBR")` then
     `publish_for_blender(asset_id=...)` and apply via `execute_blender_code`
   - Apply materials via `set_texture(object_name=..., ...)` or `execute_blender_code`

3. **Screenshot**: `get_viewport_screenshot()` to verify materials look correct

## Material Application Code Pattern

```python
import bpy

# Create a new material
mat = bpy.data.materials.new(name="Wood")
mat.use_nodes = True
nodes = mat.node_tree.nodes
principled = nodes.get("Principled BSDF")

# Set base color
principled.inputs["Base Color"].default_value = (0.4, 0.25, 0.1, 1.0)

# Apply to object
obj = bpy.data.objects.get("Table")
if obj:
    obj.data.materials.clear()
    obj.data.materials.append(mat)
```

## Completion

Update pipeline-state.json. Output: `Stage 4 MATERIALS complete -- HDRI set, {N} materials applied`
