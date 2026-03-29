"""
Generate Rigify metarig skeleton templates and export as GLB.
Run via headless Blender:
  blender --background --python generate_rigify_templates.py
"""
import bpy
import os
import sys

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "references")


def clear_scene():
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()


def export_glb(filepath):
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    bpy.ops.export_scene.gltf(
        filepath=filepath,
        export_format='GLB',
        use_selection=False,
        export_animations=False,
        export_skins=True,
    )
    size = os.path.getsize(filepath)
    print(f"  Exported: {filepath} ({size} bytes)")


def generate_human_metarig():
    """Generate standard human metarig skeleton."""
    clear_scene()
    bpy.ops.preferences.addon_enable(module='rigify')
    bpy.ops.object.armature_human_metarig_add()
    metarig = bpy.context.active_object
    metarig.name = "rigify_human_metarig"

    # Count bones
    bone_count = len(metarig.data.bones)
    print(f"  Human metarig: {bone_count} bones")

    out = os.path.join(OUTPUT_DIR, "humanoid", "rigify_human_metarig.glb")
    export_glb(out)

    # Also export as .blend for reference
    blend_out = os.path.join(OUTPUT_DIR, "humanoid", "rigify_human_metarig.blend")
    os.makedirs(os.path.dirname(blend_out), exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=blend_out, copy=True)
    print(f"  Saved blend: {blend_out}")


def generate_basic_human_metarig():
    """Generate simplified human metarig (fewer bones)."""
    clear_scene()
    bpy.ops.preferences.addon_enable(module='rigify')
    # Try basic human - may not exist in all Blender versions
    try:
        bpy.ops.object.armature_basic_human_metarig_add()
        metarig = bpy.context.active_object
        metarig.name = "rigify_basic_human_metarig"
        bone_count = len(metarig.data.bones)
        print(f"  Basic human metarig: {bone_count} bones")
        out = os.path.join(OUTPUT_DIR, "humanoid", "rigify_basic_human_metarig.glb")
        export_glb(out)
    except Exception as e:
        print(f"  Basic human metarig not available: {e}")


def generate_quadruped_samples():
    """Generate quadruped skeleton samples from Rigify."""
    clear_scene()
    bpy.ops.preferences.addon_enable(module='rigify')

    # Create a basic armature and add rigify samples
    bpy.ops.object.armature_add()
    armature = bpy.context.active_object
    armature.name = "quadruped_reference"

    bpy.ops.object.mode_set(mode='EDIT')

    # Add rigify sample bones for quadruped parts
    # Spine chain
    samples_added = []
    try:
        # Try adding individual rig samples
        for sample_type in ['spines.basic_spine', 'limbs.front_paw', 'limbs.rear_paw',
                            'spines.basic_tail', 'faces.super_face']:
            try:
                bpy.ops.armature.rigify_add_bone_groups()
            except:
                pass
    except Exception as e:
        print(f"  Rigify sample addition: {e}")

    bpy.ops.object.mode_set(mode='OBJECT')

    bone_count = len(armature.data.bones)
    print(f"  Quadruped reference: {bone_count} bones")

    if bone_count > 1:
        out = os.path.join(OUTPUT_DIR, "quadruped", "rigify_quadruped_sample.glb")
        export_glb(out)


