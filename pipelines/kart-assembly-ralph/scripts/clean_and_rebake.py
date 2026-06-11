"""
Clean arm/leg weight overlap + re-run hybrid bake with increased arm angle.
Runs via blender-mcp execute_code or headless Blender.

Fixes: hand mesh bleeding into pants during driving pose.
Root cause: auto-weights assigned arm bone influence to thigh vertices.
"""
import bpy
import math
import os
import json
from mathutils import Vector


def find_objects():
    mesh_obj = None
    armature = None
    for obj in bpy.data.objects:
        if obj.type == 'MESH' and len(obj.data.vertices) > 100:
            mesh_obj = obj
        elif obj.type == 'ARMATURE':
            armature = obj
    return armature, mesh_obj


def clean_weight_overlap(mesh_obj):
    """Remove arm weights from below-hip vertices and leg weights from above-chest."""
    arm_keywords = {'upperarm', 'lowerarm', 'hand', 'shoulder', 'finger', 'thumb'}
    leg_keywords = {'upperleg', 'lowerleg', 'foot', 'toe'}

    arm_vg_indices = set()
    leg_vg_indices = set()
    for vg in mesh_obj.vertex_groups:
        name_lower = vg.name.lower().replace('.', '')
        if any(kw in name_lower for kw in arm_keywords):
            arm_vg_indices.add(vg.index)
        elif any(kw in name_lower for kw in leg_keywords):
            leg_vg_indices.add(vg.index)

    verts_world = [mesh_obj.matrix_world @ v.co for v in mesh_obj.data.vertices]
    min_z = min(v.z for v in verts_world)
    max_z = max(v.z for v in verts_world)
    height = max_z - min_z

    hip_z = min_z + height * 0.45
    chest_z = min_z + height * 0.55
    blend_lo = hip_z - height * 0.05
    blend_hi = chest_z + height * 0.05

    arm_stripped = 0
    leg_stripped = 0

    for v in mesh_obj.data.vertices:
        wco = mesh_obj.matrix_world @ v.co

        # Below hip: strip arm weights
        if wco.z < blend_lo:
            for g in list(v.groups):
                if g.group in arm_vg_indices and g.weight > 0.001:
                    mesh_obj.vertex_groups[g.group].remove([v.index])
                    arm_stripped += 1
        elif wco.z < hip_z:
            t = (wco.z - blend_lo) / (hip_z - blend_lo)
            t = t * t * (3 - 2 * t)
            for g in list(v.groups):
                if g.group in arm_vg_indices and g.weight > 0.001:
                    new_w = g.weight * t
                    if new_w < 0.001:
                        mesh_obj.vertex_groups[g.group].remove([v.index])
                        arm_stripped += 1
                    else:
                        mesh_obj.vertex_groups[g.group].add([v.index], new_w, 'REPLACE')

        # Above chest: strip leg weights
        if wco.z > blend_hi:
            for g in list(v.groups):
                if g.group in leg_vg_indices and g.weight > 0.001:
                    mesh_obj.vertex_groups[g.group].remove([v.index])
                    leg_stripped += 1
        elif wco.z > chest_z:
            t = (blend_hi - wco.z) / (blend_hi - chest_z)
            t = t * t * (3 - 2 * t)
            for g in list(v.groups):
                if g.group in leg_vg_indices and g.weight > 0.001:
                    new_w = g.weight * t
                    if new_w < 0.001:
                        mesh_obj.vertex_groups[g.group].remove([v.index])
                        leg_stripped += 1
                    else:
                        mesh_obj.vertex_groups[g.group].add([v.index], new_w, 'REPLACE')

    # Normalize
    bpy.ops.object.select_all(action='DESELECT')
    mesh_obj.select_set(True)
    bpy.context.view_layer.objects.active = mesh_obj
    bpy.ops.object.mode_set(mode='WEIGHT_PAINT')
    bpy.ops.object.vertex_group_normalize_all()
    bpy.ops.object.mode_set(mode='OBJECT')

    print(f"Weight clean: arm_stripped={arm_stripped} leg_stripped={leg_stripped}")
    return arm_stripped, leg_stripped


