#!/usr/bin/env python3
"""reapply_texture.py — give the rigged barbarian clips a shippable material.

The barbarian was generated as a GEOMETRY-ONLY Hunyuan3D mesh: verified across
barbarian_clean.glb and the rigged meshes, it has no UVs, no materials, no textures,
and no vertex colors, and the UniRig output is likewise bare — so there is no source
texture to transfer. This script therefore:

  1. inspects --source for a usable material (image-texture material, or vertex colors)
     and transfers it if one is ever present (the path for a future textured re-gen);
  2. otherwise authors a solid leather-brown (#8B5E3C) Principled material that needs no
     UVs — a flat base color is the ONLY thing the mesh (no UVs) can carry through FBX
     into Unity — so the clips render as a solid character instead of flat grey;
  3. strips the stray Icosphere that rides along in the rig export;

and re-exports each clip to output/export/barbarian/textured/<clip>.fbx (textures embedded).

Usage:
    blender --background --python reapply_texture.py -- <out_dir> <source_or_NONE> <clip1.fbx> [clip2 ...]
"""
import bpy
import sys
import os

a = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
OUT_DIR, SOURCE = a[0], a[1]
CLIPS = a[2:]
os.makedirs(OUT_DIR, exist_ok=True)


def imp(path):
    (bpy.ops.import_scene.gltf if path.lower().endswith((".glb", ".gltf"))
     else bpy.ops.import_scene.fbx)(filepath=path)


def source_material(path):
    """Return a usable material from the source mesh (image-texture or vertex-color), or None."""
    if not path or path.upper() == "NONE" or not os.path.isfile(path):
        return None
    bpy.ops.object.select_all(action='SELECT'); bpy.ops.object.delete()
    imp(path)
    for o in bpy.data.objects:
        if o.type != 'MESH':
            continue
        me = o.data
        for m in me.materials:
            if m and m.use_nodes and any(n.type == 'TEX_IMAGE' and n.image
                                         for n in m.node_tree.nodes):
                return m.copy()
        if getattr(me, "color_attributes", None) and len(me.color_attributes):
            return _vertex_color_material(me.color_attributes[0].name)
    return None


def _vertex_color_material(attr_name):
    mat = bpy.data.materials.new("barbarian_vcol"); mat.use_nodes = True
    nt = mat.node_tree
    bsdf = nt.nodes.get("Principled BSDF")
    col = nt.nodes.new("ShaderNodeVertexColor"); col.layer_name = attr_name
    nt.links.new(col.outputs["Color"], bsdf.inputs["Base Color"])
    bsdf.inputs["Roughness"].default_value = 0.7
    return mat


def leather_material():
    """Solid warm-leather PBR. FBX can only carry a basic material (diffuse color +
    image maps) — NOT a procedural node graph — and the mesh has no UVs to bake an
    image onto, so a solid Principled base color is the only thing that survives the
    FBX round-trip into Unity. A game artist replaces this with a real texture set."""
    # #8B5E3C leather brown. Blender's Base Color is LINEAR, so convert from sRGB:
    #   8B,5E,3C = (0.545,0.369,0.235) sRGB -> (0.258,0.118,0.045) linear.
    LEATHER_LIN = (0.258, 0.118, 0.045, 1.0)
    mat = bpy.data.materials.new("barbarian_leather"); mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = LEATHER_LIN
    bsdf.inputs["Roughness"].default_value = 0.65
    if "Specular IOR Level" in bsdf.inputs:
        bsdf.inputs["Specular IOR Level"].default_value = 0.3
    mat.diffuse_color = LEATHER_LIN   # viewport/FBX basic-material fallback (#8B5E3C)
    return mat


def process(clip, out_path, make_mat):
    bpy.ops.object.select_all(action='SELECT'); bpy.ops.object.delete()
    imp(clip)
    meshes = [o for o in bpy.data.objects if o.type == 'MESH']
    arm = next((o for o in bpy.data.objects if o.type == 'ARMATURE'), None)
    if not meshes:
        print(f"SKIP {os.path.basename(clip)} no mesh"); return
    char = max(meshes, key=lambda o: len(o.data.vertices))
    # pin the scene frame range to THIS clip's action so bake_anim exports its full
    # length (not the leftover scene range from a prior clip).
    act = arm.animation_data.action if (arm and arm.animation_data) else None
    if act:
        sc = bpy.context.scene
        sc.frame_start = int(round(act.frame_range[0]))
        sc.frame_end = int(round(act.frame_range[1]))
        print(f"  range {os.path.basename(clip)} = {sc.frame_start}..{sc.frame_end}")
    # strip stray meshes (the Icosphere) and any empties from the rig export
    for o in list(bpy.data.objects):
        if o.type == 'MESH' and o is not char:
            print(f"  stripped stray mesh '{o.name}' ({len(o.data.vertices)} v)")
            bpy.data.objects.remove(o, do_unlink=True)
        elif o.type == 'EMPTY':
            bpy.data.objects.remove(o, do_unlink=True)
    mat = make_mat()
    char.data.materials.clear(); char.data.materials.append(mat)
    for o in bpy.data.objects:
        o.select_set(o.type in ('ARMATURE', 'MESH'))
    bpy.context.view_layer.objects.active = arm or char
    bpy.ops.export_scene.fbx(filepath=out_path, use_selection=True, bake_anim=True,
                             bake_anim_use_all_actions=False, bake_anim_use_nla_strips=False,
                             add_leaf_bones=False, object_types={'ARMATURE', 'MESH'},
                             path_mode='COPY', embed_textures=True)
    print(f"TEXTURED {os.path.basename(out_path)} mat='{mat.name}' verts={len(char.data.vertices)}")


def main():
    src_mat = source_material(SOURCE)
    if src_mat is not None:
        print(f"SOURCE_MATERIAL found: '{src_mat.name}' (transferring)")
        make = lambda: src_mat
    else:
        print("SOURCE_MATERIAL none usable (geometry-only mesh) -> authoring procedural leather")
        make = leather_material
    for clip in CLIPS:
        out_name = os.path.splitext(os.path.basename(clip))[0] + ".fbx"
        process(clip, os.path.join(OUT_DIR, out_name), make)
    print(f"REAPPLY_DONE clips={len(CLIPS)}")


main()
