"""
Hybrid Bake Driver: Bake lower body into driving pose, keep upper body rigged.

This script solves the mesh bleeding problem where AI-generated single-mesh characters
have arms connected to pants/torso. By baking the lower body (legs/hips) into the
seated driving position permanently, we eliminate ALL lower-body deformation. The
upper body armature remains active for runtime animation (steering, head tilt).

Usage via blender-mcp execute_code:
    exec(open('pipelines/kart-assembly-ralph/scripts/hybrid_bake_driver.py').read())

Usage headless:
    blender --background --python hybrid_bake_driver.py -- \
        --input character-rigged.glb --output character-hybrid-baked.glb

Requires: Blender 5.0+, character GLB with armature and mesh.
"""
import bpy
import math
import sys
import os
import json
from mathutils import Vector


# ─── CONFIGURATION ───

# Driving pose bone rotations (degrees)
DRIVING_POSE = {
    "upperleg.l": {"rx": -90},
    "upperleg.r": {"rx": -90},
    "lowerleg.l": {"rx": 90},
    "lowerleg.r": {"rx": 90},
    "spine":      {"rx": -15},
    "chest":      {"rx": -10},
    "shoulder.l": {"rz": -15},
    "shoulder.r": {"rz": 15},
    "upperarm.l": {"rx": -70, "rz": 15},
    "upperarm.r": {"rx": -70, "rz": -15},
    "lowerarm.l": {"rx": -40},
    "lowerarm.r": {"rx": -40},
    "hand.l":     {"rx": -10},
    "hand.r":     {"rx": -10},
    "head":       {"rx": 20},
    "neck":       {"rx": 10},
    "foot.l":     {"rx": -35},
    "foot.r":     {"rx": -35},
}

# Bones whose influence should be baked (lower body)
BAKE_BONES = {
    "upperleg.l", "upperleg.r",
    "lowerleg.l", "lowerleg.r",
    "foot.l", "foot.r",
    "toe.l", "toe.r",
}

# Bake region: fraction of character height from feet
BAKE_HEIGHT_FRACTION = 0.50  # bake everything below 50% height
BLEND_ZONE_FRACTION = 0.08   # 8% height blending zone at boundary


# ─── HELPERS ───

def find_armature():
    for obj in bpy.data.objects:
        if obj.type == 'ARMATURE':
            return obj
    return None


def find_meshes(armature):
    """Find all mesh objects parented to the armature."""
    meshes = []
    for obj in bpy.data.objects:
        if obj.type == 'MESH' and obj.parent == armature:
            meshes.append(obj)
    if not meshes:
        # Try finding any mesh
        meshes = [obj for obj in bpy.data.objects if obj.type == 'MESH']
    return meshes


def pose_bone(armature, name_part, rx=0, ry=0, rz=0):
    """Set rotation on a pose bone matching name_part (case-insensitive)."""
    for pb in armature.pose.bones:
        if name_part.lower() in pb.name.lower():
            pb.rotation_mode = 'XYZ'
            pb.rotation_euler = (math.radians(rx), math.radians(ry), math.radians(rz))
            return pb
    return None


def apply_driving_pose(armature):
    """Apply the full driving pose to the armature."""
    bpy.ops.object.select_all(action='DESELECT')
    armature.select_set(True)
    bpy.context.view_layer.objects.active = armature
    bpy.ops.object.mode_set(mode='POSE')

    for bone_name, rotations in DRIVING_POSE.items():
        pose_bone(armature, bone_name,
                  rx=rotations.get("rx", 0),
                  ry=rotations.get("ry", 0),
                  rz=rotations.get("rz", 0))

    bpy.ops.object.mode_set(mode='OBJECT')
    bpy.context.view_layer.update()


def get_mesh_bounds(mesh_obj):
    """Get world-space bounding box of a mesh."""
    verts = [mesh_obj.matrix_world @ v.co for v in mesh_obj.data.vertices]
    if not verts:
        return Vector((0, 0, 0)), Vector((0, 0, 0))
    min_co = Vector((min(v.x for v in verts), min(v.y for v in verts), min(v.z for v in verts)))
    max_co = Vector((max(v.x for v in verts), max(v.y for v in verts), max(v.z for v in verts)))
    return min_co, max_co


