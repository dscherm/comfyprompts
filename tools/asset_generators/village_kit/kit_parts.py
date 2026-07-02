"""kit_parts — shared modular BUILDING parts for GrimForge kits (KayKit-style).

Snap-together components on a 1-unit grid so a whole village can be assembled
from a small vocabulary of parts (the main lever toward 200+ pieces). Every part
is authored in a canonical cell and orientation; place/rotate on the grid to build.

Conventions
-----------
* Cell size = ``CELL`` (1.0). Wall thickness = ``WT`` (0.16).
* **Walls** are 1 wide along X, 1.0 tall, centred on the origin with the face
  plane at y=0 (spans y in [-WT/2, WT/2]); base at z=0. Rotate 0/90/180/270 to
  wrap a cell. They carry a base course + top cornice (KayKit trim).
* **Floors / foundations** are 1x1 with the top face at z=0, so walls sit on them.
* **Roofs** sit from z=1.0 up.
* Openings (door / window) are cut by construction (jambs + sill + lintel) and a
  matching insert part (``door`` / ``window``) drops into the hole.

Builders are spec-native ``fn(kit) -> obj`` so a kit spec can splice ``ALL_PARTS``
(or a family subset) into its ``PIECES`` list.
"""

from __future__ import annotations

import math
from typing import Any

CELL = 1.0
WT = 0.16    # wall thickness


# --------------------------------------------------------------------------- #
# Trim helpers (base course / cornice / opening frame)
# --------------------------------------------------------------------------- #

def _base_course(k: Any, P: list, w: float = CELL, color: str = "stone_dk") -> None:
    k.box(P, w + 0.04, WT + 0.05, 0.12, (0, 0, 0.06), color)      # plinth


def _cornice(k: Any, P: list, w: float = CELL, color: str = "stone_dk") -> None:
    k.box(P, w + 0.04, WT + 0.05, 0.08, (0, 0, 0.96), color)      # top course


def _timber_frame(k: Any, P: list) -> None:
    """Tudor corner posts + top/bottom rails + a brace, on a plaster panel."""
    for x in (-0.44, 0.44):
        k.box(P, 0.08, WT + 0.02, 1.0, (x, 0, 0.5), "beam")
    k.box(P, CELL, WT + 0.02, 0.08, (0, 0, 0.08), "beam")
    k.box(P, CELL, WT + 0.02, 0.08, (0, 0, 0.94), "beam")
    for s in (-1, 1):                                             # braces
        k.box(P, 0.07, WT + 0.02, 0.55, (s * 0.24, 0, 0.42),
              "beam", rot=(0, math.radians(s * 34), 0))


# --------------------------------------------------------------------------- #
# Walls
# --------------------------------------------------------------------------- #

def wall(k: Any) -> Any:
    """Plain stone wall panel."""
    P: list = []
    k.box(P, CELL, WT, 1.0, (0, 0, 0.5), "stone")
    _base_course(k, P)
    _cornice(k, P)
    return k.join(P, "wall")


def wall_plaster(k: Any) -> Any:
    """Half-timbered plaster wall panel."""
    P: list = []
    k.box(P, CELL, WT, 1.0, (0, 0, 0.5), "plaster")
    _timber_frame(k, P)
    _base_course(k, P)
    return k.join(P, "wall_plaster")


def wall_wood(k: Any) -> Any:
    """Board wall panel (barns / sheds)."""
    P: list = []
    k.box(P, CELL, WT, 1.0, (0, 0, 0.5), "wood")
    for x in (-0.33, 0.0, 0.33):
        k.box(P, 0.06, WT + 0.02, 1.0, (x, 0, 0.5), "wood_dk")    # batten boards
    _base_course(k, P, color="wood_dk")
    return k.join(P, "wall_wood")


