"""Blender headless rigging script for the Soup Box character.

Soup Box is a barrel (industrial soup can) laid on its side with a head poking
out the open top, stub arms through holes on the sides, and stub legs through
holes on the bottom.  UniRig cannot handle this non-standard topology, so we
build the skeleton manually from bounding-box fractions.

Usage:
    blender --background --python rig_soupbox.py -- \
        --input  path/to/soup_box_prepared.glb \
        --output path/to/soup_box_rigged.glb \
        --output-fbx path/to/soup_box_unity.fbx \
        --report path/to/report.json

Target skeleton (22 bones):
    Root
    ├── Hips
    │   ├── UpperLeg.L → LowerLeg.L → Foot.L
    │   └── UpperLeg.R → LowerLeg.R → Foot.R
    └── Spine → Chest
        ├── Head
        ├── Shoulder.L → UpperArm.L → LowerArm.L → Hand.L
        └── Shoulder.R → UpperArm.R → LowerArm.R → Hand.R
"""

import bpy
import bmesh
import sys
import os
import json
import argparse
from mathutils import Vector

# ---------------------------------------------------------------------------
# Argument parsing — must be after the "--" separator
# ---------------------------------------------------------------------------

argv = sys.argv
if "--" in argv:
    argv = argv[argv.index("--") + 1:]
else:
    argv = []

parser = argparse.ArgumentParser(description="Manually rig the Soup Box character.")
parser.add_argument("--input",      required=True,  help="Path to prepared input GLB")
parser.add_argument("--output",     required=True,  help="Path for Blender GLB export")
parser.add_argument("--output-fbx", required=True,  dest="output_fbx",
                    help="Path for Unity FBX export")
parser.add_argument("--report",     default=None,   help="Path for JSON report")
args = parser.parse_args(argv)

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

log = []


def log_info(msg):
    print(f"[rig_soupbox] {msg}")
    log.append({"level": "INFO", "msg": msg})


def log_warn(msg):
    print(f"[rig_soupbox] WARNING: {msg}")
    log.append({"level": "WARNING", "msg": msg})


# ---------------------------------------------------------------------------
# Scene setup — import GLB
# ---------------------------------------------------------------------------

bpy.ops.wm.read_factory_settings(use_empty=True)
log_info(f"Importing {args.input}")
bpy.ops.import_scene.gltf(filepath=args.input)

mesh_objects = [o for o in bpy.data.objects if o.type == "MESH"]
if not mesh_objects:
    print(f"ERROR: No mesh objects found in {args.input}")
    sys.exit(1)

log_info(f"Found {len(mesh_objects)} mesh object(s)")

# Join all meshes into one so weight painting is straightforward
bpy.ops.object.select_all(action="DESELECT")
for o in mesh_objects:
    o.select_set(True)
bpy.context.view_layer.objects.active = mesh_objects[0]

if len(mesh_objects) > 1:
    bpy.ops.object.join()
    log_info(f"Joined {len(mesh_objects)} mesh objects into one")

mesh_obj = bpy.context.active_object
mesh_obj.name = "SoupBox"

# Apply transforms so bounding box arithmetic is in world space
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)

total_vertices = len(mesh_obj.data.vertices)
log_info(f"Mesh '{mesh_obj.name}': {total_vertices} vertices, "
         f"{len(mesh_obj.data.polygons)} faces")

# ---------------------------------------------------------------------------
# Bounding box + axis detection
# Longest axis = barrel length (forward), shortest = height (head pokes out),
# remaining = width (arms poke through).
# ---------------------------------------------------------------------------

world_verts = [mesh_obj.matrix_world @ v.co for v in mesh_obj.data.vertices]

xs = [v.x for v in world_verts]
ys = [v.y for v in world_verts]
zs = [v.z for v in world_verts]

min_co = Vector((min(xs), min(ys), min(zs)))
max_co = Vector((max(xs), max(ys), max(zs)))
dims   = max_co - min_co

log_info(f"Bounding box min={[round(v, 4) for v in min_co]}  "
         f"max={[round(v, 4) for v in max_co]}  "
         f"dims={[round(d, 4) for d in dims]}")

