"""kit_tiles — shared grid-modular ground, path, and road tiles for GrimForge kits.

Every tile is a 1x1 unit footprint with its surface at z=0 (slab hanging below),
so tiles snap seamlessly on the square grid and butt cleanly against building
base courses. Builders are spec-native (``fn(kit) -> obj``), so any kit spec can
splice ``ALL_TILES`` (or the ``GROUND_TILES`` / ``PATH_TILES`` / ``ROAD_TILES``
subsets) straight into its ``PIECES`` list.

Surface materials lean on the atlas patterns in kitlib: ``cobble`` -> domed
setts, ``gravel`` -> speckle, ``stone``/``stone_dk`` -> masonry flagstones,
``dirt``/``grass``/``moss`` -> plain gradient. Directional path/road tiles are
authored pointing along ±Y (rotate on the grid to orient).
"""

from __future__ import annotations

from typing import Any


def _slab(k: Any, P: list, color: str, h: float = 0.1) -> None:
    """A 1x1 ground slab of thickness ``h`` with its top face at z=0."""
    k.box(P, 1.0, 1.0, h, (0, 0, -h / 2), color)


# --------------------------------------------------------------------------- #
# Ground fills
# --------------------------------------------------------------------------- #

def ground_cobble(k: Any) -> Any:
    """A full cobblestone tile — reads as domed setts via the atlas."""
    P: list = []
    _slab(k, P, "cobble", 0.1)
    for x, y in ((-0.28, 0.18), (0.24, -0.22), (0.06, 0.31), (-0.12, -0.3)):
        k.box(P, 0.15, 0.15, 0.03, (x, y, 0.015), "cobble")   # a few proud setts
    return k.join(P, "ground_cobble")


def ground_flagstone(k: Any) -> Any:
    """A stone-flagged floor tile — masonry pattern reads as flagstones."""
    P: list = []
    _slab(k, P, "stone_dk", 0.1)
    for x, y, s in ((-0.24, -0.2, 0.42), (0.22, 0.2, 0.44), (0.05, -0.05, 0.32)):
        k.box(P, s, s, 0.03, (x, y, 0.015), "stone")          # raised slabs
    return k.join(P, "ground_flagstone")


def ground_gravel(k: Any) -> Any:
    """A gravel tile — speckle pattern with a scatter of pebbles."""
    P: list = []
    _slab(k, P, "gravel", 0.1)
    for x, y, r in ((-0.26, 0.2, 0.06), (0.2, -0.16, 0.05),
                    (0.1, 0.28, 0.045), (-0.08, -0.28, 0.05)):
        k.ico(P, r, (x, y, 0.03), "stone_dk")
    return k.join(P, "ground_gravel")


def ground_moss(k: Any) -> Any:
    """A mossy flagstone tile — stone with green moss clumps."""
    P: list = []
    _slab(k, P, "stone_dk", 0.1)
    for x, y, s in ((-0.2, 0.16, 0.5), (0.26, -0.2, 0.34)):
        k.box(P, s, s, 0.03, (x, y, 0.015), "stone")
    for x, y, r in ((-0.16, -0.14, 0.09), (0.18, 0.22, 0.08), (0.3, 0.0, 0.06)):
        k.ico(P, r, (x, y, 0.04), "moss")
    return k.join(P, "ground_moss")


def ground_mud(k: Any) -> Any:
    """A muddy dirt tile with dark puddles."""
    P: list = []
    _slab(k, P, "dirt", 0.1)
    k.cyl(P, 10, 0.3, 0.02, (0.06, -0.04, 0.006), "soot")     # big puddle
    k.cyl(P, 8, 0.16, 0.015, (-0.24, 0.22, 0.006), "soot")    # small puddle
    return k.join(P, "ground_mud")


# --------------------------------------------------------------------------- #
# Dirt paths (cobble-strip through dirt) — junction set (through-axis = Y)
# --------------------------------------------------------------------------- #

def path_cross(k: Any) -> Any:
    """A 4-way dirt-path crossing with a cobble strip both ways."""
    P: list = []
    _slab(k, P, "dirt", 0.08)
    k.box(P, 0.44, 1.0, 0.05, (0, 0, 0.0), "cobble")          # N-S strip
    k.box(P, 1.0, 0.44, 0.05, (0, 0, 0.0), "cobble")          # E-W strip
    return k.join(P, "path_cross")


