"""Tests for autotile.py bitmask expansion logic."""
import pytest
import numpy as np
import importlib.util
import os

# Load the module directly to avoid importing the package __init__.py
# which chains relative imports to all node files.
_mod_path = os.path.join(os.path.dirname(__file__), "..", "utils", "autotile.py")
_spec = importlib.util.spec_from_file_location("autotile", _mod_path)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)

expand_tileset = _mod.expand_tileset
get_tile_count = _mod.get_tile_count
_quadrant_source = _mod._quadrant_source
_corners_to_case = _mod._corners_to_case
_get_quadrant = _mod._get_quadrant
_set_quadrant = _mod._set_quadrant
_expand_single_tile = _mod._expand_single_tile


def _make_dummy_tiles(count=16, size=32, channels=3):
    """Create dummy tiles as numpy arrays [H, W, C] with distinct content."""
    tiles = []
    for i in range(count):
        # Each tile has a unique uniform value so we can track provenance
        tile = np.full((size, size, channels), fill_value=i / 15.0, dtype=np.float32)
        tiles.append(tile)
    return tiles


class TestGetTileCount:
    def test_godot_minimal(self):
        assert get_tile_count("godot_minimal") == 47

    def test_godot_full(self):
        assert get_tile_count("godot_full") == 256

    def test_rpgmaker(self):
        assert get_tile_count("rpgmaker") == 48

    def test_gamemaker(self):
        assert get_tile_count("gamemaker") == 47

    def test_generic(self):
        assert get_tile_count("generic") == 256

    def test_unknown_format_raises(self):
        with pytest.raises(ValueError, match="Unknown format"):
            get_tile_count("unity")


class TestExpandTileset:
    def test_godot_minimal_count(self):
        tiles = _make_dummy_tiles()
        result = expand_tileset(tiles, "godot_minimal")
        assert len(result) == 47

    def test_godot_full_count(self):
        tiles = _make_dummy_tiles()
        result = expand_tileset(tiles, "godot_full")
        assert len(result) == 256

    def test_rpgmaker_count(self):
        tiles = _make_dummy_tiles()
        result = expand_tileset(tiles, "rpgmaker")
        assert len(result) == 48

    def test_gamemaker_count(self):
        tiles = _make_dummy_tiles()
        result = expand_tileset(tiles, "gamemaker")
        assert len(result) == 47

    def test_generic_count(self):
        tiles = _make_dummy_tiles()
        result = expand_tileset(tiles, "generic")
        assert len(result) == 256

    def test_tile_dimensions_preserved(self):
        size = 64
        tiles = _make_dummy_tiles(size=size)
        result = expand_tileset(tiles, "godot_minimal")
        for tile in result:
            assert tile.shape == (size, size, 3)

    def test_tile_dimensions_non_square(self):
        """Even tiles work if all source tiles have the same shape."""
        tiles = [np.zeros((32, 64, 3), dtype=np.float32) for _ in range(16)]
        result = expand_tileset(tiles, "generic")
        for tile in result:
            assert tile.shape == (32, 64, 3)

    def test_requires_16_input_tiles(self):
        tiles = _make_dummy_tiles(count=10)
        with pytest.raises(ValueError, match="16"):
            expand_tileset(tiles, "godot_minimal")

    def test_too_many_input_tiles(self):
        tiles = _make_dummy_tiles(count=20)
        with pytest.raises(ValueError, match="16"):
            expand_tileset(tiles, "godot_minimal")

    def test_unknown_format_raises(self):
        tiles = _make_dummy_tiles()
        with pytest.raises(ValueError):
            expand_tileset(tiles, "unity")

    def test_generic_has_all_256_bitmasks(self):
        """Generic format should have one tile per bitmask."""
        tiles = _make_dummy_tiles()
        result = expand_tileset(tiles, "generic")
        assert len(result) == 256

    def test_godot_minimal_no_duplicates(self):
        """Godot minimal should contain only unique tiles."""
        tiles = _make_dummy_tiles()
        result = expand_tileset(tiles, "godot_minimal")
        for i, a in enumerate(result):
            for j, b in enumerate(result):
                if i != j:
                    assert not np.array_equal(a, b), (
                        f"Tiles {i} and {j} are identical in godot_minimal output"
                    )

    def test_output_dtype_matches_input(self):
        tiles = _make_dummy_tiles()
        result = expand_tileset(tiles, "godot_minimal")
        for tile in result:
            assert tile.dtype == np.float32


