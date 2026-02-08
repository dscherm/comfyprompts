"""Blender Python script for importing assets from ComfyUI MCP Server.

This script is executed by Blender when called via the external app manager.
It handles importing various file formats into Blender.

Usage (called by external_app_manager.py):
    blender --python blender_import.py -- <asset_path> <action>

Actions:
    import: Import the asset into a new Blender scene
"""

import sys
import os
from pathlib import Path

# Blender's Python module
try:
    import bpy
except ImportError:
    print("ERROR: This script must be run from within Blender")
    sys.exit(1)


def clear_scene():
    """Clear all objects from the current scene."""
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)


def import_gltf(filepath: str):
    """Import a glTF/GLB file."""
    bpy.ops.import_scene.gltf(filepath=filepath)


def import_fbx(filepath: str):
    """Import an FBX file."""
    bpy.ops.import_scene.fbx(filepath=filepath)


def import_obj(filepath: str):
    """Import an OBJ file."""
    bpy.ops.wm.obj_import(filepath=filepath)


def import_image_as_plane(filepath: str):
    """Import an image as a textured plane."""
    # Enable Images as Planes addon if not already enabled
    if "io_import_images_as_planes" not in bpy.context.preferences.addons:
        try:
            bpy.ops.preferences.addon_enable(module="io_import_images_as_planes")
        except Exception as e:
            print(f"Warning: Could not enable Images as Planes addon: {e}")
            # Fallback: just import as background image
            bpy.ops.object.empty_add(type='IMAGE')
            bpy.context.active_object.data = bpy.data.images.load(filepath)
            return

    bpy.ops.import_image.to_plane(files=[{"name": os.path.basename(filepath)}],
                                   directory=os.path.dirname(filepath))


def setup_camera_and_lighting():
    """Set up basic camera and lighting for viewing imported assets."""
    # Add camera if none exists
    if not any(obj.type == 'CAMERA' for obj in bpy.data.objects):
        bpy.ops.object.camera_add(location=(7, -7, 5), rotation=(1.1, 0, 0.8))
        camera = bpy.context.active_object
        bpy.context.scene.camera = camera

    # Add light if none exists
    if not any(obj.type == 'LIGHT' for obj in bpy.data.objects):
        bpy.ops.object.light_add(type='SUN', location=(5, 5, 10))
        light = bpy.context.active_object
        light.data.energy = 3.0


def frame_selected():
    """Frame the view on selected/imported objects."""
    # Select all mesh objects
    bpy.ops.object.select_all(action='DESELECT')
    for obj in bpy.data.objects:
        if obj.type in ('MESH', 'EMPTY'):
            obj.select_set(True)

    # Frame selected in 3D view
    for area in bpy.context.screen.areas:
        if area.type == 'VIEW_3D':
            for region in area.regions:
                if region.type == 'WINDOW':
                    override = bpy.context.copy()
                    override['area'] = area
                    override['region'] = region
                    with bpy.context.temp_override(**override):
                        bpy.ops.view3d.view_selected()
                    break


def main():
    """Main entry point for the import script."""
    # Parse command line arguments (after --)
    argv = sys.argv
    try:
        arg_idx = argv.index("--") + 1
        args = argv[arg_idx:]
    except (ValueError, IndexError):
        print("ERROR: No arguments provided. Usage: blender --python script.py -- <path> <action>")
        return

    if len(args) < 2:
        print("ERROR: Missing arguments. Usage: blender --python script.py -- <path> <action>")
        return

    asset_path = Path(args[0])
    action = args[1].lower()

    print(f"ComfyUI MCP Import: {asset_path} (action: {action})")

    if not asset_path.exists():
        print(f"ERROR: File not found: {asset_path}")
        return

    if action != "import":
        print(f"ERROR: Unknown action: {action}")
        return

    # Clear the default scene
    clear_scene()

    # Import based on file extension
    ext = asset_path.suffix.lower()
    filepath = str(asset_path.resolve())

    try:
        if ext in [".glb", ".gltf"]:
            import_gltf(filepath)
            print(f"Imported glTF: {asset_path.name}")

        elif ext == ".fbx":
            import_fbx(filepath)
            print(f"Imported FBX: {asset_path.name}")

        elif ext == ".obj":
            import_obj(filepath)
            print(f"Imported OBJ: {asset_path.name}")

        elif ext in [".png", ".jpg", ".jpeg", ".webp", ".exr", ".hdr"]:
            import_image_as_plane(filepath)
            print(f"Imported image: {asset_path.name}")

        else:
            print(f"ERROR: Unsupported format: {ext}")
            return

        # Set up scene for viewing
        setup_camera_and_lighting()
        frame_selected()

        print(f"Successfully imported: {asset_path.name}")

    except Exception as e:
        print(f"ERROR: Import failed: {e}")


if __name__ == "__main__":
    main()