def path_tee(k: Any) -> Any:
    """A T-junction dirt path (through E-W, stem to -Y)."""
    P: list = []
    _slab(k, P, "dirt", 0.08)
    k.box(P, 1.0, 0.44, 0.05, (0, 0, 0.0), "cobble")          # through E-W
    k.box(P, 0.44, 0.5, 0.05, (0, -0.25, 0.0), "cobble")      # stem to -Y
    return k.join(P, "path_tee")


def path_end(k: Any) -> Any:
    """A dirt path that terminates (stub from +Y edge, rounded cap)."""
    P: list = []
    _slab(k, P, "dirt", 0.08)
    k.box(P, 0.44, 0.6, 0.05, (0, 0.2, 0.0), "cobble")        # stub from +Y edge
    k.cyl(P, 12, 0.22, 0.05, (0, -0.1, 0.0), "cobble")        # rounded cap
    return k.join(P, "path_end")


# --------------------------------------------------------------------------- #
# Cobblestone roads (wide cobble strip + kerb stones on dirt verges)
# --------------------------------------------------------------------------- #

def road_straight(k: Any) -> Any:
    """A cobblestone road tile running N-S with kerb stones."""
    P: list = []
    _slab(k, P, "dirt", 0.08)
    k.box(P, 0.7, 1.0, 0.05, (0, 0, 0.0), "cobble")           # road N-S
    for s in (-1, 1):
        k.box(P, 0.06, 1.0, 0.07, (s * 0.37, 0, 0.01), "stone_dk")  # kerbs
    return k.join(P, "road_straight")


def road_corner(k: Any) -> Any:
    """An L-bend cobblestone road (from -Y edge to +X edge)."""
    P: list = []
    _slab(k, P, "dirt", 0.08)
    k.box(P, 0.7, 0.65, 0.05, (0, -0.175, 0.0), "cobble")     # leg from -Y
    k.box(P, 0.65, 0.7, 0.05, (0.175, 0, 0.0), "cobble")      # leg to +X
    k.box(P, 0.06, 0.6, 0.07, (-0.37, -0.15, 0.01), "stone_dk")   # outer kerb (W)
    k.box(P, 0.6, 0.06, 0.07, (0.15, 0.37, 0.01), "stone_dk")     # outer kerb (N)
    return k.join(P, "road_corner")


def road_cross(k: Any) -> Any:
    """A 4-way cobblestone road crossing."""
    P: list = []
    _slab(k, P, "dirt", 0.08)
    k.box(P, 0.7, 1.0, 0.05, (0, 0, 0.0), "cobble")           # N-S
    k.box(P, 1.0, 0.7, 0.05, (0, 0, 0.0), "cobble")           # E-W
    for cx, cy in ((0.42, 0.42), (-0.42, 0.42), (0.42, -0.42), (-0.42, -0.42)):
        k.box(P, 0.14, 0.14, 0.07, (cx, cy, 0.01), "stone_dk")  # corner kerb blocks
    return k.join(P, "road_cross")


def road_tee(k: Any) -> Any:
    """A T-junction cobblestone road (through E-W, branch to -Y)."""
    P: list = []
    _slab(k, P, "dirt", 0.08)
    k.box(P, 1.0, 0.7, 0.05, (0, 0, 0.0), "cobble")           # through E-W
    k.box(P, 0.7, 0.5, 0.05, (0, -0.25, 0.0), "cobble")       # branch -Y
    for cx in (-0.42, 0.42):
        k.box(P, 0.14, 0.14, 0.07, (cx, 0.42, 0.01), "stone_dk")  # top corner kerbs
    return k.join(P, "road_tee")


GROUND_TILES = [
    ("ground_cobble", ground_cobble),
    ("ground_flagstone", ground_flagstone),
    ("ground_gravel", ground_gravel),
    ("ground_moss", ground_moss),
    ("ground_mud", ground_mud),
]
PATH_TILES = [
    ("path_cross", path_cross),
    ("path_tee", path_tee),
    ("path_end", path_end),
]
ROAD_TILES = [
    ("road_straight", road_straight),
    ("road_corner", road_corner),
    ("road_cross", road_cross),
    ("road_tee", road_tee),
]
#: Full shared tile set — splice into a kit's PIECES for grid-modular terrain.
ALL_TILES = GROUND_TILES + PATH_TILES + ROAD_TILES

__all__ = ["GROUND_TILES", "PATH_TILES", "ROAD_TILES", "ALL_TILES"]
