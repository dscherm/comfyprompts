"""kitlib — shared procedural primitive DSL for GrimForge low-poly kits.

This module is the single source of truth for the GrimForge construction
vocabulary that was previously copy-pasted into ``kit_full.py`` and
``kit_vol2.py``: a fixed hex palette, flat-shaded materials, and a handful of
primitive builders (box / cyl / cone / ico / gable) plus ``join`` and GLB
export.

Two layers:

* **Pure helpers** (:func:`hex_to_rgba`, :data:`PALETTE`, :data:`EMISSION`,
  :func:`validate_palette`) import without Blender, so they are unit-testable
  in plain CPython / CI.
* **The :class:`Kit` class** wraps the Blender API. It imports ``bpy`` /
  ``bmesh`` lazily on construction, so it is only usable inside Blender
  (``blender -b --python your_script.py``). Importing this module never
  requires Blender.

The palette is the *union* of the two original kits. Where the two kits
disagreed on a name, both values are preserved under distinct keys (see
``bone`` vs ``bone_pale``) so existing assets reproduce byte-for-byte.

Style contract (do not break — it is what makes a piece "GrimForge"):

* solid flat-shaded colors only, drawn from :data:`PALETTE`
* 1-unit grid, +Z up (Blender), pieces centered on origin
* every piece ``join``-ed into a single mesh before export
* ``window`` / ``fire`` materials are emissive
"""

from __future__ import annotations

from typing import Any

# --------------------------------------------------------------------------- #
# Pure, Blender-free surface (unit-testable)
# --------------------------------------------------------------------------- #

Color = tuple[float, float, float, float]
_HEXDIGITS = set("0123456789abcdefABCDEF")


def hex_to_rgba(h: str) -> Color:
    """Convert a 6-digit hex string (``"6f756a"`` or ``"#6f756a"``) to an
    RGBA tuple with each channel in ``[0, 1]`` and alpha fixed at ``1.0``."""
    h = h.lstrip("#")
    if len(h) != 6 or any(c not in _HEXDIGITS for c in h):
        raise ValueError(f"expected a 6-digit hex color, got {h!r}")
    r, g, b = (int(h[i : i + 2], 16) / 255 for i in (0, 2, 4))
    return (r, g, b, 1.0)


#: Canonical GrimForge palette — union of kit_full.py and kit_vol2.py.
#: ``bone`` keeps the Vol.1 value; ``bone_pale`` keeps the lighter Vol.2 value.
PALETTE: dict[str, str] = {
    # stone & masonry
    "stone": "6f756a",
    "stone_dk": "4c5249",
    "cobble": "5a5a62",
    # plaster / framing
    "plaster": "c9bfa6",
    "plaster2": "bcae8e",
    "beam": "3a2a1a",
    # wood
    "wood": "5a4230",
    "wood_dk": "39291b",
    # roofing
    "thatch": "7a6332",
    "thatch_dk": "5e4d27",
    "slate": "3b434d",
    "roof_red": "823629",
    # metal
    "iron": "474b52",
    "gold": "c8a23a",
    # foliage & ground
    "moss": "4f6a37",
    "grass": "44602f",
    "dirt": "4d3c29",
    "leaf": "3f7a35",
    "leaf_dk": "2e5a26",
    "pine": "2f5a33",
    # cloth / banners
    "cloth": "355f58",
    "cloth_r": "7a2f2a",
    "flag": "7a2f2a",
    # liquids
    "water": "2c6492",
    # grimdark
    "bone": "c4bba2",
    "bone_pale": "d8d0bc",
    # emissive
    "window": "ffcf6b",
    "fire": "ff8a2a",
}

#: Material name -> emission strength. Materials not listed are non-emissive.
EMISSION: dict[str, float] = {"fire": 2.0, "window": 1.5}


def validate_palette() -> None:
    """Raise ``ValueError`` if any palette entry is not a valid hex color, or
    if an emissive name is missing from the palette. Cheap integrity check used
    by tests and callable as a preflight guard."""
    for value in PALETTE.values():
        hex_to_rgba(value)  # raises on malformed entries
    missing = [n for n in EMISSION if n not in PALETTE]
    if missing:
        raise ValueError(f"EMISSION names not in PALETTE: {missing}")


# --------------------------------------------------------------------------- #
# Blender layer
# --------------------------------------------------------------------------- #