def hybrid_bake(armature, mesh_obj, arm_angle=-80):
    """Hybrid bake with configurable arm angle."""
    DRIVING_POSE = {
        "upperleg.l": {"rx": -90},
        "upperleg.r": {"rx": -90},
        "lowerleg.l": {"rx": 90},
        "lowerleg.r": {"rx": 90},
        "spine":      {"rx": -15},
        "chest":      {"rx": -10},
        "shoulder.l": {"rz": -15},
        "shoulder.r": {"rz": 15},
        "upperarm.l": {"rx": arm_angle, "rz": 15},
        "upperarm.r": {"rx": arm_angle, "rz": -15},
        "lowerarm.l": {"rx": -45},
        "lowerarm.r": {"rx": -45},
        "hand.l":     {"rx": -10},
        "hand.r":     {"rx": -10},
        "head":       {"rx": 20},
        "neck":       {"rx": 10},
        "foot.l":     {"rx": -35},
        "foot.r":     {"rx": -35},
    }

    BAKE_BONES = {
        "upperleg.l", "upperleg.r",
        "lowerleg.l", "lowerleg.r",
        "foot.l", "foot.r", "toe.l", "toe.r",
    }

    # Apply driving pose
    bpy.ops.object.select_all(action='DESELECT')
    armature.select_set(True)
    bpy.context.view_layer.objects.active = armature
    bpy.ops.object.mode_set(mode='POSE')

    for bone_name, rotations in DRIVING_POSE.items():
        for pb in armature.pose.bones:
            if bone_name.lower() in pb.name.lower():
                pb.rotation_mode = 'XYZ'
                pb.rotation_euler = (
                    math.radians(rotations.get("rx", 0)),
                    math.radians(rotations.get("ry", 0)),
                    math.radians(rotations.get("rz", 0))
                )
                break

    bpy.ops.object.mode_set(mode='OBJECT')
    bpy.context.view_layer.update()
    print(f"Driving pose applied (arm angle {arm_angle})")

    # Evaluate posed positions
    depsgraph = bpy.context.evaluated_depsgraph_get()
    mesh_eval = mesh_obj.evaluated_get(depsgraph)

    # Compute bake region
    verts_w = [mesh_obj.matrix_world @ v.co for v in mesh_obj.data.vertices]
    min_z = min(v.z for v in verts_w)
    max_z = max(v.z for v in verts_w)
    h = max_z - min_z
    bake_z = min_z + h * 0.50
    blend_lo = bake_z - h * 0.04
    blend_hi = bake_z + h * 0.04

    # Hips VG
    hips_vg = mesh_obj.vertex_groups.get("Hips")
    if not hips_vg:
        hips_vg = mesh_obj.vertex_groups.new(name="Hips")

    baked = blended = kept = 0
    for v_idx, v in enumerate(mesh_obj.data.vertices):
        rest_world = mesh_obj.matrix_world @ v.co
        posed_co = mesh_eval.data.vertices[v_idx].co

        if rest_world.z < blend_lo:
            v.co = posed_co
            for g in list(v.groups):
                mesh_obj.vertex_groups[g.group].remove([v_idx])
            hips_vg.add([v_idx], 1.0, 'REPLACE')
            baked += 1
        elif rest_world.z < blend_hi:
            t = (rest_world.z - blend_lo) / (blend_hi - blend_lo)
            t = t * t * (3 - 2 * t)
            v.co = v.co.lerp(posed_co, 1.0 - t)
            for g in list(v.groups):
                vg_obj = mesh_obj.vertex_groups[g.group]
                nw = g.weight * t
                if nw > 0.001:
                    vg_obj.add([v_idx], nw, 'REPLACE')
                else:
                    vg_obj.remove([v_idx])
            hips_vg.add([v_idx], 1.0 - t, 'ADD')
            blended += 1
        else:
            kept += 1

    # Strip arm weights from bake zone
    ARM_KW = {"upperarm", "lowerarm", "hand", "shoulder", "finger", "thumb"}
    arm_vg_idx = {vg.index for vg in mesh_obj.vertex_groups if any(k in vg.name.lower() for k in ARM_KW)}
    hips_idx = hips_vg.index
    stripped = 0
    for v_idx, v in enumerate(mesh_obj.data.vertices):
        has_hips = any(g.group == hips_idx and g.weight > 0.01 for g in v.groups)
        if has_hips:
            for g in list(v.groups):
                if g.group in arm_vg_idx:
                    mesh_obj.vertex_groups[g.group].remove([v_idx])
                    stripped += 1

    # Clear bake bone poses
    bpy.ops.object.select_all(action='DESELECT')
    armature.select_set(True)
    bpy.context.view_layer.objects.active = armature
    bpy.ops.object.mode_set(mode='POSE')
    for pb in armature.pose.bones:
        if any(bn in pb.name.lower() for bn in BAKE_BONES):
            pb.rotation_euler = (0, 0, 0)
            pb.location = (0, 0, 0)
    bpy.ops.pose.armature_apply(selected=False)
    bpy.ops.object.mode_set(mode='OBJECT')

    # Normalize
    bpy.ops.object.select_all(action='DESELECT')
    mesh_obj.select_set(True)
    bpy.context.view_layer.objects.active = mesh_obj
    bpy.ops.object.mode_set(mode='WEIGHT_PAINT')
    bpy.ops.object.vertex_group_normalize_all()
    bpy.ops.object.mode_set(mode='OBJECT')

    print(f"Bake done: baked={baked} blended={blended} kept={kept} arm_stripped={stripped}")
    return {"baked": baked, "blended": blended, "kept": kept, "arm_stripped": stripped}


def main():
    armature, mesh_obj = find_objects()
    if not armature or not mesh_obj:
        print("ERROR: Missing armature or mesh")
        return

    print(f"Armature: {armature.name} ({len(armature.data.bones)} bones)")
    print(f"Mesh: {mesh_obj.name} ({len(mesh_obj.data.vertices)} verts)")

    # Step 1: Clean weight overlap
    arm_s, leg_s = clean_weight_overlap(mesh_obj)

    # Step 2: Hybrid bake with arm angle -80
    bake_result = hybrid_bake(armature, mesh_obj, arm_angle=-80)

    # Step 3: Export
    output_path = "D:/Projects/comfyui-toolchain/pipelines/character-ralph/output/rigged/character-hybrid-baked-plusY.glb"
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.export_scene.gltf(
        filepath=output_path,
        export_format='GLB',
        use_selection=True,
        export_animations=False,
        export_skins=True,
    )
    glb_size = os.path.getsize(output_path)

    report = {
        "weight_cleaning": {"arm_stripped": arm_s, "leg_stripped": leg_s},
        "hybrid_bake": bake_result,
        "arm_angle": -80,
        "output": output_path,
        "glb_size": glb_size,
    }
    report_path = output_path.replace('.glb', '-report.json')
    with open(report_path, 'w') as f:
        json.dump(report, f, indent=2)

    print(f"COMPLETE: {output_path} ({glb_size:,} bytes)")


if __name__ == "__main__":
    main()