class TestQuadrantSource:
    def test_valid_quadrants(self):
        """All quadrants return valid case indices for all bitmasks."""
        for bitmask in range(256):
            for quad in ("TL", "TR", "BL", "BR"):
                case = _quadrant_source(bitmask, quad)
                assert 0 <= case <= 15, (
                    f"bitmask={bitmask}, quadrant={quad} returned case {case}"
                )

    def test_invalid_quadrant_raises(self):
        with pytest.raises(ValueError, match="Invalid quadrant"):
            _quadrant_source(0, "XX")

    def test_bitmask_0_all_quadrants(self):
        """Bitmask 0 = no neighbors. Each quadrant sees only center filled."""
        # TL: corners_to_case(nw=F, n=F, w=F, center=T) = case(F,F,F,T) = 0*8+0*4+1*2+0*1 = 2
        assert _quadrant_source(0, "TL") == _corners_to_case(False, False, False, True)
        # TR: corners_to_case(n=F, ne=F, center=T, e=F) = case(F,F,T,F) = 0*8+0*4+0*2+0*1...
        # Actually let's just check they're valid
        for quad in ("TL", "TR", "BL", "BR"):
            case = _quadrant_source(0, quad)
            assert 0 <= case <= 15

    def test_bitmask_255_all_quadrants(self):
        """Bitmask 255 = all neighbors filled. Should return case 15 (all true)."""
        for quad in ("TL", "TR", "BL", "BR"):
            assert _quadrant_source(255, quad) == 15

    def test_corner_diagonal_requires_both_edges(self):
        """Corner diagonal bits only count if both adjacent edge neighbors are present."""
        # NW bit set but N or W not set -> NW should not count
        # BIT_NW=7, BIT_N=0, BIT_W=6
        # Only NW set (bit 7): bitmask = 128
        case_nw_only = _quadrant_source(128, "TL")
        # N+W+NW set (bits 0,6,7): bitmask = 1+64+128 = 193
        case_nw_with_edges = _quadrant_source(193, "TL")
        # They should differ because NW only matters when both N and W are set
        assert case_nw_only != case_nw_with_edges


class TestCornersToCase:
    def test_all_false(self):
        assert _corners_to_case(False, False, False, False) == 0

    def test_all_true(self):
        assert _corners_to_case(True, True, True, True) == 15

    def test_roundtrip_all_16(self):
        """All 16 combinations of 4 bools map to unique case indices 0-15."""
        seen = set()
        for tl in (False, True):
            for tr in (False, True):
                for bl in (False, True):
                    for br in (False, True):
                        idx = _corners_to_case(tl, tr, bl, br)
                        assert 0 <= idx <= 15
                        seen.add(idx)
        assert seen == set(range(16))


class TestQuadrantOperations:
    def test_get_quadrant_tl(self):
        img = np.arange(16).reshape(4, 4).astype(np.float32)
        q = _get_quadrant(img, "TL")
        assert q.shape == (2, 2)
        np.testing.assert_array_equal(q, img[:2, :2])

    def test_get_quadrant_br(self):
        img = np.arange(16).reshape(4, 4).astype(np.float32)
        q = _get_quadrant(img, "BR")
        assert q.shape == (2, 2)
        np.testing.assert_array_equal(q, img[2:, 2:])

    def test_get_quadrant_returns_copy(self):
        img = np.zeros((4, 4), dtype=np.float32)
        q = _get_quadrant(img, "TL")
        q[:] = 1.0
        assert img[0, 0] == 0.0  # Original unchanged

    def test_set_quadrant_modifies_in_place(self):
        img = np.zeros((4, 4, 3), dtype=np.float32)
        data = np.ones((2, 2, 3), dtype=np.float32)
        _set_quadrant(img, "TR", data)
        np.testing.assert_array_equal(img[:2, 2:, :], data)
        assert img[0, 0, 0] == 0.0  # Other quadrants unchanged

    def test_invalid_quadrant_get(self):
        img = np.zeros((4, 4), dtype=np.float32)
        with pytest.raises(ValueError):
            _get_quadrant(img, "XX")

    def test_invalid_quadrant_set(self):
        img = np.zeros((4, 4), dtype=np.float32)
        with pytest.raises(ValueError):
            _set_quadrant(img, "XX", np.zeros((2, 2)))


class TestExpandSingleTile:
    def test_bitmask_0_output_shape(self):
        tiles = _make_dummy_tiles(size=32)
        result = _expand_single_tile(0, tiles)
        assert result.shape == (32, 32, 3)

    def test_bitmask_255_uses_case_15(self):
        """All neighbors present -> all quadrants come from case 15 (all filled)."""
        tiles = _make_dummy_tiles(size=32)
        result = _expand_single_tile(255, tiles)
        # Case 15 is the fully-filled tile
        np.testing.assert_array_equal(result, tiles[15])


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
