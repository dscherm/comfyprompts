"""ComfyUI nodes for assembling and splitting tileset grids."""

import math
import torch


class TilesetGridAssemble:
    """Arranges a batch of tile images into a grid."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "tiles": ("IMAGE",),
                "columns": ("INT", {"default": 4, "min": 1, "max": 64}),
            }
        }

    RETURN_TYPES = ("IMAGE",)
    FUNCTION = "assemble"
    CATEGORY = "tileset"

    def assemble(self, tiles, columns):
        B, H, W, C = tiles.shape
        rows = math.ceil(B / columns)

        # Create output grid filled with black
        grid = torch.zeros(1, rows * H, columns * W, C,
                           dtype=tiles.dtype, device=tiles.device)

        for i in range(B):
            r = i // columns
            c = i % columns
            grid[0, r * H:(r + 1) * H, c * W:(c + 1) * W, :] = tiles[i]

        return (grid,)


class TilesetGridSplit:
    """Splits a grid image into individual tiles."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "grid": ("IMAGE",),
                "tile_width": ("INT", {"default": 64, "min": 1, "max": 2048}),
                "tile_height": ("INT", {"default": 64, "min": 1, "max": 2048}),
            }
        }

    RETURN_TYPES = ("IMAGE",)
    FUNCTION = "split"
    CATEGORY = "tileset"

    def split(self, grid, tile_width, tile_height):
        _, H, W, C = grid.shape
        cols = W // tile_width
        rows = H // tile_height

        tiles = []
        for r in range(rows):
            for c in range(cols):
                tile = grid[0,
                            r * tile_height:(r + 1) * tile_height,
                            c * tile_width:(c + 1) * tile_width,
                            :]
                tiles.append(tile)

        return (torch.stack(tiles),)
