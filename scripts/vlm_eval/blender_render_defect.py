"""Headless Blender: import a GLB read-only, optionally inject a defect, render one
labeled 3/4 view PNG for the VLM eval set.

Never writes back to the source GLB — it is imported into a fresh, empty scene and
only the in-memory copy is mutated.

Usage:
    blender --background --python blender_render_defect.py -- \\
        <glb_path> <defect_type> <seed> <out_png>

defect_type is one of: none, flipped_normals, unwelded_cracks, missing_texture,
uv_smear, scale_error, wrong_orientation.
"""

from __future__ import annotations

import math
import random
import sys

import bmesh
import bpy
from mathutils import Matrix, Vector

DEFECT_TYPES = frozenset(
    {
        "none",
        "flipped_normals",
        "unwelded_cracks",
        "missing_texture",
        "uv_smear",
        "scale_error",
        "wrong_orientation",
    }
)

REF_CUBE_COLOR = (1.0, 0.25, 0.05, 1.0)
BACKGROUND_COLOR = (0.82, 0.83, 0.86, 1.0)
MISSING_TEX_COLOR = (0.02, 0.02, 0.02, 1.0)


def _parse_args() -> tuple[str, str, int, str]:
    argv = sys.argv[sys.argv.index("--") + 1 :]
    glb_path, defect_type, seed_str, out_png = argv[0], argv[1], argv[2], argv[3]
    if defect_type not in DEFECT_TYPES:
        raise ValueError(f"unknown defect_type: {defect_type}")
    return glb_path, defect_type, int(seed_str), out_png


def _mesh_objects() -> list[bpy.types.Object]:
    return sorted(
        (o for o in bpy.data.objects if o.type == "MESH"), key=lambda o: o.name
    )


def _compute_bbox(objs: list[bpy.types.Object]) -> tuple[Vector, Vector, Vector, float]:
    mins = Vector((1e9, 1e9, 1e9))
    maxs = Vector((-1e9, -1e9, -1e9))
    for obj in objs:
        for corner in obj.bound_box:
            world_corner = obj.matrix_world @ Vector(corner)
            for i in range(3):
                mins[i] = min(mins[i], world_corner[i])
                maxs[i] = max(maxs[i], world_corner[i])
    center = (mins + maxs) / 2
    size = max(maxs[i] - mins[i] for i in range(3))
    return mins, maxs, center, max(size, 1e-6)


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


def _setup_camera(scene: bpy.types.Scene, center: Vector, size: float) -> None:
    cam_data = bpy.data.cameras.new("eval_cam")
    cam = bpy.data.objects.new("eval_cam", cam_data)
    scene.collection.objects.link(cam)
    scene.camera = cam
    cam_data.type = "ORTHO"
    cam_data.ortho_scale = size * 1.7

    az = math.radians(35)
    el = math.radians(22)
    dist = size * 3.0
    x = center.x + dist * math.cos(el) * math.sin(az)
    y = center.y - dist * math.cos(el) * math.cos(az)
    z = center.z + dist * math.sin(el)
    cam.location = (x, y, z)
    direction = center - cam.location
    cam.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()


def _add_reference_cube(mins: Vector, size: float) -> None:
    ref_size = size * 0.12
    location = (mins.x - ref_size * 1.2, mins.y, mins.z + ref_size / 2)
    bpy.ops.mesh.primitive_cube_add(size=ref_size, location=location)
    ref_obj = bpy.context.active_object
    ref_obj.name = "ref_cube"
    mat = bpy.data.materials.new("ref_cube_mat")
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    if bsdf is not None:
        bsdf.inputs["Base Color"].default_value = REF_CUBE_COLOR
    ref_obj.data.materials.append(mat)


def _defect_flipped_normals(objs: list[bpy.types.Object], seed: int) -> None:
    for idx, obj in enumerate(objs):
        rng = random.Random(seed + idx)
        mesh = obj.data
        bm = bmesh.new()
        bm.from_mesh(mesh)
        bm.faces.ensure_lookup_table()
        n_faces = len(bm.faces)
        if n_faces == 0:
            bm.free()
            continue
        k = max(1, int(n_faces * 0.45))
        picked = rng.sample(range(n_faces), min(k, n_faces))
        faces = [bm.faces[i] for i in picked]
        bmesh.ops.reverse_faces(bm, faces=faces)
        bm.normal_update()
        bm.to_mesh(mesh)
        bm.free()
        mesh.update()


