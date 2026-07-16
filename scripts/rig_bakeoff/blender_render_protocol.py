"""Headless Blender: render the rig-bakeoff diagnostic set for one lane output.

Implements docs/rig_bakeoff_protocol.md: still poses S1-S4 from a per-lane bone
map, each captured from camera C1 (full body, 3/4 front-left, elevation 12) and
C2 (joint detail, adjacent regions in frame — the VL9 wide-framing rule), plus
animation clips A1/A2 sampled as frame strips when the file carries actions.

The bone map JSON decouples the protocol from skeleton naming (CC_Base vs
UniRig bone_N vs Meshy/Tripo skeletons):

{
  "poses": {
    "S1": {"label": "deep knee bend", "bones": [{"bone": "bone_8", "axis": 0, "angle_deg": 75}],
            "focus_vgroups": ["bone_8"]},
    ...
  },
  "clips": {"A1": "idle", "A2": "walk"}          # action name substrings, optional
}

Usage:
    blender --background --factory-startup --python blender_render_protocol.py \\
        -- <rigged_file> <bone_map.json> <out_dir>

Deterministic: fixed camera math, fixed lighting, fixed sample frames.
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector

RESOLUTION = 1024
BACKGROUND_COLOR = (0.82, 0.83, 0.86, 1.0)
FULL_AZIMUTH_DEG = 35.0
FULL_ELEVATION_DEG = 12.0
DETAIL_AZIMUTH_DEG = 40.0
DETAIL_ELEVATION_DEG = 14.0
CLIP_SAMPLE_FRAMES = 6


def _parse_args() -> tuple[str, dict, Path]:
    argv = sys.argv[sys.argv.index("--") + 1 :]
    rigged_file, bone_map_path, out_dir = argv[0], argv[1], argv[2]
    with open(bone_map_path, encoding="utf-8") as f:
        bone_map = json.load(f)
    return rigged_file, bone_map, Path(out_dir)


def _import_scene(path: str) -> tuple[bpy.types.Object, list[bpy.types.Object]]:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    suffix = Path(path).suffix.lower()
    if suffix == ".fbx":
        bpy.ops.import_scene.fbx(filepath=path)
    elif suffix in (".glb", ".gltf"):
        bpy.ops.import_scene.gltf(filepath=path)
    else:
        print(f"ERROR: unsupported format {suffix}", file=sys.stderr)
        sys.exit(1)
    arms = [o for o in bpy.data.objects if o.type == "ARMATURE"]
    if not arms:
        print(f"ERROR: no armature in {path} — not a rigged file", file=sys.stderr)
        sys.exit(1)
    meshes = [
        o for o in bpy.data.objects
        if o.type == "MESH"
        and any(m.type == "ARMATURE" and m.object == arms[0] for m in o.modifiers)
    ]
    if not meshes:
        print(f"ERROR: no mesh skinned to {arms[0].name}", file=sys.stderr)
        sys.exit(1)
    for o in bpy.data.objects:
        if o.type == "MESH" and o not in meshes:
            o.hide_render = True
        if o.type == "ARMATURE":
            o.hide_render = True
    return arms[0], meshes


def _reset_pose(rig: bpy.types.Object) -> None:
    for pb in rig.pose.bones:
        pb.rotation_mode = "XYZ"
        pb.rotation_euler = (0.0, 0.0, 0.0)
        pb.rotation_quaternion = (1.0, 0.0, 0.0, 0.0)
        pb.location = (0.0, 0.0, 0.0)
        pb.scale = (1.0, 1.0, 1.0)


def _world_bounds(meshes: list[bpy.types.Object]) -> tuple[Vector, Vector]:
    depsgraph = bpy.context.evaluated_depsgraph_get()
    mins = Vector((1e18,) * 3)
    maxs = Vector((-1e18,) * 3)
    for mesh in meshes:
        eval_obj = mesh.evaluated_get(depsgraph)
        em = eval_obj.to_mesh()
        for v in em.vertices:
            w = mesh.matrix_world @ v.co
            for i in range(3):
                mins[i] = min(mins[i], w[i])
                maxs[i] = max(maxs[i], w[i])
        eval_obj.to_mesh_clear()
    return mins, maxs


def _vgroup_centroid(meshes: list[bpy.types.Object], names: list[str]) -> Vector | None:
    depsgraph = bpy.context.evaluated_depsgraph_get()
    total = Vector((0.0, 0.0, 0.0))
    count = 0
    for mesh in meshes:
        idxs = {vg.index for n in names if (vg := mesh.vertex_groups.get(n))}
        if not idxs:
            continue
        eval_obj = mesh.evaluated_get(depsgraph)
        em = eval_obj.to_mesh()
        for v_orig, v_eval in zip(mesh.data.vertices, em.vertices):
            if any(g.group in idxs and g.weight > 0.4 for g in v_orig.groups):
                total += mesh.matrix_world @ v_eval.co
                count += 1
        eval_obj.to_mesh_clear()
    return (total / count) if count else None


def _setup_render(scene: bpy.types.Scene) -> bpy.types.Object:
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = RESOLUTION
    scene.render.resolution_y = RESOLUTION
    scene.render.film_transparent = False

    world = bpy.data.worlds.new("bakeoff_world")
    world.use_nodes = True
    bg = world.node_tree.nodes.get("Background")
    if bg is not None:
        bg.inputs["Color"].default_value = BACKGROUND_COLOR
        bg.inputs["Strength"].default_value = 1.0
    scene.world = world

    key = bpy.data.lights.new("key", type="SUN")
    key.energy = 3.0
    key.angle = math.radians(5)
    key_obj = bpy.data.objects.new("key", key)
    key_obj.rotation_euler = (math.radians(55), 0, math.radians(30))
    scene.collection.objects.link(key_obj)

    fill = bpy.data.lights.new("fill", type="SUN")
    fill.energy = 1.0
    fill.angle = math.radians(9)
    fill_obj = bpy.data.objects.new("fill", fill)
    fill_obj.rotation_euler = (math.radians(-40), 0, math.radians(-140))
    scene.collection.objects.link(fill_obj)

    cam_data = bpy.data.cameras.new("cam")
    cam_data.type = "ORTHO"
    cam = bpy.data.objects.new("cam", cam_data)
    scene.collection.objects.link(cam)
    scene.camera = cam
    return cam


def _aim(cam: bpy.types.Object, focus: Vector, view: float, az_deg: float, el_deg: float) -> None:
    cam.data.ortho_scale = view
    az, el = math.radians(az_deg), math.radians(el_deg)
    dist = view * 3.0
    cam.location = (
        focus.x + dist * math.cos(el) * math.sin(az),
        focus.y - dist * math.cos(el) * math.cos(az),
        focus.z + dist * math.sin(el),
    )
    cam.rotation_euler = (focus - cam.location).to_track_quat("-Z", "Y").to_euler()


def _render(scene: bpy.types.Scene, out_file: Path) -> None:
    scene.render.filepath = str(out_file)
    bpy.ops.render.render(write_still=True)
    print("RENDERED", out_file)


def _apply_pose(rig: bpy.types.Object, bones: list[dict]) -> None:
    for spec in bones:
        pb = rig.pose.bones.get(spec["bone"])
        if pb is None:
            print(f"ERROR: bone '{spec['bone']}' not in armature "
                  f"(have: {[b.name for b in rig.pose.bones][:12]}...)", file=sys.stderr)
            sys.exit(1)
        pb.rotation_mode = "XYZ"
        euler = [0.0, 0.0, 0.0]
        euler[int(spec.get("axis", 0))] = math.radians(float(spec["angle_deg"]))
        pb.rotation_euler = euler


def _render_stills(rig, meshes, poses: dict, cam, scene, out_dir: Path) -> None:
    rig.animation_data_clear()
    _reset_pose(rig)
    bpy.context.view_layer.update()
    mins, maxs = _world_bounds(meshes)
    size = max(maxs - mins)
    body_focus = (mins + maxs) / 2

    for pose_id, pdef in poses.items():
        _reset_pose(rig)
        _apply_pose(rig, pdef["bones"])
        bpy.context.view_layer.update()

        _aim(cam, body_focus, size * 1.25, FULL_AZIMUTH_DEG, FULL_ELEVATION_DEG)
        _render(scene, out_dir / f"{pose_id}_C1_full.png")

        focus = _vgroup_centroid(meshes, pdef.get("focus_vgroups", []))
        if focus is None:
            focus = body_focus
        _aim(cam, focus, size * 0.55, DETAIL_AZIMUTH_DEG, DETAIL_ELEVATION_DEG)
        _render(scene, out_dir / f"{pose_id}_C2_detail.png")


def _find_action(substring: str) -> bpy.types.Action | None:
    matches = [a for a in bpy.data.actions if substring.lower() in a.name.lower()]
    return matches[0] if matches else None


def _render_clips(rig, meshes, clips: dict, cam, scene, out_dir: Path) -> None:
    for clip_id, substring in clips.items():
        action = _find_action(substring)
        if action is None:
            print(f"CLIP_MISSING {clip_id} (no action matching '{substring}'); "
                  f"available: {[a.name for a in bpy.data.actions]}")
            continue
        if rig.animation_data is None:
            rig.animation_data_create()
        rig.animation_data.action = action
        start, end = (int(action.frame_range[0]), int(action.frame_range[1]))
        bpy.context.view_layer.update()
        mins, maxs = _world_bounds(meshes)
        size = max(maxs - mins)
        focus = (mins + maxs) / 2
        _aim(cam, focus, size * 1.35, FULL_AZIMUTH_DEG, FULL_ELEVATION_DEG)
        span = max(end - start, 1)
        for k in range(CLIP_SAMPLE_FRAMES):
            frame = start + round(k * span / (CLIP_SAMPLE_FRAMES - 1))
            scene.frame_set(frame)
            _render(scene, out_dir / f"{clip_id}_{action.name}_f{k}.png")
        rig.animation_data.action = None


def main() -> None:
    rigged_file, bone_map, out_dir = _parse_args()
    out_dir.mkdir(parents=True, exist_ok=True)
    rig, meshes = _import_scene(rigged_file)
    scene = bpy.context.scene
    cam = _setup_render(scene)

    clips = bone_map.get("clips", {})
    if clips:
        _render_clips(rig, meshes, clips, cam, scene, out_dir)
    _render_stills(rig, meshes, bone_map.get("poses", {}), cam, scene, out_dir)
    print("DONE")


if __name__ == "__main__":
    main()