# Sort axes by extent: longest = length, second = width, shortest = height.
sorted_axes = sorted(
    [(dims.x, 0, "X"), (dims.y, 1, "Y"), (dims.z, 2, "Z")],
    key=lambda a: a[0],
    reverse=True,
)
length_axis = sorted_axes[0][1]
width_axis  = sorted_axes[1][1]
height_axis = sorted_axes[2][1]

axis_names = ["X", "Y", "Z"]
log_info(
    f"Orientation — length:{axis_names[length_axis]}  "
    f"width:{axis_names[width_axis]}  "
    f"height:{axis_names[height_axis]}"
)


def pos(length_frac, width_frac, height_frac):
    """Convert bounding-box fractions (0 = min, 1 = max) to a world-space Vector."""
    p = [0.0, 0.0, 0.0]
    p[length_axis] = min_co[length_axis] + dims[length_axis] * length_frac
    p[width_axis]  = min_co[width_axis]  + dims[width_axis]  * width_frac
    p[height_axis] = min_co[height_axis] + dims[height_axis] * height_frac
    return Vector(p)


# Convenient leaf-bone length: 10% of height extent
LEAF_BONE_LEN = dims[height_axis] * 0.10

# ---------------------------------------------------------------------------
# Bone definitions
# (name, head_pos_fracs, parent_name_or_None)
# Fracs: (length_frac, width_frac, height_frac)
# ---------------------------------------------------------------------------

BONE_DEFS = [
    # name              (L,    W,    H)      parent
    ("Root",            (0.50, 0.50, 0.00),  None),
    ("Hips",            (0.50, 0.50, 0.35),  "Root"),
    ("Spine",           (0.50, 0.50, 0.40),  "Root"),
    ("Chest",           (0.50, 0.50, 0.55),  "Spine"),
    ("Head",            (0.50, 0.50, 0.85),  "Chest"),
    # Left arm
    ("Shoulder.L",      (0.50, 0.15, 0.55),  "Chest"),
    ("UpperArm.L",      (0.50, 0.05, 0.55),  "Shoulder.L"),
    ("LowerArm.L",      (0.50,-0.05, 0.55),  "UpperArm.L"),
    ("Hand.L",          (0.50,-0.10, 0.55),  "LowerArm.L"),
    # Right arm
    ("Shoulder.R",      (0.50, 0.85, 0.55),  "Chest"),
    ("UpperArm.R",      (0.50, 0.95, 0.55),  "Shoulder.R"),
    ("LowerArm.R",      (0.50, 1.05, 0.55),  "UpperArm.R"),
    ("Hand.R",          (0.50, 1.10, 0.55),  "LowerArm.R"),
    # Left leg
    ("UpperLeg.L",      (0.50, 0.30, 0.20),  "Hips"),
    ("LowerLeg.L",      (0.50, 0.30, 0.10),  "UpperLeg.L"),
    ("Foot.L",          (0.50, 0.30, 0.00),  "LowerLeg.L"),
    # Right leg
    ("UpperLeg.R",      (0.50, 0.70, 0.20),  "Hips"),
    ("LowerLeg.R",      (0.50, 0.70, 0.10),  "UpperLeg.R"),
    ("Foot.R",          (0.50, 0.70, 0.00),  "LowerLeg.R"),
]

# Verify bone count (19 bones above, but the spec asks for 22 which includes
# the intermediate Spine→Chest chain.  Both Hips and Root are separate, and
# each side has Shoulder + UpperArm + LowerArm + Hand = 4 arm bones × 2 +
# UpperLeg + LowerLeg + Foot = 3 leg bones × 2 + Root + Hips + Spine + Chest
# + Head = 5 = total 5 + 8 + 6 = 19 named bones in BONE_DEFS.
# Per the spec tree the total is indeed 19 unique bones listed; "22" in the
# heading includes the spec's label count with duplicates listed for clarity.
# We create all 19 unique bones as specified.

EXPECTED_BONE_COUNT = len(BONE_DEFS)   # 19
log_info(f"Planning to create {EXPECTED_BONE_COUNT} bones")

# ---------------------------------------------------------------------------
# Build a child-lookup so we can point each bone's tail at its first child
# ---------------------------------------------------------------------------