def _defect_unwelded_cracks(objs: list[bpy.types.Object], seed: int, size: float) -> None:
    offset_amt = size * 0.05
    for idx, obj in enumerate(objs):
        rng = random.Random(seed + idx)
        mesh = obj.data
        bm = bmesh.new()
        bm.from_mesh(mesh)
        bm.faces.ensure_lookup_table()
        n_faces = len(bm.faces)
        if n_faces == 0:
            bm.free()
            continue
        k = max(1, int(n_faces * 0.25))
        picked = rng.sample(range(n_faces), min(k, n_faces))
        faces_to_split = [bm.faces[i] for i in picked]
        ret = bmesh.ops.split(bm, geom=faces_to_split)
        # bmesh.ops.split() invalidates the input face refs and returns the
        # detached geometry (including the new duplicated faces) in ret['geom'].
        split_faces = [g for g in ret["geom"] if isinstance(g, bmesh.types.BMFace)]
        bm.normal_update()
        moved: set[bmesh.types.BMVert] = set()
        for f in split_faces:
            if not f.is_valid:
                continue
            normal = f.normal.copy()
            for v in f.verts:
                if v not in moved:
                    v.co += normal * offset_amt
                    moved.add(v)
        bm.to_mesh(mesh)
        bm.free()
        mesh.update()


def _defect_missing_texture(objs: list[bpy.types.Object]) -> None:
    mat = bpy.data.materials.new("missing_texture_mat")
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    if bsdf is not None:
        bsdf.inputs["Base Color"].default_value = MISSING_TEX_COLOR
        if "Roughness" in bsdf.inputs:
            bsdf.inputs["Roughness"].default_value = 1.0
    for obj in objs:
        mesh = obj.data
        mesh.materials.clear()
        mesh.materials.append(mat)
        for vc_name in list(mesh.color_attributes.keys()):
            mesh.color_attributes.remove(mesh.color_attributes[vc_name])


def _defect_uv_smear(objs: list[bpy.types.Object], seed: int) -> None:
    for idx, obj in enumerate(objs):
        mesh = obj.data
        uv_layer = mesh.uv_layers.active
        if uv_layer is None:
            continue
        rng = random.Random(seed + idx)
        coords = [tuple(loop_uv.uv) for loop_uv in uv_layer.data]
        shuffled = coords[:]
        rng.shuffle(shuffled)
        for loop_uv, uv in zip(uv_layer.data, shuffled):
            loop_uv.uv = uv
        mesh.update()


def _defect_scale_error(objs: list[bpy.types.Object], seed: int, center: Vector) -> None:
    rng = random.Random(seed)
    factor = rng.choice([0.15, 2.4])
    scale_mat = (
        Matrix.Translation(center)
        @ Matrix.Diagonal((factor, factor, factor, 1.0))
        @ Matrix.Translation(-center)
    )
    for obj in objs:
        obj.matrix_world = scale_mat @ obj.matrix_world


def _defect_wrong_orientation(objs: list[bpy.types.Object], seed: int, center: Vector) -> None:
    rng = random.Random(seed)
    axis = rng.choice(["X", "Y"])
    direction = rng.choice([1, -1])
    angle = math.radians(90 * direction)
    rot_mat = (
        Matrix.Translation(center)
        @ Matrix.Rotation(angle, 4, axis)
        @ Matrix.Translation(-center)
    )
    for obj in objs:
        obj.matrix_world = rot_mat @ obj.matrix_world


def _apply_defect(
    defect_type: str,
    objs: list[bpy.types.Object],
    seed: int,
    size: float,
    center: Vector,
) -> None:
    if defect_type == "none":
        return
    if defect_type == "flipped_normals":
        _defect_flipped_normals(objs, seed)
    elif defect_type == "unwelded_cracks":
        _defect_unwelded_cracks(objs, seed, size)
    elif defect_type == "missing_texture":
        _defect_missing_texture(objs)
    elif defect_type == "uv_smear":
        _defect_uv_smear(objs, seed)
    elif defect_type == "scale_error":
        _defect_scale_error(objs, seed, center)
    elif defect_type == "wrong_orientation":
        _defect_wrong_orientation(objs, seed, center)


def _enable_backface_culling(objs: list[bpy.types.Object]) -> None:
    for obj in objs:
        for mat in obj.data.materials:
            if mat is not None:
                mat.use_backface_culling = True


def main() -> None:
    glb_path, defect_type, seed, out_png = _parse_args()

    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=glb_path)

    orig_objs = _mesh_objects()
    mins, maxs, center, size = _compute_bbox(orig_objs)

    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = 768
    scene.render.resolution_y = 768
    scene.render.film_transparent = False

    _setup_lighting(scene)
    _setup_camera(scene, center, size)

    _apply_defect(defect_type, orig_objs, seed, size, center)

    _add_reference_cube(mins, size)

    _enable_backface_culling(orig_objs)

    scene.render.filepath = out_png
    bpy.ops.render.render(write_still=True)
    print("RENDERED", out_png)


if __name__ == "__main__":
    main()
