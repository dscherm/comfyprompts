# Blender snippet: Import a GLB/GLTF file into the current scene
# Parameters: FILEPATH (absolute path to .glb or .gltf file)
#
# Usage via blender-mcp:
#   execute_blender_code(code=snippet.replace("FILEPATH", actual_path))

import bpy

filepath = "FILEPATH"

# Clear selection
bpy.ops.object.select_all(action='DESELECT')

# Import the file
bpy.ops.import_scene.gltf(filepath=filepath)

# Get the imported objects
imported = [obj for obj in bpy.context.selected_objects]

# Center the imported model at the world origin
if imported:
    # Find the mesh objects
    meshes = [obj for obj in imported if obj.type == 'MESH']
    if meshes:
        # Calculate combined bounding box
        from mathutils import Vector
        all_corners = []
        for obj in meshes:
            all_corners.extend(obj.matrix_world @ Vector(c) for c in obj.bound_box)
        min_co = Vector((min(v.x for v in all_corners), min(v.y for v in all_corners), min(v.z for v in all_corners)))
        max_co = Vector((max(v.x for v in all_corners), max(v.y for v in all_corners), max(v.z for v in all_corners)))
        center = (min_co + max_co) / 2

        # Report what was imported
        height = max_co.z - min_co.z
        print(f"Imported {len(imported)} objects ({len(meshes)} meshes), height={height:.3f}m, center={center}")
    else:
        print(f"Imported {len(imported)} objects (no meshes)")
else:
    print("Warning: No objects were imported")
