"""Blender headless script: fix kart FBX orientation for Unity.

Reads each assembled _blender.glb, analyzes which direction the kart faces,
rotates the entire hierarchy so the front points toward Blender -Y (which the
FBX exporter maps to Unity +Z), then re-exports both FBX and GLB.

The problem: kart_assembler.py places empties along the auto-detected longest
axis but never rotates geometry to align that axis with Blender -Y. So depending
on the raw mesh orientation, karts may face any direction after FBX export.

Usage:
    blender --background --python fix_kart_orientation.py -- \
        --input-dir path/to/output/final \
        [--dry-run]

    Or fix a single kart:
    blender --background --python fix_kart_orientation.py -- \
        --input path/to/kart_blender.glb \
        --output-fbx path/to/kart_unity.fbx \
        --output-glb path/to/kart_blender.glb
"""

import bpy
import sys
import os
import json
import math
import argparse
from mathutils import Vector, Matrix

# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------
argv = sys.argv
if "--" in argv:
    argv = argv[argv.index("--") + 1:]
else:
    argv = []

parser = argparse.ArgumentParser(description="Fix kart orientation for Unity +Z forward.")
parser.add_argument("--input-dir", dest="input_dir", default=None,
                    help="Directory containing kart subdirectories (batch mode)")
parser.add_argument("--input", default=None, help="Single GLB file to fix")
parser.add_argument("--output-fbx", dest="output_fbx", default=None)
parser.add_argument("--output-glb", dest="output_glb", default=None)
parser.add_argument("--dry-run", dest="dry_run", action="store_true",
                    help="Analyze only, do not export")
args = parser.parse_args(argv)


# ---------------------------------------------------------------------------
# Orientation detection and fix logic
# ---------------------------------------------------------------------------

def find_child_recursive(obj, name):
    """Find a child object by name recursively."""
    for child in obj.children:
        if child.name == name:
            return child
        found = find_child_recursive(child, name)
        if found:
            return found
    return None


def get_kart_root(scene_objects):
    """Find the KartRoot empty in the scene."""
    for obj in scene_objects:
        if obj.name == "KartRoot" and obj.type == "EMPTY":
            return obj
    # Fallback: find root-level empty
    for obj in scene_objects:
        if obj.parent is None and obj.type == "EMPTY":
            return obj
    return None


def analyze_forward_direction(kart_root):
    """Determine which direction the kart faces based on named transforms.

    Returns a tuple: (current_forward_axis, needs_rotation, rotation_angle_deg)

    In Blender, we want the front of the kart (Bumper_Front, Axle_Front, Hood)
    to face -Y direction. The FBX exporter with axis_forward='-Z', axis_up='Y'
    then maps Blender -Y to Unity +Z (forward).

    We detect where front parts are relative to rear parts to find current forward,
    then compute the rotation needed to align with -Y.
    """
    # Find front/rear reference transforms
    bumper_front = find_child_recursive(kart_root, "Bumper_Front")
    bumper_rear = find_child_recursive(kart_root, "Bumper_Rear")
    axle_front = find_child_recursive(kart_root, "Axle_Front")
    axle_rear = find_child_recursive(kart_root, "Axle_Rear")
    hood = find_child_recursive(kart_root, "Hood")
    spoiler = find_child_recursive(kart_root, "Spoiler")

    # Collect front/rear world positions
    front_positions = []
    rear_positions = []

    if bumper_front:
        front_positions.append(bumper_front.matrix_world.translation.copy())
    if axle_front:
        front_positions.append(axle_front.matrix_world.translation.copy())
    if hood:
        front_positions.append(hood.matrix_world.translation.copy())

    if bumper_rear:
        rear_positions.append(bumper_rear.matrix_world.translation.copy())
    if axle_rear:
        rear_positions.append(axle_rear.matrix_world.translation.copy())
    if spoiler:
        rear_positions.append(spoiler.matrix_world.translation.copy())

    if not front_positions or not rear_positions:
        print("  WARNING: Cannot determine orientation — missing front/rear transforms")
        return None, False, 0

    # Average front and rear positions
    front_avg = sum(front_positions, Vector((0, 0, 0))) / len(front_positions)
    rear_avg = sum(rear_positions, Vector((0, 0, 0))) / len(rear_positions)

    # Forward vector: from rear toward front
    forward = front_avg - rear_avg
    forward.z = 0  # Project onto XY plane (ignore height)

    if forward.length < 0.001:
        print("  WARNING: Front and rear are at same position — cannot determine forward")
        return None, False, 0

    forward.normalize()

    # Target: -Y direction in Blender
    target = Vector((0, -1, 0))

    # Angle between current forward and target (in XY plane)
    angle = math.atan2(forward.x, -forward.y)  # Angle from -Y to forward
    angle_deg = math.degrees(angle)

    print(f"  Forward vector (XY): ({forward.x:.3f}, {forward.y:.3f})")
    print(f"  Current heading: {angle_deg:.1f} deg from -Y")
    print(f"  Front avg: ({front_avg.x:.3f}, {front_avg.y:.3f}, {front_avg.z:.3f})")
    print(f"  Rear avg: ({rear_avg.x:.3f}, {rear_avg.y:.3f}, {rear_avg.z:.3f})")

    # If within 5 degrees, no fix needed
    if abs(angle_deg) < 5:
        return "-Y", False, 0

    # Rotation needed: negate the angle to align with -Y, rotate around Z axis
    return f"{angle_deg:.1f}deg from -Y", True, -angle_deg


