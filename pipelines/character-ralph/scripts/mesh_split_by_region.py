"""
Split character mesh into body-region objects by face center position.
Arm splits: vertical cuts (90 degrees along Z axis) at shoulder width.
Leg/hip split: 45-degree angled cut from hip center outward.
Head split: horizontal cut at neck height.
"""
import bpy
import bmesh
from mathutils import Vector


def get_mesh():
    skip = {'body_head', 'body_arm_L', 'body_arm_R', 'body_legs', 'body_torso'}
    for obj in bpy.data.objects:
        if obj.type == 'MESH' and obj.name not in skip and len(obj.data.vertices) > 100:
            return obj
    return None


def get_bounds(mesh_obj):
    vw = [mesh_obj.matrix_world @ v.co for v in mesh_obj.data.vertices]
    min_x = min(v.x for v in vw)
    max_x = max(v.x for v in vw)
    min_z = min(v.z for v in vw)
    max_z = max(v.z for v in vw)
    h = max_z - min_z
    w = max_x - min_x
    cx = (min_x + max_x) / 2
    return min_x, max_x, min_z, max_z, h, w, cx


def extract_region(region_name, test_fn):
    """Select faces matching test_fn, separate into new object, rename."""
    src = get_mesh()
    if not src:
        print(f"ERROR: No source mesh for {region_name}")
        return

    bpy.ops.object.select_all(action='DESELECT')
    src.select_set(True)
    bpy.context.view_layer.objects.active = src
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='DESELECT')
    bpy.ops.mesh.select_mode(type='FACE')

    bm = bmesh.from_edit_mesh(src.data)
    bm.faces.ensure_lookup_table()

    ct = 0
    for f in bm.faces:
        fc = src.matrix_world @ f.calc_center_median()
        if test_fn(fc.x, fc.z):
            f.select = True
            ct += 1

    bmesh.update_edit_mesh(src.data)

    if ct > 0:
        bpy.ops.mesh.separate(type='SELECTED')

    bpy.ops.object.mode_set(mode='OBJECT')

    # Find and rename the new object
    skip = {'body_head', 'body_arm_L', 'body_arm_R', 'body_legs', 'body_torso'}
    for obj in bpy.data.objects:
        if obj.type == 'MESH' and obj.name not in skip and obj != src and len(obj.data.vertices) > 10:
            obj.name = region_name
            print(f"{region_name}: {len(obj.data.vertices)} verts ({ct} faces)")
            return

    print(f"{region_name}: no faces separated ({ct} selected)")


def main():
    mesh_obj = get_mesh()
    if not mesh_obj:
        print("ERROR: No mesh found")
        return

    min_x, max_x, min_z, max_z, h, w, cx = get_bounds(mesh_obj)

    # --- ARM BOUNDARIES ---
    # Vertical cuts at armpit width (90 degrees along Z axis)
    # Use the narrowest point at armpit height (~60% of character height)
    vw = [mesh_obj.matrix_world @ v.co for v in mesh_obj.data.vertices]
    armpit_z_lo = min_z + h * 0.58
    armpit_z_hi = min_z + h * 0.65
    # Find the outer edge of the torso at armpit height (where the gap between arm and body is)
    armpit_verts = [v for v in vw if armpit_z_lo < v.z < armpit_z_hi]

    # The armpit is where there's a gap in X between torso and arm
    # Find the torso outer boundary by looking at verts near center X
    torso_at_armpit = [v for v in armpit_verts if abs(v.x - cx) < w * 0.18]

    if torso_at_armpit:
        torso_left = min(v.x for v in torso_at_armpit)
        torso_right = max(v.x for v in torso_at_armpit)
    else:
        torso_left = cx - w * 0.15
        torso_right = cx + w * 0.15

    # Cut at the torso outer edge — arms are everything beyond this
    arm_cut_L = torso_left
    arm_cut_R = torso_right

    arm_z_lo = min_z + h * 0.25
    arm_z_hi = min_z + h * 0.83

    # --- HIP/LEG BOUNDARY ---
    # 45-degree angled cut from hip center outward
    hip_center_z = min_z + h * 0.42

    # --- HEAD BOUNDARY ---
    head_z = min_z + h * 0.83

    print(f"Bounds: h={h:.3f} w={w:.3f} cx={cx:.3f}")
    print(f"Arm cuts: L at X>{arm_cut_L:.3f}, R at X<{arm_cut_R:.3f}, Z [{arm_z_lo:.3f}, {arm_z_hi:.3f}]")
    print(f"Hip center Z: {hip_center_z:.3f} (45deg outward)")
    print(f"Head Z: {head_z:.3f}")

    # Extract head (horizontal cut)
    extract_region('body_head', lambda x, z: z > head_z)

    # Armpit Z height — arms only exist above this height
    armpit_z = min_z + h * 0.52

    # Extract arms FIRST — outside armpit X AND above armpit Z
    extract_region('body_arm_L', lambda x, z: x < arm_cut_L and z > armpit_z and z < arm_z_hi)
    extract_region('body_arm_R', lambda x, z: x > arm_cut_R and z > armpit_z and z < arm_z_hi)

    # Extract legs — 45-degree cut from hip center, capped at armpit X width
    def is_legs(x, z):
        dist_from_center = abs(x - cx)
        max_dist = abs(arm_cut_L - cx)
        capped_dist = min(dist_from_center, max_dist)
        cut_z_at_x = hip_center_z + capped_dist
        return z < cut_z_at_x

    extract_region('body_legs', is_legs)

    # Rename remainder as torso
    src = get_mesh()
    if src:
        src.name = 'body_torso'
        print(f"body_torso: {len(src.data.vertices)} verts")

    # Report
    print("\nFinal objects:")
    for obj in sorted(bpy.data.objects, key=lambda o: o.name):
        if obj.type == 'MESH':
            print(f"  {obj.name}: {len(obj.data.vertices)}v {len(obj.data.polygons)}f")

    # Color regions
    colors = {
        'body_head': (0.9, 0.7, 0.5, 1),
        'body_torso': (0.9, 0.5, 0.1, 1),
        'body_arm_L': (0.2, 0.6, 0.9, 1),
        'body_arm_R': (0.2, 0.9, 0.4, 1),
        'body_legs': (0.3, 0.3, 0.3, 1),
    }
    for obj in bpy.data.objects:
        if obj.type == 'MESH' and obj.name in colors:
            mat = bpy.data.materials.new(name=f'mat_{obj.name}')
            mat.diffuse_color = colors[obj.name]
            obj.data.materials.clear()
            obj.data.materials.append(mat)

    for area in bpy.context.screen.areas:
        if area.type == 'VIEW_3D':
            area.spaces[0].shading.color_type = 'MATERIAL'
            break

    # Export
    import os
    output_path = "D:/Projects/comfyui-toolchain/pipelines/character-ralph/output/3d/character-split.glb"
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.export_scene.gltf(
        filepath=output_path, export_format='GLB',
        use_selection=True, export_animations=False)
    print(f"\nExported: {output_path} ({os.path.getsize(output_path):,} bytes)")


if __name__ == "__main__":
    main()