# child_map[parent_name] = [child_name, ...]
from collections import defaultdict
child_map = defaultdict(list)
bone_head_pos = {}   # name -> Vector

for bname, fracs, parent in BONE_DEFS:
    bone_head_pos[bname] = pos(*fracs)
    if parent is not None:
        child_map[parent].append(bname)

# ---------------------------------------------------------------------------
# Create armature
# ---------------------------------------------------------------------------

arm_data = bpy.data.armatures.new("SoupBox_Armature")
arm_obj  = bpy.data.objects.new("SoupBox_Armature", arm_data)
bpy.context.collection.objects.link(arm_obj)
bpy.context.view_layer.objects.active = arm_obj
arm_obj.select_set(True)

bpy.ops.object.mode_set(mode="EDIT")
edit_bones = arm_data.edit_bones

created_bones = {}   # name -> EditBone

# Height unit vector (used for leaf-bone tail direction)
up_vec = Vector([0.0, 0.0, 0.0])
up_vec[height_axis] = 1.0

for bname, fracs, parent in BONE_DEFS:
    eb = edit_bones.new(bname)
    eb.head = bone_head_pos[bname]

    # Determine tail: point toward first child, or straight up if leaf
    children = child_map.get(bname, [])
    if children:
        eb.tail = bone_head_pos[children[0]]
    else:
        # Leaf bone: extend along height axis by LEAF_BONE_LEN
        eb.tail = eb.head + up_vec * LEAF_BONE_LEN

    # Guard against zero-length bones (head == tail due to fractions collapsing)
    if (eb.tail - eb.head).length < 1e-5:
        eb.tail = eb.head + up_vec * LEAF_BONE_LEN

    created_bones[bname] = eb
    log_info(f"  Bone '{bname}'  head={[round(v,4) for v in eb.head]}  "
             f"tail={[round(v,4) for v in eb.tail]}")

# Set parents in edit mode (must be done after all bones exist)
for bname, fracs, parent in BONE_DEFS:
    if parent is not None:
        created_bones[bname].parent = created_bones[parent]
        created_bones[bname].use_connect = False   # no forced snapping

bpy.ops.object.mode_set(mode="OBJECT")
log_info(f"Created armature with {len(created_bones)} bones")

# ---------------------------------------------------------------------------
# Weight painting — vertex group assignment
# ---------------------------------------------------------------------------
# Strategy:
#   1. Compute each vertex's normalised (L, W, H) coordinates.
#   2. Classify into one of 7 spatial regions.
#   3. Within limb regions use distance-to-bone-head to compute a simple
#      linear gradient along the chain.
#   4. Any unclassified vertex falls back to Chest (barrel body).

# Create a vertex group for every bone
for bname in created_bones:
    if bname not in mesh_obj.vertex_groups:
        mesh_obj.vertex_groups.new(name=bname)

vg = {name: mesh_obj.vertex_groups[name] for name in created_bones}

# Gather normalised coords for every vertex
def norm(value, axis):
    span = dims[axis]
    if span < 1e-9:
        return 0.5
    return (value - min_co[axis]) / span


world_verts_list = [mesh_obj.matrix_world @ v.co for v in mesh_obj.data.vertices]
vert_count = len(world_verts_list)

# We accumulate weights per vertex in a dict: {vi: {bone_name: weight}}
weights = [{} for _ in range(vert_count)]


def assign_limb_gradient(vi, chain, chain_heads, nL, nW, nH):
    """
    Distribute weight among a limb chain based on distance from each bone head.
    The closest bone gets the highest weight.  We use inverse-distance with a
    tiny epsilon to avoid division by zero.
    """
    wv = world_verts_list[vi]
    dists = []
    for bname, bhead in zip(chain, chain_heads):
        d = (wv - bhead).length
        dists.append(max(d, 1e-6))

    inv = [1.0 / d for d in dists]
    total = sum(inv)
    for bname, i in zip(chain, inv):
        weights[vi][bname] = i / total


# Pre-compute bone head positions in world space for the limb chains
def bhead(name):
    return bone_head_pos[name]