def generate_custom_biped_skeleton():
    """Generate a clean biped skeleton manually (guaranteed to work)."""
    clear_scene()

    # Create armature
    bpy.ops.object.armature_add(enter_editmode=True)
    armature = bpy.context.active_object
    armature.name = "biped_reference_skeleton"
    arm_data = armature.data
    arm_data.name = "biped_reference"

    # Delete default bone
    bpy.ops.armature.select_all(action='SELECT')
    bpy.ops.armature.delete()

    def add_bone(name, head, tail, parent_name=None):
        bone = arm_data.edit_bones.new(name)
        bone.head = head
        bone.tail = tail
        if parent_name and parent_name in arm_data.edit_bones:
            bone.parent = arm_data.edit_bones[parent_name]
        return bone

    # Spine chain (Z-up, facing -Y)
    add_bone("spine",      (0, 0, 0.95),    (0, 0, 1.05))
    add_bone("spine.001",  (0, 0, 1.05),    (0, 0, 1.15),  "spine")
    add_bone("spine.002",  (0, 0, 1.15),    (0, 0, 1.30),  "spine.001")
    add_bone("chest",      (0, 0, 1.30),    (0, 0, 1.45),  "spine.002")
    add_bone("neck",       (0, 0, 1.45),    (0, 0, 1.55),  "chest")
    add_bone("head",       (0, 0, 1.55),    (0, 0, 1.75),  "neck")

    # Left arm
    add_bone("shoulder.L",   (0.05, 0, 1.42), (0.15, 0, 1.42),  "chest")
    add_bone("upper_arm.L",  (0.15, 0, 1.42), (0.40, 0, 1.42),  "shoulder.L")
    add_bone("forearm.L",    (0.40, 0, 1.42), (0.62, 0, 1.42),  "upper_arm.L")
    add_bone("hand.L",       (0.62, 0, 1.42), (0.70, 0, 1.42),  "forearm.L")

    # Right arm
    add_bone("shoulder.R",   (-0.05, 0, 1.42), (-0.15, 0, 1.42),  "chest")
    add_bone("upper_arm.R",  (-0.15, 0, 1.42), (-0.40, 0, 1.42),  "shoulder.R")
    add_bone("forearm.R",    (-0.40, 0, 1.42), (-0.62, 0, 1.42),  "upper_arm.R")
    add_bone("hand.R",       (-0.62, 0, 1.42), (-0.70, 0, 1.42),  "forearm.R")

    # Fingers (simplified - 3 bones per finger, L side)
    for i, (fname, x_off) in enumerate([
        ("thumb", 0.01), ("finger_index", 0.02),
        ("finger_middle", 0.02), ("finger_ring", 0.02), ("finger_pinky", 0.02)
    ]):
        base_x = 0.70 + i * 0.015
        for j in range(1, 4):
            pname = f"{fname}.0{j}.L"
            parent = "hand.L" if j == 1 else f"{fname}.0{j-1}.L"
            seg_len = 0.015
            add_bone(pname,
                     (base_x + (j-1)*seg_len, 0, 1.42 - i*0.005),
                     (base_x + j*seg_len, 0, 1.42 - i*0.005),
                     parent)

    # Fingers R side (mirror)
    for i, (fname, x_off) in enumerate([
        ("thumb", 0.01), ("finger_index", 0.02),
        ("finger_middle", 0.02), ("finger_ring", 0.02), ("finger_pinky", 0.02)
    ]):
        base_x = -(0.70 + i * 0.015)
        for j in range(1, 4):
            pname = f"{fname}.0{j}.R"
            parent = "hand.R" if j == 1 else f"{fname}.0{j-1}.R"
            seg_len = 0.015
            add_bone(pname,
                     (base_x - (j-1)*seg_len, 0, 1.42 - i*0.005),
                     (base_x - j*seg_len, 0, 1.42 - i*0.005),
                     parent)

    # Left leg
    add_bone("thigh.L",  (0.10, 0, 0.95),  (0.10, 0, 0.52),  "spine")
    add_bone("shin.L",   (0.10, 0, 0.52),  (0.10, 0, 0.08),  "thigh.L")
    add_bone("foot.L",   (0.10, 0, 0.08),  (0.10, -0.12, 0.0), "shin.L")
    add_bone("toe.L",    (0.10, -0.12, 0.0), (0.10, -0.18, 0.0), "foot.L")

    # Right leg
    add_bone("thigh.R",  (-0.10, 0, 0.95),  (-0.10, 0, 0.52),  "spine")
    add_bone("shin.R",   (-0.10, 0, 0.52),  (-0.10, 0, 0.08),  "thigh.R")
    add_bone("foot.R",   (-0.10, 0, 0.08),  (-0.10, -0.12, 0.0), "shin.R")
    add_bone("toe.R",    (-0.10, -0.12, 0.0), (-0.10, -0.18, 0.0), "foot.R")

    bpy.ops.object.mode_set(mode='OBJECT')

    bone_count = len(arm_data.bones)
    print(f"  Custom biped skeleton: {bone_count} bones")

    out = os.path.join(OUTPUT_DIR, "humanoid", "biped_reference_skeleton.glb")
    export_glb(out)