def wall_window(k: Any) -> Any:
    """Stone wall with a framed, glazed window opening."""
    P: list = []
    k.box(P, CELL, WT, 0.32, (0, 0, 0.16), "stone")              # sill wall
    k.box(P, CELL, WT, 0.26, (0, 0, 0.87), "stone")              # head wall
    for x in (-0.37, 0.37):
        k.box(P, 0.26, WT, 0.42, (x, 0, 0.53), "stone")          # jambs
    _base_course(k, P)
    _cornice(k, P)
    k.box(P, 0.5, 0.06, 0.42, (0, 0, 0.53), "gem")               # glazing
    for x in (-0.24, 0.24):
        k.box(P, 0.05, 0.1, 0.46, (x, 0, 0.53), "wood_dk")       # frame jambs
    k.box(P, 0.54, 0.1, 0.05, (0, 0, 0.32), "wood_dk")           # sill
    k.box(P, 0.54, 0.1, 0.05, (0, 0, 0.74), "wood_dk")           # head
    k.box(P, 0.05, 0.1, 0.42, (0, 0, 0.53), "wood_dk")           # mullion
    return k.join(P, "wall_window")


def wall_door(k: Any) -> Any:
    """Stone wall with a framed door opening (drop a ``door`` in)."""
    P: list = []
    for x in (-0.37, 0.37):
        k.box(P, 0.26, WT, 1.0, (x, 0, 0.5), "stone")            # side walls
    k.box(P, CELL, WT, 0.22, (0, 0, 0.89), "stone")              # lintel wall
    _base_course(k, P)
    _cornice(k, P)
    for x in (-0.27, 0.27):
        k.box(P, 0.05, 0.12, 0.8, (x, 0, 0.4), "wood_dk")        # door frame jambs
    k.box(P, 0.62, 0.12, 0.06, (0, 0, 0.79), "wood_dk")          # frame head
    return k.join(P, "wall_door")


def wall_half(k: Any) -> Any:
    """Half-height stone wall (yard walls, parapets)."""
    P: list = []
    k.box(P, CELL, WT, 0.5, (0, 0, 0.25), "stone")
    _base_course(k, P)
    k.box(P, CELL + 0.04, WT + 0.06, 0.06, (0, 0, 0.5), "stone_dk")  # capstone
    return k.join(P, "wall_half")


def wall_corner(k: Any) -> Any:
    """Quoined corner post joining two wall runs (L)."""
    P: list = []
    k.box(P, WT, WT, 1.0, (0, 0, 0.5), "stone")
    for z in (0.2, 0.4, 0.6, 0.8):                               # quoin stones
        dx = 0.02 if (int(z * 10) % 2) else -0.02
        k.box(P, WT + 0.06, WT + 0.06, 0.1, (dx, dx, z), "stone_dk")
    return k.join(P, "wall_corner")


# --------------------------------------------------------------------------- #
# Floors / foundations
# --------------------------------------------------------------------------- #

def floor(k: Any) -> Any:
    """Plank floor tile, top face at z=0."""
    P: list = []
    k.box(P, CELL, CELL, 0.1, (0, 0, -0.05), "wood")
    for x in (-0.34, 0.0, 0.34):
        k.box(P, 0.02, CELL, 0.02, (x, 0, 0.005), "wood_dk")     # plank gaps
    return k.join(P, "floor")


def foundation(k: Any) -> Any:
    """Stone foundation block, top face at z=0."""
    P: list = []
    k.box(P, CELL, CELL, 0.3, (0, 0, -0.15), "stone")
    k.box(P, CELL + 0.04, CELL + 0.04, 0.08, (0, 0, -0.04), "stone_dk")  # top course
    return k.join(P, "foundation")


# --------------------------------------------------------------------------- #
# Roofs
# --------------------------------------------------------------------------- #

def roof_gable(k: Any) -> Any:
    """A full A-frame roof unit (both slopes), sitting from z=1.0."""
    P: list = []
    k.gable(P, CELL, CELL, 0.62, (0, 0, 1.0), "slate", over=0.18)
    sw = (CELL + 0.18) / 2
    theta = math.atan2(0.62, sw)
    for f in (0.28, 0.6):                                        # shingle-course battens
        for sgn in (-1, 1):
            k.box(P, 0.03, CELL + 0.2, 0.05, (sgn * sw * (1 - f), 0, 1.0 + 0.62 * f),
                  "wood_dk", rot=(0, sgn * theta, 0))
    k.box(P, 0.08, CELL + 0.24, 0.08, (0, 0, 1.64), "wood_dk")   # ridge board
    return k.join(P, "roof_gable")


