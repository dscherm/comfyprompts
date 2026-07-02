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

import os
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
    "gravel": "6e655a",
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
    "shake": "6b4a2a",     # wood-shingle / shake roof (common dwellings & workshops)
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
    # dark-fantasy / occult sub-palette (tuned to the grimforge_style LoRA:
    # high-contrast, saturated accents over deep darks)
    "charwood": "150f0a",
    "soot": "08060a",      # near-black, for charring / scorch / cavities
    "ash": "242329",
    "shroud": "1c1a22",
    "rot": "32341f",
    "blood": "5e1512",
    "gore": "7a1f17",
    "crimson": "9e1b1b",   # the knight's tattered cape — signature warm accent
    "gunmetal": "23262b",  # dark armor / iron base (high contrast vs steel)
    "steel": "9aa4ad",     # bright metal highlight
    # emissive
    "window": "ffcf6b",
    "fire": "ff8a2a",
    # emissive occult accents (glowing eyes, forge-glow, gems, leaking light)
    "ember": "ff4a16",     # forge-interior orange — the LoRA's iconic glow
    "amber": "ffb12e",     # glowing creature eyes / lantern (the dire wolf)
    "gem": "4fd4ff",       # cyan rune-gem accent (sword / treasure)
    "witchlight": "7dff5c",
    "ghostfire": "5cd2ff",
    "rune": "a04dff",
}

#: Material name -> emission strength. Materials not listed are non-emissive.
EMISSION: dict[str, float] = {
    "fire": 2.0,
    "window": 1.5,
    # occult / dark-fantasy glows burn a little hotter so they read at scale
    "ember": 2.5,
    "amber": 2.5,
    "gem": 1.6,
    "witchlight": 2.5,
    "ghostfire": 2.5,
    "rune": 2.2,
}


def validate_palette() -> None:
    """Raise ``ValueError`` if any palette entry is not a valid hex color, or
    if an emissive name is missing from the palette. Cheap integrity check used
    by tests and callable as a preflight guard."""
    for value in PALETTE.values():
        hex_to_rgba(value)  # raises on malformed entries
    missing = [n for n in EMISSION if n not in PALETTE]
    if missing:
        raise ValueError(f"EMISSION names not in PALETTE: {missing}")


#: GrimForge roof rule — the roof MATERIAL a structure should wear, keyed by its
#: class. The material scales with the building's status: rural/humble = thatch
#: (hay); ordinary dwellings & workshops = wood shingle (shake); tradesman /
#: better townhouses = clay tile (roof_red); grand civic/religious/noble/fortified
#: = slate. See ``docs`` / QUALITY_RUBRIC.md "Roof rule". A builder should pick its
#: roof colour via ``roof_for(<class>)`` (or the matching palette name) so the look
#: stays consistent across kits.
ROOF_RULES: dict[str, str] = {
    "humble": "thatch",     # cottage, hovel, barn, stable, well, farmhut, shed
    "dwelling": "shake",    # common houses, workshop, blacksmith, mill (wood shingle)
    "tradesman": "roof_red",  # tavern, inn, shopfront, guild stall, townhouse (clay tile)
    "grand": "slate",       # manor, guild/town hall, church, cathedral, keep, gatehouse
}


