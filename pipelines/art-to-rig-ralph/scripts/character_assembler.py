"""Blender headless character assembly script.

Takes a UniRig-rigged GLB and:
1. Renames bones to Soapbox/Mecanim convention
2. Adds a DriverMount empty for kart Seat attachment
3. Validates the skeleton hierarchy
4. Exports to FBX (Unity/Unreal) and GLB (Blender)

Usage:
    blender --background --python character_assembler.py -- \
        --input path/to/unirig_rigged.glb \
        --output-fbx path/to/character_unity.fbx \
        --output-glb path/to/character_blender.glb \
        --character-id player \
        --report path/to/report.json

Target skeleton (29 bones, matching MK Shy Guy):
    Root
    ├── Hips
    │   ├── UpperLeg.L → LowerLeg.L → Foot.L
    │   └── UpperLeg.R → LowerLeg.R → Foot.R
    └── Spine → Chest
        ├── Head → Hair.001 → Hair.002
        ├── Shoulder.L → UpperArm.L → LowerArm.L → Hand.L
        │   ├── Finger.L → Finger.L.001
        │   └── Thumb.L → Thumb.L.001
        └── Shoulder.R → UpperArm.R → LowerArm.R → Hand.R
            ├── Finger.R → Finger.R.001
            └── Thumb.R → Thumb.R.001
"""

import bpy
import bmesh
import sys
import os
import json
import argparse
from mathutils import Vector

# ---------------------------------------------------------------------------
# Argument parsing — must be after "--" separator
# ---------------------------------------------------------------------------
argv = sys.argv
if "--" in argv:
    argv = argv[argv.index("--") + 1:]
else:
    argv = []

parser = argparse.ArgumentParser(description="Assemble UniRig-rigged GLB into convention-compliant character.")
parser.add_argument("--input", required=True, help="Path to unirig_rigged.glb")
parser.add_argument("--output-fbx", required=True, dest="output_fbx", help="Path for Unity FBX export")
parser.add_argument("--output-glb", required=True, dest="output_glb", help="Path for Blender GLB export")
parser.add_argument("--character-id", default="player", dest="character_id", help="Character identifier for report")
parser.add_argument("--report", default=None, help="Path for JSON report")
args = parser.parse_args(argv)

# ---------------------------------------------------------------------------
# Bone rename maps
# ---------------------------------------------------------------------------

