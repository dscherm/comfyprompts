"""Tile layout definitions and neighbor maps for the 16 marching squares cases."""

from dataclasses import dataclass


@dataclass(frozen=True)
class TileCorners:
    """Represents which corners of a tile are terrain A (True) vs terrain B (False).

    Corner layout:
        TL --- TR
        |       |
        BL --- BR
    """
    top_left: bool
    top_right: bool
    bottom_left: bool
    bottom_right: bool

    @property
    def case_index(self) -> int:
        """4-bit marching squares case: TL*8 + TR*4 + BR*2 + BL*1."""
        return (
            int(self.top_left) * 8
            + int(self.top_right) * 4
            + int(self.bottom_right) * 2
            + int(self.bottom_left) * 1
        )


# All 16 marching squares configurations, indexed by case number.
MARCHING_SQUARES_CASES: list[TileCorners] = [
    TileCorners(False, False, False, False),  # 0:  0000 - all empty
    TileCorners(False, False, True, False),   # 1:  0001 - BL filled
    TileCorners(False, False, False, True),   # 2:  0010 - BR filled
    TileCorners(False, False, True, True),    # 3:  0011 - bottom edge
    TileCorners(False, True, False, False),   # 4:  0100 - TR filled
    TileCorners(False, True, True, False),    # 5:  0101 - BL+TR diagonal
    TileCorners(False, True, False, True),    # 6:  0110 - right edge
    TileCorners(False, True, True, True),     # 7:  0111 - all except TL
    TileCorners(True, False, False, False),   # 8:  1000 - TL filled
    TileCorners(True, False, True, False),    # 9:  1001 - left edge
    TileCorners(True, False, False, True),    # 10: 1010 - TL+BR diagonal
    TileCorners(True, False, True, True),     # 11: 1011 - all except TR
    TileCorners(True, True, False, False),    # 12: 1100 - top edge
    TileCorners(True, True, True, False),     # 13: 1101 - all except BR
    TileCorners(True, True, False, True),     # 14: 1110 - all except BL
    TileCorners(True, True, True, True),      # 15: 1111 - all filled
]

# Standard 4x4 grid layout mapping (row, col) -> case index.
GRID_LAYOUT_4x4: dict[tuple[int, int], int] = {
    (r, c): r * 4 + c for r in range(4) for c in range(4)
}


def get_shared_edges(case_a: int, case_b: int, direction: str) -> bool:
    """Check whether two cases can be adjacent in the given direction.

    Args:
        case_a: Case index of the reference tile.
        case_b: Case index of the neighbor tile.
        direction: "up", "down", "left", or "right" - where case_b is
                   relative to case_a.

    Returns:
        True if the tiles' corners match at their shared edge.
    """
    a = MARCHING_SQUARES_CASES[case_a]
    b = MARCHING_SQUARES_CASES[case_b]

    if direction == "up":
        # B is above A: A's top edge must match B's bottom edge.
        return a.top_left == b.bottom_left and a.top_right == b.bottom_right
    elif direction == "down":
        # B is below A: A's bottom edge must match B's top edge.
        return a.bottom_left == b.top_left and a.bottom_right == b.top_right
    elif direction == "left":
        # B is left of A: A's left edge must match B's right edge.
        return a.top_left == b.top_right and a.bottom_left == b.bottom_right
    elif direction == "right":
        # B is right of A: A's right edge must match B's left edge.
        return a.top_right == b.top_left and a.bottom_right == b.bottom_left
    else:
        raise ValueError(f"Invalid direction: {direction}")


def _find_valid_neighbors(case_index: int, direction: str) -> list[int]:
    """Find all case indices that are valid neighbors in a given direction."""
    return [
        i for i in range(16)
        if get_shared_edges(case_index, i, direction)
    ]


# Direction offsets: (row_offset, col_offset) -> direction string
_DIRECTION_MAP: dict[tuple[int, int], str] = {
    (-1, 0): "up",
    (1, 0): "down",
    (0, -1): "left",
    (0, 1): "right",
}

# Diagonal positions need both adjacent edges to match
_DIAGONAL_MAP: dict[tuple[int, int], tuple[str, str]] = {
    (-1, -1): ("up", "left"),     # top-left
    (-1, 1): ("up", "right"),     # top-right
    (1, -1): ("down", "left"),    # bottom-left
    (1, 1): ("down", "right"),    # bottom-right
}


def get_3x3_neighbors(case_index: int) -> list[list[int]]:
    """Get valid 3x3 neighborhood tiles for a given case.

    Returns a 3x3 grid (list of 3 lists of 3 elements) where each element
    is a valid tile case index for that position. The center [1][1] is always
    the input case_index itself.

    For edge neighbors (up/down/left/right), a tile is valid if its corners
    match at the shared edge.

    For diagonal neighbors, a tile is valid if the single shared corner
    matches (the corner where all three tiles meet).
    """
    center = MARCHING_SQUARES_CASES[case_index]
    result: list[list[int]] = [[0] * 3 for _ in range(3)]
    result[1][1] = case_index

    # Precompute valid edge neighbors
    edge_valid: dict[tuple[int, int], list[int]] = {}
    for offset, direction in _DIRECTION_MAP.items():
        valid = _find_valid_neighbors(case_index, direction)
        edge_valid[offset] = valid
        # Pick first valid neighbor as default
        result[1 + offset[0]][1 + offset[1]] = valid[0] if valid else 0

    # Diagonal neighbors: shared corner must match
    corner_map = {
        (-1, -1): center.top_left,      # TL corner
        (-1, 1): center.top_right,       # TR corner
        (1, -1): center.bottom_left,     # BL corner
        (1, 1): center.bottom_right,     # BR corner
    }

    # For diagonal, the shared corner is the one closest to center tile
    diagonal_corner_attr = {
        (-1, -1): "bottom_right",  # Diagonal tile's BR = center's TL
        (-1, 1): "bottom_left",    # Diagonal tile's BL = center's TR
        (1, -1): "top_right",      # Diagonal tile's TR = center's BL
        (1, 1): "top_left",        # Diagonal tile's TL = center's BR
    }

    for offset in _DIAGONAL_MAP:
        corner_val = corner_map[offset]
        attr = diagonal_corner_attr[offset]
        # Find tiles whose corresponding corner matches
        valid = [
            i for i in range(16)
            if getattr(MARCHING_SQUARES_CASES[i], attr) == corner_val
        ]
        result[1 + offset[0]][1 + offset[1]] = valid[0] if valid else 0

    return result