# ─── CORE: HYBRID BAKE ───

def hybrid_bake(armature, mesh_obj):
    """
    Bake lower-body vertices into their posed positions.
    Keep upper-body vertices deformable by the armature.
    """
    # Get mesh bounds for height-based region splitting
    min_co, max_co = get_mesh_bounds(mesh_obj)
    height = max_co.z - min_co.z

    # Define bake boundary
    bake_z = min_co.z + height * BAKE_HEIGHT_FRACTION
    blend_lo = bake_z - height * BLEND_ZONE_FRACTION / 2
    blend_hi = bake_z + height * BLEND_ZONE_FRACTION / 2

    print(f"Mesh height: {height:.3f}m, bake below Z={bake_z:.3f}")
    print(f"Blend zone: Z={blend_lo:.3f} to Z={blend_hi:.3f}")

    # Step 1: Apply driving pose
    apply_driving_pose(armature)
    print("Driving pose applied")

    # Step 2: Evaluate depsgraph to get posed vertex positions
    depsgraph = bpy.context.evaluated_depsgraph_get()
    mesh_eval = mesh_obj.evaluated_get(depsgraph)

    # Step 3: Bake lower body vertices
    # Get the Hips vertex group (or create it)
    hips_vg = mesh_obj.vertex_groups.get("Hips")
    if not hips_vg:
        hips_vg = mesh_obj.vertex_groups.new(name="Hips")

    baked_count = 0
    blended_count = 0
    kept_count = 0

    for v_idx, v in enumerate(mesh_obj.data.vertices):
        rest_world = mesh_obj.matrix_world @ v.co
        posed_co = mesh_eval.data.vertices[v_idx].co  # local space posed position

        if rest_world.z < blend_lo:
            # FULL BAKE: write posed position, assign rigid to Hips
            v.co = posed_co
            # Remove all existing vertex group assignments
            for g in list(v.groups):
                mesh_obj.vertex_groups[g.group].remove([v_idx])
            # Assign to Hips with weight 1.0
            hips_vg.add([v_idx], 1.0, 'REPLACE')
            baked_count += 1

        elif rest_world.z < blend_hi:
            # BLEND ZONE: partial bake with smooth falloff
            # t=0 at blend_lo (fully baked), t=1 at blend_hi (fully rigged)
            t = (rest_world.z - blend_lo) / (blend_hi - blend_lo)
            t = t * t * (3 - 2 * t)  # smoothstep

            # Interpolate between posed and rest positions
            blended_co = v.co.lerp(posed_co, 1.0 - t)
            v.co = blended_co

            # Reduce existing weights by t, add Hips weight for (1-t)
            for g in list(v.groups):
                vg = mesh_obj.vertex_groups[g.group]
                new_weight = g.weight * t
                if new_weight > 0.001:
                    vg.add([v_idx], new_weight, 'REPLACE')
                else:
                    vg.remove([v_idx])
            hips_vg.add([v_idx], 1.0 - t, 'ADD')
            blended_count += 1

        else:
            # KEEP: upper body stays fully rigged
            kept_count += 1

    print(f"Baked: {baked_count}, Blended: {blended_count}, Kept: {kept_count}")

    # Step 3b: Strip arm bone weights from baked + blended vertices
    # The blend zone keeps scaled weights from ALL bones including arms.
    # Arm bones must have ZERO influence on anything at or below the blend zone
    # to prevent arm rotation from moving the lower body.
    ARM_BONE_KEYWORDS = {
        "upperarm", "upper_arm", "lowerarm", "lower_arm", "forearm",
        "hand", "shoulder", "finger", "thumb", "index", "middle", "ring", "pinky",
    }
    arm_vg_indices = set()
    for vg in mesh_obj.vertex_groups:
        if any(kw in vg.name.lower() for kw in ARM_BONE_KEYWORDS):
            arm_vg_indices.add(vg.index)

    stripped_count = 0
    hips_vg_idx = hips_vg.index
    for v_idx, v in enumerate(mesh_obj.data.vertices):
        # Strip arm weights from any vertex that has Hips weight (was touched by bake)
        has_hips = any(g.group == hips_vg_idx and g.weight > 0.01 for g in v.groups)
        if has_hips:
            for g in list(v.groups):
                if g.group in arm_vg_indices:
                    mesh_obj.vertex_groups[g.group].remove([v_idx])
                    stripped_count += 1

    print(f"Stripped {stripped_count} arm bone weight assignments from bake+blend zone")

    # Step 4: Clear lower-body bone poses (mesh already has the shape)
    bpy.ops.object.select_all(action='DESELECT')
    armature.select_set(True)
    bpy.context.view_layer.objects.active = armature
    bpy.ops.object.mode_set(mode='POSE')

    for pb in armature.pose.bones:
        if any(bake_name in pb.name.lower() for bake_name in BAKE_BONES):
            pb.rotation_euler = (0, 0, 0)
            pb.location = (0, 0, 0)

    # Step 5: Apply current pose as rest pose
    # This makes the upper body driving pose the new rest pose
    bpy.ops.pose.armature_apply(selected=False)
    bpy.ops.object.mode_set(mode='OBJECT')

    print("Hybrid bake complete: lower body baked, upper body rest = driving pose")

    # Step 6: Normalize weights
    bpy.ops.object.select_all(action='DESELECT')
    mesh_obj.select_set(True)
    bpy.context.view_layer.objects.active = mesh_obj
    bpy.ops.object.mode_set(mode='WEIGHT_PAINT')
    bpy.ops.object.vertex_group_normalize_all()
    bpy.ops.object.mode_set(mode='OBJECT')

    return {
        "baked": baked_count,
        "blended": blended_count,
        "kept": kept_count,
        "bake_z": round(bake_z, 4),
        "blend_zone": [round(blend_lo, 4), round(blend_hi, 4)],
    }