def roof_slope(k: Any) -> Any:
    """A single pitched roof panel (lean-to / half roof)."""
    P: list = []
    ang = math.radians(36)
    k.box(P, CELL + 0.06, 1.28, 0.1, (0, 0.0, 1.42), "slate", rot=(ang, 0, 0))
    k.box(P, CELL + 0.1, 0.1, 0.1, (0, -0.5, 1.02), "wood_dk")   # eave board
    return k.join(P, "roof_slope")


def roof_flat(k: Any) -> Any:
    """A flat roof section with a low parapet."""
    P: list = []
    k.box(P, CELL, CELL, 0.12, (0, 0, 1.06), "stone_dk")
    for sy in (-1, 1):
        k.box(P, CELL, 0.1, 0.2, (0, sy * 0.45, 1.2), "stone")   # parapet front/back
        k.box(P, 0.1, CELL, 0.2, (sy * 0.45, 0, 1.2), "stone")   # parapet sides
    return k.join(P, "roof_flat")


def chimney(k: Any) -> Any:
    """A stone chimney stack with a cap."""
    P: list = []
    k.box(P, 0.32, 0.32, 1.1, (0, 0, 0.55), "stone")
    for cz in (0.3, 0.6, 0.9):
        k.box(P, 0.36, 0.36, 0.05, (0, 0, cz), "stone_dk")
    k.box(P, 0.4, 0.4, 0.1, (0, 0, 1.12), "stone_dk")            # cap
    for dx, dy in ((-0.09, -0.09), (0.09, -0.09), (-0.09, 0.09), (0.09, 0.09)):
        k.box(P, 0.1, 0.1, 0.12, (dx, dy, 1.22), "charwood")     # flue pots
    return k.join(P, "chimney")


# --------------------------------------------------------------------------- #
# Openings & inserts
# --------------------------------------------------------------------------- #

def door(k: Any) -> Any:
    """A plank door leaf (fits the ``wall_door`` opening)."""
    P: list = []
    k.box(P, 0.5, 0.08, 0.78, (0, 0, 0.39), "wood_dk")
    for x in (-0.15, 0.15):
        k.box(P, 0.12, 0.09, 0.74, (x, 0, 0.39), "wood")         # planks
    for z in (0.16, 0.62):
        k.box(P, 0.5, 0.09, 0.06, (0, 0, z), "wood")             # ledges
    k.cyl(P, 8, 0.03, 0.05, (0.17, -0.07, 0.4), "iron", rot=(math.radians(90), 0, 0))  # ring
    for hz in (0.2, 0.58):
        k.box(P, 0.06, 0.03, 0.05, (-0.22, -0.06, hz), "iron")   # hinges
    return k.join(P, "door")


def door_arch(k: Any) -> Any:
    """An arched double door in a stone surround."""
    P: list = []
    for x in (-0.34, 0.34):
        k.box(P, 0.12, 0.16, 1.0, (x, 0, 0.5), "stone")          # arch jambs
    for i in range(7):                                           # voussoir arch
        a = math.radians(20 + i * 23)
        k.box(P, 0.16, 0.16, 0.16, (math.cos(a) * 0.36, 0, 0.95 + math.sin(a) * 0.36),
              "stone_dk", rot=(0, 0, a - math.radians(90)))
    for s in (-1, 1):
        k.box(P, 0.26, 0.07, 0.9, (s * 0.14, 0, 0.45), "wood_dk")  # door leaves
        k.box(P, 0.03, 0.08, 0.86, (s * 0.02, 0, 0.45), "iron")    # centre straps
    return k.join(P, "door_arch")


