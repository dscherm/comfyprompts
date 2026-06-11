"""Tests for TilesetGridAssemble and TilesetGridSplit ComfyUI nodes."""
import pytest
import torch
import importlib.util
import os

# Load the module directly to avoid importing the package __init__.py
# which chains relative imports to all node files.
_mod_path = os.path.join(os.path.dirname(__file__), "..", "nodes", "tileset_grid.py")
_spec = importlib.util.spec_from_file_location("tileset_grid", _mod_path)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)

TilesetGridAssemble = _mod.TilesetGridAssemble
TilesetGridSplit = _mod.TilesetGridSplit


class TestTilesetGridAssemble:
    def test_dimensions_4x4(self):
        """16 tiles of 64x64x3, columns=4 -> 1x256x256x3"""
        node = TilesetGridAssemble()
        tiles = torch.rand(16, 64, 64, 3)
        result = node.assemble(tiles, columns=4)
        grid = result[0]
        assert grid.shape == (1, 256, 256, 3)

    def test_dimensions_2_columns(self):
        """8 tiles of 32x32x3, columns=2 -> 1x128x64x3"""
        node = TilesetGridAssemble()
        tiles = torch.rand(8, 32, 32, 3)
        result = node.assemble(tiles, columns=2)
        grid = result[0]
        assert grid.shape == (1, 128, 64, 3)

    def test_padding_incomplete_row(self):
        """15 tiles with columns=4: 4 rows needed, last row padded with black."""
        node = TilesetGridAssemble()
        tiles = torch.rand(15, 64, 64, 3)
        result = node.assemble(tiles, columns=4)
        grid = result[0]
        # 15/4 = 3.75 -> ceil = 4 rows
        assert grid.shape == (1, 256, 256, 3)

    def test_padding_is_black(self):
        """The padded area should be zeros (black)."""
        node = TilesetGridAssemble()
        tiles = torch.ones(15, 64, 64, 3)  # All white tiles
        result = node.assemble(tiles, columns=4)
        grid = result[0]
        # Last tile position (row=3, col=3) should be all zeros
        last_tile = grid[0, 192:256, 192:256, :]
        assert torch.all(last_tile == 0.0)

    def test_single_tile(self):
        node = TilesetGridAssemble()
        tiles = torch.rand(1, 64, 64, 3)
        result = node.assemble(tiles, columns=1)
        grid = result[0]
        assert grid.shape == (1, 64, 64, 3)

    def test_single_row(self):
        node = TilesetGridAssemble()
        tiles = torch.rand(4, 64, 64, 3)
        result = node.assemble(tiles, columns=4)
        grid = result[0]
        assert grid.shape == (1, 64, 256, 3)

    def test_output_is_tuple(self):
        """ComfyUI nodes return tuples matching RETURN_TYPES."""
        node = TilesetGridAssemble()
        tiles = torch.rand(4, 32, 32, 3)
        result = node.assemble(tiles, columns=2)
        assert isinstance(result, tuple)
        assert len(result) == 1

    def test_batch_dim_is_1(self):
        node = TilesetGridAssemble()
        tiles = torch.rand(9, 32, 32, 3)
        result = node.assemble(tiles, columns=3)
        grid = result[0]
        assert grid.shape[0] == 1

    def test_pixel_values_preserved(self):
        """Check that tile content is placed correctly in the grid."""
        node = TilesetGridAssemble()
        tiles = torch.zeros(4, 2, 2, 3)
        # Give each tile a unique value
        for i in range(4):
            tiles[i] = float(i + 1)
        result = node.assemble(tiles, columns=2)
        grid = result[0]
        # Tile 0 at (0,0): row 0:2, col 0:2
        assert torch.all(grid[0, 0:2, 0:2, :] == 1.0)
        # Tile 1 at (0,1): row 0:2, col 2:4
        assert torch.all(grid[0, 0:2, 2:4, :] == 2.0)
        # Tile 2 at (1,0): row 2:4, col 0:2
        assert torch.all(grid[0, 2:4, 0:2, :] == 3.0)
        # Tile 3 at (1,1): row 2:4, col 2:4
        assert torch.all(grid[0, 2:4, 2:4, :] == 4.0)

    def test_dtype_preserved(self):
        node = TilesetGridAssemble()
        tiles = torch.rand(4, 32, 32, 3, dtype=torch.float32)
        result = node.assemble(tiles, columns=2)
        assert result[0].dtype == torch.float32


