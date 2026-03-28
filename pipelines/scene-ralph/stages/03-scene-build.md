# Mini-Ralph: Stage 3 -- SCENE-BUILD

Assemble the 3D scene in Blender using blender-mcp.

## Process

1. Clear the Blender scene: `execute_blender_code("bpy.ops.wm.read_factory_settings(use_empty=True)")`
2. For each asset in the scene plan:
   a. Import GLB via `execute_blender_code` with import_glb snippet
   b. Position, rotate, and scale per the scene plan
   c. Rename the object for clarity
3. Add ground plane if specified
4. Set up 3-point lighting using scene_setup snippet
5. Take viewport screenshot: `get_viewport_screenshot()`
6. Review layout -- if objects overlap or look wrong, adjust positions
7. Take final layout screenshot

## Positioning Code Pattern

```python
import bpy
obj = bpy.data.objects.get("imported_object_name")
if obj:
    obj.location = (x, y, z)
    obj.rotation_euler = (rx, ry, rz)
    obj.scale = (s, s, s)
    obj.name = "descriptive_name"
```

## Ground Plane

```python
bpy.ops.mesh.primitive_plane_add(size=20, location=(0, 0, 0))
ground = bpy.context.active_object
ground.name = "Ground"
```

## Completion

Update pipeline-state.json. Output: `Stage 3 SCENE-BUILD complete -- {N} assets placed, layout verified`
