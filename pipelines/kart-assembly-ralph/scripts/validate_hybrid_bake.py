"""
Validate hybrid bake: bake completeness test + close-up screenshots + 4-view rest pose.
Runs headless in Blender.

Usage:
    blender --background --python validate_hybrid_bake.py -- \
        --input <character-hybrid-baked-plusY.glb> \
        --output-dir <gate-hybrid-bake-screenshots/>
"""
import bpy
import math
import sys
import os
import json
from mathutils import Vector, Euler


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


def setup_render(res_x=800, res_y=800):
    scene = bpy.context.scene
    scene.render.resolution_x = res_x
    scene.render.resolution_y = res_y
    scene.render.image_settings.file_format = 'PNG'
    # Use workbench for solid shading in background mode
    scene.render.engine = 'BLENDER_WORKBENCH'
    bpy.context.scene.display.shading.light = 'STUDIO'
    bpy.context.scene.display.shading.color_type = 'MATERIAL'


def add_camera():
    """Add a camera for rendering."""
    bpy.ops.object.camera_add(location=(0, -3, 1), rotation=(math.radians(80), 0, 0))
    cam = bpy.context.active_object
    bpy.context.scene.camera = cam
    return cam


def point_camera_at(cam, target, distance=2.0, angle_h=0, angle_v=math.radians(15)):
    """Point camera at target from given angle and distance."""
    x = target.x + distance * math.sin(angle_h) * math.cos(angle_v)
    y = target.y - distance * math.cos(angle_h) * math.cos(angle_v)
    z = target.z + distance * math.sin(angle_v)
    cam.location = Vector((x, y, z))

    direction = target - cam.location
    rot_quat = direction.to_track_quat('-Z', 'Y')
    cam.rotation_euler = rot_quat.to_euler()


def render_to(filepath):
    bpy.context.scene.render.filepath = filepath
    bpy.ops.render.render(write_still=True)
    print(f"Rendered: {filepath}")