# Comprehensive map from common UniRig/Rigify/Mixamo input names → Soapbox convention
BONE_RENAME_MAP: dict[str, str] = {
    # Root variants
    "root": "Root",
    "Skl_Root": "Root",
    "Armature": "Root",

    # Hips
    "hips": "Hips",
    "Hip": "Hips",
    "pelvis": "Hips",
    "Hips": "Hips",
    "mixamorig:Hips": "Hips",

    # Spine
    "spine": "Spine",
    "Spine1": "Spine",
    "spine.001": "Spine",
    "spine_01": "Spine",
    "mixamorig:Spine": "Spine",

    # Chest
    "chest": "Chest",
    "Spine2": "Chest",
    "spine.002": "Chest",
    "spine_02": "Chest",
    "mixamorig:Spine1": "Chest",

    # Head
    "head": "Head",
    "Head": "Head",
    "mixamorig:Head": "Head",

    # Hair
    "Hair1": "Hair.001",
    "hair_01": "Hair.001",
    "Hair2": "Hair.002",
    "hair_02": "Hair.002",

    # Left arm chain
    "shoulder.L": "Shoulder.L",
    "ShoulderL": "Shoulder.L",
    "clavicle_l": "Shoulder.L",
    "mixamorig:LeftShoulder": "Shoulder.L",

    "upper_arm.L": "UpperArm.L",
    "ArmL": "UpperArm.L",
    "upperarm_l": "UpperArm.L",
    "mixamorig:LeftArm": "UpperArm.L",

    "forearm.L": "LowerArm.L",
    "ElbowL": "LowerArm.L",
    "lowerarm_l": "LowerArm.L",
    "mixamorig:LeftForeArm": "LowerArm.L",

    "hand.L": "Hand.L",
    "HandL": "Hand.L",
    "hand_l": "Hand.L",
    "mixamorig:LeftHand": "Hand.L",

    # Left fingers
    "Finger1L": "Finger.L",
    "finger_01_l": "Finger.L",
    "Finger2L": "Finger.L.001",
    "finger_02_l": "Finger.L.001",
    "Thumb1L": "Thumb.L",
    "thumb_01_l": "Thumb.L",
    "Thumb2L": "Thumb.L.001",
    "thumb_02_l": "Thumb.L.001",

    # Right arm chain (mirror of left)
    "shoulder.R": "Shoulder.R",
    "ShoulderR": "Shoulder.R",
    "clavicle_r": "Shoulder.R",
    "mixamorig:RightShoulder": "Shoulder.R",

    "upper_arm.R": "UpperArm.R",
    "ArmR": "UpperArm.R",
    "upperarm_r": "UpperArm.R",
    "mixamorig:RightArm": "UpperArm.R",

    "forearm.R": "LowerArm.R",
    "ElbowR": "LowerArm.R",
    "lowerarm_r": "LowerArm.R",
    "mixamorig:RightForeArm": "LowerArm.R",

    "hand.R": "Hand.R",
    "HandR": "Hand.R",
    "hand_r": "Hand.R",
    "mixamorig:RightHand": "Hand.R",

    # Right fingers
    "Finger1R": "Finger.R",
    "finger_01_r": "Finger.R",
    "Finger2R": "Finger.R.001",
    "finger_02_r": "Finger.R.001",
    "Thumb1R": "Thumb.R",
    "thumb_01_r": "Thumb.R",
    "Thumb2R": "Thumb.R.001",
    "thumb_02_r": "Thumb.R.001",

    # Left leg chain
    "thigh.L": "UpperLeg.L",
    "LegL": "UpperLeg.L",
    "thigh_l": "UpperLeg.L",
    "mixamorig:LeftUpLeg": "UpperLeg.L",

    "shin.L": "LowerLeg.L",
    "KneeL": "LowerLeg.L",
    "calf_l": "LowerLeg.L",
    "mixamorig:LeftLeg": "LowerLeg.L",

    "foot.L": "Foot.L",
    "FootL": "Foot.L",
    "foot_l": "Foot.L",
    "mixamorig:LeftFoot": "Foot.L",

    # Right leg chain (mirror)
    "thigh.R": "UpperLeg.R",
    "LegR": "UpperLeg.R",
    "thigh_r": "UpperLeg.R",
    "mixamorig:RightUpLeg": "UpperLeg.R",

    "shin.R": "LowerLeg.R",
    "KneeR": "LowerLeg.R",
    "calf_r": "LowerLeg.R",
    "mixamorig:RightLeg": "LowerLeg.R",

    "foot.R": "Foot.R",
    "FootR": "Foot.R",
    "foot_r": "Foot.R",
    "mixamorig:RightFoot": "Foot.R",
}

# Build a case-insensitive fallback lookup: lowercase_key → canonical_target
# Used when exact match fails.
_BONE_RENAME_LOWER: dict[str, str] = {k.lower(): v for k, v in BONE_RENAME_MAP.items()}

# Required bones for hierarchy validation
REQUIRED_BONES: list[str] = [
    "Hips",
    "Spine", "Chest",
    "Head",
    "Shoulder.L", "UpperArm.L", "LowerArm.L", "Hand.L",
    "Shoulder.R", "UpperArm.R", "LowerArm.R", "Hand.R",
    "UpperLeg.L", "LowerLeg.L", "Foot.L",
    "UpperLeg.R", "LowerLeg.R", "Foot.R",
]

# Mecanim names for Unity FBX export
MECANIM_MAP: dict[str, str] = {
    "Hips": "Hips",
    "Spine": "Spine",
    "Chest": "Chest",
    "Head": "Head",
    "Shoulder.L": "LeftShoulder",
    "UpperArm.L": "LeftUpperArm",
    "LowerArm.L": "LeftLowerArm",
    "Hand.L": "LeftHand",
    "Shoulder.R": "RightShoulder",
    "UpperArm.R": "RightUpperArm",
    "LowerArm.R": "RightLowerArm",
    "Hand.R": "RightHand",
    "UpperLeg.L": "LeftUpperLeg",
    "LowerLeg.L": "LeftLowerLeg",
    "Foot.L": "LeftFoot",
    "UpperLeg.R": "RightUpperLeg",
    "LowerLeg.R": "RightLowerLeg",
    "Foot.R": "RightFoot",
}

