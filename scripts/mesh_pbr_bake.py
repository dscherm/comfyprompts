"""mesh_pbr_bake — bake a PBR texture set onto a UV'd mesh (Business Plan C1.2 / §4.3).

Takes a cleaned, UV-unwrapped mesh (the output of mesh_product_check.py --fix) and
bakes a game-ready PBR set — **albedo, ambient-occlusion, normal, roughness** — onto
its UV layout, wires a single Principled material (albedo + roughness + normal; AO
saved as a separate map for the buyer's occlusion slot), and re-exports GLB + FBX
with the textures embedded. Batches a folder in one Blender process.

Handles the three colour sources these meshes use: an image-texture material (atlas),
a **vertex/colour attribute** (kit meshes — wired to base-colour before the albedo
bake so the colours are captured), or a flat material colour.

Cycles bake (GPU generation is fine; falls back to CPU). Headless Blender:
  blender --background --factory-startup --python scripts/mesh_pbr_bake.py -- \
      --src <uvd_mesh_or_dir> --out <dir> [--res 1024] [--ao-samples 64] [--cpu]
"""
import argparse
import sys
from pathlib import Path

import bpy

MESH_EXTS = (".glb", ".gltf", ".obj", ".fbx", ".ply", ".stl")


def _args():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", required=True)
    ap.add_argument("--out", required=True, help="Output dir for GLB/FBX + <stem>_textures/.")
    ap.add_argument("--res", type=int, default=1024)
    ap.add_argument("--ao-samples", type=int, default=64)
    ap.add_argument("--cpu", action="store_true", help="Force CPU bake (default: GPU if available).")
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
    {".glb": bpy.ops.import_scene.gltf, ".gltf": bpy.ops.import_scene.gltf,
     ".fbx": bpy.ops.import_scene.fbx, ".obj": bpy.ops.wm.obj_import,
     ".ply": bpy.ops.wm.ply_import, ".stl": bpy.ops.wm.stl_import}[ext](filepath=str(path))


def _join():
    ms = [o for o in bpy.context.scene.objects if o.type == "MESH"]
    if not ms:
        return None
    bpy.ops.object.select_all(action="DESELECT")
    for o in ms:
        o.select_set(True)
    bpy.context.view_layer.objects.active = ms[0]
    if len(ms) > 1:
        bpy.ops.object.join()
    return bpy.context.view_layer.objects.active


def _set_cycles(cpu: bool, samples: int):
    sc = bpy.context.scene
    sc.render.engine = "CYCLES"
    sc.cycles.samples = samples
    if cpu:
        sc.cycles.device = "CPU"
        return
    try:
        prefs = bpy.context.preferences.addons["cycles"].preferences
        prefs.compute_device_type = "CUDA"
        prefs.get_devices()
        for d in prefs.devices:
            d.use = (d.type == "CUDA")
        sc.cycles.device = "GPU"
    except Exception:
        sc.cycles.device = "CPU"


def _ensure_material(obj):
    """A geometry-only mesh (raw TRELLIS) has no material — nothing to bake to.
    Give it a node-based Principled (mid-grey) so albedo/roughness/normal have a
    source; convert any non-node material to nodes too."""
    slots = [s for s in obj.material_slots if s.material]
    if not slots:
        mat = bpy.data.materials.new(obj.name + "_src")
        mat.use_nodes = True
        mat.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.6, 0.6, 0.6, 1)
        obj.data.materials.append(mat)
        return
    for s in slots:
        if not s.material.use_nodes:
            s.material.use_nodes = True


