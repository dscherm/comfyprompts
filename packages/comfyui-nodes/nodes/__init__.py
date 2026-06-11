"""ComfyUI node definitions for tileset generation."""

from .tileset_grid import TilesetGridAssemble, TilesetGridSplit
from .marching_squares_masks import MarchingSquaresMasks
from .tileset_preview import TilesetPreview
from .godot_export import GodotTilesetExport
from .autotile_expand_node import AutotileExpand

NODE_CLASS_MAPPINGS = {
    "TilesetGridAssemble": TilesetGridAssemble,
    "TilesetGridSplit": TilesetGridSplit,
    "MarchingSquaresMasks": MarchingSquaresMasks,
    "TilesetPreview": TilesetPreview,
    "GodotTilesetExport": GodotTilesetExport,
    "AutotileExpand": AutotileExpand,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "TilesetGridAssemble": "Tileset Grid Assemble",
    "TilesetGridSplit": "Tileset Grid Split",
    "MarchingSquaresMasks": "Marching Squares Masks",
    "TilesetPreview": "Tileset Preview",
    "GodotTilesetExport": "Godot Tileset Export",
    "AutotileExpand": "Autotile Expand",
}

# NonManifoldTilesetSampler requires comfy.* imports (only in ComfyUI runtime)
try:
    from .tileset_sampler import NonManifoldTilesetSampler
    NODE_CLASS_MAPPINGS["NonManifoldTilesetSampler"] = NonManifoldTilesetSampler
    NODE_DISPLAY_NAME_MAPPINGS["NonManifoldTilesetSampler"] = "Non-Manifold Tileset Sampler"
except ImportError:
    pass
