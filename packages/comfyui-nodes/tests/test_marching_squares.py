"""Tests for marching_squares.py tile layout definitions and neighbor maps."""
import pytest
import importlib.util
import os

# Load the module directly to avoid importing the package __init__.py
# which chains relative imports to all node files.
_mod_path = os.path.join(os.path.dirname(__file__), "..", "utils", "marching_squares.py")
_spec = importlib.util.spec_from_file_location("marching_squares", _mod_path)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)

TileCorners = _mod.TileCorners
MARCHING_SQUARES_CASES = _mod.MARCHING_SQUARES_CASES
GRID_LAYOUT_4x4 = _mod.GRID_LAYOUT_4x4
get_shared_edges = _mod.get_shared_edges
get_3x3_neighbors = _mod.get_3x3_neighbors


class TestTileCorners:
    def test_case_index_binary_encoding(self):
        """case_index uses TL*8 + TR*4 + BR*2 + BL*1"""
        tc = TileCorners(True, False, True, False)
        # TL=1*8 + TR=0*4 + BR=0*2 + BL=1*1 = 9
        assert tc.case_index == 9

    def test_case_index_all_false(self):
        assert TileCorners(False, False, False, False).case_index == 0

    def test_case_index_all_true(self):
        assert TileCorners(True, True, True, True).case_index == 15

    def test_frozen_dataclass(self):
        tc = TileCorners(True, False, False, True)
        with pytest.raises(AttributeError):
            tc.top_left = False


class TestMarchingSquaresCases:
    def test_16_cases_defined(self):
        assert len(MARCHING_SQUARES_CASES) == 16

    def test_case_index_roundtrip(self):
        """Each case's case_index matches its position in the list."""
        for i, case in enumerate(MARCHING_SQUARES_CASES):
            assert case.case_index == i, f"Case at index {i} has case_index {case.case_index}"

    def test_case_0_all_false(self):
        case = MARCHING_SQUARES_CASES[0]
        assert not case.top_left
        assert not case.top_right
        assert not case.bottom_left
        assert not case.bottom_right

    def test_case_15_all_true(self):
        case = MARCHING_SQUARES_CASES[15]
        assert case.top_left
        assert case.top_right
        assert case.bottom_left
        assert case.bottom_right

    def test_all_cases_unique(self):
        indices = [c.case_index for c in MARCHING_SQUARES_CASES]
        assert len(set(indices)) == 16

    def test_case_1_bl_only(self):
        case = MARCHING_SQUARES_CASES[1]
        assert case.bottom_left
        assert not case.top_left
        assert not case.top_right
        assert not case.bottom_right

    def test_case_4_tr_only(self):
        case = MARCHING_SQUARES_CASES[4]
        assert case.top_right
        assert not case.top_left
        assert not case.bottom_left
        assert not case.bottom_right

    def test_case_8_tl_only(self):
        case = MARCHING_SQUARES_CASES[8]
        assert case.top_left
        assert not case.top_right
        assert not case.bottom_left
        assert not case.bottom_right