def export_hybrid_baked(output_path):
    """Export the hybrid-baked character as GLB."""
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.export_scene.gltf(
        filepath=output_path,
        export_format='GLB',
        use_selection=True,
        export_animations=False,
        export_skins=True,
    )
    size = os.path.getsize(output_path)
    print(f"Exported: {output_path} ({size:,} bytes)")
    return size


# ─── MAIN ───

def main(input_path=None, output_path=None):
    """Run the full hybrid bake pipeline."""
    if input_path:
        # Clear and import
        bpy.ops.object.select_all(action='SELECT')
        bpy.ops.object.delete()
        for d in [bpy.data.armatures, bpy.data.meshes, bpy.data.materials,
                  bpy.data.images, bpy.data.actions]:
            for item in list(d):
                d.remove(item)
        bpy.ops.import_scene.gltf(filepath=input_path)

    armature = find_armature()
    meshes = find_meshes(armature)

    if not armature:
        print("ERROR: No armature found")
        return
    if not meshes:
        print("ERROR: No mesh found")
        return

    print(f"Armature: {armature.name} ({len(armature.data.bones)} bones)")
    print(f"Meshes: {[m.name for m in meshes]} ({sum(len(m.data.vertices) for m in meshes)} total verts)")

    # Bake each mesh part
    results = {}
    for mesh_obj in meshes:
        print(f"\n--- Baking: {mesh_obj.name} ---")
        result = hybrid_bake(armature, mesh_obj)
        results[mesh_obj.name] = result

    # Export
    if output_path:
        export_hybrid_baked(output_path)

    # Write report
    report = {
        "input": input_path,
        "output": output_path,
        "armature": armature.name,
        "bone_count": len(armature.data.bones),
        "meshes": results,
        "driving_pose": DRIVING_POSE,
        "bake_height_fraction": BAKE_HEIGHT_FRACTION,
    }

    report_path = output_path.replace('.glb', '-report.json') if output_path else None
    if report_path:
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2)
        print(f"Report: {report_path}")

    print("\nHYBRID BAKE COMPLETE")
    return report


# ─── CLI ENTRY ───

if __name__ == "__main__":
    argv = sys.argv
    if "--" in argv:
        argv = argv[argv.index("--") + 1:]
        args = {}
        i = 0
        while i < len(argv):
            if argv[i] == "--input":
                args["input"] = argv[i + 1]; i += 2
            elif argv[i] == "--output":
                args["output"] = argv[i + 1]; i += 2
            else:
                i += 1
        main(input_path=args.get("input"), output_path=args.get("output"))
