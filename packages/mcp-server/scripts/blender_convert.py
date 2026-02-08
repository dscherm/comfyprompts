"""Blender Python script for converting 3D assets between formats.

This script is executed by Blender in background mode for format conversion.

Usage (called by external_app_manager.py):
    blender --background --python blender_convert.py -- <input_path> <output_path> <format>

Supported formats:
    glb: Binary glTF (recommended for most use cases)
    gltf: Text-based glTF with separate files
    fbx: Autodesk FBX (best for Unreal Engine)
    obj: Wavefront OBJ (legacy format)
"""

import sys
import os
from pathlib import Path

try:
    import bpy
except ImportError:
    print("ERROR: This script must be run from within Blender")
    sys.exit(1)


def clear_scene():
    """Clear all objects from the current scene."""
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)


def import_asset(filepath: str) -> bool:
    """Import a 3D asset based on its extension.

    Returns:
        True if import succeeded, False otherwise
    """
    path = Path(filepath)
    ext = path.suffix.lower()

    try:
        if ext in [".glb", ".gltf"]:
            bpy.ops.import_scene.gltf(filepath=filepath)
        elif ext == ".fbx":
            bpy.ops.import_scene.fbx(filepath=filepath)
        elif ext == ".obj":
            bpy.ops.wm.obj_import(filepath=filepath)
        else:
            print(f"ERROR: Unsupported input format: {ext}")
            return False

        print(f"Imported: {path.name}")
        return True

    except Exception as e:
        print(f"ERROR: Import failed: {e}")
        return False


def export_asset(filepath: str, format: str) -> bool:
    """Export the scene to a specific format.

    Args:
        filepath: Output file path
        format: Target format (glb, gltf, fbx, obj)

    Returns:
        True if export succeeded, False otherwise
    """
    # Select all mesh objects for export
    bpy.ops.object.select_all(action='DESELECT')
    for obj in bpy.data.objects:
        if obj.type in ('MESH', 'ARMATURE', 'EMPTY', 'CURVE'):
            obj.select_set(True)

    try:
        if format == "glb":
            bpy.ops.export_scene.gltf(
                filepath=filepath,
                export_format='GLB',
                use_selection=False,
                export_apply=True
            )

        elif format == "gltf":
            bpy.ops.export_scene.gltf(
                filepath=filepath,
                export_format='GLTF_SEPARATE',
                use_selection=False,
                export_apply=True
            )

        elif format == "fbx":
            bpy.ops.export_scene.fbx(
                filepath=filepath,
                use_selection=False,
                apply_scale_options='FBX_SCALE_ALL',
                path_mode='COPY',
                embed_textures=True
            )

        elif format == "obj":
            bpy.ops.wm.obj_export(
                filepath=filepath,
                export_selected_objects=False,
                export_materials=True,
                export_uv=True,
                export_normals=True
            )

        else:
            print(f"ERROR: Unsupported output format: {format}")
            return False

        print(f"Exported: {filepath}")
        return True

    except Exception as e:
        print(f"ERROR: Export failed: {e}")
        return False


def main():
    """Main entry point for the conversion script."""
    # Parse command line arguments (after --)
    argv = sys.argv
    try:
        arg_idx = argv.index("--") + 1
        args = argv[arg_idx:]
    except (ValueError, IndexError):
        print("ERROR: No arguments provided.")
        print("Usage: blender --background --python script.py -- <input> <output> <format>")
        sys.exit(1)

    if len(args) < 3:
        print("ERROR: Missing arguments.")
        print("Usage: blender --background --python script.py -- <input> <output> <format>")
        sys.exit(1)

    input_path = Path(args[0])
    output_path = Path(args[1])
    target_format = args[2].lower().lstrip(".")

    print(f"ComfyUI MCP Convert: {input_path} -> {output_path} ({target_format})")

    if not input_path.exists():
        print(f"ERROR: Input file not found: {input_path}")
        sys.exit(1)

    # Validate formats
    supported_formats = ["glb", "gltf", "fbx", "obj"]
    if target_format not in supported_formats:
        print(f"ERROR: Unsupported target format: {target_format}")
        print(f"Supported formats: {supported_formats}")
        sys.exit(1)

    # Clear the scene
    clear_scene()

    # Import the source asset
    if not import_asset(str(input_path.resolve())):
        sys.exit(1)

    # Ensure output directory exists
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Export to target format
    if not export_asset(str(output_path.resolve()), target_format):
        sys.exit(1)

    # Verify output was created
    if not output_path.exists():
        print("ERROR: Output file was not created")
        sys.exit(1)

    print(f"Conversion complete: {output_path}")
    print(f"Output size: {output_path.stat().st_size} bytes")


if __name__ == "__main__":
    main()