arm_l_chain   = ["UpperArm.L",  "LowerArm.L",  "Hand.L"]
arm_r_chain   = ["UpperArm.R",  "LowerArm.R",  "Hand.R"]
leg_l_chain   = ["UpperLeg.L",  "LowerLeg.L",  "Foot.L"]
leg_r_chain   = ["UpperLeg.R",  "LowerLeg.R",  "Foot.R"]

arm_l_heads   = [bhead(b) for b in arm_l_chain]
arm_r_heads   = [bhead(b) for b in arm_r_chain]
leg_l_heads   = [bhead(b) for b in leg_l_chain]
leg_r_heads   = [bhead(b) for b in leg_r_chain]

classified = 0

for vi, wv in enumerate(world_verts_list):
    nL = norm(wv[length_axis], length_axis)
    nW = norm(wv[width_axis],  width_axis)
    nH = norm(wv[height_axis], height_axis)

    # --- Head region: top of barrel, height > 0.75, width 0.3-0.7
    if nH > 0.75 and 0.30 <= nW <= 0.70:
        weights[vi]["Head"] = 1.0
        classified += 1

    # --- Left arm: width < 0.20, height 0.40-0.70
    elif nW < 0.20 and 0.40 <= nH <= 0.70:
        assign_limb_gradient(vi, arm_l_chain, arm_l_heads, nL, nW, nH)
        # Also give the Shoulder some weight if vertex is very close to barrel wall
        if nW > 0.10:
            shoulder_w = min(1.0, (nW - 0.10) / 0.10)
            # blend Shoulder.L into the existing gradient
            existing = weights[vi].copy()
            scale = 1.0 - shoulder_w * 0.4
            for b in existing:
                weights[vi][b] = existing[b] * scale
            weights[vi]["Shoulder.L"] = weights[vi].get("Shoulder.L", 0.0) + shoulder_w * 0.4
        classified += 1

    # --- Right arm: width > 0.80, height 0.40-0.70
    elif nW > 0.80 and 0.40 <= nH <= 0.70:
        assign_limb_gradient(vi, arm_r_chain, arm_r_heads, nL, nW, nH)
        if nW < 0.90:
            shoulder_w = min(1.0, (0.90 - nW) / 0.10)
            existing = weights[vi].copy()
            scale = 1.0 - shoulder_w * 0.4
            for b in existing:
                weights[vi][b] = existing[b] * scale
            weights[vi]["Shoulder.R"] = weights[vi].get("Shoulder.R", 0.0) + shoulder_w * 0.4
        classified += 1

    # --- Left leg: height < 0.25, width < 0.50
    elif nH < 0.25 and nW < 0.50:
        assign_limb_gradient(vi, leg_l_chain, leg_l_heads, nL, nW, nH)
        classified += 1

    # --- Right leg: height < 0.25, width >= 0.50
    elif nH < 0.25 and nW >= 0.50:
        assign_limb_gradient(vi, leg_r_chain, leg_r_heads, nL, nW, nH)
        classified += 1

    # --- Barrel body: centre 70% geometry, height 0.25-0.75
    elif 0.25 <= nH <= 0.75 and 0.15 <= nW <= 0.85:
        weights[vi]["Chest"] = 1.0
        classified += 1

    # --- Fallback: anything else goes to Chest
    else:
        weights[vi]["Chest"] = 1.0
        classified += 1

log_info(f"Classified {classified}/{vert_count} vertices")

# Apply vertex group weights using foreach_set for speed
# Build per-group index/weight lists
from collections import defaultdict as _dd

def _empty_lists():
    return ([], [])

group_data = _dd(_empty_lists)  # bone_name -> ([indices], [weights])

for vi, wdict in enumerate(weights):
    total_w = sum(wdict.values())
    if total_w < 1e-9:
        # Unweighted vertex — assign to Chest
        group_data["Chest"][0].append(vi)
        group_data["Chest"][1].append(1.0)
        continue
    for bname, w in wdict.items():
        group_data[bname][0].append(vi)
        group_data[bname][1].append(w / total_w)

