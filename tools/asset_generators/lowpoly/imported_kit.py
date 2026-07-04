"""Adapter: turn a folder of finished low-poly GLBs (decimated image-to-3D
meshes) into a productize ``PIECES`` list, so the standard kit finishing —
5-format export + catalog/hero/gallery + quality gate + README/LISTING — runs on
IMPORTED meshes instead of procedural build functions.

Each piece keeps its own baked texture, so run productize WITHOUT ``--atlas``:

    blender -b --python productize.py -- spec_<kit>.py <product_dir> --gallery

A spec module then reads:

    from imported_kit import pieces_from_dir
    PIECES = pieces_from_dir(r"<dir of decimated .glb>")
    AESTHETIC = "medieval"
    TITLE = "<Kit Title>"
"""
import os

import bpy


def import_piece(path):
    """Return a productize build fn: import ``path`` into the Kit scene, join to
    one mesh object, drop non-mesh leftovers, and return the object."""
    def build(k):
        before = set(bpy.data.objects)
        bpy.ops.import_scene.gltf(filepath=path)
        new = [o for o in bpy.data.objects if o not in before]
        meshes = [o for o in new if o.type == "MESH"]
        if not meshes:
            raise ValueError(f"no mesh imported from {path}")
        obj = meshes[0]
        if len(meshes) > 1:
            bpy.ops.object.select_all(action="DESELECT")
            for o in meshes:
                o.select_set(True)
            bpy.context.view_layer.objects.active = meshes[0]
            bpy.ops.object.join()
            obj = bpy.context.active_object
        for o in new:  # cameras/empties/lights that rode along in the glb
            if o.type != "MESH" and o.name in bpy.data.objects:
                bpy.data.objects.remove(o, do_unlink=True)
        obj.name = os.path.basename(path)[:-4]
        return obj
    return build


def pieces_from_dir(d, names=None):
    """(name, build_fn) for every .glb in ``d`` (optionally filtered to ``names``)."""
    files = sorted(f for f in os.listdir(d) if f.lower().endswith(".glb"))
    if names:
        files = [f for f in files if f[:-4] in names]
    return [(f[:-4], import_piece(os.path.join(d, f))) for f in files]
