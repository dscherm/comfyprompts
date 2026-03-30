"""
Re-split character mesh into body regions with enforced gaps.
Fixes bridging faces by using boolean-style vertex deletion at region boundaries.

Proven parameters from Soapbox Sabotage pipeline:
- Head: horizontal cut at 83% height
- Arms: vertical cut at armpit X (torso outer edge at 58-65% height), above 52% Z
- Legs: 45-degree from hip center (42% height), capped at armpit X
- Torso: remainder
- Extract order: head -> arms -> legs -> torso

Usage:
    blender --background --python resplit_mesh.py -- input.glb output.glb [gap_cm]
"""

import bpy
import bmesh
import math
import sys
import os
from mathutils import Vector

argv = sys.argv
if "--" in argv:
    argv = argv[argv.index("--") + 1:]
else:
    argv = []

if len(argv) < 2:
    print("Usage: blender --background --python resplit_mesh.py -- input.glb output.glb [gap_cm]")
    sys.exit(1)

input_path = argv[0]
output_path = argv[1]
gap_cm = float(argv[2]) if len(argv) > 2 else 2.0  # minimum gap in cm
gap_m = gap_cm / 100.0  # convert to meters


def main():
    print(f"Input:  {input_path}")
    print(f"Output: {output_path}")
    print(f"Gap:    {gap_cm} cm ({gap_m} m)")

    # Clear and import
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()
    bpy.ops.import_scene.gltf(filepath=input_path)

    # Find the mesh (join all meshes if multiple)
    meshes = [obj for obj in bpy.data.objects if obj.type == 'MESH']
    if not meshes:
        print("ERROR: No mesh found")
        return

    if len(meshes) > 1:
        print(f"Joining {len(meshes)} mesh objects...")
        bpy.ops.object.select_all(action='DESELECT')
        for m in meshes:
            m.select_set(True)
        bpy.context.view_layer.objects.active = meshes[0]
        bpy.ops.object.join()

    obj = bpy.context.active_object
    if not obj or obj.type != 'MESH':
        obj = [o for o in bpy.data.objects if o.type == 'MESH'][0]
        bpy.context.view_layer.objects.active = obj

    print(f"Mesh: {obj.name}, {len(obj.data.vertices)} verts, {len(obj.data.polygons)} faces")

    # Get bounding box in world space
    bb = [obj.matrix_world @ Vector(c) for c in obj.bound_box]
    min_z = min(v.z for v in bb)
    max_z = max(v.z for v in bb)
    min_x = min(v.x for v in bb)
    max_x = max(v.x for v in bb)
    height = max_z - min_z
    width = max_x - min_x

    print(f"Bounds: height={height:.3f}m, width={width:.3f}m, Z=[{min_z:.3f}, {max_z:.3f}]")

    # Key heights (proven parameters)
    head_cut_z = min_z + height * 0.83
    armpit_z = min_z + height * 0.52
    hip_z = min_z + height * 0.42

    # Measure torso width at chest height (58-65% height)
    chest_z = min_z + height * 0.62
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bm.verts.ensure_lookup_table()

    # Find torso outer X at chest height (±5% tolerance)
    chest_verts = [v for v in bm.verts if abs((obj.matrix_world @ v.co).z - chest_z) < height * 0.05]
    if chest_verts:
        chest_xs = [(obj.matrix_world @ v.co).x for v in chest_verts]
        armpit_x_pos = max(chest_xs) * 0.85  # slightly inward from widest point
        armpit_x_neg = min(chest_xs) * 0.85
    else:
        armpit_x_pos = width * 0.15
        armpit_x_neg = -width * 0.15

    print(f"Cut planes: head_z={head_cut_z:.3f}, armpit_z={armpit_z:.3f}, hip_z={hip_z:.3f}")
    print(f"Armpit X: [{armpit_x_neg:.3f}, {armpit_x_pos:.3f}]")

    bm.free()

    # === REGION ASSIGNMENT ===
    # Assign each vertex to a region based on proven parameters
    # Use vertex groups for selection

    region_names = ["body_head", "body_arm_R", "body_arm_L", "body_legs", "body_torso"]
    for name in region_names:
        if name not in obj.vertex_groups:
            obj.vertex_groups.new(name=name)

    vg_head = obj.vertex_groups["body_head"]
    vg_arm_r = obj.vertex_groups["body_arm_R"]
    vg_arm_l = obj.vertex_groups["body_arm_L"]
    vg_legs = obj.vertex_groups["body_legs"]
    vg_torso = obj.vertex_groups["body_torso"]

    assigned = {"head": 0, "arm_r": 0, "arm_l": 0, "legs": 0, "torso": 0}

    for v in obj.data.vertices:
        co = obj.matrix_world @ v.co
        x, y, z = co.x, co.y, co.z

        # HEAD: above 83% height
        if z > head_cut_z:
            vg_head.add([v.index], 1.0, 'REPLACE')
            assigned["head"] += 1

        # ARMS: above armpit_z AND outside armpit_x (with gap buffer)
        elif z > armpit_z and x > (armpit_x_pos + gap_m):
            vg_arm_r.add([v.index], 1.0, 'REPLACE')
            assigned["arm_r"] += 1
        elif z > armpit_z and x < (armpit_x_neg - gap_m):
            vg_arm_l.add([v.index], 1.0, 'REPLACE')
            assigned["arm_l"] += 1

        # LEGS: below hip_z AND outside center column (with gap)
        elif z < hip_z:
            vg_legs.add([v.index], 1.0, 'REPLACE')
            assigned["legs"] += 1

        # TORSO: everything else (including gap zone vertices)
        else:
            vg_torso.add([v.index], 1.0, 'REPLACE')
            assigned["torso"] += 1

    print(f"\nRegion assignment:")
    for region, count in assigned.items():
        print(f"  {region}: {count} verts")

    # === DELETE GAP ZONE VERTICES ===
    # Remove vertices in the boundary zones to create physical gaps
    print(f"\n=== Enforcing {gap_cm}cm gaps ===")

    bpy.ops.object.mode_set(mode='EDIT')
    bm = bmesh.from_edit_mesh(obj.data)
    bm.verts.ensure_lookup_table()

    to_delete = []
    for v in bm.verts:
        co = obj.matrix_world @ v.co
        x, y, z = co.x, co.y, co.z

        # Gap zone between head and torso
        if abs(z - head_cut_z) < gap_m / 2:
            to_delete.append(v)
            continue

        # Gap zone between arms and torso (vertical strip at armpit X)
        if z > armpit_z and z < head_cut_z:
            if abs(x - armpit_x_pos) < gap_m or abs(x - armpit_x_neg) < gap_m:
                to_delete.append(v)
                continue

        # Gap zone between arms/torso and legs (horizontal strip at armpit_z)
        if abs(z - armpit_z) < gap_m / 2 and (x > armpit_x_pos or x < armpit_x_neg):
            to_delete.append(v)
            continue

        # Gap zone at hip level (between torso and legs)
        if abs(z - hip_z) < gap_m / 2:
            to_delete.append(v)
            continue

    print(f"  Deleting {len(to_delete)} gap-zone vertices")
    bmesh.ops.delete(bm, geom=to_delete, context='VERTS')
    bmesh.update_edit_mesh(obj.data)
    bpy.ops.object.mode_set(mode='OBJECT')

    print(f"  Remaining: {len(obj.data.vertices)} verts")

    # === SEPARATE BY VERTEX GROUPS ===
    print("\n=== Separating into objects ===")

    # Separate each region into its own object
    for region_name in ["body_head", "body_arm_R", "body_arm_L", "body_legs"]:
        bpy.ops.object.select_all(action='DESELECT')
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_all(action='DESELECT')

        # Select vertices in this group
        obj.vertex_groups.active = obj.vertex_groups[region_name]
        bpy.ops.object.vertex_group_select()

        # Separate selected
        try:
            bpy.ops.mesh.separate(type='SELECTED')
            print(f"  Separated: {region_name}")
        except Exception as e:
            print(f"  WARN: Could not separate {region_name}: {e}")

        bpy.ops.object.mode_set(mode='OBJECT')

    # Rename the remaining object (torso)
    obj.name = "body_torso"

    # Rename separated objects
    for new_obj in bpy.data.objects:
        if new_obj.type == 'MESH' and new_obj != obj:
            # Check which vertex group has the most verts
            best_group = None
            best_count = 0
            for vg in new_obj.vertex_groups:
                count = 0
                for v in new_obj.data.vertices:
                    for g in v.groups:
                        if g.group == vg.index:
                            count += 1
                            break
                if count > best_count:
                    best_count = count
                    best_group = vg.name

            if best_group and best_group.startswith("body_"):
                new_obj.name = best_group
                print(f"  Renamed: {new_obj.name} ({len(new_obj.data.vertices)} verts)")

    # === VALIDATE SEPARATION ===
    print("\n=== Validation ===")
    objects = [o for o in bpy.data.objects if o.type == 'MESH']
    print(f"Objects: {len(objects)}")
    for o in objects:
        bb = [o.matrix_world @ Vector(c) for c in o.bound_box]
        min_z_o = min(v.z for v in bb)
        max_z_o = max(v.z for v in bb)
        print(f"  {o.name}: {len(o.data.vertices)} verts, Z=[{min_z_o:.3f}, {max_z_o:.3f}]")

    # Check gaps between arm and leg objects
    arm_objects = [o for o in objects if "arm" in o.name.lower()]
    leg_objects = [o for o in objects if "leg" in o.name.lower()]

    for arm in arm_objects:
        arm_bb = [arm.matrix_world @ Vector(c) for c in arm.bound_box]
        arm_min_z = min(v.z for v in arm_bb)
        for leg in leg_objects:
            leg_bb = [leg.matrix_world @ Vector(c) for c in leg.bound_box]
            leg_max_z = max(v.z for v in leg_bb)
            gap = arm_min_z - leg_max_z
            print(f"  Gap {arm.name} <-> {leg.name}: {gap*100:.1f} cm")

    # === EXPORT ===
    print(f"\n=== Exporting to {output_path} ===")
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

    bpy.ops.object.select_all(action='DESELECT')
    for o in bpy.data.objects:
        if o.type == 'MESH':
            o.select_set(True)

    bpy.ops.export_scene.gltf(
        filepath=output_path,
        export_format='GLB',
        use_selection=True,
        export_animations=False,
    )

    size = os.path.getsize(output_path)
    print(f"Exported: {output_path} ({size:,} bytes)")
    print(f"Objects: {len([o for o in bpy.data.objects if o.type == 'MESH'])}")
    print("DONE")


main()