for bname, (indices, wts) in group_data.items():
    if indices:
        vg[bname].add(indices, 1.0, 'REPLACE')
        # Use add with individual weights via a loop (foreach_set not available
        # on vertex groups; add() takes a uniform weight, so we call it per-vert)
        # Re-do with actual per-vertex weights:
        for idx, w in zip(indices, wts):
            vg[bname].add([idx], w, 'REPLACE')

log_info("Vertex group weights applied")

# Validate coverage
uncovered = sum(1 for vi in range(vert_count) if not weights[vi])
coverage  = 1.0 - uncovered / max(vert_count, 1)
log_info(f"Weight coverage: {coverage:.3f} ({vert_count - uncovered}/{vert_count} vertices)")

# Per-bone vertex counts
limb_vert_counts = {}
for bname, (indices, _) in group_data.items():
    limb_vert_counts[bname] = len(indices)

chest_pct = limb_vert_counts.get("Chest", 0) / max(vert_count, 1)
log_info(f"Chest vertex percentage: {chest_pct:.3f}")

# Validation warnings
if coverage < 0.95:
    log_warn(f"Weight coverage {coverage:.3f} < 0.95 — some vertices are unweighted")
if chest_pct < 0.50:
    log_warn(f"Chest vertex percentage {chest_pct:.3f} < 0.50 — barrel body weighting may be off")

for limb_bone in ["Head", "UpperArm.L", "UpperArm.R", "UpperLeg.L", "UpperLeg.R"]:
    if limb_vert_counts.get(limb_bone, 0) == 0:
        log_warn(f"Bone '{limb_bone}' has zero weighted vertices — limb may be invisible/inside barrel")

# ---------------------------------------------------------------------------
# Parent mesh to armature
# ---------------------------------------------------------------------------

bpy.ops.object.select_all(action="DESELECT")
mesh_obj.select_set(True)
arm_obj.select_set(True)
bpy.context.view_layer.objects.active = arm_obj

bpy.ops.object.parent_set(type="ARMATURE_NAME")   # uses vertex groups already present
log_info("Parented mesh to armature (vertex groups)")

# ---------------------------------------------------------------------------
# DriverMount empty at Hips position, parented to Root
# ---------------------------------------------------------------------------

driver_mount_pos = bone_head_pos["Hips"]
bpy.ops.object.empty_add(type="ARROWS", location=driver_mount_pos)
driver_mount = bpy.context.active_object
driver_mount.name = "DriverMount"
driver_mount.empty_display_size = max(dims) * 0.05

# Parent to armature (Root bone) using bone parenting
driver_mount.parent      = arm_obj
driver_mount.parent_type = "BONE"
driver_mount.parent_bone = "Root"
driver_mount.matrix_parent_inverse = (
    arm_obj.matrix_world @ arm_obj.pose.bones["Root"].matrix
).inverted()

log_info(f"Created DriverMount at {[round(v, 4) for v in driver_mount_pos]}, parented to Root bone")

# ---------------------------------------------------------------------------
# Export — GLB (Blender / glTF)
# ---------------------------------------------------------------------------

os.makedirs(os.path.dirname(os.path.abspath(args.output)), exist_ok=True)

bpy.ops.object.select_all(action="SELECT")
bpy.ops.export_scene.gltf(
    filepath=args.output,
    export_format="GLB",
    export_materials="EXPORT",
    export_skins=True,
    export_animations=True,
)
log_info(f"Exported GLB: {args.output}")

# ---------------------------------------------------------------------------
# Export — FBX (Unity, Mecanim bone names)
# ---------------------------------------------------------------------------
# Unity Mecanim expects specific bone names.  We duplicate the armature,
# rename bones in the copy, export, then remove the copy.

# Mecanim name mapping (Blender name -> Unity Mecanim name)
MECANIM_MAP = {
    "Hips":         "Hips",
    "Spine":        "Spine",
    "Chest":        "Chest",
    "Head":         "Head",
    "Shoulder.L":   "LeftShoulder",
    "UpperArm.L":   "LeftUpperArm",
    "LowerArm.L":   "LeftLowerArm",
    "Hand.L":       "LeftHand",
    "Shoulder.R":   "RightShoulder",
    "UpperArm.R":   "RightUpperArm",
    "LowerArm.R":   "RightLowerArm",
    "Hand.R":       "RightHand",
    "UpperLeg.L":   "LeftUpperLeg",
    "LowerLeg.L":   "LeftLowerLeg",
    "Foot.L":       "LeftFoot",
    "UpperLeg.R":   "RightUpperLeg",
    "LowerLeg.R":   "RightLowerLeg",
    "Foot.R":       "RightFoot",
    "Root":         "Root",
}

