"""ComfyUI node for generating tileset preview maps."""

import torch


class TilesetPreview:
    """Assembles a preview map showing how tiles connect."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "tiles": ("IMAGE",),
                "pattern": (["random", "checkerboard", "gradient", "all_transitions"],),
                "map_width": ("INT", {"default": 8, "min": 4, "max": 32}),
                "map_height": ("INT", {"default": 8, "min": 4, "max": 32}),
                "seed": ("INT", {"default": 0}),
            }
        }

    RETURN_TYPES = ("IMAGE",)
    FUNCTION = "preview"
    CATEGORY = "tileset"

    def preview(self, tiles, pattern, map_width, map_height, seed):
        if tiles.shape[0] < 16:
            raise ValueError(f"Expected at least 16 tiles, got {tiles.shape[0]}")

        _, tile_h, tile_w, C = tiles.shape

        # Generate terrain grid: True = terrain A at each vertex
        # Grid is (map_height+1) x (map_width+1) vertices
        verts_h = map_height + 1
        verts_w = map_width + 1
        terrain = self._generate_terrain(pattern, verts_h, verts_w, seed)

        # Build output image
        out_h = map_height * tile_h
        out_w = map_width * tile_w
        output = torch.zeros(1, out_h, out_w, C, dtype=tiles.dtype, device=tiles.device)

        for r in range(map_height):
            for c in range(map_width):
                tl = terrain[r][c]
                tr = terrain[r][c + 1]
                bl = terrain[r + 1][c]
                br = terrain[r + 1][c + 1]
                case_idx = int(tl) * 8 + int(tr) * 4 + int(br) * 2 + int(bl) * 1
                output[0,
                       r * tile_h:(r + 1) * tile_h,
                       c * tile_w:(c + 1) * tile_w,
                       :] = tiles[case_idx]

        return (output,)

    def _generate_terrain(self, pattern, h, w, seed):
        """Generate vertex terrain grid (list of lists of bool)."""
        if pattern == "random":
            gen = torch.Generator()
            gen.manual_seed(seed)
            rand = torch.rand(h, w, generator=gen)
            return [[bool(rand[r, c] > 0.5) for c in range(w)] for r in range(h)]

        elif pattern == "checkerboard":
            return [[(r + c) % 2 == 0 for c in range(w)] for r in range(h)]

        elif pattern == "gradient":
            return [[c >= w // 2 for c in range(w)] for r in range(h)]

        elif pattern == "all_transitions":
            # Create a pattern that produces all 16 cases
            # Use a 4x4 block in the center that cycles through cases
            terrain = [[False] * w for _ in range(h)]
            # Place a structured pattern to create varied transitions
            for r in range(h):
                for c in range(w):
                    # Create islands and edges to produce all cases
                    block_r = r % 4
                    block_c = c % 4
                    # Pattern designed to produce all 16 marching squares cases
                    pattern_4x4 = [
                        [False, True, True, False],
                        [True, True, False, False],
                        [True, False, False, True],
                        [False, False, True, True],
                    ]
                    terrain[r][c] = pattern_4x4[block_r][block_c]
            return terrain

        raise ValueError(f"Unknown pattern: {pattern}")
