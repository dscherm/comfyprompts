"""Bitmask autotile expansion - port of webtyler algorithm.

Expands 16 marching squares tiles into full autotile sets (47 or 256 tiles)
by compositing quadrants based on 8-bit neighbor bitmasks.
"""

import numpy as np

# Neighbor bitmask bit positions (standard convention)
BIT_N = 0
BIT_NE = 1
BIT_E = 2
BIT_SE = 3
BIT_S = 4
BIT_SW = 5
BIT_W = 6
BIT_NW = 7


def _has_bit(bitmask: int, bit: int) -> bool:
    return bool(bitmask & (1 << bit))


def _corners_to_case(tl: bool, tr: bool, bl: bool, br: bool) -> int:
    """Map corner fill states to marching squares case index (0-15)."""
    return int(tl) * 8 + int(tr) * 4 + int(br) * 2 + int(bl) * 1


def _quadrant_source(bitmask: int, quadrant: str) -> int:
    """Determine which marching squares source tile a quadrant comes from.

    Args:
        bitmask: 8-bit neighbor bitmask.
        quadrant: One of "TL", "TR", "BL", "BR".

    Returns:
        Marching squares case index (0-15) of the source tile.
    """
    n = _has_bit(bitmask, BIT_N)
    ne = _has_bit(bitmask, BIT_NE)
    e = _has_bit(bitmask, BIT_E)
    se = _has_bit(bitmask, BIT_SE)
    s = _has_bit(bitmask, BIT_S)
    sw = _has_bit(bitmask, BIT_SW)
    w = _has_bit(bitmask, BIT_W)
    nw = _has_bit(bitmask, BIT_NW)

    # The center tile is always terrain A (filled).
    # Each quadrant's appearance depends on 3 neighbors.
    # Corner diagonal only matters if BOTH adjacent edge neighbors are filled.

    if quadrant == "TL":
        # Depends on N, NW, W
        has_n = n
        has_w = w
        has_nw = nw and n and w  # Corner only counts if both edges present
        return _corners_to_case(tl=has_nw, tr=has_n, bl=has_w, br=True)
    elif quadrant == "TR":
        # Depends on N, NE, E
        has_n = n
        has_e = e
        has_ne = ne and n and e
        return _corners_to_case(tl=has_n, tr=has_ne, bl=True, br=has_e)
    elif quadrant == "BL":
        # Depends on S, SW, W
        has_s = s
        has_w = w
        has_sw = sw and s and w
        return _corners_to_case(tl=has_w, tr=True, bl=has_sw, br=has_s)
    elif quadrant == "BR":
        # Depends on S, SE, E
        has_s = s
        has_e = e
        has_se = se and s and e
        return _corners_to_case(tl=True, tr=has_e, bl=has_s, br=has_se)
    else:
        raise ValueError(f"Invalid quadrant: {quadrant}")


def _get_quadrant(image: np.ndarray, quadrant: str) -> np.ndarray:
    """Extract a quadrant from a tile image.

    Args:
        image: Tile image array [H, W, C] or [H, W].
        quadrant: "TL", "TR", "BL", or "BR".
    """
    h, w = image.shape[:2]
    mid_h, mid_w = h // 2, w // 2

    if quadrant == "TL":
        return image[:mid_h, :mid_w].copy()
    elif quadrant == "TR":
        return image[:mid_h, mid_w:].copy()
    elif quadrant == "BL":
        return image[mid_h:, :mid_w].copy()
    elif quadrant == "BR":
        return image[mid_h:, mid_w:].copy()
    else:
        raise ValueError(f"Invalid quadrant: {quadrant}")


def _set_quadrant(image: np.ndarray, quadrant: str, data: np.ndarray):
    """Place quadrant data into a tile image (in-place).

    Args:
        image: Target tile image [H, W, C] or [H, W].
        quadrant: "TL", "TR", "BL", or "BR".
        data: Quadrant data to place.
    """
    h, w = image.shape[:2]
    mid_h, mid_w = h // 2, w // 2

    if quadrant == "TL":
        image[:mid_h, :mid_w] = data
    elif quadrant == "TR":
        image[:mid_h, mid_w:] = data
    elif quadrant == "BL":
        image[mid_h:, :mid_w] = data
    elif quadrant == "BR":
        image[mid_h:, mid_w:] = data
    else:
        raise ValueError(f"Invalid quadrant: {quadrant}")


def _expand_single_tile(bitmask: int, source_tiles: list[np.ndarray]) -> np.ndarray:
    """Create one expanded tile by compositing quadrants from source tiles.

    Args:
        bitmask: 8-bit neighbor bitmask.
        source_tiles: List of 16 marching squares source tile images.

    Returns:
        Composited tile image.
    """
    h, w = source_tiles[0].shape[:2]
    output = np.zeros_like(source_tiles[0])

    for quadrant in ("TL", "TR", "BL", "BR"):
        src_case = _quadrant_source(bitmask, quadrant)
        quad_data = _get_quadrant(source_tiles[src_case], quadrant)
        _set_quadrant(output, quadrant, quad_data)

    return output


def _deduplicate(tiles: list[np.ndarray]) -> list[np.ndarray]:
    """Remove duplicate tiles, keeping order of first occurrence."""
    seen = []
    unique = []
    for tile in tiles:
        is_dup = False
        for s in seen:
            if np.array_equal(tile, s):
                is_dup = True
                break
        if not is_dup:
            seen.append(tile)
            unique.append(tile)
    return unique


def get_tile_count(output_format: str) -> int:
    """Return expected tile count for a given output format."""
    counts = {
        "godot_minimal": 47,
        "godot_full": 256,
        "rpgmaker": 48,
        "gamemaker": 47,
        "generic": 256,
    }
    if output_format not in counts:
        raise ValueError(
            f"Unknown format: {output_format}. "
            f"Valid formats: {list(counts.keys())}"
        )
    return counts[output_format]


def expand_tileset(
    source_tiles: list[np.ndarray],
    output_format: str = "godot_minimal",
) -> list[np.ndarray]:
    """Expand 16 marching squares tiles into a full autotile set.

    Args:
        source_tiles: List of 16 tile images as numpy arrays [H, W, C].
        output_format: Target format - "godot_minimal" (47), "godot_full" (256),
                       "rpgmaker" (48), "gamemaker" (47), or "generic" (256).

    Returns:
        List of expanded tile images.
    """
    if len(source_tiles) != 16:
        raise ValueError(f"Expected 16 source tiles, got {len(source_tiles)}")

    # Generate all 256 bitmask variations
    all_tiles = []
    for bitmask in range(256):
        all_tiles.append(_expand_single_tile(bitmask, source_tiles))

    if output_format == "generic" or output_format == "godot_full":
        return all_tiles

    if output_format in ("godot_minimal", "gamemaker"):
        return _deduplicate(all_tiles)

    if output_format == "rpgmaker":
        # RPG Maker uses a specific 48-tile subset
        # Standard RPG Maker VX/MV autotile indices
        rpgmaker_bitmasks = [
            0, 1, 4, 5, 16, 17, 20, 21,
            64, 65, 68, 69, 80, 81, 84, 85,
            2, 3, 6, 7, 18, 19, 22, 23,
            66, 67, 70, 71, 82, 83, 86, 87,
            8, 9, 12, 13, 24, 25, 28, 29,
            72, 73, 76, 77, 88, 89, 92, 93,
        ]
        return [all_tiles[b] for b in rpgmaker_bitmasks]

    raise ValueError(f"Unknown format: {output_format}")
