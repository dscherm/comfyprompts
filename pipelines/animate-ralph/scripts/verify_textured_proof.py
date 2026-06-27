#!/usr/bin/env python3
"""verify_textured_proof.py — prove the leather material survives the FBX round-trip.

Imports a textured clip FBX (output of reapply_texture.py), reads the material BACK
off the reimported mesh to confirm the #8B5E3C leather color survived export/reimport
(not reset to grey/default), then renders a posed beauty frame using the clip's OWN
embedded material — NOT the grey matte that render_rootmotion.py forces — so the PNG
actually shows the colored character.

Bakes in the deform fix from render_rootmotion.py: re-bind each mesh's Armature
modifier to the imported armature so the body is posed, not a static rest pose.

Exit code is nonzero if the round-trip color check fails (R>G>B brown, not grey).

Usage (headless):
    blender --background --python verify_textured_proof.py -- <textured.fbx> <out_png> [frame]
"""
import bpy, sys, os
from mathutils import Vector

a = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
FBX = os.path.abspath(a[0])
OUT_PNG = os.path.abspath(a[1])   # Blender resolves relative render paths oddly in --background
FRAME = int(a[2]) if len(a) > 2 and a[2] else None
os.makedirs(os.path.dirname(OUT_PNG), exist_ok=True)

# #8B5E3C expected linear base color (see reapply_texture.leather_material)
EXPECT = (0.258, 0.118, 0.045)


def set_engine():
    for eng in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE", "CYCLES"):
        try:
            bpy.context.scene.render.engine = eng
            return eng
        except (TypeError, ValueError):
            continue
    return bpy.context.scene.render.engine


def read_back_color(mesh):
    """Return the reimported Principled base-color RGB, or None."""
    for m in mesh.data.materials:
        if not m:
            continue
        if m.use_nodes:
            bsdf = next((n for n in m.node_tree.nodes if n.type == 'BSDF_PRINCIPLED'), None)
            if bsdf:
                return tuple(bsdf.inputs["Base Color"].default_value)[:3], m.name
        return tuple(m.diffuse_color)[:3], m.name
    return None, None


def main():
    bpy.ops.object.select_all(action='SELECT'); bpy.ops.object.delete()
    bpy.ops.import_scene.fbx(filepath=FBX)
    arm = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
    meshes = [o for o in bpy.data.objects if o.type == 'MESH']
    char = max(meshes, key=lambda o: len(o.data.vertices))

    # --- round-trip color check ---
    rgb, mat_name = read_back_color(char)
    print(f"ROUNDTRIP_MATERIAL name='{mat_name}' base_color={rgb}")
    ok = (rgb is not None
          and rgb[0] > rgb[1] > rgb[2]            # warm brown ordering
          and rgb[0] > 0.10 and rgb[0] < 0.60     # not black, not the 0.8 default grey
          and abs(rgb[0] - EXPECT[0]) < 0.12)     # near #8B5E3C
    print(f"ROUNDTRIP_{'PASS' if ok else 'FAIL'} expected~{EXPECT}")

    # --- deform fix: re-bind armature modifier so the frame is posed ---
    for m in meshes:
        mod = next((md for md in m.modifiers if md.type == 'ARMATURE'), None)
        if mod is None:
            mod = m.modifiers.new("Armature", 'ARMATURE')
        mod.object = arm

    # --- frame the character (front ortho) across the chosen frame ---
    sc = bpy.context.scene
    if FRAME is not None:
        sc.frame_set(FRAME)
    else:
        sc.frame_set(int((sc.frame_start + sc.frame_end) / 2))
    dg = bpy.context.evaluated_depsgraph_get()
    mn = Vector((1e9, 1e9, 1e9)); mx = Vector((-1e9, -1e9, -1e9))
    for m in meshes:
        ev = m.evaluated_get(dg)
        for v in ev.data.vertices:
            w = ev.matrix_world @ v.co
            for i in range(3):
                mn[i] = min(mn[i], w[i]); mx[i] = max(mx[i], w[i])
    center = (mn + mx) / 2
    size = max((mx - mn).x, (mx - mn).z) * 1.15

    cam_data = bpy.data.cameras.new("cam"); cam_data.type = 'ORTHO'
    cam_data.ortho_scale = size
    cam = bpy.data.objects.new("cam", cam_data); sc.collection.objects.link(cam)
    cam.location = (center.x, center.y - max((mx - mn).y, size) * 4 - 2, center.z)
    cam.rotation_euler = (1.5708, 0, 0)   # look along +Y (front view)
    sc.camera = cam

    # --- lighting + world so the leather reads, not silhouettes ---
    sun = bpy.data.objects.new("sun", bpy.data.lights.new("sun", 'SUN'))
    sun.data.energy = 4.0; sun.rotation_euler = (0.9, 0.2, 0.5)
    sc.collection.objects.link(sun)
    if sc.world is None:
        sc.world = bpy.data.worlds.new("w")
    sc.world.use_nodes = True
    bg = sc.world.node_tree.nodes.get("Background")
    if bg:
        bg.inputs["Color"].default_value = (0.27, 0.27, 0.27, 1.0)
        bg.inputs["Strength"].default_value = 0.6

    set_engine()
    sc.render.resolution_x = sc.render.resolution_y = 480
    sc.render.image_settings.file_format = 'PNG'
    sc.render.filepath = OUT_PNG
    bpy.ops.render.render(write_still=True)
    print(f"PROOF_RENDER {OUT_PNG}")

    if not ok:
        sys.exit(2)


main()