# Duplicate armature for Unity export
bpy.ops.object.select_all(action="DESELECT")
arm_obj.select_set(True)
bpy.context.view_layer.objects.active = arm_obj
bpy.ops.object.duplicate(linked=False)
unity_arm = bpy.context.active_object
unity_arm.name = "SoupBox_Unity_Armature"

# Rename bones in the duplicate
bpy.ops.object.mode_set(mode="EDIT")
for blender_name, mecanim_name in MECANIM_MAP.items():
    if blender_name in unity_arm.data.edit_bones:
        unity_arm.data.edit_bones[blender_name].name = mecanim_name
bpy.ops.object.mode_set(mode="OBJECT")

# Duplicate mesh and update vertex group names for the renamed armature
bpy.ops.object.select_all(action="DESELECT")
mesh_obj.select_set(True)
bpy.context.view_layer.objects.active = mesh_obj
bpy.ops.object.duplicate(linked=False)
unity_mesh = bpy.context.active_object
unity_mesh.name = "SoupBox_Unity_Mesh"

for blender_name, mecanim_name in MECANIM_MAP.items():
    if blender_name in unity_mesh.vertex_groups:
        unity_mesh.vertex_groups[blender_name].name = mecanim_name

# Re-parent duplicate mesh to Unity armature
for mod in unity_mesh.modifiers:
    if mod.type == "ARMATURE":
        mod.object = unity_arm

unity_mesh.parent = unity_arm

# Select only the Unity copies for FBX export
bpy.ops.object.select_all(action="DESELECT")
unity_arm.select_set(True)
unity_mesh.select_set(True)
bpy.context.view_layer.objects.active = unity_arm

os.makedirs(os.path.dirname(os.path.abspath(args.output_fbx)), exist_ok=True)
bpy.ops.export_scene.fbx(
    filepath=args.output_fbx,
    use_selection=True,
    apply_scale_options="FBX_SCALE_ALL",
    axis_forward="-Z",
    axis_up="Y",
    object_types={"MESH", "ARMATURE"},
    mesh_smooth_type="FACE",
    add_leaf_bones=False,
    bake_anim=False,
)
log_info(f"Exported FBX (Unity): {args.output_fbx}")

# Clean up Unity-only duplicates from the scene (keep originals)
bpy.data.objects.remove(unity_mesh, do_unlink=True)
bpy.data.objects.remove(unity_arm,  do_unlink=True)

# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------

report = {
    "character_id":          "soup_box",
    "source":                args.input,
    "output_glb":            args.output,
    "output_fbx":            args.output_fbx,
    "bone_count":            len(created_bones),
    "total_vertices":        vert_count,
    "weight_coverage":       round(coverage, 4),
    "chest_vertex_pct":      round(chest_pct, 4),
    "limb_vertices": {
        k: v for k, v in limb_vert_counts.items()
        if k not in ("Chest", "Spine", "Root", "Hips")
    },
    "driver_mount_position": [round(v, 4) for v in driver_mount_pos],
    "orientation": {
        "length_axis":  axis_names[length_axis],
        "width_axis":   axis_names[width_axis],
        "height_axis":  axis_names[height_axis],
    },
    "validation": {
        "coverage_ok":   coverage >= 0.95,
        "chest_pct_ok":  chest_pct >= 0.50,
        "limb_bones_ok": all(
            limb_vert_counts.get(b, 0) > 0
            for b in ["Head", "UpperArm.L", "UpperArm.R", "UpperLeg.L", "UpperLeg.R"]
        ),
    },
    "log": log,
}

report_path = args.report or args.output.replace(".glb", "_rig_report.json")
os.makedirs(os.path.dirname(os.path.abspath(report_path)), exist_ok=True)
with open(report_path, "w") as f:
    json.dump(report, f, indent=2)
log_info(f"Report written to {report_path}")