class Kit:
    """Stateful builder bound to a Blender scene.

    Construct one per build script. ``bpy``/``bmesh`` are imported here, so
    this class can only be instantiated inside Blender. Materials are cached by
    name, so repeated color use shares a single material datablock.

    Example (run with ``blender -b --python build.py``)::

        from kitlib import Kit
        k = Kit(reset_scene=True)
        parts = []
        k.box(parts, 1.0, 1.0, 0.6, (0, 0, 0.3), "stone")
        k.cone(parts, 7, 0.5, 0, 0.7, (0, 0, 0.9), "leaf")
        obj = k.join(parts, "rock_tree")
        k.export_glb(obj, "/tmp/rock_tree.glb")
    """

    def __init__(
        self,
        palette: dict[str, str] | None = None,
        emission: dict[str, float] | None = None,
        reset_scene: bool = False,
    ) -> None:
        import bmesh  # noqa: F401  (imported for builders below)
        import bpy

        self._bpy = bpy
        self._bmesh = bmesh
        self.palette = dict(palette) if palette is not None else dict(PALETTE)
        self.emission = dict(emission) if emission is not None else dict(EMISSION)
        self._mat_cache: dict[str, Any] = {}
        if reset_scene:
            bpy.ops.wm.read_factory_settings(use_empty=True)
        self.scene = bpy.context.scene

    # -- materials ---------------------------------------------------------- #

    def mat(self, name: str) -> Any:
        """Return (creating + caching on first use) a flat principled material
        for a palette ``name``. Emissive names glow per :attr:`emission`."""
        if name in self._mat_cache:
            return self._mat_cache[name]
        if name not in self.palette:
            raise KeyError(f"unknown palette color {name!r}")
        m = self._bpy.data.materials.new(name)
        m.use_nodes = True
        bsdf = m.node_tree.nodes["Principled BSDF"]
        bsdf.inputs["Base Color"].default_value = hex_to_rgba(self.palette[name])
        bsdf.inputs["Roughness"].default_value = 0.9
        if name in self.emission:
            bsdf.inputs["Emission Color"].default_value = hex_to_rgba(self.palette[name])
            bsdf.inputs["Emission Strength"].default_value = self.emission[name]
        self._mat_cache[name] = m
        return m

    @staticmethod
    def flat(obj: Any) -> None:
        """Force flat (faceted) shading on every polygon of ``obj``."""
        for p in obj.data.polygons:
            p.use_smooth = False

    def _finish(self, parts: list, color: str) -> Any:
        obj = self._bpy.context.active_object
        obj.data.materials.append(self.mat(color))
        self.flat(obj)
        parts.append(obj)
        return obj

    # -- primitives --------------------------------------------------------- #

    def box(self, parts, sx, sy, sz, loc, color, rot=(0, 0, 0)) -> Any:
        """Axis-aligned cuboid of size ``(sx, sy, sz)`` at ``loc``."""
        self._bpy.ops.mesh.primitive_cube_add(size=1, location=loc, rotation=rot)
        self._bpy.context.active_object.scale = (sx, sy, sz)
        return self._finish(parts, color)

    def cyl(self, parts, vn, r, dz, loc, color, rot=(0, 0, 0)) -> Any:
        """``vn``-sided cylinder, radius ``r``, depth ``dz``."""
        self._bpy.ops.mesh.primitive_cylinder_add(
            vertices=vn, radius=r, depth=dz, location=loc, rotation=rot
        )
        return self._finish(parts, color)

    def cone(self, parts, vn, r1, r2, dz, loc, color, rot=(0, 0, 0)) -> Any:
        """``vn``-sided (truncated) cone from radius ``r1`` to ``r2``."""
        self._bpy.ops.mesh.primitive_cone_add(
            vertices=vn, radius1=r1, radius2=r2, depth=dz, location=loc, rotation=rot
        )
        return self._finish(parts, color)

    def ico(self, parts, r, loc, color, sub=1) -> Any:
        """Ico-sphere of radius ``r`` and subdivision ``sub`` (low for facets)."""
        self._bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=sub, radius=r, location=loc)
        return self._finish(parts, color)

    def gable(self, parts, w, d, h, loc, color, over=0.16) -> Any:
        """A gable (triangular-prism roof) of footprint ``w`` x ``d``, ridge
        height ``h``, with ``over`` eave overhang added to both spans."""
        bmesh = self._bmesh
        w += over
        d += over
        bm = bmesh.new()
        v = [
            bm.verts.new((-w / 2, -d / 2, 0)),
            bm.verts.new((w / 2, -d / 2, 0)),
            bm.verts.new((0, -d / 2, h)),
            bm.verts.new((-w / 2, d / 2, 0)),
            bm.verts.new((w / 2, d / 2, 0)),
            bm.verts.new((0, d / 2, h)),
        ]
        for f in [(0, 1, 2), (5, 4, 3), (0, 2, 5, 3), (2, 1, 4, 5), (1, 0, 3, 4)]:
            bm.faces.new([v[i] for i in f])
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        me = self._bpy.data.meshes.new("gable")
        bm.to_mesh(me)
        bm.free()
        obj = self._bpy.data.objects.new("gable", me)
        self.scene.collection.objects.link(obj)
        obj.location = loc
        obj.data.materials.append(self.mat(color))
        self.flat(obj)
        parts.append(obj)
        return obj

    # -- assembly / export -------------------------------------------------- #

    def join(self, parts: list, name: str) -> Any:
        """Join all ``parts`` into a single mesh object named ``name`` and
        return it. ``parts`` must be non-empty."""
        if not parts:
            raise ValueError("join() needs at least one part")
        bpy = self._bpy
        bpy.ops.object.select_all(action="DESELECT")
        for o in parts:
            o.select_set(True)
        bpy.context.view_layer.objects.active = parts[0]
        bpy.ops.object.join()
        obj = bpy.context.active_object
        obj.name = name
        return obj

    def export_glb(self, obj: Any, filepath: str) -> None:
        """Export ``obj`` (selected, alone) to a binary glTF (``.glb``)."""
        bpy = self._bpy
        bpy.ops.object.select_all(action="DESELECT")
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj
        bpy.ops.export_scene.gltf(filepath=filepath, export_format="GLB", use_selection=True)


__all__ = ["Color", "hex_to_rgba", "PALETTE", "EMISSION", "validate_palette", "Kit"]
