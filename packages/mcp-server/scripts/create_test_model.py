"""Create a simple test humanoid model for rigging tests."""
import os
import sys
try:
    import bpy
    from mathutils import Vector
except ImportError:
    print("ERROR: Run from Blender")
    sys.exit(1)

def create_simple_humanoid():
    """Create a very simple humanoid shape for rigging tests."""
    # Clear scene
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()

    # Create body (cylinder)
    bpy.ops.mesh.primitive_cylinder_add(
        radius=0.3, depth=1.2,
        location=(0, 0, 0.8)
    )
    body = bpy.context.active_object
    body.name = "Body"

    # Create head (sphere)
    bpy.ops.mesh.primitive_uv_sphere_add(
        radius=0.25,
        location=(0, 0, 1.65)
    )
    head = bpy.context.active_object
    head.name = "Head"

    # Left arm
    bpy.ops.mesh.primitive_cylinder_add(
        radius=0.08, depth=0.6,
        location=(0.5, 0, 1.1),
        rotation=(0, 1.57, 0)
    )
    arm_l = bpy.context.active_object
    arm_l.name = "Arm_L"

    # Right arm
    bpy.ops.mesh.primitive_cylinder_add(
        radius=0.08, depth=0.6,
        location=(-0.5, 0, 1.1),
        rotation=(0, 1.57, 0)
    )
    arm_r = bpy.context.active_object
    arm_r.name = "Arm_R"

    # Left leg
    bpy.ops.mesh.primitive_cylinder_add(
        radius=0.1, depth=0.8,
        location=(0.15, 0, 0.4)
    )
    leg_l = bpy.context.active_object
    leg_l.name = "Leg_L"

    # Right leg
    bpy.ops.mesh.primitive_cylinder_add(
        radius=0.1, depth=0.8,
        location=(-0.15, 0, 0.4)
    )
    leg_r = bpy.context.active_object
    leg_r.name = "Leg_R"

    # Join all meshes
    bpy.ops.object.select_all(action='SELECT')
    bpy.context.view_layer.objects.active = body
    bpy.ops.object.join()

    # Rename final object
    body.name = "Humanoid_Test"

    # Apply transforms
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)

    return body

def main():
    argv = sys.argv
    try:
        idx = argv.index("--") + 1
        output_path = argv[idx]
    except:
        output_path = os.path.join(os.path.dirname(__file__), '..', 'test_humanoid.glb')

    print(f"Creating test humanoid model...")
    model = create_simple_humanoid()

    # Export as GLB
    bpy.ops.export_scene.gltf(
        filepath=output_path,
        export_format='GLB',
        use_selection=True
    )
    print(f"Saved to: {output_path}")

if __name__ == "__main__":
    main()
