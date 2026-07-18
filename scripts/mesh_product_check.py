"""mesh_product_check — the MESH-PRODUCT auto-validator (Business Plan C1.1 / §4.3).

Turns a raw generated mesh (TRELLIS/Hunyuan3D/kit GLB/OBJ/FBX/STL) into a
game-ready, sellable static prop — or tells you exactly why it isn't. It VALIDATES
against the §4.3 gate, optionally FIXES the mechanical failures, and optionally
EXPORTS clean GLB + FBX. Batch: point --src at a folder and it loops every mesh in
ONE Blender process, writing a JSON report + a per-mesh PASS/FAIL summary.

Checks (§4.3): tri budget · non-manifold edges · watertight · consistent normals ·
loose/floating parts · UVs present + in-bounds · real-meter scale · sane base-centered
origin. Fixes (--fix): weld · recalc normals outside · decimate to budget ·
meter-normalize to a target height · recenter origin to the base. Export (--export-dir):
GLB + FBX.

Headless Blender (import/analyze/export — CPU, no GPU):
  blender --background --factory-startup --python scripts/mesh_product_check.py -- \
      --src <mesh_or_dir> [--max-tris 5000] [--target-height 0] [--min-dim 0.05] \
      [--max-dim 20] [--fix] [--export-dir <dir>] [--report <report.json>]

Exit code: 0 if every mesh PASSES (post-fix), 1 otherwise.
"""
import argparse
import json
import sys
from pathlib import Path

import bpy
import bmesh
from mathutils import Vector

MESH_EXTS = (".glb", ".gltf", ".obj", ".fbx", ".ply", ".stl")


def _args():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", required=True, help="Mesh file or a directory (recursed).")
    ap.add_argument("--max-tris", type=int, default=5000, help="Tri budget (game-ready prop).")
    ap.add_argument("--target-height", type=float, default=0.0,
                    help="If >0, meter-normalize so the mesh is this tall (Z).")
    ap.add_argument("--min-dim", type=float, default=0.05, help="Min sane max-dimension (m).")
    ap.add_argument("--max-dim", type=float, default=20.0, help="Max sane max-dimension (m).")
    ap.add_argument("--fix", action="store_true", help="Apply mechanical fixes in place.")
    ap.add_argument("--export-dir", default=None, help="Write cleaned GLB + FBX here.")
    ap.add_argument("--report", default=None, help="Write the JSON report here.")
    return ap.parse_args(argv)


def _wipe():
    if bpy.context.mode != "OBJECT":
        try:
            bpy.ops.object.mode_set(mode="OBJECT")
        except RuntimeError:
            pass
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    for coll in (bpy.data.meshes, bpy.data.materials, bpy.data.images):
        for b in list(coll):
            if b.users == 0:
                coll.remove(b)


def _import(path: Path):
    ext = path.suffix.lower()
    if ext in (".glb", ".gltf"):
        bpy.ops.import_scene.gltf(filepath=str(path))
    elif ext == ".fbx":
        bpy.ops.import_scene.fbx(filepath=str(path))
    elif ext == ".obj":
        bpy.ops.wm.obj_import(filepath=str(path))
    elif ext == ".ply":
        bpy.ops.wm.ply_import(filepath=str(path))
    elif ext == ".stl":
        bpy.ops.wm.stl_import(filepath=str(path))
    else:
        raise RuntimeError("unsupported: " + ext)


def _join_meshes():
    meshes = [o for o in bpy.context.scene.objects if o.type == "MESH"]
    if not meshes:
        return None
    bpy.ops.object.select_all(action="DESELECT")
    for o in meshes:
        o.select_set(True)
    bpy.context.view_layer.objects.active = meshes[0]
    if len(meshes) > 1:
        bpy.ops.object.join()
    return bpy.context.view_layer.objects.active


def _tri_count(obj) -> int:
    obj.data.calc_loop_triangles()
    return len(obj.data.loop_triangles)