def apply_rotation_fix(kart_root, angle_deg):
    """Rotate the KartRoot around the Z axis (Blender up) by angle_deg.

    This rotates the entire hierarchy. After rotation, we apply the transform
    so the rotation is baked into vertex positions and child transforms.
    """
    # Select all objects in the hierarchy
    bpy.ops.object.select_all(action='DESELECT')

    def select_recursive(obj):
        obj.select_set(True)
        for child in obj.children:
            select_recursive(child)

    select_recursive(kart_root)
    kart_root.select_set(True)
    bpy.context.view_layer.objects.active = kart_root

    # Apply rotation to KartRoot
    angle_rad = math.radians(angle_deg)
    rot_matrix = Matrix.Rotation(angle_rad, 4, 'Z')

    # Rotate KartRoot
    kart_root.matrix_world = rot_matrix @ kart_root.matrix_world

    # Apply transforms on all objects so vertex data is updated
    # First, parent all children at their current world transforms
    bpy.ops.object.select_all(action='DESELECT')
    select_recursive(kart_root)
    bpy.context.view_layer.objects.active = kart_root

    # Apply rotation to root
    bpy.ops.object.select_all(action='DESELECT')
    kart_root.select_set(True)
    bpy.context.view_layer.objects.active = kart_root
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=False)

    # Apply on all children too
    def apply_transforms_recursive(obj):
        bpy.ops.object.select_all(action='DESELECT')
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj
        try:
            bpy.ops.object.transform_apply(location=False, rotation=True, scale=False)
        except Exception as e:
            print(f"  Warning: Could not apply transform on {obj.name}: {e}")
        for child in obj.children:
            apply_transforms_recursive(child)

    for child in kart_root.children:
        apply_transforms_recursive(child)

    print(f"  Applied {angle_deg:.1f} deg Z rotation to KartRoot and all children")


def fix_single_kart(glb_path, output_fbx=None, output_glb=None, dry_run=False):
    """Load a kart GLB, fix orientation, and re-export."""
    kart_name = os.path.basename(glb_path).replace("_blender.glb", "")
    print(f"\n{'='*60}")
    print(f"Processing: {kart_name}")
    print(f"{'='*60}")

    # Clean scene
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=glb_path)

    # Find KartRoot
    kart_root = get_kart_root(list(bpy.data.objects))
    if not kart_root:
        print(f"  ERROR: No KartRoot found in {glb_path}")
        return False

    print(f"  KartRoot found: {kart_root.name}")

    # Analyze orientation
    heading, needs_fix, angle_deg = analyze_forward_direction(kart_root)

    if not needs_fix:
        print(f"  Orientation OK — no fix needed")
        if dry_run:
            return True
    else:
        print(f"  NEEDS FIX: heading is {heading}, rotating {-angle_deg:.1f} deg around Z")

        if dry_run:
            return True

        apply_rotation_fix(kart_root, angle_deg)

        # Verify fix
        heading2, still_needs_fix, angle2 = analyze_forward_direction(kart_root)
        if still_needs_fix and abs(angle2) > 10:
            print(f"  WARNING: Post-fix heading still off by {angle2:.1f} deg")
        else:
            print(f"  Verification: orientation now correct")

    # Export FBX
    if output_fbx:
        os.makedirs(os.path.dirname(os.path.abspath(output_fbx)), exist_ok=True)
        bpy.ops.export_scene.fbx(
            filepath=output_fbx,
            use_selection=False,
            apply_scale_options="FBX_SCALE_ALL",
            axis_forward="-Z",
            axis_up="Y",
            object_types={"MESH", "EMPTY"},
            mesh_smooth_type="FACE",
            add_leaf_bones=False,
        )
        print(f"  Exported FBX: {output_fbx}")

    # Export GLB
    if output_glb:
        os.makedirs(os.path.dirname(os.path.abspath(output_glb)), exist_ok=True)
        bpy.ops.export_scene.gltf(
            filepath=output_glb,
            export_format="GLB",
            export_materials="EXPORT",
        )
        print(f"  Exported GLB: {output_glb}")

    return True


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
if args.input:
    # Single kart mode
    fix_single_kart(
        args.input,
        output_fbx=args.output_fbx,
        output_glb=args.output_glb,
        dry_run=args.dry_run,
    )
elif args.input_dir:
    # Batch mode — process all kart subdirectories
    input_dir = args.input_dir
    kart_dirs = sorted([
        d for d in os.listdir(input_dir)
        if os.path.isdir(os.path.join(input_dir, d)) and d.endswith("_kart")
    ])

    print(f"Found {len(kart_dirs)} kart directories in {input_dir}")

    results = {}
    for kart_dir in kart_dirs:
        kart_id = kart_dir
        glb_path = os.path.join(input_dir, kart_dir, f"{kart_id}_blender.glb")
        fbx_path = os.path.join(input_dir, kart_dir, f"{kart_id}_unity.fbx")
        glb_out = os.path.join(input_dir, kart_dir, f"{kart_id}_blender.glb")

        if not os.path.exists(glb_path):
            print(f"  SKIP: {glb_path} not found")
            results[kart_id] = "MISSING"
            continue

        success = fix_single_kart(
            glb_path,
            output_fbx=fbx_path if not args.dry_run else None,
            output_glb=glb_out if not args.dry_run else None,
            dry_run=args.dry_run,
        )
        results[kart_id] = "OK" if success else "FAILED"

    # Summary
    print(f"\n{'='*60}")
    print("BATCH SUMMARY")
    print(f"{'='*60}")
    for kart_id, status in results.items():
        print(f"  {kart_id}: {status}")
else:
    print("ERROR: Provide --input (single) or --input-dir (batch)")
    sys.exit(1)