def window(k: Any) -> Any:
    """A framed, shuttered window insert."""
    P: list = []
    k.box(P, 0.5, 0.06, 0.5, (0, 0, 0.25), "gem")                # glazing
    for x in (-0.27, 0.27):
        k.box(P, 0.06, 0.1, 0.56, (x, 0, 0.25), "wood_dk")       # frame
    for z in (0.0, 0.5):
        k.box(P, 0.6, 0.1, 0.06, (0, 0, z), "wood_dk")
    k.box(P, 0.05, 0.1, 0.5, (0, 0, 0.25), "wood_dk")            # mullion
    for s in (-1, 1):                                            # open shutters
        k.box(P, 0.22, 0.05, 0.52, (s * 0.42, -0.03, 0.25), "wood",
              rot=(0, math.radians(s * -30), 0))
    return k.join(P, "window")


# --------------------------------------------------------------------------- #
# Structure / trim
# --------------------------------------------------------------------------- #

def pillar(k: Any) -> Any:
    """A square stone pillar with base + capital."""
    P: list = []
    k.box(P, 0.26, 0.26, 1.0, (0, 0, 0.5), "stone")
    for z in (0.05, 0.95):
        k.box(P, 0.36, 0.36, 0.1, (0, 0, z), "stone_dk")         # base / capital
    return k.join(P, "pillar")


def post_beam(k: Any) -> Any:
    """A timber post carrying a cross-beam (frame bay)."""
    P: list = []
    for x in (-0.42, 0.42):
        k.box(P, 0.14, 0.14, 1.0, (x, 0, 0.5), "wood")           # posts
        br = math.radians(-40 if x > 0 else 40)
        k.box(P, 0.2, 0.14, 0.1, (x, 0, 0.9), "wood_dk", rot=(0, br, 0))  # bracket
    k.box(P, CELL + 0.1, 0.16, 0.16, (0, 0, 0.92), "wood_dk")    # beam
    return k.join(P, "post_beam")


def arch(k: Any) -> Any:
    """A free-standing stone archway."""
    P: list = []
    for x in (-0.42, 0.42):
        k.box(P, 0.22, 0.3, 1.0, (x, 0, 0.5), "stone")           # piers
    for i in range(9):                                           # voussoirs
        a = math.radians(10 + i * 20)
        k.box(P, 0.2, 0.3, 0.2, (math.cos(a) * 0.44, 0, 0.98 + math.sin(a) * 0.44),
              "stone", rot=(0, 0, a - math.radians(90)))
    k.box(P, 0.16, 0.3, 0.16, (0, 0, 1.44), "stone_dk")          # keystone
    return k.join(P, "arch")


def stairs(k: Any) -> Any:
    """A stone staircase (five steps up +Y)."""
    P: list = []
    for i in range(5):
        k.box(P, CELL, 0.2, 0.2 * (i + 1), (0, -0.4 + i * 0.2, 0.1 * (i + 1)), "stone")
    for sx in (-1, 1):
        k.box(P, 0.08, 1.0, 0.1, (sx * 0.46, 0.1, 0.62), "stone_dk",
              rot=(math.radians(45), 0, 0))                        # ramp rail
    return k.join(P, "stairs")


def railing(k: Any) -> Any:
    """A baluster railing segment."""
    P: list = []
    for x in (-0.42, 0.42):
        k.box(P, 0.08, 0.08, 0.5, (x, 0, 0.25), "wood")          # end posts
    for x in (-0.2, 0.0, 0.2):
        k.cyl(P, 6, 0.03, 0.42, (x, 0, 0.23), "wood_dk")         # balusters
    k.box(P, CELL, 0.1, 0.06, (0, 0, 0.47), "wood")              # handrail
    k.box(P, CELL, 0.08, 0.05, (0, 0, 0.05), "wood")             # bottom rail
    return k.join(P, "railing")


# --------------------------------------------------------------------------- #
# Demo assembly — proves the parts snap together into a building
# --------------------------------------------------------------------------- #