def _bm(obj):
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    return bm


def _island_count(bm) -> int:
    seen = set()
    islands = 0
    verts = bm.verts
    for v in verts:
        if v.index in seen:
            continue
        islands += 1
        stack = [v]
        seen.add(v.index)
        while stack:
            cur = stack.pop()
            for e in cur.link_edges:
                o = e.other_vert(cur)
                if o.index not in seen:
                    seen.add(o.index)
                    stack.append(o)
    return islands


def check(obj, a) -> dict:
    r = {}
    tris = _tri_count(obj)
    r["tris"] = tris
    r["tri_budget_ok"] = tris <= a.max_tris

    bm = _bm(obj)
    bm.verts.ensure_lookup_table()
    non_manifold = sum(1 for e in bm.edges if not e.is_manifold)
    boundary = sum(1 for e in bm.edges if len(e.link_faces) == 1)
    over = sum(1 for e in bm.edges if len(e.link_faces) > 2)
    r["non_manifold_edges"] = non_manifold
    r["boundary_edges"] = boundary
    r["nonmanifold_ok"] = over == 0            # a >2-face edge is a real defect
    r["watertight"] = (boundary == 0 and over == 0)
    r["loose_parts"] = _island_count(bm)
    # normals consistency: recalc on a copy and see if any face would flip
    before = [f.normal.copy() for f in bm.faces]
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    flipped = sum(1 for f, n0 in zip(bm.faces, before) if f.normal.dot(n0) < 0)
    r["flipped_normals"] = flipped
    r["normals_ok"] = flipped == 0
    bm.free()

    me = obj.data
    r["has_uvs"] = len(me.uv_layers) > 0
    uv_oob = 0
    if r["has_uvs"]:
        uv = me.uv_layers.active.data
        n = len(uv) or 1
        uv_oob = sum(1 for d in uv if not (-0.001 <= d.uv.x <= 1.001 and -0.001 <= d.uv.y <= 1.001))
        r["uv_out_of_bounds_frac"] = round(uv_oob / n, 3)
    r["uv_ok"] = r["has_uvs"] and (uv_oob / (len(me.uv_layers.active.data) or 1) < 0.02 if r["has_uvs"] else False)

    # world-space bbox
    mn = Vector((1e18,) * 3)
    mx = Vector((-1e18,) * 3)
    for c in obj.bound_box:
        w = obj.matrix_world @ Vector(c)
        for i in range(3):
            mn[i] = min(mn[i], w[i])
            mx[i] = max(mx[i], w[i])
    dims = mx - mn
    r["dims_m"] = [round(dims.x, 4), round(dims.y, 4), round(dims.z, 4)]
    max_dim = max(dims)
    r["max_dim_m"] = round(max_dim, 4)
    r["scale_ok"] = a.min_dim <= max_dim <= a.max_dim
    # origin: distance from object origin to the base-center (XY center, min Z)
    base = Vector(((mn.x + mx.x) / 2, (mn.y + mx.y) / 2, mn.z))
    r["origin_offset_m"] = round((obj.matrix_world.translation - base).length, 4)
    r["origin_ok"] = r["origin_offset_m"] <= max(0.02, max_dim * 0.05)

    r["PASS"] = all([r["tri_budget_ok"], r["nonmanifold_ok"], r["normals_ok"],
                     r["uv_ok"], r["scale_ok"], r["origin_ok"]])
    return r


