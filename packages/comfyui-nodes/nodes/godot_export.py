"""ComfyUI node for exporting tilesets in Godot 4.x format."""

import math
import os

import numpy as np
import torch


class GodotTilesetExport:
    """Exports tileset as PNG atlas + Godot .tres resource."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "tiles": ("IMAGE",),
                "tileset_name": ("STRING", {"default": "terrain"}),
                "tile_size": ("INT", {"default": 64, "min": 16, "max": 256}),
                "terrain_set_name": ("STRING", {"default": "terrain_0"}),
                "output_directory": ("STRING", {"default": ""}),
            }
        }

    RETURN_TYPES = ("IMAGE", "STRING")
    RETURN_NAMES = ("atlas", "tres_content")
    FUNCTION = "export"
    CATEGORY = "tileset"
    OUTPUT_NODE = True

    def export(self, tiles, tileset_name, tile_size, terrain_set_name, output_directory):
        B, H, W, C = tiles.shape

        # Calculate atlas layout (prefer power-of-2 width)
        cols = self._optimal_columns(B)
        rows = math.ceil(B / cols)

        atlas_w = cols * tile_size
        atlas_h = rows * tile_size

        # Build atlas image
        atlas = torch.zeros(1, atlas_h, atlas_w, C, dtype=tiles.dtype, device=tiles.device)
        for i in range(B):
            r = i // cols
            c = i % cols
            # Resize tiles to tile_size if needed
            tile = tiles[i]
            if tile.shape[0] != tile_size or tile.shape[1] != tile_size:
                tile = torch.nn.functional.interpolate(
                    tile.unsqueeze(0).permute(0, 3, 1, 2),
                    size=(tile_size, tile_size),
                    mode="bilinear",
                    align_corners=False,
                ).permute(0, 2, 3, 1).squeeze(0)
            atlas[0, r * tile_size:(r + 1) * tile_size,
                  c * tile_size:(c + 1) * tile_size, :] = tile

        # Generate .tres content
        atlas_filename = f"{tileset_name}_atlas.png"
        tres = self._generate_tres(
            tileset_name, atlas_filename, tile_size,
            atlas_w, atlas_h, cols, rows, B, terrain_set_name,
        )

        # Save files if output_directory specified
        if output_directory:
            os.makedirs(output_directory, exist_ok=True)
            # Save atlas PNG
            atlas_np = (atlas[0].cpu().numpy() * 255).astype(np.uint8)
            self._save_png(atlas_np, os.path.join(output_directory, atlas_filename))
            # Save .tres
            tres_path = os.path.join(output_directory, f"{tileset_name}.tres")
            with open(tres_path, "w") as f:
                f.write(tres)

        return (atlas, tres)

    def _optimal_columns(self, tile_count):
        """Choose column count for near-square, power-of-2-friendly atlas."""
        cols = int(math.sqrt(tile_count))
        # Try to find a power of 2 that works
        for po2 in [4, 8, 16, 32]:
            if po2 * po2 >= tile_count:
                return po2
        return cols

    def _generate_tres(self, name, atlas_file, tile_size,
                       atlas_w, atlas_h, cols, rows, tile_count,
                       terrain_set_name):
        """Generate Godot 4.x TileSet .tres resource text."""
        lines = [
            f'[gd_resource type="TileSet" load_steps=2 format=3]',
            "",
            f'[ext_resource type="Texture2D" path="res://{atlas_file}" id="1"]',
            "",
            "[resource]",
            f"tile_size = Vector2i({tile_size}, {tile_size})",
            "",
            "# Terrain sets",
            f'0/name = "{terrain_set_name}"',
            "0/mode = 1",  # match_corners_and_sides
            '0/terrains/0/name = "terrain_a"',
            '0/terrains/0/color = Color(0.2, 0.8, 0.2, 1)',
            '0/terrains/1/name = "terrain_b"',
            '0/terrains/1/color = Color(0.6, 0.4, 0.2, 1)',
            "",
            "# Atlas source",
            '0:sources/0/name = "atlas"',
            '0:sources/0/texture = ExtResource("1")',
            f"0:sources/0/texture_region_size = Vector2i({tile_size}, {tile_size})",
            "",
            "# Tiles",
        ]

        for i in range(tile_count):
            r = i // cols
            c = i % cols
            lines.append(
                f"0:sources/0/{c}:{r}/0/terrain_set = 0"
            )
            # Assign terrain peering bits based on bitmask index
            bitmask = i
            bit_labels = [
                ("top", 0), ("top_right", 1), ("right", 2),
                ("bottom_right", 3), ("bottom", 4), ("bottom_left", 5),
                ("left", 6), ("top_left", 7),
            ]
            for label, bit in bit_labels:
                terrain_id = 0 if (bitmask & (1 << bit)) else 1
                lines.append(
                    f"0:sources/0/{c}:{r}/0/terrain_peering/{label} = {terrain_id}"
                )

        return "\n".join(lines) + "\n"

    def _save_png(self, image_np, path):
        """Save numpy array as PNG using basic method."""
        try:
            from PIL import Image
            img = Image.fromarray(image_np)
            img.save(path)
        except ImportError:
            # Fallback: write raw data (ComfyUI should have PIL)
            import struct
            import zlib
            h, w = image_np.shape[:2]
            channels = image_np.shape[2] if image_np.ndim == 3 else 1

            # Minimal PNG writer
            def write_png(f, data, width, height, channels):
                def chunk(chunk_type, data):
                    c = chunk_type + data
                    crc = struct.pack(">I", zlib.crc32(c) & 0xFFFFFFFF)
                    return struct.pack(">I", len(data)) + c + crc

                color_type = {1: 0, 3: 2, 4: 6}[channels]
                header = struct.pack(">IIBBBBB", width, height, 8,
                                     color_type, 0, 0, 0)
                raw = b""
                for y in range(height):
                    raw += b"\x00"  # filter none
                    raw += data[y].tobytes()
                compressed = zlib.compress(raw)

                f.write(b"\x89PNG\r\n\x1a\n")
                f.write(chunk(b"IHDR", header))
                f.write(chunk(b"IDAT", compressed))
                f.write(chunk(b"IEND", b""))

            with open(path, "wb") as f:
                write_png(f, image_np, w, h, channels)
