"""ComfyUI node wrapping the autotile expansion utility."""

import numpy as np
import torch

from ..utils.autotile import expand_tileset


class AutotileExpand:
    """Expands 16 marching squares tiles into a full autotile set."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "tiles": ("IMAGE",),
                "output_format": (["godot_minimal", "godot_full", "rpgmaker",
                                   "gamemaker", "generic"],),
            }
        }

    RETURN_TYPES = ("IMAGE",)
    FUNCTION = "expand"
    CATEGORY = "tileset"

    def expand(self, tiles, output_format):
        if tiles.shape[0] != 16:
            raise ValueError(f"Expected 16 tiles, got {tiles.shape[0]}")

        # Convert torch [B,H,W,C] float32 [0,1] -> numpy [H,W,C] uint8 [0,255]
        source = []
        for i in range(16):
            np_tile = (tiles[i].cpu().numpy() * 255).astype(np.uint8)
            source.append(np_tile)

        expanded = expand_tileset(source, output_format)

        # Convert back to torch [B,H,W,C] float32 [0,1]
        tensors = []
        for tile in expanded:
            t = torch.from_numpy(tile.astype(np.float32) / 255.0)
            tensors.append(t)

        return (torch.stack(tensors),)