def generate_quadruped_skeleton():
    """Generate a clean quadruped skeleton manually."""
    clear_scene()

    bpy.ops.object.armature_add(enter_editmode=True)
    armature = bpy.context.active_object
    armature.name = "quadruped_reference_skeleton"
    arm_data = armature.data
    arm_data.name = "quadruped_reference"

    bpy.ops.armature.select_all(action='SELECT')
    bpy.ops.armature.delete()

    def add_bone(name, head, tail, parent_name=None):
        bone = arm_data.edit_bones.new(name)
        bone.head = head
        bone.tail = tail
        if parent_name and parent_name in arm_data.edit_bones:
            bone.parent = arm_data.edit_bones[parent_name]
        return bone

    # Spine (horizontal, along Y axis)
    add_bone("spine",      (0, -0.3, 0.6),  (0, -0.1, 0.6))
    add_bone("spine.001",  (0, -0.1, 0.6),  (0, 0.1, 0.62))
    add_bone("spine.002",  (0, 0.1, 0.62),  (0, 0.25, 0.64), "spine.001")
    add_bone("spine.003",  (0, 0.25, 0.64), (0, 0.35, 0.66), "spine.002")
    add_bone("neck",       (0, 0.35, 0.66), (0, 0.45, 0.75), "spine.003")
    add_bone("neck.001",   (0, 0.45, 0.75), (0, 0.50, 0.82), "neck")
    add_bone("head",       (0, 0.50, 0.82), (0, 0.60, 0.85), "neck.001")
    add_bone("jaw",        (0, 0.55, 0.80), (0, 0.65, 0.78), "head")

    # Front legs
    for side, x in [(".L", 0.12), (".R", -0.12)]:
        add_bone(f"front_thigh{side}",  (x, 0.30, 0.60), (x, 0.30, 0.35), "spine.003")
        add_bone(f"front_shin{side}",   (x, 0.30, 0.35), (x, 0.30, 0.10), f"front_thigh{side}")
        add_bone(f"front_foot{side}",   (x, 0.30, 0.10), (x, 0.25, 0.0),  f"front_shin{side}")
        add_bone(f"front_toe{side}",    (x, 0.25, 0.0),  (x, 0.20, 0.0),  f"front_foot{side}")

    # Rear legs
    for side, x in [(".L", 0.12), (".R", -0.12)]:
        add_bone(f"rear_thigh{side}",  (x, -0.25, 0.58), (x, -0.25, 0.33), "spine")
        add_bone(f"rear_shin{side}",   (x, -0.25, 0.33), (x, -0.25, 0.10), f"rear_thigh{side}")
        add_bone(f"rear_foot{side}",   (x, -0.25, 0.10), (x, -0.30, 0.0),  f"rear_shin{side}")
        add_bone(f"rear_toe{side}",    (x, -0.30, 0.0),  (x, -0.35, 0.0),  f"rear_foot{side}")

    # Tail
    add_bone("tail",      (0, -0.3, 0.58),  (0, -0.45, 0.55), "spine")
    add_bone("tail.001",  (0, -0.45, 0.55), (0, -0.58, 0.50), "tail")
    add_bone("tail.002",  (0, -0.58, 0.50), (0, -0.70, 0.45), "tail.001")

    bpy.ops.object.mode_set(mode='OBJECT')

    bone_count = len(arm_data.bones)
    print(f"  Quadruped skeleton: {bone_count} bones")

    out = os.path.join(OUTPUT_DIR, "quadruped", "quadruped_reference_skeleton.glb")
    export_glb(out)


def generate_serpentine_skeleton():
    """Generate a spine-chain skeleton for serpentine creatures."""
    clear_scene()

    bpy.ops.object.armature_add(enter_editmode=True)
    armature = bpy.context.active_object
    armature.name = "serpentine_reference_skeleton"
    arm_data = armature.data
    arm_data.name = "serpentine_reference"

    bpy.ops.armature.select_all(action='SELECT')
    bpy.ops.armature.delete()

    # 20-segment spine chain
    import math
    segments = 20
    for i in range(segments):
        name = f"spine.{i:03d}" if i > 0 else "spine"
        t = i / segments
        y = t * 2.0 - 1.0  # -1 to 1
        z = 0.1 + 0.05 * math.sin(t * math.pi * 2)  # slight wave
        y_next = (i + 1) / segments * 2.0 - 1.0
        z_next = 0.1 + 0.05 * math.sin((i + 1) / segments * math.pi * 2)

        bone = arm_data.edit_bones.new(name)
        bone.head = (0, y, z)
        bone.tail = (0, y_next, z_next)
        if i > 0:
            prev_name = f"spine.{(i-1):03d}" if i > 1 else "spine"
            bone.parent = arm_data.edit_bones[prev_name]

    # Add head at front
    head = arm_data.edit_bones.new("head")
    head.head = (0, 1.0, 0.1)
    head.tail = (0, 1.15, 0.15)
    head.parent = arm_data.edit_bones[f"spine.{segments-1:03d}"]

    bpy.ops.object.mode_set(mode='OBJECT')

    bone_count = len(arm_data.bones)
    print(f"  Serpentine skeleton: {bone_count} bones")

    out = os.path.join(OUTPUT_DIR, "serpentine", "serpentine_reference_skeleton.glb")
    export_glb(out)


if __name__ == "__main__":
    print("=" * 60)
    print("Generating Rigify/Reference Skeleton Templates")
    print("=" * 60)

    print("\n[1/5] Human Rigify metarig...")
    generate_human_metarig()

    print("\n[2/5] Basic human metarig...")
    generate_basic_human_metarig()

    print("\n[3/5] Custom biped skeleton (guaranteed)...")
    generate_custom_biped_skeleton()

    print("\n[4/5] Quadruped skeleton...")
    generate_quadruped_skeleton()

    print("\n[5/5] Serpentine skeleton...")
    generate_serpentine_skeleton()

    print("\n" + "=" * 60)
    print("All skeleton templates generated!")
    print("=" * 60)