def _house_roof(k: Any) -> Any:
    """A gable roof spanning the 2x2 demo house (ridge along Y) + a small chimney
    poking through the slope. Built inline so it sizes to the whole footprint."""
    P: list = []
    span = 2.0
    h = 0.72                                                     # roof < wall height (cottage)
    over = 0.14                                                  # modest, even eaves
    k.gable(P, span, span, h, (0, 0, 1.0), "thatch", over=over)  # humble -> thatch (roof rule)
    sw = (span + over) / 2
    theta = math.atan2(h, sw)
    for f in (0.32, 0.64):                                        # thatch ties
        for sgn in (-1, 1):
            k.box(P, 0.03, span + 0.2, 0.04, (sgn * sw * (1 - f), 0, 1.0 + h * f),
                  "wood_dk", rot=(0, sgn * theta, 0))
    k.box(P, 0.08, span + 0.22, 0.08, (0, 0, 1.0 + h), "wood_dk")  # ridge
    cx, cy = 0.62, 0.5                                            # small chimney on the slope
    k.box(P, 0.26, 0.26, 0.9, (cx, cy, 1.15), "stone")
    for cz in (0.95, 1.28):
        k.box(P, 0.3, 0.3, 0.05, (cx, cy, cz), "stone_dk")
    k.box(P, 0.34, 0.34, 0.08, (cx, cy, 1.62), "stone_dk")       # cap
    for dx, dy in ((-0.07, -0.07), (0.07, -0.07), (-0.07, 0.07), (0.07, 0.07)):
        k.box(P, 0.08, 0.08, 0.1, (cx + dx, cy + dy, 1.7), "charwood")  # flue pots
    return k.join(P, "roof")


def house_demo(k: Any) -> Any:
    """A cottage assembled from the parts on a 2x2 grid: stone foundations + plank
    floors, a door + window wall on the front, window walls on the sides, plain
    back walls, quoined corners, a door leaf, and a full gable roof + chimney."""
    placed: list = []

    def put(fn, x, y, z, rz=0):
        o = fn(k)
        o.location = (x, y, z)
        o.rotation_euler = (0, 0, math.radians(rz))
        placed.append(o)

    for cx in (-0.5, 0.5):                          # 2x2 base + floor
        for cy in (-0.5, 0.5):
            put(foundation, cx, cy, 0)
            put(floor, cx, cy, 0)
    put(wall_door, -0.5, -1.0, 0, 0)                # front: door + window
    put(wall_window, 0.5, -1.0, 0, 0)
    put(door, -0.5, -1.0, 0, 0)                     # door leaf seated in the opening
    for cx in (-0.5, 0.5):                          # back: plain walls
        put(wall, cx, 1.0, 0, 180)
    for cy in (-0.5, 0.5):                          # sides: window walls
        put(wall_window, -1.0, cy, 0, 90)
        put(wall_window, 1.0, cy, 0, 270)
    for cx in (-1.0, 1.0):                          # quoined corner posts
        for cy in (-1.0, 1.0):
            put(wall_corner, cx, cy, 0)
    placed.append(_house_roof(k))                   # gable roof + chimney
    return k.join(placed, "house_demo")


WALL_PARTS = [
    ("wall", wall), ("wall_plaster", wall_plaster), ("wall_wood", wall_wood),
    ("wall_window", wall_window), ("wall_door", wall_door),
    ("wall_half", wall_half), ("wall_corner", wall_corner),
]
FLOOR_PARTS = [("floor", floor), ("foundation", foundation)]
ROOF_PARTS = [
    ("roof_gable", roof_gable), ("roof_slope", roof_slope),
    ("roof_flat", roof_flat), ("chimney", chimney),
]
OPENING_PARTS = [("door", door), ("door_arch", door_arch), ("window", window)]
STRUCT_PARTS = [
    ("pillar", pillar), ("post_beam", post_beam), ("arch", arch),
    ("stairs", stairs), ("railing", railing),
]
#: The full modular building-parts vocabulary (21 parts).
ALL_PARTS = WALL_PARTS + FLOOR_PARTS + ROOF_PARTS + OPENING_PARTS + STRUCT_PARTS

__all__ = ["WALL_PARTS", "FLOOR_PARTS", "ROOF_PARTS", "OPENING_PARTS",
           "STRUCT_PARTS", "ALL_PARTS", "CELL", "WT"]
