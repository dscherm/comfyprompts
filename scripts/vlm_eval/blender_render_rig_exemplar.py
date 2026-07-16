"""Headless Blender: build the canonical GOOD/BAD rig-deformation exemplar pair.

Loads a rigged, textured-free FBX (mesh + armature, read-only import into a fresh
in-memory scene) and produces two twins that differ in EXACTLY ONE variable — skin
weights:

- GOOD twin: the mesh with its original (AccuRIG) skin weights, untouched.
- BAD twin: the same mesh + same skeleton, but with the vertex groups replaced by
  naive envelope-based automatic weights (``bpy.ops.object.parent_set`` with
  ``type='ARMATURE_ENVELOPE'``). This reproduces the "bad automatic weights"
  mechanism documented in lessons/unirig-skin-weights-melt-use-accurig.md.

Both twins are posed identically (same bone, same rotation) and rendered from the
same camera with the same lighting, one PNG per (twin, pose). The source FBX is
never written to.

Usage:
    blender --background --factory-startup --python blender_render_rig_exemplar.py \\
        -- <model_path> <rig_kind> <seed> <out_dir>

``model_path`` may be an FBX or a GLB/GLTF. ``rig_kind`` selects the diagnostic
pose table: ``humanoid`` (AccuRIG CC_Base bone names) or ``quadruped`` (UniRig
generic bone_N names as produced for the GrimForge bestiary quads).

The pipeline is fully deterministic (fixed geometry, fixed bend angles, fixed
camera math) — ``seed`` is accepted for interface consistency with the rest of the
vlm_eval toolchain but does not drive any randomness here.
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector

# bone to rotate, rotation_euler axis index (0=X,1=Y,2=Z), angle in degrees,
# vertex groups used to locate the joint for camera framing, how far (as a
# fraction of character height) a candidate vertex may be from the group's
# median position before it's discarded as an unrelated prop (e.g. a held
# weapon sharing the same bone weights), and the camera's ortho view size /
# azimuth / elevation (also as fractions/degrees).
POSE_TABLES: dict[str, dict[str, dict[str, object]]] = {
    "humanoid": {
        "knee_bend": {
            "bone": "CC_Base_L_Calf",
            "axis": 0,
            "angle_deg": -90,
            "vgroups": ["CC_Base_L_CalfTwist01", "CC_Base_L_CalfTwist02"],
            "radius_frac": 0.25,
            "view_frac": 0.85,
        },
        "elbow_bend": {
            "bone": "CC_Base_L_Forearm",
            "axis": 0,
            "angle_deg": 100,
            "vgroups": ["CC_Base_L_ForearmTwist01", "CC_Base_L_ForearmTwist02"],
            "radius_frac": 0.15,
            "view_frac": 0.45,
        },
        "hip_flex": {
            "bone": "CC_Base_L_Thigh",
            "axis": 0,
            "angle_deg": -90,
            "vgroups": ["CC_Base_L_ThighTwist01", "CC_Base_L_ThighTwist02"],
            "radius_frac": 0.3,
            "view_frac": 0.85,
        },
    },
    # UniRig ArticulationXL skeleton on the GrimForge bestiary quads (generic
    # bone_N names, animal faces -Y). Chain map for hell_hound_rigged.glb:
    # spine bone_0..3, head bone_4/5, front legs bone_6-9 / bone_10-13,
    # hind legs bone_14-17 / bone_18-21, tail bone_22-24. UniRig bone local
    # axes are arbitrary, but the exemplar contract only needs an identical,
    # substantial rotation on both twins — the good/bad delta is what matters.
    "quadruped": {
        "front_knee_bend": {
            "bone": "bone_8",
            "axis": 0,
            "angle_deg": 75,
            "vgroups": ["bone_8"],
            "radius_frac": 0.6,
            "view_frac": 0.9,
        },
        "hind_knee_bend": {
            "bone": "bone_16",
            "axis": 0,
            "angle_deg": 75,
            "vgroups": ["bone_16"],
            "radius_frac": 0.6,
            "view_frac": 0.9,
        },
        "neck_bend": {
            "bone": "bone_3",
            "axis": 0,
            "angle_deg": 45,
            "vgroups": ["bone_4"],
            "radius_frac": 0.6,
            "view_frac": 0.9,
        },
    },
}

BACKGROUND_COLOR = (0.82, 0.83, 0.86, 1.0)
RESOLUTION = 768
CAM_AZIMUTH_DEG = 40.0
CAM_ELEVATION_DEG = 11.0
CAM_DIST_FACTOR = 2.5


def _parse_args() -> tuple[str, str, int, str]:
    argv = sys.argv[sys.argv.index("--") + 1 :]
    model_path, rig_kind, seed_str, out_dir = argv[0], argv[1], argv[2], argv[3]
    if rig_kind not in POSE_TABLES:
        print(f"ERROR: unknown rig_kind '{rig_kind}' (want one of {sorted(POSE_TABLES)})",
              file=sys.stderr)
        sys.exit(1)
    return model_path, rig_kind, int(seed_str), out_dir


def _reset_pose(rig: bpy.types.Object) -> None:
    for pb in rig.pose.bones:
        pb.rotation_mode = "XYZ"
        pb.rotation_euler = (0.0, 0.0, 0.0)
        pb.rotation_quaternion = (1.0, 0.0, 0.0, 0.0)
        pb.location = (0.0, 0.0, 0.0)
        pb.scale = (1.0, 1.0, 1.0)


def _apply_bend(rig: bpy.types.Object, bone: str, axis: int, angle_deg: float) -> None:
    pb = rig.pose.bones[bone]
    pb.rotation_mode = "XYZ"
    euler = [0.0, 0.0, 0.0]
    euler[axis] = math.radians(angle_deg)
    pb.rotation_euler = euler


def _import_and_validate(model_path: str) -> tuple[bpy.types.Object, bpy.types.Object]:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    suffix = Path(model_path).suffix.lower()
    if suffix == ".fbx":
        bpy.ops.import_scene.fbx(filepath=model_path)
    elif suffix in (".glb", ".gltf"):
        bpy.ops.import_scene.gltf(filepath=model_path)
    else:
        print(f"ERROR: unsupported model format '{suffix}' for {model_path}", file=sys.stderr)
        sys.exit(1)

    arm_objs = [o for o in bpy.data.objects if o.type == "ARMATURE"]
    if not arm_objs:
        print(f"ERROR: no armature found in {model_path}", file=sys.stderr)
        sys.exit(1)
    arm_obj = arm_objs[0]

    # The skinned body is the mesh bound to the armature with actual weights —
    # some assets ship extra unskinned meshes (e.g. the hell hound's Icosphere
    # eye prop) that must not be mistaken for the body nor left floating in
    # renders while the body deforms.
    skinned = [
        o for o in bpy.data.objects
        if o.type == "MESH"
        and any(m.type == "ARMATURE" and m.object == arm_obj for m in o.modifiers)
        and len(o.vertex_groups) > 0
    ]
    if not skinned:
        print(f"ERROR: no mesh skinned to '{arm_obj.name}' found in {model_path}",
              file=sys.stderr)
        sys.exit(1)
    mesh_obj = max(skinned, key=lambda o: len(o.data.vertices))
    for o in bpy.data.objects:
        if o.type == "MESH" and o is not mesh_obj:
            o.hide_render = True

    # FBX imports of this kind ship a baked-in "pose" action (e.g. a
    # "0_T-Pose" clip) that is NOT a clean rest pose — its F-curves keep
    # overwriting any manual pose_bone assignment on every depsgraph
    # evaluation unless the action is discarded first.
    arm_obj.animation_data_clear()
    _reset_pose(arm_obj)
    bpy.context.view_layer.update()

    return arm_obj, mesh_obj


def _make_bad_twin(
    mesh_good: bpy.types.Object, arm_good: bpy.types.Object, good_world
) -> tuple[bpy.types.Object, bpy.types.Object]:
    bpy.ops.object.select_all(action="DESELECT")
    mesh_good.select_set(True)
    arm_good.select_set(True)
    bpy.context.view_layer.objects.active = arm_good
    bpy.ops.object.duplicate(linked=False)

    new_objs = list(bpy.context.selected_objects)
    arm_bad = next(o for o in new_objs if o.type == "ARMATURE")
    mesh_bad = next(o for o in new_objs if o.type == "MESH")
    arm_bad.name = "rig_bad"
    mesh_bad.name = "mesh_bad"

    modifier = next(m for m in mesh_bad.modifiers if m.type == "ARMATURE")
    assert modifier.object == arm_bad, "duplicate() failed to remap the armature modifier"

    # Default bone envelope radii don't track the armature's bone-length scale
    # (berserkr FBX bones are 5-20+ units, the bestiary GLB quads are 0.05-0.3m),
    # so naive parent_set(ARMATURE_ENVELOPE) can leave every vertex unweighted.
    # Scale radii proportional to each bone's own length so the envelopes reach
    # the mesh; the degenerate-bone floor is scale-aware (median bone length),
    # not an absolute 0.5 which would swamp a small rig.
    lengths = sorted(b.length for b in arm_bad.data.bones)
    median_len = lengths[len(lengths) // 2]
    for bone in arm_bad.data.bones:
        length = max(bone.length, median_len * 0.25)
        bone.head_radius = length * 0.55
        bone.tail_radius = length * 0.35
        bone.envelope_distance = length * 0.4

    for vg in list(mesh_bad.vertex_groups):
        mesh_bad.vertex_groups.remove(vg)
    for mod in list(mesh_bad.modifiers):
        if mod.type == "ARMATURE":
            mesh_bad.modifiers.remove(mod)

    bpy.ops.object.select_all(action="DESELECT")
    mesh_bad.select_set(True)
    arm_bad.select_set(True)
    bpy.context.view_layer.objects.active = arm_bad
    bpy.ops.object.parent_set(type="ARMATURE_ENVELOPE")
    bpy.context.view_layer.update()

    # parent_set(), when the mesh was already parented to this armature,
    # recomputes matrix_parent_inverse from scratch and silently drops the
    # object's 0.01 import scale (matrix_world collapses to a pure rotation).
    # Force the world transform back to the known-good one.
    mesh_bad.matrix_world = good_world.copy()
    bpy.context.view_layer.update()

    return arm_bad, mesh_bad


def _mesh_height(mesh_obj: bpy.types.Object) -> float:
    mins = Vector((1e9, 1e9, 1e9))
    maxs = Vector((-1e9, -1e9, -1e9))
    for v in mesh_obj.data.vertices:
        wc = mesh_obj.matrix_world @ v.co
        for i in range(3):
            mins[i] = min(mins[i], wc[i])
            maxs[i] = max(maxs[i], wc[i])
    return maxs.z - mins.z


def _robust_seed_verts(
    mesh_obj: bpy.types.Object, vgroup_names: list[str], height: float, radius_frac: float
) -> list[int]:
    """Vertex indices near the joint, excluding far outliers (e.g. a held prop
    that happens to share the same bone weights)."""
    idxs = {
        vg.index for name in vgroup_names if (vg := mesh_obj.vertex_groups.get(name))
    }
    candidates = [
        v.index
        for v in mesh_obj.data.vertices
        if any(g.group in idxs and g.weight > 0.5 for g in v.groups)
    ]
    pts = [mesh_obj.matrix_world @ mesh_obj.data.vertices[i].co for i in candidates]
    n = len(pts)
    median = Vector(
        (sorted(p.x for p in pts)[n // 2], sorted(p.y for p in pts)[n // 2],
         sorted(p.z for p in pts)[n // 2])
    )
    radius = height * radius_frac
    filtered = [candidates[i] for i, p in enumerate(pts) if (p - median).length < radius]
    return filtered if filtered else candidates


def _centroid_at(mesh_obj: bpy.types.Object, seed_verts: list[int]) -> Vector:
    depsgraph = bpy.context.evaluated_depsgraph_get()
    eval_obj = mesh_obj.evaluated_get(depsgraph)
    eval_mesh = eval_obj.to_mesh()
    total = Vector((0.0, 0.0, 0.0))
    for i in seed_verts:
        total += mesh_obj.matrix_world @ eval_mesh.vertices[i].co
    eval_obj.to_mesh_clear()
    return total / len(seed_verts)


def _setup_lighting(scene: bpy.types.Scene) -> None:
    world = bpy.data.worlds.new("eval_world")
    world.use_nodes = True
    bg = world.node_tree.nodes.get("Background")
    if bg is not None:
        bg.inputs["Color"].default_value = BACKGROUND_COLOR
        bg.inputs["Strength"].default_value = 1.0
    scene.world = world

    key_data = bpy.data.lights.new("key_sun", type="SUN")
    key_data.energy = 3.2
    key_data.angle = math.radians(4)
    key = bpy.data.objects.new("key_sun", key_data)
    key.rotation_euler = (math.radians(55), 0, math.radians(35))
    scene.collection.objects.link(key)

    fill_data = bpy.data.lights.new("fill_sun", type="SUN")
    fill_data.energy = 1.1
    fill_data.angle = math.radians(8)
    fill = bpy.data.objects.new("fill_sun", fill_data)
    fill.rotation_euler = (math.radians(-40), 0, math.radians(-145))
    scene.collection.objects.link(fill)


def _create_camera(scene: bpy.types.Scene) -> bpy.types.Object:
    cam_data = bpy.data.cameras.new("eval_cam")
    cam_data.type = "ORTHO"
    cam = bpy.data.objects.new("eval_cam", cam_data)
    scene.collection.objects.link(cam)
    scene.camera = cam
    return cam


def _point_camera(cam: bpy.types.Object, focus: Vector, view_size: float) -> None:
    cam.data.ortho_scale = view_size
    az = math.radians(CAM_AZIMUTH_DEG)
    el = math.radians(CAM_ELEVATION_DEG)
    dist = view_size * CAM_DIST_FACTOR
    x = focus.x + dist * math.cos(el) * math.sin(az)
    y = focus.y - dist * math.cos(el) * math.cos(az)
    z = focus.z + dist * math.sin(el)
    cam.location = (x, y, z)
    cam.rotation_euler = (focus - cam.location).to_track_quat("-Z", "Y").to_euler()


def main() -> None:
    model_path, rig_kind, _seed, out_dir = _parse_args()
    poses = POSE_TABLES[rig_kind]
    out_path = Path(out_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    arm_good, mesh_good = _import_and_validate(model_path)
    arm_good.name = "rig_good"
    mesh_good.name = "mesh_good"
    good_world = mesh_good.matrix_world.copy()

    arm_bad, mesh_bad = _make_bad_twin(mesh_good, arm_good, good_world)

    height = _mesh_height(mesh_good)

    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = RESOLUTION
    scene.render.resolution_y = RESOLUTION
    scene.render.film_transparent = False
    _setup_lighting(scene)
    cam = _create_camera(scene)

    for pose_name, pdef in poses.items():
        bone = str(pdef["bone"])
        axis = int(pdef["axis"])
        angle_deg = float(pdef["angle_deg"])
        vgroups = list(pdef["vgroups"])  # type: ignore[arg-type]
        radius_frac = float(pdef["radius_frac"])
        view_frac = float(pdef["view_frac"])

        seed_verts = _robust_seed_verts(mesh_good, vgroups, height, radius_frac)

        _reset_pose(arm_good)
        bpy.context.view_layer.update()
        rest_focus = _centroid_at(mesh_good, seed_verts)
        _apply_bend(arm_good, bone, axis, angle_deg)
        bpy.context.view_layer.update()
        posed_focus = _centroid_at(mesh_good, seed_verts)
        focus = (rest_focus + posed_focus) / 2
        _point_camera(cam, focus, height * view_frac)

        for twin_name, rig in (("good", arm_good), ("bad", arm_bad)):
            _reset_pose(arm_good)
            _reset_pose(arm_bad)
            _apply_bend(rig, bone, axis, angle_deg)
            mesh_good.hide_render = twin_name != "good"
            arm_good.hide_render = True
            mesh_bad.hide_render = twin_name != "bad"
            arm_bad.hide_render = True
            bpy.context.view_layer.update()

            out_file = out_path / f"{twin_name}__{pose_name}.png"
            scene.render.filepath = str(out_file)
            bpy.ops.render.render(write_still=True)
            print("RENDERED", out_file)


if __name__ == "__main__":
    main()