# Unreal Engine names for Unreal FBX export
UNREAL_MAP: dict[str, str] = {
    "Hips": "pelvis",
    "Spine": "spine_01",
    "Chest": "spine_02",
    "Head": "head",
    "Shoulder.L": "clavicle_l",
    "UpperArm.L": "upperarm_l",
    "LowerArm.L": "lowerarm_l",
    "Hand.L": "hand_l",
    "Shoulder.R": "clavicle_r",
    "UpperArm.R": "upperarm_r",
    "LowerArm.R": "lowerarm_r",
    "Hand.R": "hand_r",
    "UpperLeg.L": "thigh_l",
    "LowerLeg.L": "calf_l",
    "Foot.L": "foot_l",
    "UpperLeg.R": "thigh_r",
    "LowerLeg.R": "calf_r",
    "Foot.R": "foot_r",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def log(msg: str) -> None:
    print(f"[character_assembler] {msg}", flush=True)


def resolve_bone_name(name: str) -> str | None:
    """Return the canonical Soapbox bone name for a given input name.

    Tries exact match first, then case-insensitive fallback.
    Returns None if no mapping found.
    """
    if name in BONE_RENAME_MAP:
        return BONE_RENAME_MAP[name]
    lower = name.lower()
    if lower in _BONE_RENAME_LOWER:
        return _BONE_RENAME_LOWER[lower]
    return None


def clear_scene() -> None:
    """Remove all default objects from a fresh Blender scene."""
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)


def find_armature() -> bpy.types.Object | None:
    """Return the first ARMATURE object in the scene, or None."""
    for obj in bpy.data.objects:
        if obj.type == "ARMATURE":
            return obj
    return None


def get_mesh_children(armature: bpy.types.Object) -> list[bpy.types.Object]:
    """Return all MESH objects that are direct children of the armature."""
    return [obj for obj in bpy.data.objects if obj.type == "MESH" and obj.parent == armature]


def ensure_object_mode() -> None:
    """Ensure we're in object mode (needed after opening .blend files)."""
    if bpy.context.mode != "OBJECT":
        try:
            bpy.ops.object.mode_set(mode="OBJECT")
        except RuntimeError:
            pass


def deselect_all() -> None:
    ensure_object_mode()
    bpy.ops.object.select_all(action="DESELECT")


def set_active(obj: bpy.types.Object) -> None:
    ensure_object_mode()
    for o in bpy.context.view_layer.objects:
        o.select_set(False)
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj


# ---------------------------------------------------------------------------
# Step 1: Import GLB
# ---------------------------------------------------------------------------

def import_glb(path: str) -> None:
    log(f"Importing: {path}")
    ext = os.path.splitext(path)[1].lower()
    if ext == ".blend":
        bpy.ops.wm.open_mainfile(filepath=path)
    elif ext == ".fbx":
        bpy.ops.wm.read_factory_settings(use_empty=True)
        bpy.ops.import_scene.fbx(filepath=path)
    else:
        bpy.ops.wm.read_factory_settings(use_empty=True)
        bpy.ops.import_scene.gltf(filepath=path)


# ---------------------------------------------------------------------------
# Step 2 & 3: Rename bones and vertex groups
# ---------------------------------------------------------------------------