def main():
    args = parse_args()
    input_path = args.get("input")
    output_dir = args.get("output_dir", "D:/Projects/comfyui-toolchain/pipelines/kart-assembly-ralph/output/gate-hybrid-bake")

    os.makedirs(output_dir, exist_ok=True)

    # Import hybrid-baked character
    clear_scene()
    bpy.ops.import_scene.gltf(filepath=input_path)
    bpy.context.view_layer.update()

    armature = None
    mesh = None
    for obj in bpy.data.objects:
        if obj.type == 'ARMATURE':
            armature = obj
        elif obj.type == 'MESH':
            mesh = obj

    if not armature or not mesh:
        print("ERROR: Missing armature or mesh")
        return

    bone_count = len(armature.data.bones)
    vert_count = len(mesh.data.vertices)
    print(f"Imported: {armature.name} ({bone_count} bones), {mesh.name} ({vert_count} verts)")

    # ─── BAKE COMPLETENESS TEST ───
    # Find vertices that are fully baked (100% Hips weight) by checking vertex groups.
    # After hybrid bake, baked vertices have only Hips group with weight 1.0.
    # We monitor these to ensure they don't move during upper-body posing.
    world_bb = [mesh.matrix_world @ Vector(c) for c in mesh.bound_box]
    min_z = min(v.z for v in world_bb)
    max_z = max(v.z for v in world_bb)
    hip_z = min_z + (max_z - min_z) * 0.45

    # Find the Hips vertex group index
    hips_vg_idx = None
    for vg in mesh.vertex_groups:
        if vg.name.lower() == "hips":
            hips_vg_idx = vg.index
            break

    # Separate fully-baked vertices (Hips=1.0, must not move) from blend-zone (0.5-0.99, small movement ok)
    rest_positions = {}       # fully baked — strict 2mm tolerance
    blend_positions = {}      # blend zone — relaxed 10mm tolerance
    if hips_vg_idx is not None:
        for v in mesh.data.vertices:
            hips_weight = 0.0
            for g in v.groups:
                if g.group == hips_vg_idx:
                    hips_weight = g.weight
                    break
            if hips_weight >= 0.99:  # fully baked
                wco = mesh.matrix_world @ v.co
                rest_positions[v.index] = wco.copy()
            elif hips_weight > 0.5:  # blend zone
                wco = mesh.matrix_world @ v.co
                blend_positions[v.index] = wco.copy()
    else:
        for v in mesh.data.vertices:
            wco = mesh.matrix_world @ v.co
            if wco.z < hip_z:
                rest_positions[v.index] = wco.copy()

    print(f"Monitoring {len(rest_positions)} fully-baked vertices (Hips >= 0.99)")
    print(f"Monitoring {len(blend_positions)} blend-zone vertices (Hips 0.5-0.99)")

    # Apply arm rotation +15 degrees
    bpy.context.view_layer.objects.active = armature
    bpy.ops.object.mode_set(mode='POSE')
    bpy.ops.pose.select_all(action='SELECT')
    bpy.ops.pose.transforms_clear()

    for pb in armature.pose.bones:
        if 'upperarm' in pb.name.lower() or 'upper_arm' in pb.name.lower():
            pb.rotation_mode = 'XYZ'
            pb.rotation_euler[0] = math.radians(15)
            print(f"  Rotated {pb.name} +15 deg")

    bpy.context.view_layer.update()

    def check_displacement(positions, label):
        """Check max displacement of a set of monitored vertices."""
        depsgraph = bpy.context.evaluated_depsgraph_get()
        mesh_eval = mesh.evaluated_get(depsgraph)
        max_d = 0.0
        worst = -1
        for idx, rest_pos in positions.items():
            posed_pos = mesh.matrix_world @ mesh_eval.data.vertices[idx].co
            d = (posed_pos - rest_pos).length
            if d > max_d:
                max_d = d
                worst = idx
        return max_d, worst

    # Check fully-baked and blend-zone displacement for arm +15
    max_disp_plus15, worst_vert_plus15 = check_displacement(rest_positions, "baked")
    max_blend_plus15, _ = check_displacement(blend_positions, "blend")
    bake_pass_plus15 = max_disp_plus15 <= 0.002
    blend_pass_plus15 = max_blend_plus15 <= 0.010  # 10mm tolerance for blend zone
    print(f"Arm +15deg: baked max {max_disp_plus15*1000:.2f}mm -> {'PASS' if bake_pass_plus15 else 'FAIL'}, blend max {max_blend_plus15*1000:.2f}mm -> {'PASS' if blend_pass_plus15 else 'WARN'}")

    # Reset and test -15 degrees
    bpy.ops.pose.select_all(action='SELECT')
    bpy.ops.pose.transforms_clear()
    for pb in armature.pose.bones:
        if 'upperarm' in pb.name.lower() or 'upper_arm' in pb.name.lower():
            pb.rotation_mode = 'XYZ'
            pb.rotation_euler[0] = math.radians(-15)

    bpy.context.view_layer.update()
    max_disp_minus15, worst_vert_minus15 = check_displacement(rest_positions, "baked")
    max_blend_minus15, _ = check_displacement(blend_positions, "blend")
    bake_pass_minus15 = max_disp_minus15 <= 0.002
    blend_pass_minus15 = max_blend_minus15 <= 0.010
    print(f"Arm -15deg: baked max {max_disp_minus15*1000:.2f}mm -> {'PASS' if bake_pass_minus15 else 'FAIL'}, blend max {max_blend_minus15*1000:.2f}mm -> {'PASS' if blend_pass_minus15 else 'WARN'}")

    # Head tilt test +25 / -25
    head_pass = True
    for angle in [25, -25]:
        bpy.ops.pose.select_all(action='SELECT')
        bpy.ops.pose.transforms_clear()
        for pb in armature.pose.bones:
            if 'head' in pb.name.lower() and 'headband' not in pb.name.lower():
                pb.rotation_mode = 'XYZ'
                pb.rotation_euler[0] = math.radians(angle)
                break
        bpy.context.view_layer.update()
        max_d, _ = check_displacement(rest_positions, "baked")
        head_ok = max_d <= 0.002
        if not head_ok:
            head_pass = False
        print(f"Head {angle}deg: baked max {max_d*1000:.2f}mm -> {'PASS' if head_ok else 'FAIL'}")

    # Reset pose
    bpy.ops.pose.select_all(action='SELECT')
    bpy.ops.pose.transforms_clear()
    bpy.ops.object.mode_set(mode='OBJECT')

    # ─── RENDER SCREENSHOTS ───
    setup_render(800, 800)
    cam = add_camera()

    # Compute mesh center
    mid_x = (max(v.x for v in world_bb) + min(v.x for v in world_bb)) / 2
    mid_y = (max(v.y for v in world_bb) + min(v.y for v in world_bb)) / 2
    mid_z = (max_z + min_z) / 2
    center = Vector((mid_x, mid_y, mid_z))
    height = max_z - min_z

    # 4-view rest pose
    views = [
        ("rest-front", 0, math.radians(10), 2.5),
        ("rest-side", math.radians(90), math.radians(10), 2.5),
        ("rest-back", math.radians(180), math.radians(10), 2.5),
        ("rest-34", math.radians(35), math.radians(25), 2.8),
    ]
    for name, angle_h, angle_v, dist in views:
        point_camera_at(cam, center, dist, angle_h, angle_v)
        render_to(os.path.join(output_dir, f"{name}.png"))

    # Close-up zones
    chest_z = min_z + height * 0.65
    closeups = [
        ("closeup-hip-boundary-front", Vector((mid_x, mid_y, hip_z)), 0, math.radians(5), 0.8),
        ("closeup-hip-boundary-side", Vector((mid_x, mid_y, hip_z)), math.radians(90), math.radians(5), 0.8),
        ("closeup-chest-front", Vector((mid_x, mid_y, chest_z)), 0, math.radians(5), 0.7),
        ("closeup-chest-side", Vector((mid_x, mid_y, chest_z)), math.radians(90), math.radians(5), 0.7),
        ("closeup-hand-thigh-front", Vector((mid_x, mid_y, hip_z - height * 0.05)), 0, math.radians(0), 0.7),
        ("closeup-hand-thigh-side", Vector((mid_x, mid_y, hip_z - height * 0.05)), math.radians(90), math.radians(0), 0.7),
    ]
    setup_render(600, 600)
    for name, target, angle_h, angle_v, dist in closeups:
        point_camera_at(cam, target, dist, angle_h, angle_v)
        render_to(os.path.join(output_dir, f"{name}.png"))

    # ─── WRITE GATE RESULT ───
    all_checks = [
        {"name": "bake_completeness_arm_plus15", "passed": bake_pass_plus15,
         "detail": f"Fully-baked max displacement {max_disp_plus15*1000:.2f}mm during arm +15deg (threshold: 2mm)"},
        {"name": "bake_completeness_arm_minus15", "passed": bake_pass_minus15,
         "detail": f"Fully-baked max displacement {max_disp_minus15*1000:.2f}mm during arm -15deg (threshold: 2mm)"},
        {"name": "blend_zone_arm_plus15", "passed": blend_pass_plus15,
         "detail": f"Blend-zone max displacement {max_blend_plus15*1000:.2f}mm during arm +15deg (threshold: 10mm)"},
        {"name": "blend_zone_arm_minus15", "passed": blend_pass_minus15,
         "detail": f"Blend-zone max displacement {max_blend_minus15*1000:.2f}mm during arm -15deg (threshold: 10mm)"},
        {"name": "head_tilt_stability", "passed": head_pass,
         "detail": "Head tilt +/-25deg does not move fully-baked vertices"},
        {"name": "bone_count", "passed": bone_count >= 15,
         "detail": f"{bone_count} bones in hybrid-baked GLB"},
        {"name": "mesh_intact", "passed": vert_count > 10000,
         "detail": f"{vert_count} vertices preserved"},
        {"name": "4view_rest_pose", "passed": True,
         "detail": "rest-front/side/back/34 screenshots rendered"},
        {"name": "closeup_scans", "passed": True,
         "detail": "6 close-up screenshots rendered (hip boundary, chest, hand-thigh)"},
    ]

    all_passed = all(c["passed"] for c in all_checks)
    warnings = []
    if max_blend_plus15 > 0.005:
        warnings.append(f"Blend-zone displacement {max_blend_plus15*1000:.2f}mm at arm +15deg (within 10mm tolerance)")
    if max_blend_minus15 > 0.005:
        warnings.append(f"Blend-zone displacement {max_blend_minus15*1000:.2f}mm at arm -15deg (within 10mm tolerance)")

    result = {
        "stage": "hybrid-bake",
        "gate": "gate-hybrid-bake",
        "result": "PASS" if all_passed else "FAIL",
        "checks": all_checks,
        "warnings": warnings,
        "blocking_errors": [c["detail"] for c in all_checks if not c["passed"]],
        "bone_count": bone_count,
        "mesh_count": 1,
        "vertex_count": vert_count,
        "fully_baked_monitored": len(rest_positions),
        "blend_zone_monitored": len(blend_positions),
        "max_baked_displacement_mm": round(max(max_disp_plus15, max_disp_minus15) * 1000, 2),
        "max_blend_displacement_mm": round(max(max_blend_plus15, max_blend_minus15) * 1000, 2),
        "recommendation": "Hybrid bake validated -- proceed to kart assembly" if all_passed
                          else "Hybrid bake FAILED -- re-bake with adjusted parameters"
    }

    result_path = os.path.join(output_dir, "gate-hybrid-bake-result.json")
    with open(result_path, "w") as f:
        json.dump(result, f, indent=2)
    print(f"\nGate result: {result['result']}")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
