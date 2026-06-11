"""Debug: find which bones influence the worst blend-zone vertex in hybrid-baked GLB."""
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
        else:
            i += 1
    return args


def main():
    args = parse_args()
    input_path = args.get("input")

    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()
    for d in [bpy.data.armatures, bpy.data.meshes, bpy.data.materials,
              bpy.data.images, bpy.data.actions]:
        for item in list(d):
            d.remove(item)

    bpy.ops.import_scene.gltf(filepath=input_path)
    bpy.context.view_layer.update()

    armature = None
    mesh = None
    for obj in bpy.data.objects:
        if obj.type == 'ARMATURE':
            armature = obj
        elif obj.type == 'MESH':
            mesh = obj

    # Find Hips VG
    hips_vg_idx = None
    for vg in mesh.vertex_groups:
        if vg.name.lower() == "hips":
            hips_vg_idx = vg.index
            break

    print(f"\nVertex groups ({len(mesh.vertex_groups)}):")
    for vg in mesh.vertex_groups:
        print(f"  [{vg.index}] {vg.name}")

    # Find blend-zone vertices (Hips weight 0.5-0.99)
    blend_verts = {}
    for v in mesh.data.vertices:
        hips_w = 0.0
        for g in v.groups:
            if g.group == hips_vg_idx:
                hips_w = g.weight
                break
        if 0.5 <= hips_w < 0.99:
            blend_verts[v.index] = {
                "hips_weight": hips_w,
                "world_pos": mesh.matrix_world @ v.co,
                "groups": [(mesh.vertex_groups[g.group].name, round(g.weight, 4)) for g in v.groups]
            }

    print(f"\nBlend-zone vertices: {len(blend_verts)}")

    # Pose arm +15 degrees
    bpy.context.view_layer.objects.active = armature
    bpy.ops.object.mode_set(mode='POSE')
    bpy.ops.pose.select_all(action='SELECT')
    bpy.ops.pose.transforms_clear()

    for pb in armature.pose.bones:
        if 'upperarm' in pb.name.lower():
            pb.rotation_mode = 'XYZ'
            pb.rotation_euler[0] = math.radians(15)
            print(f"  Posed: {pb.name} +15deg")

    bpy.context.view_layer.update()

    # Check displacement of blend verts
    depsgraph = bpy.context.evaluated_depsgraph_get()
    mesh_eval = mesh.evaluated_get(depsgraph)

    displacements = []
    for idx, info in blend_verts.items():
        rest_pos = info["world_pos"]
        posed_pos = mesh.matrix_world @ mesh_eval.data.vertices[idx].co
        disp = (posed_pos - rest_pos).length
        displacements.append((idx, disp, info))

    displacements.sort(key=lambda x: x[1], reverse=True)

    print(f"\nTop 20 worst blend-zone displacements (arm +15deg):")
    for idx, disp, info in displacements[:20]:
        print(f"  Vert {idx}: {disp*1000:.2f}mm, Hips={info['hips_weight']:.3f}")
        for name, w in info["groups"]:
            print(f"    {name}: {w}")

    bpy.ops.object.mode_set(mode='OBJECT')


if __name__ == "__main__":
    main()
