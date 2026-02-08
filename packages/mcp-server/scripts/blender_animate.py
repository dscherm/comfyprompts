"""Blender Python script for generating procedural animations.

This script creates animations for rigged 3D models.
It supports various animation types like walk cycles, idle, etc.

Usage (called by external_app_manager.py):
    blender --background <blend_file> --python blender_animate.py -- <animation_type> [options_json]

Animation Types:
    walk: Walking cycle
    run: Running cycle
    idle: Breathing/idle animation
    wave: Waving gesture
    jump: Jump animation
    nod: Head nodding
    look_around: Looking left and right

Options (JSON):
    {
        "duration": 2.0,           # Animation duration in seconds
        "fps": 30,                 # Frames per second
        "loop": true,              # Make animation loop-friendly
        "intensity": 1.0,          # Animation intensity multiplier
        "output_path": "anim.glb", # Export path
        "output_format": "glb",    # glb, fbx, or blend
        "render_video": false,     # Render to MP4
        "video_path": "anim.mp4"   # Video output path
    }
"""

import sys
import os
import json
import math
from pathlib import Path

try:
    import bpy
    from mathutils import Vector, Euler, Quaternion
except ImportError:
    print("ERROR: This script must be run from within Blender")
    sys.exit(1)

# Add scripts directory to path so we can import the shared library
scripts_dir = os.path.dirname(os.path.abspath(__file__))
if scripts_dir not in sys.path:
    sys.path.insert(0, scripts_dir)

from animation_library import (
    get_armature,
    generate_animation,
    list_animations,
    ANIMATION_GENERATORS,
)


# ==================== EXPORT FUNCTIONS ====================

def export_animation(output_path, output_format):
    """Export the animated model."""
    ext = output_format.lower()

    if ext in ['glb', 'gltf']:
        bpy.ops.export_scene.gltf(
            filepath=output_path,
            export_format='GLB' if ext == 'glb' else 'GLTF_SEPARATE',
            export_animations=True,
            export_animation_mode='ACTIONS',
        )
    elif ext == 'fbx':
        bpy.ops.export_scene.fbx(
            filepath=output_path,
            bake_anim=True,
            bake_anim_use_all_actions=False,
        )
    elif ext == 'blend':
        bpy.ops.wm.save_as_mainfile(filepath=output_path)
    else:
        raise ValueError(f"Unsupported export format: {ext}")


def render_video(video_path, fps, frame_start, frame_end):
    """Render animation to video."""
    scene = bpy.context.scene

    # Setup render settings
    scene.render.fps = fps
    scene.frame_start = frame_start
    scene.frame_end = frame_end
    scene.render.image_settings.file_format = 'FFMPEG'
    scene.render.ffmpeg.format = 'MPEG4'
    scene.render.ffmpeg.codec = 'H264'
    scene.render.ffmpeg.constant_rate_factor = 'MEDIUM'
    scene.render.filepath = video_path

    # Setup camera if none exists
    if not any(obj.type == 'CAMERA' for obj in bpy.data.objects):
        bpy.ops.object.camera_add(location=(3, -3, 2))
        camera = bpy.context.active_object
        camera.rotation_euler = (math.radians(60), 0, math.radians(45))
        scene.camera = camera

    # Add basic lighting if none exists
    if not any(obj.type == 'LIGHT' for obj in bpy.data.objects):
        bpy.ops.object.light_add(type='SUN', location=(5, -5, 10))

    # Render
    bpy.ops.render.render(animation=True)


# ==================== MAIN ====================

def main():
    argv = sys.argv
    try:
        idx = argv.index("--") + 1
        args = argv[idx:]
    except (ValueError, IndexError):
        print("Usage: blender <file.blend> --python blender_animate.py -- <animation_type> [options_json]")
        print(f"Available animations: {list_animations()}")
        sys.exit(1)

    if len(args) < 1:
        print("ERROR: Missing animation type")
        sys.exit(1)

    animation_type = args[0]

    # Parse options
    options = {}
    if len(args) > 1:
        try:
            options = json.loads(args[1])
        except json.JSONDecodeError as e:
            print(f"Warning: Failed to parse options JSON: {e}")

    print(f"ComfyUI Animate: {animation_type}")
    print(f"Options: {options}")

    # Find armature
    armature = get_armature()
    if not armature:
        print("ERROR: No armature found in the file")
        sys.exit(1)

    print(f"Found armature: {armature.name} ({len(armature.pose.bones)} bones)")

    # Generate animation using shared library
    try:
        action = generate_animation(armature, animation_type, options)
    except ValueError as e:
        print(f"ERROR: {e}")
        sys.exit(1)

    print(f"Created animation: {action.name}")
    print(f"Frames: {bpy.context.scene.frame_start} - {bpy.context.scene.frame_end}")

    # Export if requested
    output_path = options.get('output_path')
    if output_path:
        output_format = options.get('output_format', 'glb')
        if not output_path.endswith(f'.{output_format}'):
            output_path = f"{output_path}.{output_format}"

        export_animation(output_path, output_format)
        print(f"Exported to: {output_path}")

    # Render video if requested
    if options.get('render_video'):
        video_path = options.get('video_path', output_path.replace('.glb', '.mp4') if output_path else 'animation.mp4')
        print(f"Rendering video to: {video_path}")
        render_video(
            video_path,
            options.get('fps', 30),
            bpy.context.scene.frame_start,
            bpy.context.scene.frame_end
        )
        print(f"Video rendered: {video_path}")

    # Save blend file if no other output specified
    if not output_path and not options.get('render_video'):
        bpy.ops.wm.save_mainfile()
        print("Saved animation to blend file")

    print(f"Successfully animated with {animation_type}")


if __name__ == "__main__":
    main()