def _ensure_vertexcolor_source(obj):
    """If a material has no base-colour texture but the mesh has a colour attribute,
    wire that attribute into Principled base colour so the albedo bake captures it."""
    me = obj.data
    attrs = list(me.color_attributes) if hasattr(me, "color_attributes") else []
    if not attrs:
        return
    cname = attrs[0].name
    for slot in obj.material_slots:
        mat = slot.material
        if not mat or not mat.use_nodes:
            continue
        bsdf = next((n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED"), None)
        if not bsdf:
            continue
        base = bsdf.inputs["Base Color"]
        if base.is_linked:
            continue  # already textured
        ca = mat.node_tree.nodes.new("ShaderNodeVertexColor")
        ca.layer_name = cname
        mat.node_tree.links.new(ca.outputs["Color"], base)


def _new_image(name, res, is_data=False):
    img = bpy.data.images.new(name, res, res, alpha=False, float_buffer=False, is_data=is_data)
    return img


def _bake_to(obj, img, bake_type, out_png, **kw):
    # add an image node to every material, make it active + selected (bake target)
    nodes_added = []
    for slot in obj.material_slots:
        mat = slot.material
        if not mat or not mat.use_nodes:
            continue
        nt = mat.node_tree
        for nn in nt.nodes:          # deselect ALL first, then add + select the target
            nn.select = False
        n = nt.nodes.new("ShaderNodeTexImage")
        n.image = img
        n.select = True
        nt.nodes.active = n
        nodes_added.append((mat, n))
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.bake(type=bake_type, **kw)
    img.filepath_raw = str(out_png)
    img.file_format = "PNG"
    img.save()
    for mat, n in nodes_added:  # clean the temp bake nodes
        mat.node_tree.nodes.remove(n)


def bake_set(obj, out_dir: Path, stem: str, res: int, ao_samples: int, cpu: bool):
    tex = out_dir / f"{stem}_textures"
    tex.mkdir(parents=True, exist_ok=True)
    _ensure_material(obj)
    _ensure_vertexcolor_source(obj)

    _set_cycles(cpu, 1)
    albedo = _new_image(f"{stem}_albedo", res)
    _bake_to(obj, albedo, "DIFFUSE", tex / f"{stem}_albedo.png",
             pass_filter={"COLOR"})
    rough = _new_image(f"{stem}_roughness", res, is_data=True)
    _bake_to(obj, rough, "ROUGHNESS", tex / f"{stem}_roughness.png")
    normal = _new_image(f"{stem}_normal", res, is_data=True)
    _bake_to(obj, normal, "NORMAL", tex / f"{stem}_normal.png")
    _set_cycles(cpu, ao_samples)
    ao = _new_image(f"{stem}_ao", res, is_data=True)
    _bake_to(obj, ao, "AO", tex / f"{stem}_ao.png")

    # rebuild ONE clean Principled material wiring albedo + roughness + normal
    for m in list(obj.data.materials):
        pass
    obj.data.materials.clear()
    mat = bpy.data.materials.new(f"{stem}_pbr")
    mat.use_nodes = True
    nt = mat.node_tree
    bsdf = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    ai = nt.nodes.new("ShaderNodeTexImage"); ai.image = albedo
    nt.links.new(ai.outputs["Color"], bsdf.inputs["Base Color"])
    ri = nt.nodes.new("ShaderNodeTexImage"); ri.image = rough; ri.image.colorspace_settings.name = "Non-Color"
    nt.links.new(ri.outputs["Color"], bsdf.inputs["Roughness"])
    ni = nt.nodes.new("ShaderNodeTexImage"); ni.image = normal; ni.image.colorspace_settings.name = "Non-Color"
    nmap = nt.nodes.new("ShaderNodeNormalMap")
    nt.links.new(ni.outputs["Color"], nmap.inputs["Color"])
    nt.links.new(nmap.outputs["Normal"], bsdf.inputs["Normal"])
    obj.data.materials.append(mat)
    return tex


def export(obj, out_dir: Path, stem: str):
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True); bpy.context.view_layer.objects.active = obj
    bpy.ops.export_scene.gltf(filepath=str(out_dir / f"{stem}.glb"), export_format="GLB",
                              use_selection=True, export_animations=False)
    bpy.ops.export_scene.fbx(filepath=str(out_dir / f"{stem}.fbx"), use_selection=True,
                             bake_anim=False, path_mode="COPY", embed_textures=True)


def main() -> int:
    a = _args()
    src = Path(a.src)
    meshes = ([src] if src.is_file() else
              sorted(p for p in src.rglob("*") if p.suffix.lower() in MESH_EXTS))
    out = Path(a.out)
    ok = 0
    for mp in meshes:
        _wipe()
        try:
            _import(mp)
            obj = _join()
            if obj is None or len(obj.data.uv_layers) == 0:
                print(f"  ! {mp.name}: skipped (no mesh / no UVs — run mesh_product_check --fix first)")
                continue
            tex = bake_set(obj, out, mp.stem, a.res, a.ao_samples, a.cpu)
            export(obj, out, mp.stem)
            ok += 1
            print(f"  + {mp.name}: baked PBR ({a.res}px) -> {tex.name}/ + {mp.stem}.glb/.fbx")
        except Exception as e:
            print(f"  ! {mp.name}: bake failed: {str(e)[:120]}")
    print(f"\nPBR-BAKE: {ok}/{len(meshes)} baked -> {out}")
    return 0 if ok == len(meshes) else 1


if __name__ == "__main__":
    sys.exit(main())
