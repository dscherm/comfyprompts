# Blender snippet: Export the scene (or selected objects) to GLB
# Parameters: FILEPATH (output .glb path), SELECTED_ONLY ("True" or "False")
#
# Usage via blender-mcp:
#   execute_blender_code(code=snippet.replace("FILEPATH", path).replace("SELECTED_ONLY", "False"))

import bpy

filepath = "FILEPATH"
selected_only = "SELECTED_ONLY" == "True"

bpy.ops.export_scene.gltf(
    filepath=filepath,
    export_format='GLB',
    use_selection=selected_only,
    export_animations=True,
    export_skins=True,
)

import os
size = os.path.getsize(filepath) if os.path.exists(filepath) else 0
print(f"SUCCESS: Exported GLB to {filepath} ({size} bytes, selected_only={selected_only})")