def rename_bones(armature: bpy.types.Object) -> dict:
    """Enter edit mode on the armature and rename all bones using BONE_RENAME_MAP.

    Returns a stats dict with counts and lists for the report.
    """
    log("Renaming bones...")

    # Build a mapping: old_name → new_name for all bones that will be renamed.
    # We collect this before entering edit mode so vertex groups can be updated.
    rename_plan: dict[str, str] = {}
    unmapped: list[str] = []

    for bone in armature.data.bones:
        target = resolve_bone_name(bone.name)
        if target is not None and target != bone.name:
            rename_plan[bone.name] = target
        elif target is None:
            unmapped.append(bone.name)

    log(f"  Rename plan: {len(rename_plan)} bones to rename, {len(unmapped)} unmapped")

    # Enter edit mode to rename edit bones (avoids pose bone / constraint issues)
    set_active(armature)
    bpy.ops.object.mode_set(mode="EDIT")

    # We must rename via edit bones. Collect them first to avoid mutating while iterating.
    edit_bones = armature.data.edit_bones
    for old_name, new_name in rename_plan.items():
        if old_name in edit_bones:
            # Guard against name collisions: if new_name already exists and is a different
            # bone, we skip (log a warning) to avoid destroying existing correct names.
            if new_name in edit_bones and edit_bones[new_name] != edit_bones[old_name]:
                log(f"  WARNING: Cannot rename '{old_name}' → '{new_name}': target name already occupied by another bone.")
                continue
            edit_bones[old_name].name = new_name
            log(f"  Renamed: '{old_name}' → '{new_name}'")
        else:
            log(f"  WARNING: Bone '{old_name}' not found in edit bones (may have been renamed earlier in loop)")

    bpy.ops.object.mode_set(mode="OBJECT")

    # Rename vertex groups on all mesh children to mirror bone renames
    mesh_children = get_mesh_children(armature)
    for mesh_obj in mesh_children:
        for old_name, new_name in rename_plan.items():
            vg = mesh_obj.vertex_groups.get(old_name)
            if vg is not None:
                vg.name = new_name
                log(f"  VGroup on '{mesh_obj.name}': '{old_name}' → '{new_name}'")

    renamed_count = sum(
        1 for old, new in rename_plan.items()
        if new in armature.data.bones
    )

    return {
        "renamed_bones": renamed_count,
        "unmapped_bones": unmapped,
    }


# ---------------------------------------------------------------------------
# Step 4: Validate hierarchy and weights
# ---------------------------------------------------------------------------

def validate_hierarchy(armature: bpy.types.Object) -> dict:
    """Check that all required bones are present after renaming."""
    log("Validating skeleton hierarchy...")
    present = {bone.name for bone in armature.data.bones}
    missing = [b for b in REQUIRED_BONES if b not in present]
    total_bones = len(present)

    if missing:
        log(f"  WARNING: Missing required bones: {missing}")
    else:
        log(f"  All {len(REQUIRED_BONES)} required bones present. Total bones: {total_bones}")

    return {
        "total_bones": total_bones,
        "missing_required": missing,
        "hierarchy_valid": len(missing) == 0,
    }


def validate_weights(armature: bpy.types.Object) -> dict:
    """Check that >90% of vertices across all mesh children have meaningful weight."""
    log("Validating vertex weights...")
    total_verts = 0
    weighted_verts = 0
    weight_threshold = 0.01

    mesh_children = get_mesh_children(armature)
    if not mesh_children:
        log("  WARNING: No mesh children found on armature — cannot validate weights.")
        return {"total_vertices": 0, "weighted_vertices": 0, "coverage": 0.0}

    for mesh_obj in mesh_children:
        mesh = mesh_obj.data
        vg_names = {vg.index: vg.name for vg in mesh_obj.vertex_groups}

        for vert in mesh.vertices:
            total_verts += 1
            max_w = 0.0
            for group_elem in vert.groups:
                if group_elem.group in vg_names:
                    max_w = max(max_w, group_elem.weight)
            if max_w >= weight_threshold:
                weighted_verts += 1

    coverage = weighted_verts / total_verts if total_verts > 0 else 0.0
    log(f"  Weight coverage: {weighted_verts}/{total_verts} ({coverage:.1%})")
    if coverage < 0.9:
        log("  WARNING: Weight coverage below 90% threshold.")

    return {
        "total_vertices": total_verts,
        "weighted_vertices": weighted_verts,
        "coverage": round(coverage, 4),
    }


# ---------------------------------------------------------------------------
# Step 5: Create DriverMount empty
# ---------------------------------------------------------------------------

def create_driver_mount(armature: bpy.types.Object) -> dict:
    """Place a DriverMount empty at the Hips bone world-space head position.

    The empty is parented to the armature root (object parent, not bone parent)
    so it moves with the character but is not bone-constrained. This makes it easy
    to use as a kart seat attachment point in Unity/Unreal.
    """
    log("Creating DriverMount empty...")

    hips_bone = armature.data.bones.get("Hips")
    if hips_bone is None:
        # Fallback: place at armature origin + 0.85 m up
        world_pos = armature.matrix_world @ Vector((0.0, 0.0, 0.85))
        log("  WARNING: 'Hips' bone not found — placing DriverMount at armature origin + 0.85 m Z.")
    else:
        # Hips bone head in armature local space → world space
        world_pos = armature.matrix_world @ hips_bone.head_local

    bpy.ops.object.empty_add(type="PLAIN_AXES", location=world_pos)
    driver_mount = bpy.context.active_object
    driver_mount.name = "DriverMount"

    # Parent to armature (keep world transform)
    driver_mount.parent = armature
    # Recalculate local transform so the empty stays at its current world position
    driver_mount.matrix_parent_inverse = armature.matrix_world.inverted()

    log(f"  DriverMount placed at world {list(round(c, 4) for c in world_pos)}, parented to '{armature.name}'")

    parent_name = armature.name
    return {
        "position": [round(c, 6) for c in world_pos],
        "parent": parent_name,
    }


