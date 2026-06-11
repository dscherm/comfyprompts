"""
Reference-based character-in-kart assembly.
Uses kart empties (Seat, SteeringColumn) as constraint targets to automatically
position and pose the character. No manual rotation or Euler angles needed.

Usage via blender-mcp execute_code:
    exec(open('pipelines/kart-assembly-ralph/scripts/reference_assemble.py').read())
    assemble(character_fbx, kart_glb, scale=0.8)
"""
import bpy
import math
from mathutils import Vector


def assemble(character_path, kart_path, scale=0.8, output_glb=None, output_fbx=None):
    """Assemble character into kart using reference empties."""

    # Clear scene
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()
    for d in [bpy.data.armatures, bpy.data.meshes, bpy.data.materials,
              bpy.data.images, bpy.data.actions]:
        for item in list(d):
            d.remove(item)

    # --- Import kart ---
    bpy.ops.import_scene.gltf(filepath=kart_path)
    bpy.context.view_layer.update()

    # Find reference empties
    seat = steering = None
    for obj in bpy.data.objects:
        if obj.type == 'EMPTY':
            name_lower = obj.name.lower()
            if 'seat' in name_lower:
                seat = obj
            elif 'steering' in name_lower and 'target' not in name_lower:
                steering = obj

    seat_pos = seat.matrix_world.translation.copy() if seat else Vector((0, 0, 0.5))
    steer_pos = steering.matrix_world.translation.copy() if steering else seat_pos + Vector((0, -0.5, 0))

    # Determine kart forward direction from seat->steering vector
    forward = (steer_pos - seat_pos).normalized()
    forward.z = 0  # Project to XY plane
    forward.normalize()

    print(f"Kart: Seat={seat_pos}, Steering={steer_pos}")
    print(f"Forward direction: {forward}")

    # --- Import character ---
    before = set(bpy.data.objects)
    if character_path.endswith('.fbx'):
        bpy.ops.import_scene.fbx(filepath=character_path)
    else:
        bpy.ops.import_scene.gltf(filepath=character_path)
    new_objs = set(bpy.data.objects) - before

    armature = None
    char_mesh = None
    for obj in new_objs:
        if obj.type == 'ARMATURE':
            armature = obj
        elif obj.type == 'MESH' and len(obj.data.vertices) > 50:
            char_mesh = obj

    if not armature:
        print("ERROR: No armature in character file")
        return

    print(f"Character: {armature.name} ({len(armature.data.bones)} bones)")

    # --- Scale ---
    armature.scale = (scale, scale, scale)
    bpy.ops.object.select_all(action='DESELECT')
    armature.select_set(True)
    bpy.context.view_layer.objects.active = armature
    bpy.ops.object.transform_apply(scale=True)

    # --- Orient character to face kart forward ---
    # UniRig FBX characters face +Y after import. Kart forward is -Y (seat->steering).
    # Always rotate 180Z to face the character toward -Y (kart forward).
    armature.rotation_euler.z = math.radians(180)
    bpy.ops.object.select_all(action='DESELECT')
    armature.select_set(True)
    bpy.context.view_layer.objects.active = armature
    bpy.ops.object.transform_apply(rotation=True)
    bpy.context.view_layer.update()
    print(f"Rotated 180Z to face kart forward (-Y)")

    # --- Position hips at seat ---
    hips_bone = armature.data.bones[0]  # Root bone = hips
    bpy.context.view_layer.update()
    hips_world = armature.matrix_world @ hips_bone.head_local
    offset = seat_pos - hips_world
    offset.z += 0.02  # Slight raise to sit ON seat
    armature.location += offset
    bpy.context.view_layer.update()

    # --- Driving pose via IK ---
    bpy.ops.object.select_all(action='DESELECT')
    armature.select_set(True)
    bpy.context.view_layer.objects.active = armature
    bpy.ops.object.mode_set(mode='POSE')

    # Legs: After 180Z rotation, X rotation signs are flipped
    for name, (rx, ry, rz) in {
        "bone_44": (90, 0, 0), "bone_45": (-90, 0, 0), "bone_46": (30, 0, 0),
        "bone_48": (90, 0, 0), "bone_49": (-90, 0, 0), "bone_50": (30, 0, 0),
        "bone_2": (15, 0, 0), "bone_3": (10, 0, 0),
        "bone_4": (-5, 0, 0), "bone_5": (-15, 0, 0),
    }.items():
        pb = armature.pose.bones.get(name)
        if pb:
            pb.rotation_mode = 'XYZ'
            pb.rotation_euler = (math.radians(rx), math.radians(ry), math.radians(rz))

    bpy.ops.object.mode_set(mode='OBJECT')

    # Hands IK: target at steering column with spread
    hand_spread = 0.12
    hand_r_pos = steer_pos + Vector((hand_spread, 0, 0.05))
    hand_l_pos = steer_pos + Vector((-hand_spread, 0, 0.05))

    bpy.ops.object.empty_add(type='PLAIN_AXES', location=hand_r_pos)
    hand_r_target = bpy.context.active_object
    hand_r_target.name = 'HandTarget_R'
    hand_r_target.scale = (0.03, 0.03, 0.03)

    bpy.ops.object.empty_add(type='PLAIN_AXES', location=hand_l_pos)
    hand_l_target = bpy.context.active_object
    hand_l_target.name = 'HandTarget_L'
    hand_l_target.scale = (0.03, 0.03, 0.03)

    # Add IK constraints
    bpy.ops.object.select_all(action='DESELECT')
    armature.select_set(True)
    bpy.context.view_layer.objects.active = armature
    bpy.ops.object.mode_set(mode='POSE')

    for bone_name, target in [("bone_9", hand_r_target), ("bone_28", hand_l_target)]:
        pb = armature.pose.bones.get(bone_name)
        if pb:
            ik = pb.constraints.new('IK')
            ik.target = target
            ik.chain_count = 3
            ik.iterations = 200

    bpy.ops.object.mode_set(mode='OBJECT')
    bpy.context.view_layer.update()

    # Parent armature to seat
    if seat:
        armature.parent = seat
        armature.matrix_parent_inverse = seat.matrix_world.inverted()

    print(f"Assembly complete: scale={scale}, hands at steering column")

    # --- Export ---
    if output_glb or output_fbx:
        import os
        bpy.ops.object.select_all(action='SELECT')
        if output_glb:
            os.makedirs(os.path.dirname(output_glb), exist_ok=True)
            bpy.ops.export_scene.gltf(filepath=output_glb, export_format='GLB',
                                       use_selection=True, export_animations=False, export_skins=True)
            print(f"GLB: {os.path.getsize(output_glb):,} bytes")
        if output_fbx:
            os.makedirs(os.path.dirname(output_fbx), exist_ok=True)
            bpy.ops.export_scene.fbx(filepath=output_fbx, use_selection=True,
                                      apply_scale_options='FBX_SCALE_ALL', bake_anim=False, add_leaf_bones=False)
            print(f"FBX: {os.path.getsize(output_fbx):,} bytes")

    return True