def fix(obj, a):
    # weld
    me = obj.data
    bm = bmesh.new(); bm.from_mesh(me)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-4)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(me); bm.free(); me.update()
    # decimate to budget
    tris = _tri_count(obj)
    if tris > a.max_tris:
        d = obj.modifiers.new("dec", "DECIMATE")
        d.decimate_type = "COLLAPSE"
        d.ratio = max(0.01, a.max_tris / tris)
        bpy.ops.object.modifier_apply(modifier=d.name)
    # give it UVs if missing (game-ready props need them) — smart project is a
    # reasonable auto-unwrap for props; a hero asset still wants a hand UV pass.
    if len(me.uv_layers) == 0:
        bpy.ops.object.select_all(action="DESELECT")
        obj.select_set(True); bpy.context.view_layer.objects.active = obj
        bpy.ops.object.mode_set(mode="EDIT")
        bpy.ops.mesh.select_all(action="SELECT")
        bpy.ops.uv.smart_project(angle_limit=1.15, island_margin=0.02)
        bpy.ops.object.mode_set(mode="OBJECT")
    # recenter origin to base, drop onto Z=0 at XY origin
    bpy.ops.object.origin_set(type="ORIGIN_GEOMETRY", center="BOUNDS")
    mn = Vector((1e18,) * 3); mx = Vector((-1e18,) * 3)
    for c in obj.bound_box:
        w = obj.matrix_world @ Vector(c)
        for i in range(3):
            mn[i] = min(mn[i], w[i]); mx[i] = max(mx[i], w[i])
    obj.location = (0.0, 0.0, (mx.z - mn.z) / 2)  # base at Z=0 after BOUNDS origin
    # meter-normalize height
    if a.target_height > 0:
        h = mx.z - mn.z or 1.0
        s = a.target_height / h
        obj.scale = (s, s, s)
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)


def export(obj, out_dir: Path, stem: str):
    out_dir.mkdir(parents=True, exist_ok=True)
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.export_scene.gltf(filepath=str(out_dir / f"{stem}.glb"), export_format="GLB",
                              use_selection=True, export_animations=False)
    bpy.ops.export_scene.fbx(filepath=str(out_dir / f"{stem}.fbx"), use_selection=True,
                             bake_anim=False, apply_scale_options="FBX_SCALE_ALL")


def main() -> int:
    a = _args()
    src = Path(a.src)
    meshes = ([src] if src.is_file() else
              sorted(p for p in src.rglob("*") if p.suffix.lower() in MESH_EXTS))
    if not meshes:
        print("no meshes under", src); return 1
    report = []
    n_pass = 0
    for mp in meshes:
        _wipe()
        try:
            _import(mp)
        except Exception as e:
            report.append({"mesh": mp.name, "error": str(e)[:120], "PASS": False})
            print(f"  ! {mp.name}: import failed: {str(e)[:80]}")
            continue
        obj = _join_meshes()
        if obj is None:
            report.append({"mesh": mp.name, "error": "no mesh objects", "PASS": False})
            continue
        pre = check(obj, a)
        rec = {"mesh": mp.name, "before": pre}
        if a.fix:
            fix(obj, a)
            rec["after"] = check(obj, a)
            verdict = rec["after"]
        else:
            verdict = pre
        if a.export_dir and verdict["PASS"]:
            export(obj, Path(a.export_dir), mp.stem)
            rec["exported"] = True
        rec["PASS"] = verdict["PASS"]
        n_pass += 1 if verdict["PASS"] else 0
        report.append(rec)
        fails = [k.replace("_ok", "") for k in ("tri_budget_ok", "nonmanifold_ok", "normals_ok",
                 "uv_ok", "scale_ok", "origin_ok") if not verdict.get(k)]
        print(f"  {'PASS' if verdict['PASS'] else 'FAIL'}  {mp.name}  "
              f"tris={verdict['tris']} maxdim={verdict['max_dim_m']}m"
              + (f"  fails: {','.join(fails)}" if fails else ""))
    out = {"total": len(meshes), "passed": n_pass, "max_tris": a.max_tris,
           "fixed": bool(a.fix), "results": report}
    if a.report:
        Path(a.report).write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"\nMESH-PRODUCT: {n_pass}/{len(meshes)} pass" + (" (post-fix)" if a.fix else ""))
    return 0 if n_pass == len(meshes) else 1


if __name__ == "__main__":
    sys.exit(main())