# ---------------------------------------------------------------------------
# Step 6: GLB export (Blender convention names, kept as-is)
# ---------------------------------------------------------------------------

def export_glb(armature: bpy.types.Object, output_path: str) -> None:
    """Export the entire scene (armature + meshes + DriverMount) as GLB."""
    log(f"Exporting GLB: {output_path}")
    os.makedirs(os.path.dirname(output_path), exist_ok=True) if os.path.dirname(output_path) else None

    # Select armature and all its children
    deselect_all()
    armature.select_set(True)
    for child in armature.children:
        child.select_set(True)
    # Also select DriverMount
    dm = bpy.data.objects.get("DriverMount")
    if dm:
        dm.select_set(True)

    bpy.ops.export_scene.gltf(
        filepath=output_path,
        use_selection=True,
        export_format="GLB",
        export_apply=False,
    )
    log("  GLB export done.")


# ---------------------------------------------------------------------------
# Step 7 & 8: FBX exports (with temporary bone rename for each convention)
# ---------------------------------------------------------------------------

def _apply_bone_rename_in_edit(armature: bpy.types.Object, rename_map: dict[str, str]) -> dict[str, str]:
    """Rename armature bones according to rename_map in edit mode.

    Returns the reverse map (new_name → old_name) so the caller can undo.
    """
    set_active(armature)
    bpy.ops.object.mode_set(mode="EDIT")
    edit_bones = armature.data.edit_bones
    reverse: dict[str, str] = {}
    for old_name, new_name in rename_map.items():
        if old_name in edit_bones and old_name != new_name:
            if new_name in edit_bones and edit_bones[new_name] != edit_bones[old_name]:
                log(f"  WARNING: FBX rename conflict '{old_name}' → '{new_name}': target occupied.")
                continue
            edit_bones[old_name].name = new_name
            reverse[new_name] = old_name
    bpy.ops.object.mode_set(mode="OBJECT")
    return reverse


def _apply_vgroup_rename(armature: bpy.types.Object, rename_map: dict[str, str]) -> None:
    """Rename vertex groups on mesh children according to rename_map."""
    for mesh_obj in get_mesh_children(armature):
        for old_name, new_name in rename_map.items():
            vg = mesh_obj.vertex_groups.get(old_name)
            if vg is not None:
                vg.name = new_name


def _select_character_objects(armature: bpy.types.Object) -> None:
    """Select armature + mesh children for FBX export (excludes empties like DriverMount)."""
    deselect_all()
    armature.select_set(True)
    bpy.context.view_layer.objects.active = armature
    for child in get_mesh_children(armature):
        child.select_set(True)


def export_fbx_unity(armature: bpy.types.Object, output_path: str) -> None:
    """Temporarily rename bones to Mecanim convention, export Unity FBX, then restore."""
    log(f"Exporting Unity FBX: {output_path}")
    os.makedirs(os.path.dirname(output_path), exist_ok=True) if os.path.dirname(output_path) else None

    # Apply Mecanim bone renames
    reverse_map = _apply_bone_rename_in_edit(armature, MECANIM_MAP)
    _apply_vgroup_rename(armature, MECANIM_MAP)

    _select_character_objects(armature)
    bpy.ops.export_scene.fbx(
        filepath=output_path,
        use_selection=True,
        apply_scale_options="FBX_SCALE_ALL",
        axis_forward="-Z",
        axis_up="Y",
        add_leaf_bones=False,
        mesh_smooth_type="FACE",
    )

    # Restore Soapbox names
    _apply_bone_rename_in_edit(armature, reverse_map)
    _apply_vgroup_rename(armature, reverse_map)

    log("  Unity FBX export done, bone names restored.")