def roof_for(kind: str) -> str:
    """Return the roof palette colour for a structure ``kind`` per :data:`ROOF_RULES`.

    ``kind`` is one of ``humble`` / ``dwelling`` / ``tradesman`` / ``grand``.
    Raises ``KeyError`` on an unknown class so a typo fails loudly at build time."""
    return ROOF_RULES[kind]


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
        atlas: bool = False,
        atlas_size: int = 256,
    ) -> None:
        import bmesh  # noqa: F401  (imported for builders below)
        import bpy

        self._bpy = bpy
        self._bmesh = bmesh
        self.palette = dict(palette) if palette is not None else dict(PALETTE)
        self.emission = dict(emission) if emission is not None else dict(EMISSION)
        self._mat_cache: dict[str, Any] = {}
        # KayKit "color-atlas" mode: one shared gradient/AO atlas + per-primitive
        # UVs into each colour's swatch (see docs/kit_texturing_design.md).
        self.use_atlas = atlas
        self.atlas_size = atlas_size
        self._atlas_mat: Any = None
        self._atlas_imgs: tuple = ()
        self._cells: dict[str, tuple] | None = None
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

    def _ensure_atlas(self, cols: int = 8, size: int | None = None) -> Any:
        """Build (once) the shared atlas: each palette colour gets a swatch with a
        baked gradient + bottom-AO AND a material PATTERN (planks / brick / straw
        thatch / stained glass), plus an emission atlas. UV rects -> self._cells."""
        if self._atlas_mat is not None:
            return self._atlas_mat
        if size is None:
            size = self.atlas_size
        bpy = self._bpy
        pat_of = {}
        for pat, group in (
            ("planks", ("wood", "wood_dk", "charwood", "beam")),
            # masonry: walls + tower battlements (crenellations) read as stonework
            ("brick", ("stone", "stone_dk", "plaster", "plaster2")),
            # sloped roofs read as boards/shingle courses, NOT stonework
            ("shingle", ("slate", "roof_red", "shake")),
            ("straw", ("thatch", "thatch_dk")),
            ("cobble", ("cobble",)),   # cobblestone ground + roads
            ("gravel", ("gravel",)),   # gravel ground
            ("glass", ("gem", "rune")),  # stained-glass mosaic colours (NOT ghostfire=water)
        ):
            for nm in group:
                pat_of[nm] = pat

        def pm(pat, xx, yy, cw, ch):
            if pat == "planks":
                ph = max(3, ch // 5)
                return 0.42 if (yy % ph) < 1 else 0.88 + 0.12 * ((yy // ph) % 2)
            if pat == "brick":
                rh, bw = max(3, ch // 5), max(4, cw // 3)
                off = bw // 2 if (yy // rh) % 2 else 0
                if (yy % rh) < 1 or ((xx + off) % bw) < 1:
                    return 0.42
                return 0.88 + 0.14 * ((xx // bw + yy // rh) % 2)
            if pat == "straw":
                coh = max(4, ch // 4)                       # thatch course height
                yc = yy % coh
                strand = 0.86 + 0.14 * (((xx * 7 + (yy // coh) * 5) % 5) / 4.0)
                shadow = 0.4 if yc < 1 else (0.66 + 0.34 * (yc / max(1, coh - 1)))
                return shadow * strand
            if pat == "shingle":
                rh = max(3, ch // 6)                         # roof course height
                row, yc = yy // rh, yy % rh
                off = (rh // 2) if (row % 2) else 0          # stagger tabs
                tw = max(3, cw // 5)
                lift = 0.58 + 0.42 * (yc / max(1, rh - 1))   # each course lighter downslope
                if yc < 1:
                    lift = 0.4                               # course overlap shadow line
                if ((xx + off) % tw) < 1:
                    lift *= 0.84                             # subtle tab gap
                return lift
            if pat == "cobble":
                cs = max(3, cw // 5)                         # cobble sett size
                off = cs // 2 if (yy // cs) % 2 else 0
                gx, gy = (xx + off) % cs, yy % cs
                if gx < 1 or gy < 1:
                    return 0.36                              # mortar gap
                dx = (gx - cs / 2.0) / (cs / 2.0)
                dy = (gy - cs / 2.0) / (cs / 2.0)
                dome = 0.72 + 0.4 * max(0.0, 1.0 - (dx * dx + dy * dy))
                vary = 0.82 + 0.32 * ((((xx // cs) * 7 + (yy // cs) * 13) % 5) / 4.0)
                return dome * vary
            if pat == "gravel":
                n = (xx * 13 + yy * 7 + (xx // 3) * 5) % 9
                return 0.55 + 0.5 * (n / 8.0)
            if pat == "glass":
                pw, ph = max(3, cw // 3), max(3, ch // 3)
                return 0.28 if ((xx % pw) < 1 or (yy % ph) < 1) else 1.3
            return 1.0

        jewels = ((0.28, 0.78, 1.0), (0.96, 0.34, 0.56), (1.0, 0.72, 0.2),
                  (0.34, 0.95, 0.42))  # stained glass panes: blue, rose, amber, green

        def glass_px(xx, yy, cw, ch):
            pw, ph = max(3, cw // 3), max(3, ch // 3)
            if (xx % pw) < 1 or (yy % ph) < 1:
                return 0.05, 0.05, 0.06, False       # dark lead came
            j = jewels[((xx // pw) + (yy // ph)) % 4]
            return j[0], j[1], j[2], True

        names = list(self.palette)
        rows = max(1, -(-len(names) // cols))
        cw, ch = size // cols, size // rows
        col = [0.0, 0.0, 0.0, 1.0] * (size * size)
        emit = [0.0, 0.0, 0.0, 1.0] * (size * size)
        self._cells = {}
        for i, name in enumerate(names):
            r, g, b, _ = hex_to_rgba(self.palette[name])
            es = self.emission.get(name, 0.0)
            pat = pat_of.get(name, "plain")
            cx, cy = (i % cols) * cw, (i // cols) * ch
            for yy in range(ch):
                t = yy / max(1, ch - 1)
                gr = (0.72 + 0.4 * t) * (0.55 + 0.45 * min(1.0, yy / (ch * 0.3)))
                for xx in range(cw):
                    p = ((cy + yy) * size + (cx + xx)) * 4
                    if pat == "glass":
                        cr, cg, cb, glow = glass_px(xx, yy, cw, ch)
                        col[p], col[p + 1], col[p + 2] = cr * gr, cg * gr, cb * gr
                        if es > 0 and glow:
                            emit[p], emit[p + 1], emit[p + 2] = cr, cg, cb
                    else:
                        f = gr * pm(pat, xx, yy, cw, ch)
                        col[p], col[p + 1], col[p + 2] = min(1, r * f), min(1, g * f), min(1, b * f)
                        if es > 0:
                            emit[p], emit[p + 1], emit[p + 2] = r, g, b
            self._cells[name] = ((cx + 1.0) / size, (cx + cw - 1.0) / size,
                                 (cy + 1.0) / size, (cy + ch - 1.0) / size)
        cimg = bpy.data.images.new("kit_atlas", size, size)
        cimg.colorspace_settings.name = "Non-Color"
        cimg.pixels = col
        eimg = bpy.data.images.new("kit_atlas_emit", size, size)
        eimg.colorspace_settings.name = "Non-Color"
        eimg.pixels = emit
        m = bpy.data.materials.new("kit_atlas_mat")
        m.use_nodes = True
        nt = m.node_tree
        bsdf = nt.nodes["Principled BSDF"]
        bsdf.inputs["Roughness"].default_value = 0.9
        tc = nt.nodes.new("ShaderNodeTexImage")
        tc.image, tc.interpolation = cimg, "Closest"
        nt.links.new(tc.outputs["Color"], bsdf.inputs["Base Color"])
        te = nt.nodes.new("ShaderNodeTexImage")
        te.image, te.interpolation = eimg, "Closest"
        nt.links.new(te.outputs["Color"], bsdf.inputs["Emission Color"])
        bsdf.inputs["Emission Strength"].default_value = 2.2
        self._atlas_mat, self._atlas_imgs = m, (cimg, eimg)
        return m

    def _uv_swatch(self, obj: Any, color: str) -> None:
        """Planar-unwrap every face into ``color``'s swatch so the swatch pattern
        (planks/brick/straw/glass) + gradient read across the face. Each face's two
        in-plane axes map to the swatch U/V (the more-vertical axis -> V)."""
        me = obj.data
        u0, u1, v0, v1 = self._cells[color]
        if not me.uv_layers:
            me.uv_layers.new(name="UVMap")
        uvl = me.uv_layers.active.data
        co = [v.co for v in me.vertices]
        for poly in me.polygons:
            n = poly.normal
            dom = max(range(3), key=lambda i: abs(n[i]))
            ax = [i for i in range(3) if i != dom]
            pts = [(co[me.loops[li].vertex_index][ax[0]],
                    co[me.loops[li].vertex_index][ax[1]]) for li in poly.loop_indices]
            amin = min(p[0] for p in pts)
            arng = (max(p[0] for p in pts) - amin) or 1.0
            bmin = min(p[1] for p in pts)
            brng = (max(p[1] for p in pts) - bmin) or 1.0
            for j, li in enumerate(poly.loop_indices):
                s = (pts[j][0] - amin) / arng
                tt = (pts[j][1] - bmin) / brng
                uvl[li].uv = (u0 + s * (u1 - u0), v0 + tt * (v1 - v0))

    def save_atlas(self, out_dir: str, thumb: int = 128) -> list[str]:
        """Write the shared atlas (colour + emission) to ``out_dir`` as PNGs at the
        native master size plus a ``thumb``² downsample, and pack the images so the
        GLB/glTF exporters embed them. No-op unless :attr:`use_atlas` and the atlas
        has been built. Returns the paths written."""
        if not self.use_atlas or self._atlas_mat is None:
            return []
        saved: list[str] = []
        for img, base in ((self._atlas_imgs[0], "atlas_color"),
                          (self._atlas_imgs[1], "atlas_emit")):
            master = os.path.join(out_dir, base + ".png")
            img.filepath_raw = master
            img.file_format = "PNG"
            img.save()
            img.pack()                       # embed in GLB/glTF too
            saved.append(master)
            t = img.copy()
            t.scale(thumb, thumb)
            tp = os.path.join(out_dir, f"{base}_{thumb}.png")
            t.filepath_raw = tp
            t.file_format = "PNG"
            t.save()
            saved.append(tp)
        return saved

    def pack_atlas(self) -> None:
        """Pack the atlas images (if built) so a GLB export embeds them without a
        prior :meth:`save_atlas`. Used by the GLB-only pipeline."""
        for img in self._atlas_imgs:
            if not img.packed_file:
                img.pack()

    @staticmethod
    def tri_count(obj: Any) -> int:
        """Triangle count of ``obj`` (each n-gon contributes ``n - 2`` tris)."""
        return sum(len(p.vertices) - 2 for p in obj.data.polygons)

    def _finish(self, parts: list, color: str) -> Any:
        obj = self._bpy.context.active_object
        if self.use_atlas:
            if color not in self.palette:
                raise KeyError(f"unknown palette color {color!r}")
            obj.data.materials.append(self._ensure_atlas())
            self._uv_swatch(obj, color)
        else:
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
        self._bpy.context.view_layer.objects.active = obj
        return self._finish(parts, color)

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

    def _select_only(self, obj: Any) -> None:
        bpy = self._bpy
        bpy.ops.object.select_all(action="DESELECT")
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj

    def export_glb(self, obj: Any, filepath: str) -> None:
        """Export ``obj`` (selected, alone) to a binary glTF (``.glb``)."""
        self._select_only(obj)
        self._bpy.ops.export_scene.gltf(filepath=filepath, export_format="GLB", use_selection=True)

    def export_gltf(self, obj: Any, filepath: str) -> None:
        """Export ``obj`` to separate glTF (``.gltf`` + ``.bin`` + textures)."""
        self._select_only(obj)
        self._bpy.ops.export_scene.gltf(
            filepath=filepath, export_format="GLTF_SEPARATE", use_selection=True
        )

    def export_obj(self, obj: Any, filepath: str) -> None:
        """Export ``obj`` to Wavefront ``.obj`` (+ ``.mtl``, copying any texture)."""
        self._select_only(obj)
        self._bpy.ops.wm.obj_export(
            filepath=filepath, export_selected_objects=True, path_mode="COPY"
        )

    def export_fbx(self, obj: Any, filepath: str) -> None:
        """Export ``obj`` to Autodesk ``.fbx`` (self-contained: textures embedded)."""
        self._select_only(obj)
        self._bpy.ops.export_scene.fbx(
            filepath=filepath, use_selection=True, path_mode="COPY", embed_textures=True
        )

    def export_usd(self, obj: Any, filepath: str) -> None:
        """Export ``obj`` to Universal Scene Description (``.usdc``)."""
        self._select_only(obj)
        self._bpy.ops.wm.usd_export(filepath=filepath, selected_objects_only=True)

    def export_dae(self, obj: Any, filepath: str) -> None:
        """Export ``obj`` to COLLADA ``.dae``. Raises ``RuntimeError`` on builds
        that dropped the Collada I/O add-on (e.g. Blender 5.0) — callers that ship
        multiple formats should treat DAE as best-effort."""
        self._select_only(obj)
        self._bpy.ops.wm.collada_export(filepath=filepath, selected=True)

    #: format name -> (method, extension) for productization multi-format export
    @property
    def exporters(self) -> dict:
        return {
            "glb": (self.export_glb, ".glb"),
            "gltf": (self.export_gltf, ".gltf"),
            "obj": (self.export_obj, ".obj"),
            "fbx": (self.export_fbx, ".fbx"),
            "usd": (self.export_usd, ".usdc"),
            "dae": (self.export_dae, ".dae"),
        }


__all__ = ["Color", "hex_to_rgba", "PALETTE", "EMISSION", "validate_palette",
           "ROOF_RULES", "roof_for", "Kit"]