class TestTilesetGridSplit:
    def test_dimensions(self):
        """Splitting 256x256 with 64x64 tiles gives 16 tiles."""
        node = TilesetGridSplit()
        grid = torch.rand(1, 256, 256, 3)
        result = node.split(grid, tile_width=64, tile_height=64)
        tiles = result[0]
        assert tiles.shape == (16, 64, 64, 3)

    def test_non_square_tiles(self):
        """Splitting with non-square tile dimensions."""
        node = TilesetGridSplit()
        grid = torch.rand(1, 128, 256, 3)
        result = node.split(grid, tile_width=64, tile_height=32)
        tiles = result[0]
        # 256/64=4 cols, 128/32=4 rows -> 16 tiles
        assert tiles.shape == (16, 32, 64, 3)

    def test_single_tile_split(self):
        node = TilesetGridSplit()
        grid = torch.rand(1, 64, 64, 3)
        result = node.split(grid, tile_width=64, tile_height=64)
        tiles = result[0]
        assert tiles.shape == (1, 64, 64, 3)

    def test_output_is_tuple(self):
        node = TilesetGridSplit()
        grid = torch.rand(1, 128, 128, 3)
        result = node.split(grid, tile_width=64, tile_height=64)
        assert isinstance(result, tuple)
        assert len(result) == 1

    def test_row_major_order(self):
        """Tiles should be extracted in row-major order."""
        node = TilesetGridSplit()
        grid = torch.zeros(1, 4, 4, 3)
        # Set distinct values in each 2x2 region
        grid[0, 0:2, 0:2, :] = 1.0  # tile 0
        grid[0, 0:2, 2:4, :] = 2.0  # tile 1
        grid[0, 2:4, 0:2, :] = 3.0  # tile 2
        grid[0, 2:4, 2:4, :] = 4.0  # tile 3
        result = node.split(grid, tile_width=2, tile_height=2)
        tiles = result[0]
        assert torch.all(tiles[0] == 1.0)
        assert torch.all(tiles[1] == 2.0)
        assert torch.all(tiles[2] == 3.0)
        assert torch.all(tiles[3] == 4.0)


class TestRoundTrip:
    def test_assemble_split_roundtrip(self):
        """Assemble tiles into grid, split back, verify identical."""
        assembler = TilesetGridAssemble()
        splitter = TilesetGridSplit()
        original = torch.rand(16, 64, 64, 3)
        grid = assembler.assemble(original, columns=4)[0]
        recovered = splitter.split(grid, tile_width=64, tile_height=64)[0]
        assert torch.allclose(original, recovered, atol=1e-6)

    def test_roundtrip_non_square_grid(self):
        """Roundtrip with non-square grid (more columns than rows)."""
        assembler = TilesetGridAssemble()
        splitter = TilesetGridSplit()
        original = torch.rand(6, 32, 32, 3)
        grid = assembler.assemble(original, columns=6)[0]
        recovered = splitter.split(grid, tile_width=32, tile_height=32)[0]
        assert torch.allclose(original, recovered, atol=1e-6)

    def test_roundtrip_single_tile(self):
        assembler = TilesetGridAssemble()
        splitter = TilesetGridSplit()
        original = torch.rand(1, 128, 128, 3)
        grid = assembler.assemble(original, columns=1)[0]
        recovered = splitter.split(grid, tile_width=128, tile_height=128)[0]
        assert torch.allclose(original, recovered, atol=1e-6)


class TestComfyUINodeInterface:
    """Test that node classes have correct ComfyUI interface attributes."""

    def test_assemble_input_types(self):
        types = TilesetGridAssemble.INPUT_TYPES()
        assert "required" in types
        assert "tiles" in types["required"]
        assert "columns" in types["required"]

    def test_assemble_return_types(self):
        assert TilesetGridAssemble.RETURN_TYPES == ("IMAGE",)

    def test_assemble_function_name(self):
        assert TilesetGridAssemble.FUNCTION == "assemble"

    def test_assemble_category(self):
        assert TilesetGridAssemble.CATEGORY == "tileset"

    def test_split_input_types(self):
        types = TilesetGridSplit.INPUT_TYPES()
        assert "required" in types
        assert "grid" in types["required"]
        assert "tile_width" in types["required"]
        assert "tile_height" in types["required"]

    def test_split_return_types(self):
        assert TilesetGridSplit.RETURN_TYPES == ("IMAGE",)

    def test_split_function_name(self):
        assert TilesetGridSplit.FUNCTION == "split"

    def test_split_category(self):
        assert TilesetGridSplit.CATEGORY == "tileset"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