def export_fbx_unreal(armature: bpy.types.Object, output_path: str) -> None:
    """Temporarily rename bones to Unreal convention, export Unreal FBX, then restore."""
    log(f"Exporting Unreal FBX: {output_path}")
    os.makedirs(os.path.dirname(output_path), exist_ok=True) if os.path.dirname(output_path) else None

    # Apply Unreal bone renames
    reverse_map = _apply_bone_rename_in_edit(armature, UNREAL_MAP)
    _apply_vgroup_rename(armature, UNREAL_MAP)

    _select_character_objects(armature)
    bpy.ops.export_scene.fbx(
        filepath=output_path,
        use_selection=True,
        apply_scale_options="FBX_SCALE_ALL",
        axis_forward="X",
        axis_up="Z",
        add_leaf_bones=False,
        mesh_smooth_type="FACE",
    )

    # Restore Soapbox names
    _apply_bone_rename_in_edit(armature, reverse_map)
    _apply_vgroup_rename(armature, reverse_map)

    log("  Unreal FBX export done, bone names restored.")


# ---------------------------------------------------------------------------
# Step 9: Write report
# ---------------------------------------------------------------------------

def write_report(report: dict, path: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True) if os.path.dirname(path) else None
    with open(path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=4)
    log(f"Report written to: {path}")


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------

def main() -> None:
    log("=== Character Assembler start ===")
    log(f"  character_id  : {args.character_id}")
    log(f"  input         : {args.input}")
    log(f"  output_fbx    : {args.output_fbx}")
    log(f"  output_glb    : {args.output_glb}")
    log(f"  report        : {args.report}")

    # ---- Scene setup ----
    clear_scene()

    # ---- 1. Import GLB ----
    import_glb(args.input)

    # ---- 2. Find armature ----
    armature = find_armature()
    if armature is None:
        log("FATAL: No ARMATURE object found in imported GLB.")
        sys.exit(1)
    log(f"Armature found: '{armature.name}' with {len(armature.data.bones)} bones")

    # ---- 3. Rename bones ----
    rename_stats = rename_bones(armature)

    # ---- 4. Validate hierarchy ----
    hierarchy_stats = validate_hierarchy(armature)
    hierarchy_stats.update(rename_stats)  # merge renamed_bones + unmapped_bones into skeleton block

    # ---- 5. Validate weights ----
    weight_stats = validate_weights(armature)

    # ---- 6. Create DriverMount ----
    driver_mount_stats = create_driver_mount(armature)

    # ---- 7. Export GLB ----
    export_glb(armature, args.output_glb)

    # ---- 8. Export Unity FBX (--output-fbx is treated as Unity FBX) ----
    export_fbx_unity(armature, args.output_fbx)

    # Derive Unreal FBX path automatically from Unity FBX path
    # e.g. character_unity.fbx → character_unreal.fbx
    unity_fbx_path = args.output_fbx
    if "_unity" in unity_fbx_path:
        unreal_fbx_path = unity_fbx_path.replace("_unity", "_unreal")
    else:
        base, ext = os.path.splitext(unity_fbx_path)
        unreal_fbx_path = base + "_unreal" + ext

    export_fbx_unreal(armature, unreal_fbx_path)

    # ---- 9. Build and write report ----
    report: dict = {
        "character_id": args.character_id,
        "source": args.input,
        "outputs": {
            "glb": args.output_glb,
            "unity_fbx": args.output_fbx,
            "unreal_fbx": unreal_fbx_path,
        },
        "skeleton": hierarchy_stats,
        "weights": weight_stats,
        "driver_mount": driver_mount_stats,
    }

    if args.report:
        write_report(report, args.report)

    # Print summary
    log("=== Character Assembler complete ===")
    log(f"  Bones total   : {hierarchy_stats['total_bones']}")
    log(f"  Bones renamed : {hierarchy_stats['renamed_bones']}")
    log(f"  Unmapped bones: {hierarchy_stats['unmapped_bones']}")
    log(f"  Missing req'd : {hierarchy_stats['missing_required']}")
    log(f"  Hierarchy OK  : {hierarchy_stats['hierarchy_valid']}")
    log(f"  Weight cover  : {weight_stats['coverage']:.1%} ({weight_stats['weighted_vertices']}/{weight_stats['total_vertices']})")
    log(f"  DriverMount   : {driver_mount_stats['position']}")


if __name__ == "__main__":
    main()