class TestSharedEdges:
    def test_symmetric_left_right(self):
        """get_shared_edges(a, b, "right") == get_shared_edges(b, a, "left")"""
        for a in range(16):
            for b in range(16):
                assert get_shared_edges(a, b, "right") == get_shared_edges(b, a, "left"), (
                    f"Symmetry broken for cases {a}, {b} on right/left"
                )

    def test_symmetric_up_down(self):
        """get_shared_edges(a, b, "up") == get_shared_edges(b, a, "down")"""
        for a in range(16):
            for b in range(16):
                assert get_shared_edges(a, b, "up") == get_shared_edges(b, a, "down"), (
                    f"Symmetry broken for cases {a}, {b} on up/down"
                )

    def test_same_tile_always_compatible_horizontally(self):
        """A tile with matching left/right edges is compatible with itself."""
        for i in range(16):
            case = MARCHING_SQUARES_CASES[i]
            # Compatible with self horizontally if TL==TR and BL==BR
            if case.top_left == case.top_right and case.bottom_left == case.bottom_right:
                assert get_shared_edges(i, i, "right")

    def test_same_tile_always_compatible_vertically(self):
        """A tile with matching top/bottom edges is compatible with itself."""
        for i in range(16):
            case = MARCHING_SQUARES_CASES[i]
            # Compatible with self vertically if TL==BL and TR==BR
            if case.top_left == case.bottom_left and case.top_right == case.bottom_right:
                assert get_shared_edges(i, i, "down")

    def test_case_0_compatible_with_self_all_directions(self):
        """All-empty is compatible with itself in every direction."""
        for d in ("up", "down", "left", "right"):
            assert get_shared_edges(0, 0, d)

    def test_case_15_compatible_with_self_all_directions(self):
        """All-filled is compatible with itself in every direction."""
        for d in ("up", "down", "left", "right"):
            assert get_shared_edges(15, 15, d)

    def test_invalid_direction_raises(self):
        with pytest.raises(ValueError):
            get_shared_edges(0, 0, "diagonal")

    def test_known_incompatible_pair(self):
        """Case 0 (all empty) right of case 15 (all filled) should fail."""
        # Case 15: TR=True, BR=True. Case 0: TL=False, BL=False.
        # For "right": a.top_right == b.top_left and a.bottom_right == b.bottom_left
        # Case 15 right, Case 0: True==False? No.
        assert not get_shared_edges(15, 0, "right")

    def test_known_compatible_pair(self):
        """Case 12 (top edge) above case 3 (bottom edge) should work."""
        # Case 12: TL=True, TR=True, BL=False, BR=False
        # Case 3: TL=False, TR=False, BL=True, BR=True
        # "down": a.bottom_left == b.top_left and a.bottom_right == b.top_right
        # Case 12 down Case 3: BL=False==TL=False, BR=False==TR=False -> True
        assert get_shared_edges(12, 3, "down")

    def test_every_tile_has_at_least_one_right_neighbor(self):
        """Each case has at least one valid tile to its right."""
        for i in range(16):
            has_any = any(get_shared_edges(i, j, "right") for j in range(16))
            assert has_any, f"Case {i} has no valid right neighbor"


class TestGet3x3Neighbors:
    def test_returns_3x3_grid(self):
        for case_idx in range(16):
            result = get_3x3_neighbors(case_idx)
            assert len(result) == 3
            for row in result:
                assert len(row) == 3

    def test_center_is_self(self):
        for case_idx in range(16):
            result = get_3x3_neighbors(case_idx)
            assert result[1][1] == case_idx

    def test_all_values_in_range(self):
        for case_idx in range(16):
            result = get_3x3_neighbors(case_idx)
            for row in result:
                for val in row:
                    assert 0 <= val <= 15, f"Neighbor {val} out of range for case {case_idx}"

    def test_edge_neighbors_are_compatible(self):
        """Edge neighbors (up/down/left/right) must share matching edges."""
        for case_idx in range(16):
            grid = get_3x3_neighbors(case_idx)
            # Up neighbor: grid[0][1]
            assert get_shared_edges(case_idx, grid[0][1], "up"), (
                f"Case {case_idx}: up neighbor {grid[0][1]} doesn't match"
            )
            # Down neighbor: grid[2][1]
            assert get_shared_edges(case_idx, grid[2][1], "down"), (
                f"Case {case_idx}: down neighbor {grid[2][1]} doesn't match"
            )
            # Left neighbor: grid[1][0]
            assert get_shared_edges(case_idx, grid[1][0], "left"), (
                f"Case {case_idx}: left neighbor {grid[1][0]} doesn't match"
            )
            # Right neighbor: grid[1][2]
            assert get_shared_edges(case_idx, grid[1][2], "right"), (
                f"Case {case_idx}: right neighbor {grid[1][2]} doesn't match"
            )


class TestGridLayout:
    def test_covers_all_16_cases(self):
        """GRID_LAYOUT_4x4 contains all 16 case indices."""
        cases_in_grid = set(GRID_LAYOUT_4x4.values())
        assert cases_in_grid == set(range(16))

    def test_has_16_entries(self):
        assert len(GRID_LAYOUT_4x4) == 16

    def test_keys_are_4x4_coordinates(self):
        expected_keys = {(r, c) for r in range(4) for c in range(4)}
        assert set(GRID_LAYOUT_4x4.keys()) == expected_keys

    def test_sequential_layout(self):
        """Default layout is row * 4 + col."""
        for r in range(4):
            for c in range(4):
                assert GRID_LAYOUT_4x4[(r, c)] == r * 4 + c


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
