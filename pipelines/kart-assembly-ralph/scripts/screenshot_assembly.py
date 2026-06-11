"""Render 4-view screenshots of an assembled character-in-kart GLB."""
import bpy
import math
import sys
import os
from mathutils import Vector


def parse_args():
    argv = sys.argv
    if "--" in argv:
        argv = argv[argv.index("--") + 1:]
    else:
        return {}
    args = {}
    i = 0
    while i < len(argv):
        if argv[i] == "--input":
            args["input"] = argv[i + 1]; i += 2
        elif argv[i] == "--output-dir":
            args["output_dir"] = argv[i + 1]; i += 2
        elif argv[i] == "--prefix":
            args["prefix"] = argv[i + 1]; i += 2
        else:
            i += 1
    return args


def clear_scene():
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()
    for d in [bpy.data.armatures, bpy.data.meshes, bpy.data.materials,
              bpy.data.images, bpy.data.actions]:
        for item in list(d):
            d.remove(item)


def point_camera_at(cam, target, distance, angle_h, angle_v):
    x = target.x + distance * math.sin(angle_h) * math.cos(angle_v)
    y = target.y - distance * math.cos(angle_h) * math.cos(angle_v)
    z = target.z + distance * math.sin(angle_v)
    cam.location = Vector((x, y, z))
    direction = target - cam.location
    rot_quat = direction.to_track_quat('-Z', 'Y')
    cam.rotation_euler = rot_quat.to_euler()


def main():
    args = parse_args()
    input_path = args.get("input")
    output_dir = args.get("output_dir", ".")
    prefix = args.get("prefix", "assembly")

    os.makedirs(output_dir, exist_ok=True)

    clear_scene()
    bpy.ops.import_scene.gltf(filepath=input_path)
    bpy.context.view_layer.update()

    # Compute scene bounds
    all_verts = []
    for obj in bpy.data.objects:
        if obj.type == 'MESH':
            for v in obj.data.vertices:
                all_verts.append(obj.matrix_world @ v.co)

    if not all_verts:
        print("ERROR: No mesh vertices found")
        return

    min_co = Vector((min(v.x for v in all_verts), min(v.y for v in all_verts), min(v.z for v in all_verts)))
    max_co = Vector((max(v.x for v in all_verts), max(v.y for v in all_verts), max(v.z for v in all_verts)))
    center = (min_co + max_co) / 2
    size = max((max_co - min_co).length, 0.5)

    print(f"Scene bounds: {min_co} to {max_co}, center: {center}, size: {size:.2f}")

    # Setup render
    scene = bpy.context.scene
    scene.render.resolution_x = 800
    scene.render.resolution_y = 800
    scene.render.image_settings.file_format = 'PNG'
    scene.render.engine = 'BLENDER_WORKBENCH'
    scene.display.shading.light = 'STUDIO'
    scene.display.shading.color_type = 'MATERIAL'

    # Add camera
    bpy.ops.object.camera_add()
    cam = bpy.context.active_object
    scene.camera = cam
    cam.data.type = 'PERSP'
    cam.data.lens = 50

    dist = size * 1.2

    views = [
        ("front", 0, math.radians(15)),
        ("side", math.radians(90), math.radians(15)),
        ("34", math.radians(35), math.radians(25)),
        ("top", 0, math.radians(80)),
    ]

    for name, angle_h, angle_v in views:
        point_camera_at(cam, center, dist, angle_h, angle_v)
        filepath = os.path.join(output_dir, f"{prefix}-{name}.png")
        scene.render.filepath = filepath
        bpy.ops.render.render(write_still=True)
        print(f"Rendered: {filepath}")

    print("4-view screenshots complete")


if __name__ == "__main__":
    main()
