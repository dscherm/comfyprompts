"""GrimForge Castle — a large modular medieval castle-builder kit (100 pieces).

Grey ashlar stone in the GrimForge voice, with round + square towers, conical
spire roofs (blue-slate & red-tile), crenellated curtain walls, machicolations,
arrow slits, gatehouses with arched gateways + portcullis, a keep, chapel and
great hall, plus details and courtyard props. Grid-modular (1-unit) so a whole
castle assembles from the parts; a few pre-built showcases prove it snaps.

Built on the shared kitlib DSL (atlas texturing). Walls face -Y; towers are
authored upright with base at z=0. Caps sit from z=1.0 (one-storey) up — stack a
cap on a tower of matching footprint.
"""

import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

TITLE = "GrimForge Castle — Modular Castle Builder (100 pieces)"
AESTHETIC = "medieval"
HERO_VIEW = "3q"

R45 = math.radians(45)
R90 = math.radians(90)
WT = 0.2       # curtain-wall thickness
CELL = 1.0


# --------------------------------------------------------------------------- #
# shared castle helpers
# --------------------------------------------------------------------------- #

def _crenel_round(k, P, r, z, n=12, color="stone"):
    """A round battlement: a SOLID continuous parapet drum (sill) with merlons of the
    SAME stone rising from it. The parapet ring is truly continuous and the crenel
    gaps stop at the drum top, never exposing the floor (QUALITY_RUBRIC §4c)."""
    k.cyl(P, max(24, n * 2), r + 0.01, 0.13, (0, 0, z + 0.065), color)   # continuous drum
    seg = 2 * math.pi * r / n * 0.52
    for i in range(n):                                                   # merlons (teeth)
        an = math.radians(i * 360 / n)
        k.box(P, seg, 0.16, 0.16, (math.cos(an) * r, math.sin(an) * r, z + 0.205),
              color, rot=(0, 0, an))


def _crenel_sq(k, P, w, d, z, color="stone"):
    """A square battlement: a CONTINUOUS solid parapet sill round all four edges,
    with same-stone merlons rising from it. Merlons are spaced ~0.26 apart (dense,
    even count per side including corners). Crenel gaps stop at the sill (§4c)."""
    for sy in (-1, 1):                                   # front/back sill walls
        k.box(P, w + 0.14, 0.12, 0.13, (0, sy * d / 2, z + 0.065), color)
    for sx in (-1, 1):                                   # left/right sill walls
        k.box(P, 0.12, d + 0.14, 0.13, (sx * w / 2, 0, z + 0.065), color)
    nx = max(4, int(round(w / 0.26)) // 2 * 2)          # even # of gaps
    for i in range(0, nx + 1, 2):                        # merlons along front/back
        x = -w / 2 + i * w / nx
        for sy in (-1, 1):
            k.box(P, 0.15, 0.13, 0.16, (x, sy * d / 2, z + 0.205), color)
    nd = max(4, int(round(d / 0.26)) // 2 * 2)
    for i in range(2, nd, 2):                            # merlons along sides (skip corners)
        y = -d / 2 + i * d / nd
        for sx in (-1, 1):
            k.box(P, 0.13, 0.15, 0.16, (sx * w / 2, y, z + 0.205), color)


def _machic_round(k, P, r, z, color="stone_dk"):
    """A machicolation corbel ring projecting under a round parapet."""
    for i in range(12):
        an = math.radians(i * 30)
        k.box(P, 0.14, 0.16, 0.14, (math.cos(an) * (r + 0.06), math.sin(an) * (r + 0.06), z),
              color, rot=(0, 0, an))
    k.cyl(P, 14, r + 0.09, 0.08, (0, 0, z + 0.1), "stone")   # cap course / wall-walk


def _cone(k, P, r, h, z, color="slate", vn=8):
    """A conical spire roof of base radius r, height h, from z."""
    k.cone(P, vn, r, 0, h, (0, 0, z + h / 2), color)
    k.cyl(P, vn, r + 0.03, 0.05, (0, 0, z), "wood_dk")        # eave ring
    k.cyl(P, 6, 0.02, 0.18, (0, 0, z + h + 0.06), "gold")     # finial spike


def _arrowslit(k, P, x, y, z, vertical=True):
    if vertical:
        k.box(P, 0.06, WT + 0.02, 0.3, (x, y, z), "soot")
    else:
        k.box(P, 0.3, WT + 0.02, 0.06, (x, y, z), "soot")


def _arch_win(k, P, x, y, z, w=0.2, h=0.34, glow="window"):
    """A pointed-arch window recessed into a -Y wall face."""
    k.box(P, w, 0.06, h, (x, y, z), glow)
    for s in (-1, 1):
        k.box(P, 0.05, 0.08, h + 0.04, (x + s * (w / 2 + 0.02), y, z), "stone_dk")
    for i in range(3):
        a = math.radians(35 + i * 55)
        k.box(P, 0.07, 0.08, 0.07,
              (x + math.cos(a) * w * 0.55, y, z + h / 2 + math.sin(a) * w * 0.5),
              "stone_dk", rot=(0, 0, a - R90))


def _batter(k, P, r, color="stone"):
    """A tower base batter (wider splayed foot)."""
    k.cone(P, 12, r + 0.12, r, 0.3, (0, 0, 0.15), color)


# --------------------------------------------------------------------------- #
# CURTAIN WALLS  (1-unit, crenellated, face -Y; rotate to run on the grid)
# --------------------------------------------------------------------------- #

def _wall_body(k, P, h=1.0):
    k.box(P, CELL, WT, h, (0, 0, h / 2), "stone")
    k.box(P, CELL + 0.04, WT + 0.05, 0.1, (0, 0, 0.05), "stone_dk")     # plinth
    k.box(P, CELL + 0.04, WT + 0.06, 0.06, (0, 0, h - 0.03), "stone_dk")  # string course


def _wall_crenel(k, P, z=1.0):
    """Battlement along a 1-unit wall top: a CONTINUOUS parapet sill on each edge
    with merlons rising from it, so crenel gaps stop at the sill and never expose
    the wall-walk floor (physically-correct — QUALITY_RUBRIC §4c)."""
    for sy in (-1, 1):
        yy = sy * (WT / 2 - 0.015)
        k.box(P, CELL + 0.02, 0.08, 0.13, (0, yy, z + 0.065), "stone")   # continuous sill
        for mx in (-0.36, -0.12, 0.12, 0.36):
            k.box(P, 0.18, 0.09, 0.17, (mx, yy, z + 0.205), "stone")     # merlons (same stone)


def wall(k):
    """A crenellated curtain-wall segment."""
    P = []
    _wall_body(k, P, 1.0)
    _wall_crenel(k, P, 1.0)
    return k.join(P, "wall")


def wall_arrow(k):
    """A curtain wall with a cross arrow-loop."""
    P = []
    _wall_body(k, P, 1.0)
    _arrowslit(k, P, 0, 0, 0.55)
    _arrowslit(k, P, 0, 0, 0.55, vertical=False)
    _wall_crenel(k, P, 1.0)
    return k.join(P, "wall_arrow")


def wall_window(k):
    """A curtain wall with an arched window."""
    P = []
    _wall_body(k, P, 1.0)
    _arch_win(k, P, 0, -WT / 2, 0.55)
    _wall_crenel(k, P, 1.0)
    return k.join(P, "wall_window")


def wall_machicol(k):
    """A wall with a machicolated (corbelled) parapet."""
    P = []
    _wall_body(k, P, 0.9)
    for mx in (-0.35, -0.12, 0.12, 0.35):                      # corbels front
        k.box(P, 0.12, 0.12, 0.1, (mx, -WT / 2 - 0.04, 0.9), "stone_dk")
    k.box(P, CELL + 0.02, WT + 0.14, 0.28, (0, 0, 1.04), "stone")  # overhanging solid parapet
    for sy in (-1, 1):                                          # merlons sit ON the parapet top
        for mx in (-0.36, -0.12, 0.12, 0.36):
            k.box(P, 0.18, 0.09, 0.16, (mx, sy * 0.11, 1.26), "stone")
    return k.join(P, "wall_machicol")


def wall_low(k):
    """A low outer/curtain wall (no crenellations)."""
    P = []
    k.box(P, CELL, WT, 0.55, (0, 0, 0.275), "stone")
    k.box(P, CELL + 0.04, WT + 0.06, 0.08, (0, 0, 0.55), "stone_dk")   # coping
    k.box(P, CELL + 0.04, WT + 0.05, 0.08, (0, 0, 0.04), "stone_dk")
    return k.join(P, "wall_low")


def wall_corner(k):
    """A crenellated corner turret joining two wall runs."""
    P = []
    k.cyl(P, 10, 0.24, 1.0, (0, 0, 0.5), "stone")
    _batter(k, P, 0.24)
    _crenel_round(k, P, 0.24, 1.0, n=8)
    k.cyl(P, 10, 0.27, 0.06, (0, 0, 0.98), "stone_dk")
    return k.join(P, "wall_corner")


def wall_stairs(k):
    """A wall run with a stone stair up to the walk."""
    P = []
    _wall_body(k, P, 1.0)
    for i in range(5):
        k.box(P, 0.22, 0.18, 0.2 * (i + 1), (-0.3 + i * 0.14, 0.2, 0.1 * (i + 1)), "stone")
    return k.join(P, "wall_stairs")


def wall_buttress(k):
    """A wall braced by an angled buttress."""
    P = []
    _wall_body(k, P, 1.0)
    _wall_crenel(k, P, 1.0)
    k.box(P, 0.24, 0.3, 0.85, (0, -0.2, 0.42), "stone")
    k.box(P, 0.24, 0.3, 0.24, (0, -0.28, 0.9), "stone_dk", rot=(math.radians(34), 0, 0))
    return k.join(P, "wall_buttress")


def wall_ruined(k):
    """A broken, crumbling curtain wall (siege dressing)."""
    P = []
    k.box(P, CELL, WT, 0.5, (0, 0, 0.25), "stone")
    k.box(P, 0.5, WT, 0.35, (-0.25, 0, 0.62), "stone")
    for r in ((0.35, 0.1), (0.2, -0.08), (0.45, 0.05)):
        k.box(P, 0.16, 0.16, 0.14, (r[0], r[1], 0.08), "stone_dk")
    k.box(P, CELL, WT + 0.02, 0.05, (0, 0, 0.02), "moss")
    return k.join(P, "wall_ruined")


def parapet(k):
    """A standalone crenellated parapet cap (to top a plain wall)."""
    P = []
    k.box(P, CELL + 0.02, WT + 0.04, 0.08, (0, 0, 0.04), "stone_dk")
    _wall_crenel(k, P, 0.02)
    return k.join(P, "parapet")


def wall_gate_arch(k):
    """A curtain-wall section pierced by an arched gateway."""
    P = []
    for x in (-0.36, 0.36):
        k.box(P, 0.28, WT, 1.0, (x, 0, 0.5), "stone")
    for i in range(7):                                         # voussoir arch
        a = math.radians(20 + i * 23)
        k.box(P, 0.14, WT, 0.14, (math.cos(a) * 0.34, 0, 0.72 + math.sin(a) * 0.34),
              "stone_dk", rot=(0, 0, a - R90))
    k.box(P, CELL, WT, 0.14, (0, 0, 0.95), "stone")
    k.box(P, CELL + 0.04, WT + 0.05, 0.1, (0, 0, 0.05), "stone_dk")
    _wall_crenel(k, P, 1.02)
    k.box(P, 0.56, 0.06, 0.9, (0, WT / 2, 0.45), "wood_dk")    # timber gate
    for gz in (0.3, 0.7):
        k.box(P, 0.6, 0.07, 0.05, (0, WT / 2, gz), "iron")
    return k.join(P, "wall_gate_arch")


# --------------------------------------------------------------------------- #
# TOWERS
# --------------------------------------------------------------------------- #

def tower_round(k):
    """A one-storey round tower with a crenellated, machicolated top."""
    P = []
    k.cyl(P, 12, 0.42, 1.1, (0, 0, 0.55), "stone")
    _batter(k, P, 0.42)
    for zz in (0.5, 0.85):
        _arrowslit(k, P, 0, -0.4, zz)
    _machic_round(k, P, 0.42, 1.1)
    _crenel_round(k, P, 0.44, 1.24, n=12)
    return k.join(P, "tower_round")


def tower_round_tall(k):
    """A tall three-storey round tower."""
    P = []
    k.cyl(P, 12, 0.42, 2.1, (0, 0, 1.05), "stone")
    _batter(k, P, 0.42)
    for cz in (0.75, 1.4):
        k.cyl(P, 12, 0.44, 0.05, (0, 0, cz), "stone_dk")      # course bands
    for zz in (0.7, 1.35, 1.9):
        _arrowslit(k, P, 0, -0.4, zz)
    _machic_round(k, P, 0.42, 2.1)
    _crenel_round(k, P, 0.44, 2.24, n=12)
    return k.join(P, "tower_round_tall")


def tower_round_mid(k):
    """A stackable round tower mid-section (no top) with windows."""
    P = []
    k.cyl(P, 12, 0.42, 1.0, (0, 0, 0.5), "stone")
    k.cyl(P, 12, 0.44, 0.05, (0, 0, 0.02), "stone_dk")
    k.cyl(P, 12, 0.44, 0.05, (0, 0, 0.97), "stone_dk")
    _arch_win(k, P, 0, -0.4, 0.55, w=0.16, h=0.3)
    return k.join(P, "tower_round_mid")


def tower_square(k):
    """A square tower with a crenellated top."""
    P = []
    k.box(P, 0.7, 0.7, 1.2, (0, 0, 0.6), "stone")
    k.box(P, 0.78, 0.78, 0.1, (0, 0, 0.06), "stone_dk")
    for zz in (0.55, 0.9):
        _arrowslit(k, P, 0, -0.36, zz)
    for mx in (-0.24, 0.0, 0.24):                              # corbels
        k.box(P, 0.12, 0.12, 0.1, (mx, -0.36, 1.18), "stone_dk")
    k.box(P, 0.82, 0.82, 0.06, (0, 0, 1.22), "stone")
    _crenel_sq(k, P, 0.78, 0.78, 1.26)
    return k.join(P, "tower_square")


def tower_square_tall(k):
    """A tall square tower (great tower / donjon element)."""
    P = []
    k.box(P, 0.8, 0.8, 2.2, (0, 0, 1.1), "stone")
    k.box(P, 0.88, 0.88, 0.12, (0, 0, 0.06), "stone_dk")
    for cz in (0.8, 1.5):
        k.box(P, 0.84, 0.84, 0.06, (0, 0, cz), "stone_dk")
    for zz in (0.7, 1.4, 1.95):
        _arch_win(k, P, 0, -0.42, zz, w=0.16, h=0.3)
    for mx in (-0.28, 0.0, 0.28):
        k.box(P, 0.14, 0.14, 0.12, (mx, -0.42, 2.18), "stone_dk")
    k.box(P, 0.92, 0.92, 0.06, (0, 0, 2.24), "stone")
    _crenel_sq(k, P, 0.88, 0.88, 2.28)
    return k.join(P, "tower_square_tall")


def turret(k):
    """A slim corner turret / bartizan."""
    P = []
    k.cyl(P, 10, 0.26, 1.4, (0, 0, 0.7), "stone")
    _crenel_round(k, P, 0.28, 1.4, n=8)
    _arrowslit(k, P, 0, -0.25, 0.8)
    return k.join(P, "turret")


def tower_base(k):
    """A wide fortified tower base (talus) — footing for a big tower."""
    P = []
    k.cone(P, 12, 0.62, 0.5, 0.5, (0, 0, 0.25), "stone")
    k.cyl(P, 12, 0.5, 0.15, (0, 0, 0.55), "stone")
    k.cyl(P, 12, 0.52, 0.05, (0, 0, 0.5), "stone_dk")
    return k.join(P, "tower_base")


def tower_gate(k):
    """A single flanking gate-tower (round, with a portcullis slot)."""
    P = []
    k.cyl(P, 12, 0.45, 1.6, (0, 0, 0.8), "stone")
    _batter(k, P, 0.45)
    k.box(P, 0.3, 0.16, 0.8, (0, -0.4, 0.5), "soot")          # gate recess
    for zz in (1.0, 1.35):
        _arrowslit(k, P, 0, -0.42, zz)
    _machic_round(k, P, 0.45, 1.6)
    _crenel_round(k, P, 0.47, 1.74, n=12)
    return k.join(P, "tower_gate")


def watchtower(k):
    """A timber-hoarded watchtower on a round stone base."""
    P = []
    k.cyl(P, 10, 0.36, 1.4, (0, 0, 0.7), "stone")
    _batter(k, P, 0.36)
    k.cyl(P, 10, 0.46, 0.4, (0, 0, 1.5), "wood_dk")           # hoarding gallery
    for i in range(10):
        an = math.radians(i * 36)
        k.box(P, 0.05, 0.05, 0.3, (math.cos(an) * 0.44, math.sin(an) * 0.44, 1.5), "wood")
    _cone(k, P, 0.5, 0.5, 1.72, "wood_dk", vn=10)
    return k.join(P, "watchtower")


def _spire_tower(k, name, roof, storeys=2):
    """A self-contained round tower with an integrated conical spire (base-origin,
    so it drops onto the grid without stacking)."""
    r = 0.42
    h = storeys * 1.0
    P = []
    k.cyl(P, 12, r, h, (0, 0, h / 2), "stone")
    _batter(k, P, r)
    for i in range(storeys):
        k.cyl(P, 12, r + 0.02, 0.05, (0, 0, i * 1.0 + 0.03), "stone_dk")   # course band
        _arch_win(k, P, 0, -r + 0.03, i * 1.0 + 0.55, w=0.16, h=0.3)       # window
    k.cyl(P, 12, r + 0.05, 0.07, (0, 0, h), "wood_dk")                     # eave ring
    _cone(k, P, r + 0.07, 0.75, h, roof, vn=12)                            # spire
    return k.join(P, name)


def tower_spire(k):
    """A round tower crowned with a blue-slate conical spire (self-contained)."""
    return _spire_tower(k, "tower_spire", "slate", 2)


def tower_spire_red(k):
    """A round tower crowned with a red-tile conical spire."""
    return _spire_tower(k, "tower_spire_red", "roof_red", 2)


def tower_spire_tall(k):
    """A tall three-storey round tower with a slate spire."""
    return _spire_tower(k, "tower_spire_tall", "slate", 3)


# --------------------------------------------------------------------------- #
# TOWER CAPS / SPIRE ROOFS  (place on top of a tower of matching footprint)
# --------------------------------------------------------------------------- #

def _cap_cone(k, name, color, r=0.5, h=0.7):
    P = []
    _cone(k, P, r, h, 1.0, color, vn=8)
    return k.join(P, name)


def cap_cone_slate(k):
    """A conical blue-slate spire roof (round tower)."""
    return _cap_cone(k, "cap_cone_slate", "slate")


def cap_cone_red(k):
    """A conical red-tile spire roof (round tower)."""
    return _cap_cone(k, "cap_cone_red", "roof_red")


def cap_cone_tall(k):
    """A tall pointed witch-hat spire."""
    return _cap_cone(k, "cap_cone_tall", "slate", r=0.48, h=1.1)


def cap_pyramid_slate(k):
    """A pyramidal slate roof (square tower)."""
    P = []
    k.cone(P, 4, 0.6, 0, 0.7, (0, 0, 1.35), "slate", rot=(0, 0, R45))
    k.box(P, 0.85, 0.85, 0.05, (0, 0, 1.0), "wood_dk")
    k.cyl(P, 6, 0.03, 0.2, (0, 0, 1.78), "gold")
    return k.join(P, "cap_pyramid_slate")


def cap_pyramid_red(k):
    """A pyramidal red-tile roof (square tower)."""
    P = []
    k.cone(P, 4, 0.6, 0, 0.7, (0, 0, 1.35), "roof_red", rot=(0, 0, R45))
    k.box(P, 0.85, 0.85, 0.05, (0, 0, 1.0), "wood_dk")
    k.cyl(P, 6, 0.03, 0.2, (0, 0, 1.78), "gold")
    return k.join(P, "cap_pyramid_red")


def cap_crenel(k):
    """A crenellated flat cap (battlement top) for a round tower."""
    P = []
    _machic_round(k, P, 0.42, 1.0)
    _crenel_round(k, P, 0.44, 1.14, n=12)
    return k.join(P, "cap_crenel")


def cap_dome(k):
    """An onion-dome cap."""
    P = []
    k.ico(P, 0.42, (0, 0, 1.32), "slate", sub=2)
    k.cyl(P, 12, 0.44, 0.08, (0, 0, 1.02), "stone_dk")
    k.cone(P, 6, 0.1, 0, 0.28, (0, 0, 1.78), "gold")
    return k.join(P, "cap_dome")


def finial(k):
    """A pinnacle finial — a small slate spire topped with a heraldic pennant."""
    P = []
    k.cyl(P, 8, 0.16, 0.05, (0, 0, 0.025), "stone_dk")         # base ring
    k.cone(P, 6, 0.14, 0, 0.42, (0, 0, 0.26), "slate")         # small spire
    k.cyl(P, 6, 0.02, 0.4, (0, 0, 0.62), "gold")               # spike
    k.box(P, 0.02, 0.16, 0.1, (0, 0.09, 0.74), "flag")         # pennant
    return k.join(P, "finial")


# --------------------------------------------------------------------------- #
# GATEHOUSE / KEEP / BUILDINGS  (assembled showcases + big parts)
# --------------------------------------------------------------------------- #

def gatehouse(k):
    """A twin-tower gatehouse: two round guard towers linked by a crenellated
    WALL-WALK over an arched gate (timber doors + portcullis + machicolations).
    The walkway floor connects the towers so a defender can walk the parapet."""
    P = []
    GT = 0.92                                                 # guard-tower centre offset
    for s in (-1, 1):                                         # flanking guard towers
        k.cyl(P, 12, 0.4, 2.0, (s * GT, 0, 1.0), "stone")
        for zz in (0.75, 1.35):                              # guard-room windows
            _arch_win(k, P, s * GT, -0.38, zz, w=0.14, h=0.26)
        _machic_round_off(k, P, s * GT, 0.4, 2.0)
        _crenel_round_off(k, P, s * GT, 0.42, 2.14, n=10)
    # gate curtain wall between the towers
    k.box(P, 2 * GT, 0.42, 1.35, (0, 0, 0.675), "stone")
    k.box(P, 2 * GT + 0.06, 0.5, 0.12, (0, 0, 0.06), "stone_dk")   # plinth
    for x in (-0.42, 0.42):                                  # gateway jambs
        k.box(P, 0.18, 0.44, 1.15, (x, 0, 0.6), "stone")
    for i in range(7):                                       # voussoir arch
        a = math.radians(20 + i * 23)
        k.box(P, 0.12, 0.44, 0.12, (math.cos(a) * 0.36, 0, 1.16 + math.sin(a) * 0.36),
              "stone_dk", rot=(0, 0, a - R90))
    k.box(P, 0.72, 0.3, 1.2, (0, 0.14, 0.62), "soot")        # shallow recess (not a void)
    for dx in (-0.17, 0.17):                                 # closed studded timber doors
        k.box(P, 0.33, 0.07, 1.18, (dx, -0.19, 0.62), "wood_dk")
        for px in (-0.09, 0.0, 0.09):
            k.box(P, 0.025, 0.085, 1.12, (dx + px, -0.19, 0.62), "wood")
    for z in (0.3, 0.66, 1.02):                              # iron cross-bands
        k.box(P, 0.7, 0.085, 0.06, (0, -0.2, z), "iron")
    for dx in (-0.24, 0.24):                                 # ring handles
        k.cyl(P, 8, 0.045, 0.03, (dx, -0.24, 0.66), "iron", rot=(R90, 0, 0))
    for gx in (-0.24, -0.08, 0.08, 0.24):                    # raised portcullis in the arch
        k.box(P, 0.04, 0.06, 0.2, (gx, -0.17, 1.32), "steel")
    k.box(P, 0.62, 0.06, 0.04, (0, -0.17, 1.42), "steel")
    for sy in (-1, 1):                                       # machicolation corbels under walk
        for mx in (-0.62, -0.37, -0.12, 0.12, 0.37, 0.62):
            k.box(P, 0.1, 0.12, 0.12, (mx, sy * 0.24, 1.36), "stone_dk")
    k.box(P, 2 * GT, 0.58, 0.1, (0, 0, 1.44), "stone")       # WALL-WALK floor (links towers)
    for sy in (-1, 1):                                       # crenellated parapets on the walk
        yy = sy * 0.25
        k.box(P, 2 * GT - 0.04, 0.08, 0.14, (0, yy, 1.56), "stone")     # continuous sill
        for mx in (-0.66, -0.4, -0.13, 0.13, 0.4, 0.66):
            k.box(P, 0.16, 0.09, 0.16, (mx, yy, 1.7), "stone")          # merlons
    return k.join(P, "gatehouse")


def _machic_round_off(k, P, cx, r, z):
    for i in range(12):
        an = math.radians(i * 30)
        k.box(P, 0.13, 0.15, 0.13, (cx + math.cos(an) * (r + 0.05), math.sin(an) * (r + 0.05), z),
              "stone_dk", rot=(0, 0, an))
    k.cyl(P, 14, r + 0.08, 0.07, (cx, 0, z + 0.09), "stone")


def _crenel_round_off(k, P, cx, r, z, n=10, cy=0.0):
    """Offset round battlement — SOLID continuous parapet drum + same-stone merlons,
    centred at (cx, cy). Crenel gaps stop at the drum top (§4c)."""
    k.cyl(P, max(20, n * 2), r + 0.01, 0.12, (cx, cy, z + 0.06), "stone")   # continuous drum
    seg = 2 * math.pi * r / n * 0.52
    for i in range(n):                                                       # merlons
        an = math.radians(i * 360 / n)
        k.box(P, seg, 0.14, 0.15, (cx + math.cos(an) * r, cy + math.sin(an) * r, z + 0.19),
              "stone", rot=(0, 0, an))


def keep(k):
    """The great keep — a massive square donjon with corner turrets + spires."""
    P = []
    k.box(P, 1.5, 1.5, 2.6, (0, 0, 1.3), "stone")
    k.box(P, 1.6, 1.6, 0.16, (0, 0, 0.08), "stone_dk")        # plinth
    for cz in (0.9, 1.7):
        k.box(P, 1.56, 1.56, 0.06, (0, 0, cz), "stone_dk")    # string courses
    for zz in (0.8, 1.5, 2.2):
        for xx in (-0.4, 0.4):
            _arch_win(k, P, xx, -0.75, zz, w=0.16, h=0.32)
    k.box(P, 0.5, 0.1, 0.9, (0, -0.75, 0.45), "wood_dk")      # entrance door
    for cx, cy in ((-0.75, -0.75), (0.75, -0.75), (-0.75, 0.75), (0.75, 0.75)):
        k.cyl(P, 10, 0.24, 3.0, (cx, cy, 1.5), "stone")       # corner turret
        _crenel_round_off(k, P, cx, 0.26, 3.0, n=8, cy=cy)    # turret battlement (on the turret)
    _crenel_sq(k, P, 1.5, 1.5, 2.6)                            # main battlement
    k.box(P, 0.7, 0.1, 1.0, (0, 0, 3.3), "flag")              # banner from the roof
    k.cyl(P, 6, 0.03, 1.2, (0, 0, 3.5), "wood_dk")
    return k.join(P, "keep")


def great_hall(k):
    """A great hall — long stone hall with a steep slate roof + chimney."""
    P = []
    k.box(P, 1.6, 1.0, 1.0, (0, 0, 0.5), "stone")
    k.box(P, 1.66, 1.06, 0.1, (0, 0, 0.05), "stone_dk")
    for xx in (-0.5, 0.0, 0.5):
        _arch_win(k, P, xx, -0.5, 0.55, w=0.16, h=0.4)
    k.gable(P, 1.6, 1.0, 0.7, (0, 0, 1.0), "slate", over=0.16)
    k.box(P, 0.24, 0.24, 1.0, (0.5, 0.3, 1.3), "stone")       # chimney
    k.box(P, 0.28, 0.28, 0.08, (0.5, 0.3, 1.82), "stone_dk")
    return k.join(P, "great_hall")


def chapel(k):
    """A castle chapel — nave, bell-cote, rose window, buttresses."""
    P = []
    k.box(P, 0.9, 1.5, 1.0, (0, 0, 0.5), "stone")
    k.gable(P, 0.9, 1.5, 0.55, (0, 0, 1.0), "slate", over=0.16)
    k.cyl(P, 12, 0.2, 0.04, (0, -0.7, 1.1), "gem", rot=(R90, 0, 0))   # rose window
    k.cyl(P, 12, 0.23, 0.03, (0, -0.72, 1.1), "stone_dk", rot=(R90, 0, 0))
    for s in (-1, 1):                                         # buttresses
        k.box(P, 0.16, 0.2, 0.9, (s * 0.5, -0.3, 0.45), "stone")
        k.box(P, 0.16, 0.2, 0.2, (s * 0.5, -0.4, 0.9), "stone_dk", rot=(math.radians(30), 0, 0))
    k.box(P, 0.24, 0.24, 0.5, (0, 0.7, 1.4), "stone")         # bell-cote
    k.cone(P, 4, 0.2, 0, 0.3, (0, 0.7, 1.8), "slate", rot=(0, 0, R45))
    k.box(P, 0.05, 0.05, 0.2, (0, 0.7, 2.0), "gold")          # cross
    k.box(P, 0.16, 0.05, 0.05, (0, 0.7, 1.95), "gold")
    return k.join(P, "chapel")


def tower_house(k):
    """A residential tower-house with a red-tile roof + timber gallery."""
    P = []
    k.box(P, 0.9, 0.9, 1.6, (0, 0, 0.8), "stone")
    k.box(P, 0.96, 0.96, 0.1, (0, 0, 0.05), "stone_dk")
    for zz in (0.6, 1.2):
        for xx in (-0.22, 0.22):
            _arch_win(k, P, xx, -0.47, zz, w=0.14, h=0.28)
    k.box(P, 1.0, 0.5, 0.4, (0, -0.5, 1.35), "wood_dk")       # jettied gallery
    for x in (-0.4, 0.0, 0.4):
        k.box(P, 0.04, 0.04, 0.34, (x, -0.72, 1.4), "wood")
    k.box(P, 0.95, 0.95, 0.55, (0, 0, 1.85), "roof_red", rot=(0, 0, 0))  # roof mass
    k.cone(P, 4, 0.68, 0, 0.5, (0, 0, 2.35), "roof_red", rot=(0, 0, R45))
    return k.join(P, "tower_house")


# --------------------------------------------------------------------------- #
# DETAILS  (wall-mount inserts & trim)
# --------------------------------------------------------------------------- #

def window_gothic(k):
    """A pointed-arch gothic window with a mullion (wall insert)."""
    P = []
    k.box(P, 0.42, 0.12, 0.76, (0, 0, 0.38), "stone")
    _arch_win(k, P, 0, -0.05, 0.42, w=0.22, h=0.46, glow="window")
    k.box(P, 0.03, 0.09, 0.44, (0, -0.05, 0.42), "stone_dk")   # mullion
    k.box(P, 0.18, 0.09, 0.03, (0, -0.05, 0.42), "stone_dk")   # transom
    return k.join(P, "window_gothic")


def window_rose(k):
    """A stained-glass rose window in a stone surround (wall insert)."""
    P = []
    k.box(P, 0.64, 0.14, 0.64, (0, 0, 0.32), "stone")
    k.cyl(P, 12, 0.28, 0.05, (0, 0.0, 0.34), "stone_dk", rot=(R90, 0, 0))   # tracery ring
    k.cyl(P, 12, 0.23, 0.04, (0, -0.05, 0.34), "window", rot=(R90, 0, 0))   # glowing glass field
    petal = ["crimson", "amber", "gem", "witchlight"]
    for i in range(8):                                                      # coloured panes
        an = math.radians(i * 45)
        k.box(P, 0.1, 0.05, 0.1, (math.cos(an) * 0.13, -0.06, 0.34 + math.sin(an) * 0.13),
              petal[i % 4], rot=(0, -an, 0))
    for i in range(4):                                                      # stone tracery spokes
        an = math.radians(i * 45)
        k.box(P, 0.46, 0.04, 0.03, (0, -0.05, 0.34), "stone_dk", rot=(0, -an, 0))
    k.cyl(P, 8, 0.055, 0.06, (0, -0.06, 0.34), "amber", rot=(R90, 0, 0))    # hub
    return k.join(P, "window_rose")


def door_arch(k):
    """An arched, iron-studded timber door in a stone surround (wall insert)."""
    P = []
    k.box(P, 0.5, 0.12, 0.9, (0, 0, 0.45), "stone")
    for i in range(7):
        a = math.radians(20 + i * 23)
        k.box(P, 0.1, 0.13, 0.1, (math.cos(a) * 0.22, -0.02, 0.66 + math.sin(a) * 0.22),
              "stone_dk", rot=(0, 0, a - R90))
    k.box(P, 0.36, 0.06, 0.62, (0, -0.05, 0.36), "wood_dk")
    for gx in (-0.09, 0.09):
        k.box(P, 0.05, 0.05, 0.6, (gx, -0.06, 0.38), "wood")
    for gz in (0.2, 0.4, 0.55):
        k.cyl(P, 6, 0.02, 0.03, (-0.09, -0.09, gz), "iron", rot=(R90, 0, 0))
        k.cyl(P, 6, 0.02, 0.03, (0.09, -0.09, gz), "iron", rot=(R90, 0, 0))
    return k.join(P, "door_arch")


def buttress_flying(k):
    """A flying buttress — outer pinnacle-pier + arch bracing a wall stub."""
    P = []
    k.box(P, 0.16, 0.5, 1.5, (-0.42, 0, 0.75), "stone")        # wall stub (abutment)
    for zz in (0.9, 1.25):
        k.box(P, 0.2, 0.54, 0.06, (-0.42, 0, zz), "stone_dk")
    k.box(P, 0.22, 0.22, 1.0, (0.42, 0, 0.5), "stone")         # outer pier
    k.box(P, 0.26, 0.26, 0.08, (0.42, 0, 1.0), "stone_dk")
    k.cone(P, 4, 0.16, 0, 0.36, (0.42, 0, 1.22), "slate", rot=(0, 0, R45))  # pinnacle
    for i in range(6):                                         # continuous flying arch
        t = i / 5.0
        x = 0.42 - t * 0.7
        z = 1.0 + math.sin(t * math.radians(90)) * 0.32 - t * 0.04
        k.box(P, 0.17, 0.16, 0.14, (x, 0, z), "stone", rot=(0, math.radians(-50 * t), 0))
    return k.join(P, "buttress_flying")


def pillar(k):
    """A stone column with a base and capital."""
    P = []
    k.box(P, 0.28, 0.28, 0.1, (0, 0, 0.05), "stone_dk")
    k.cyl(P, 10, 0.11, 1.2, (0, 0, 0.65), "stone")
    for zz in (0.35, 0.65, 0.95):
        k.cyl(P, 10, 0.12, 0.03, (0, 0, zz), "stone_dk")
    k.box(P, 0.26, 0.26, 0.12, (0, 0, 1.28), "stone")
    return k.join(P, "pillar")


def balcony(k):
    """A projecting stone balcony on a wall panel."""
    P = []
    k.box(P, 0.72, 0.16, 0.95, (0, 0.08, 0.475), "stone")      # wall backing
    k.box(P, 0.76, 0.2, 0.08, (0, 0.08, 0.04), "stone_dk")     # plinth
    _arch_win(k, P, 0, 0.0, 0.66, w=0.18, h=0.34)              # doorway onto the balcony
    k.box(P, 0.6, 0.32, 0.08, (0, -0.14, 0.34), "stone")       # floor slab
    for cx in (-0.24, 0.0, 0.24):                              # corbels under
        k.box(P, 0.1, 0.12, 0.12, (cx, -0.22, 0.24), "stone_dk", rot=(math.radians(30), 0, 0))
    for cx in (-0.28, -0.09, 0.09, 0.28):                      # balusters
        k.cyl(P, 6, 0.03, 0.2, (cx, -0.27, 0.48), "stone")
    k.box(P, 0.6, 0.06, 0.05, (0, -0.27, 0.6), "stone_dk")     # rail
    return k.join(P, "balcony")


def arrow_loop(k):
    """A cross arrow-loop block (wall insert)."""
    P = []
    k.box(P, 0.3, 0.14, 0.6, (0, 0, 0.3), "stone")
    _arrowslit(k, P, 0, -0.06, 0.32)
    _arrowslit(k, P, 0, -0.06, 0.32, vertical=False)
    return k.join(P, "arrow_loop")


def corbel_strip(k):
    """A machicolated parapet course on a wall stub (crowns a curtain wall)."""
    P = []
    k.box(P, CELL, WT, 0.55, (0, 0, 0.275), "stone")           # wall stub
    k.box(P, CELL + 0.04, WT + 0.05, 0.08, (0, 0, 0.04), "stone_dk")
    for mx in (-0.4, -0.2, 0.0, 0.2, 0.4):                     # corbels project front
        k.box(P, 0.12, 0.14, 0.12, (mx, -WT / 2 - 0.03, 0.55), "stone_dk")
    k.box(P, CELL + 0.02, WT + 0.14, 0.1, (0, 0, 0.66), "stone")   # overhang course
    for mx in (-0.33, 0.0, 0.33):                              # merlons
        k.box(P, 0.22, 0.1, 0.2, (mx, -0.04, 0.81), "stone_dk")
    return k.join(P, "corbel_strip")


def banner(k):
    """A heraldic banner hung on a stone wall panel."""
    P = []
    k.box(P, 0.5, WT, 1.0, (0, 0.08, 0.5), "stone")            # wall backing
    k.box(P, 0.54, WT + 0.05, 0.1, (0, 0.08, 0.05), "stone_dk")  # plinth
    k.cyl(P, 6, 0.02, 0.44, (0, -0.03, 0.82), "wood_dk", rot=(0, R90, 0))  # cross-pole
    k.box(P, 0.34, 0.02, 0.6, (0, -0.02, 0.52), "crimson")
    k.box(P, 0.34, 0.03, 0.12, (0, -0.02, 0.26), "crimson", rot=(math.radians(12), 0, 0))
    for tx in (-0.1, 0.1):                                     # dagged tails
        k.cone(P, 3, 0.06, 0, 0.12, (tx, -0.02, 0.18), "crimson", rot=(math.radians(180), 0, 0))
    k.ico(P, 0.05, (0, -0.03, 0.54), "gold")                  # emblem
    return k.join(P, "banner")


def dormer(k):
    """A roof dormer window (sits on a roof slope)."""
    P = []
    k.box(P, 0.3, 0.3, 0.3, (0, 0, 0.15), "stone")
    _arch_win(k, P, 0, -0.15, 0.16, w=0.12, h=0.2)
    k.gable(P, 0.34, 0.34, 0.22, (0, 0, 0.3), "slate", over=0.06)
    return k.join(P, "dormer")


# --------------------------------------------------------------------------- #
# GATE / DEFENCE
# --------------------------------------------------------------------------- #

def portcullis(k):
    """A raised iron portcullis in a stone arch."""
    P = []
    for x in (-0.34, 0.34):
        k.box(P, 0.16, 0.2, 1.1, (x, 0, 0.55), "stone")
    for i in range(7):
        a = math.radians(20 + i * 23)
        k.box(P, 0.14, 0.2, 0.14, (math.cos(a) * 0.34, 0, 0.86 + math.sin(a) * 0.34),
              "stone_dk", rot=(0, 0, a - R90))
    for gx in (-0.24, -0.08, 0.08, 0.24):                     # bars
        k.box(P, 0.04, 0.05, 0.9, (gx, 0, 0.62), "iron")
    for gz in (0.35, 0.7, 1.0):
        k.box(P, 0.56, 0.05, 0.05, (0, 0, gz), "iron")
    for gx in (-0.24, -0.08, 0.08, 0.24):                     # spiked bottoms
        k.cone(P, 4, 0.03, 0, 0.08, (gx, 0, 0.13), "iron", rot=(math.radians(180), 0, 0))
    return k.join(P, "portcullis")


def gate_arch(k):
    """A free-standing arched gateway (barbican passage)."""
    P = []
    for x in (-0.45, 0.45):
        k.box(P, 0.3, 0.5, 1.3, (x, 0, 0.65), "stone")
        k.box(P, 0.34, 0.54, 0.1, (x, 0, 0.05), "stone_dk")
    for i in range(9):
        a = math.radians(12 + i * 19)
        k.box(P, 0.16, 0.5, 0.16, (math.cos(a) * 0.45, 0, 0.95 + math.sin(a) * 0.45),
              "stone_dk", rot=(0, 0, a - R90))
    k.box(P, 1.3, 0.5, 0.3, (0, 0, 1.55), "stone")
    for mx in (-0.45, -0.15, 0.15, 0.45):
        k.box(P, 0.16, 0.14, 0.2, (mx, 0, 1.8), "stone_dk")
    return k.join(P, "gate_arch")


def drawbridge(k):
    """A timber drawbridge with iron banding, back hinges and deck lift-chains."""
    P = []
    k.box(P, 0.8, 1.3, 0.08, (0, 0, 0.04), "wood_dk")
    for py in (-0.5, -0.16, 0.18, 0.52):
        k.box(P, 0.84, 0.1, 0.05, (0, py, 0.08), "wood")       # cross-planks
    for x in (-0.34, 0.34):
        k.box(P, 0.08, 1.3, 0.06, (x, 0, 0.09), "iron")        # edge bands
        k.cyl(P, 8, 0.05, 0.12, (x, 0.66, 0.06), "iron", rot=(0, R90, 0))  # hinge pintle
    for x in (-0.26, 0.26):                                    # lift-chains lying on the deck
        for i in range(7):
            k.cyl(P, 6, 0.02, 0.07, (x, -0.55 + i * 0.15, 0.1),
                  "iron", rot=(R90 if i % 2 else 0, 0, 0))
        k.cyl(P, 8, 0.05, 0.05, (x, -0.62, 0.11), "iron", rot=(0, R90, 0))  # end ring
    return k.join(P, "drawbridge")


def barbican(k):
    """A small outer gate-tower (barbican) with a portcullis slot."""
    P = []
    k.box(P, 1.0, 0.6, 1.4, (0, 0, 0.7), "stone")
    k.box(P, 1.06, 0.66, 0.12, (0, 0, 0.06), "stone_dk")
    for x in (-0.3, 0.3):
        k.box(P, 0.28, 0.62, 1.2, (x, 0, 0.6), "stone")
    k.box(P, 0.5, 0.5, 1.2, (0, 0, 0.6), "soot")              # passage
    for gx in (-0.16, 0.0, 0.16):
        k.box(P, 0.05, 0.05, 0.9, (gx, -0.28, 0.5), "iron")
    for mx in (-0.4, -0.13, 0.13, 0.4):
        k.box(P, 0.16, 0.66, 0.12, (mx, 0, 1.44), "stone_dk")
    k.box(P, 1.06, 0.7, 0.06, (0, 0, 1.54), "stone")
    _crenel_sq(k, P, 1.0, 0.6, 1.58)
    return k.join(P, "barbican")


# --------------------------------------------------------------------------- #
# BUILDINGS
# --------------------------------------------------------------------------- #

def stable(k):
    """A timber-and-stone stable block with a shake lean-to roof."""
    P = []
    k.box(P, 1.4, 0.8, 0.7, (0, 0, 0.35), "stone")
    k.box(P, 1.44, 0.84, 0.08, (0, 0, 0.04), "stone_dk")
    for dx in (-0.42, 0.0, 0.42):                             # stall doorways
        k.box(P, 0.26, 0.06, 0.5, (dx, -0.4, 0.28), "wood_dk")
        k.box(P, 0.3, 0.05, 0.06, (dx, -0.4, 0.5), "wood")
    for x in (-0.6, 0.6):
        k.box(P, 0.08, 0.84, 0.9, (x, 0, 0.45), "wood_dk")    # timber posts
    k.box(P, 1.5, 0.95, 0.1, (0, 0.08, 0.86), "shake", rot=(math.radians(-14), 0, 0))
    return k.join(P, "stable")


def well_house(k):
    """A covered stone well with a shingled roof and a bucket."""
    P = []
    k.cyl(P, 12, 0.32, 0.4, (0, 0, 0.2), "stone")
    k.cyl(P, 12, 0.35, 0.06, (0, 0, 0.4), "stone_dk")
    k.cyl(P, 12, 0.24, 0.06, (0, 0, 0.36), "soot")            # water/shaft
    for x in (-0.28, 0.28):
        k.box(P, 0.06, 0.06, 0.7, (x, 0, 0.75), "wood_dk")    # posts
    k.cyl(P, 6, 0.04, 0.56, (0, 0, 1.1), "wood", rot=(0, R90, 0))  # windlass
    _cone(k, P, 0.44, 0.34, 1.15, "shake", vn=6)              # little roof
    k.box(P, 0.12, 0.12, 0.12, (0, 0, 0.5), "wood_dk")        # bucket
    return k.join(P, "well_house")


def round_keep(k):
    """A round shell-keep — a great drum tower with battlements + spire."""
    P = []
    k.cyl(P, 14, 0.75, 2.4, (0, 0, 1.2), "stone")
    _batter(k, P, 0.75)
    for cz in (0.9, 1.7):
        k.cyl(P, 14, 0.77, 0.06, (0, 0, cz), "stone_dk")
    for i in range(4):
        an = math.radians(i * 90 - 45)
        _arch_win(k, P, math.cos(an) * 0.72, math.sin(an) * 0.72 - 0.02, 1.2, w=0.16, h=0.34)
    k.box(P, 0.5, 0.1, 0.9, (0, -0.74, 0.45), "wood_dk")      # door
    for i in range(16):                                       # machicolation ring
        an = math.radians(i * 22.5)
        k.box(P, 0.14, 0.16, 0.14, (math.cos(an) * 0.82, math.sin(an) * 0.82, 2.4),
              "stone_dk", rot=(0, 0, an))
    k.cyl(P, 16, 0.86, 0.08, (0, 0, 2.5), "stone")
    for i in range(16):
        an = math.radians(i * 22.5)
        k.box(P, 0.17, 0.14, 0.26, (math.cos(an) * 0.8, math.sin(an) * 0.8, 2.66),
              "stone_dk", rot=(0, 0, an))
    return k.join(P, "round_keep")


def siege_tower(k):
    """A wheeled timber siege tower with a drop-ramp (siege dressing)."""
    P = []
    k.box(P, 0.9, 0.9, 2.0, (0, 0, 1.0), "wood_dk")
    for zz in (0.5, 1.1, 1.7):
        k.box(P, 0.96, 0.96, 0.06, (0, 0, zz), "wood")
    for x in (-0.4, 0.4):
        for y in (-0.4, 0.4):
            k.box(P, 0.08, 0.08, 2.0, (x, y, 1.0), "wood")    # corner beams
    k.box(P, 0.7, 0.06, 0.9, (0, -0.46, 1.9), "wood",
          rot=(math.radians(-16), 0, 0))                       # drop-ramp
    for x in (-0.45, 0.45):                                   # wheels
        for y in (-0.35, 0.35):
            k.cyl(P, 10, 0.16, 0.08, (x, y, 0.14), "wood_dk", rot=(0, R90, 0))
    k.box(P, 0.9, 0.06, 0.5, (0, 0.46, 1.4), "iron")          # hide plating
    return k.join(P, "siege_tower")


# --------------------------------------------------------------------------- #
# PROPS / COURTYARD DRESSING
# --------------------------------------------------------------------------- #

def brazier(k):
    """An iron fire brazier."""
    P = []
    for i in range(3):
        an = math.radians(i * 120)
        k.box(P, 0.04, 0.04, 0.4, (math.cos(an) * 0.1, math.sin(an) * 0.1, 0.2),
              "iron", rot=(math.radians(10) * math.cos(an), math.radians(10) * math.sin(an), 0))
    k.cyl(P, 8, 0.18, 0.14, (0, 0, 0.44), "iron")
    k.cyl(P, 8, 0.15, 0.08, (0, 0, 0.5), "ember")
    k.cone(P, 6, 0.12, 0, 0.16, (0, 0, 0.58), "fire")
    return k.join(P, "brazier")


def torch_wall(k):
    """A wall-bracket torch on a stone wall pier."""
    P = []
    k.box(P, 0.3, WT, 0.9, (0, 0.08, 0.45), "stone")          # wall pier
    k.box(P, 0.34, WT + 0.04, 0.08, (0, 0.08, 0.04), "stone_dk")
    k.box(P, 0.1, 0.1, 0.1, (0, -0.08, 0.5), "iron")          # bracket
    k.cyl(P, 6, 0.02, 0.3, (0, -0.16, 0.66), "wood_dk", rot=(math.radians(20), 0, 0))
    k.cyl(P, 6, 0.05, 0.06, (0, -0.22, 0.82), "iron")
    k.cone(P, 6, 0.06, 0, 0.14, (0, -0.22, 0.9), "fire")
    return k.join(P, "torch_wall")


def barrel(k):
    """A wooden barrel."""
    P = []
    k.cyl(P, 10, 0.16, 0.4, (0, 0, 0.2), "wood")
    k.cyl(P, 10, 0.18, 0.36, (0, 0, 0.2), "wood_dk")
    k.cyl(P, 10, 0.185, 0.1, (0, 0, 0.2), "wood")
    for zz in (0.06, 0.34):
        k.cyl(P, 10, 0.185, 0.03, (0, 0, zz), "iron")
    return k.join(P, "barrel")


def crate(k):
    """A wooden supply crate."""
    P = []
    k.box(P, 0.34, 0.34, 0.34, (0, 0, 0.17), "wood")
    for e in (-0.15, 0.15):
        k.box(P, 0.04, 0.36, 0.36, (e, 0, 0.17), "wood_dk")
        k.box(P, 0.36, 0.04, 0.36, (0, e, 0.17), "wood_dk")
    k.box(P, 0.28, 0.28, 0.04, (0, 0, 0.35), "wood_dk", rot=(0, 0, R45))
    return k.join(P, "crate")


def well(k):
    """An open stone well."""
    P = []
    k.cyl(P, 12, 0.3, 0.44, (0, 0, 0.22), "stone")
    k.cyl(P, 12, 0.33, 0.06, (0, 0, 0.44), "stone_dk")
    k.cyl(P, 12, 0.22, 0.06, (0, 0, 0.4), "soot")
    k.cyl(P, 12, 0.24, 0.03, (0, 0, 0.41), "water")
    for i in range(8):
        an = math.radians(i * 45)
        k.box(P, 0.06, 0.09, 0.06, (math.cos(an) * 0.3, math.sin(an) * 0.3, 0.47),
              "stone_dk", rot=(0, 0, an))
    return k.join(P, "well")


def statue(k):
    """A knight statue resting both hands on a downturned sword, on a plinth."""
    P = []
    k.box(P, 0.46, 0.46, 0.14, (0, 0, 0.07), "stone_dk")      # base
    k.box(P, 0.38, 0.38, 0.18, (0, 0, 0.21), "stone")         # plinth
    k.box(P, 0.3, 0.3, 0.04, (0, 0, 0.32), "stone_dk")        # cornice
    k.cone(P, 6, 0.15, 0.1, 0.34, (0, 0, 0.51), "stone")      # robe flare
    k.box(P, 0.22, 0.15, 0.34, (0, 0, 0.62), "stone")         # torso
    k.box(P, 0.27, 0.17, 0.08, (0, 0, 0.83), "stone")         # shoulders
    k.ico(P, 0.08, (0, 0, 0.95), "stone", sub=1)              # head
    k.cone(P, 6, 0.09, 0.03, 0.13, (0, 0, 1.02), "steel")     # great-helm crest
    k.box(P, 0.16, 0.05, 0.05, (0, -0.1, 0.72), "steel")      # sword crossguard
    k.box(P, 0.05, 0.05, 0.05, (0, -0.1, 0.78), "gold")       # pommel
    k.box(P, 0.05, 0.045, 0.46, (0, -0.1, 0.47), "steel")     # blade point-down
    k.cone(P, 4, 0.03, 0, 0.1, (0, -0.1, 0.2), "steel", rot=(math.radians(180), 0, 0))
    for s in (-1, 1):
        k.box(P, 0.05, 0.06, 0.28, (s * 0.11, -0.06, 0.62), "stone",
              rot=(math.radians(s * 12), 0, 0))               # arms down to the hilt
    return k.join(P, "statue")


def tree(k):
    """A stylised courtyard tree."""
    P = []
    k.cyl(P, 6, 0.07, 0.7, (0, 0, 0.35), "wood_dk")
    for zz, r in ((0.75, 0.34), (0.95, 0.28), (1.12, 0.18)):
        k.ico(P, r, (0, 0, zz), "leaf", sub=1)
    return k.join(P, "tree")


def shield(k):
    """A heraldic shield mounted on crossed spears on a wall panel."""
    P = []
    k.box(P, 0.44, WT, 0.9, (0, 0.08, 0.45), "stone")         # wall backing
    k.box(P, 0.48, WT + 0.04, 0.08, (0, 0.08, 0.04), "stone_dk")
    for s in (-1, 1):                                         # crossed spears behind
        k.box(P, 0.03, 0.03, 0.8, (0, -0.02, 0.5), "wood_dk", rot=(0, math.radians(s * 28), 0))
        k.cone(P, 4, 0.04, 0, 0.12, (s * 0.38, -0.02, 0.86), "steel", rot=(0, 0, R45))
    k.box(P, 0.34, 0.05, 0.4, (0, -0.06, 0.52), "steel")     # shield body
    k.cone(P, 3, 0.19, 0, 0.18, (0, -0.07, 0.35), "steel", rot=(math.radians(180), 0, 0))
    k.box(P, 0.24, 0.06, 0.28, (0, -0.08, 0.55), "crimson")
    k.ico(P, 0.06, (0, -0.11, 0.57), "gold")
    return k.join(P, "shield")


def cart(k):
    """A wooden hand-cart."""
    P = []
    k.box(P, 0.5, 0.8, 0.1, (0, 0, 0.24), "wood")
    for e in (-0.22, 0.22):
        k.box(P, 0.04, 0.8, 0.18, (e, 0, 0.32), "wood_dk")
    k.box(P, 0.5, 0.04, 0.18, (0, -0.38, 0.32), "wood_dk")
    for x in (-0.28, 0.28):
        k.cyl(P, 10, 0.2, 0.06, (x, 0.1, 0.2), "wood_dk", rot=(0, R90, 0))
        k.cyl(P, 10, 0.06, 0.08, (x, 0.1, 0.2), "iron", rot=(0, R90, 0))
    for x in (-0.06, 0.06):
        k.cyl(P, 6, 0.03, 0.7, (x, -0.7, 0.3), "wood_dk", rot=(math.radians(80), 0, 0))  # shafts
    return k.join(P, "cart")


def banner_pole(k):
    """A tall heraldic banner on a pole (courtyard)."""
    P = []
    k.cyl(P, 8, 0.05, 0.14, (0, 0, 0.07), "stone")            # base
    k.cyl(P, 6, 0.03, 1.5, (0, 0, 0.75), "wood_dk")
    k.cone(P, 6, 0.04, 0, 0.14, (0, 0, 1.55), "gold")
    k.box(P, 0.36, 0.02, 0.7, (0.2, 0, 1.15), "crimson")
    k.box(P, 0.36, 0.03, 0.14, (0.2, 0, 0.76), "crimson", rot=(math.radians(14), 0, 0))
    k.ico(P, 0.05, (0.2, -0.02, 1.2), "gold")
    return k.join(P, "banner_pole")


def pennant_pole(k):
    """A pennant flag on a slender pole."""
    P = []
    k.cyl(P, 8, 0.04, 0.1, (0, 0, 0.05), "stone")
    k.cyl(P, 6, 0.02, 1.3, (0, 0, 0.65), "wood_dk")
    k.box(P, 0.4, 0.02, 0.18, (0.22, 0, 1.2), "flag")
    k.cone(P, 3, 0.09, 0, 0.28, (0.5, 0, 1.2), "flag", rot=(0, 0, -R90))
    return k.join(P, "pennant_pole")


def market_stall(k):
    """A courtyard market stall with a striped awning."""
    P = []
    k.box(P, 0.9, 0.5, 0.4, (0, 0, 0.2), "wood_dk")           # counter
    k.box(P, 0.94, 0.54, 0.06, (0, 0, 0.4), "wood")
    for x in (-0.42, 0.42):
        for y in (-0.22, 0.22):
            k.cyl(P, 6, 0.03, 0.9, (x, y, 0.45), "wood_dk")
    k.box(P, 1.0, 0.6, 0.06, (0, 0, 0.92), "cloth_r", rot=(math.radians(-8), 0, 0))
    for sx in (-0.3, 0.0, 0.3):
        k.box(P, 0.14, 0.6, 0.07, (sx, 0, 0.93), "cloth", rot=(math.radians(-8), 0, 0))
    return k.join(P, "market_stall")


# --------------------------------------------------------------------------- #
# GROUND / COURTYARD TILES  (1-unit grid)
# --------------------------------------------------------------------------- #

def floor_cobble(k):
    """A cobblestone courtyard tile."""
    P = []
    k.box(P, CELL, CELL, 0.08, (0, 0, 0.04), "cobble")
    k.box(P, CELL, CELL, 0.02, (0, 0, 0.09), "gravel")
    return k.join(P, "floor_cobble")


def floor_flagstone(k):
    """A flagstone courtyard tile."""
    P = []
    k.box(P, CELL, CELL, 0.08, (0, 0, 0.04), "stone")
    for gx in (-0.25, 0.25):
        k.box(P, 0.02, CELL, 0.02, (gx, 0, 0.09), "stone_dk")
    k.box(P, CELL, 0.02, 0.02, (0, 0, 0.09), "stone_dk")
    return k.join(P, "floor_flagstone")


def floor_grass(k):
    """A grass courtyard tile."""
    P = []
    k.box(P, CELL, CELL, 0.08, (0, 0, 0.04), "grass")
    k.box(P, CELL, CELL, 0.02, (0, 0, 0.02), "dirt")
    return k.join(P, "floor_grass")


def floor_dirt(k):
    """A packed-dirt / moat-bed tile."""
    P = []
    k.box(P, CELL, CELL, 0.08, (0, 0, 0.04), "dirt")
    return k.join(P, "floor_dirt")


def stairs_stone(k):
    """A flight of stone steps."""
    P = []
    for i in range(6):
        k.box(P, 0.7, 0.16, 0.14 * (i + 1), (0, 0.32 - i * 0.14, 0.07 * (i + 1)), "stone")
    for s in (-1, 1):
        k.box(P, 0.06, 1.0, 0.5, (s * 0.35, 0, 0.25), "stone_dk")
    return k.join(P, "stairs_stone")


def ramp(k):
    """A stone ramp / approach."""
    P = []
    k.box(P, 0.8, 1.2, 0.5, (0, 0, 0.25), "stone")
    k.box(P, 0.84, 1.24, 0.06, (0, 0, 0.53), "stone_dk", rot=(math.radians(-22), 0, 0))
    return k.join(P, "ramp")


# --------------------------------------------------------------------------- #
# RECOLOUR VARIANTS  (grimforge-dark stone & alternate roof colours)
# --------------------------------------------------------------------------- #

def _recolor(k, base_fn, name, swaps):
    """Build ``base_fn`` then remap materials by swapping palette entries."""
    saved = dict(k.palette)
    for a, b in swaps.items():
        k.palette[a] = saved[b]
    try:
        obj = base_fn(k)
    finally:
        k.palette.clear()
        k.palette.update(saved)
    obj.name = name
    return obj


_DARK = {"stone": "stone_dk", "stone_dk": "charwood"}


def wall_dark(k):
    """A blackened GrimForge curtain wall."""
    return _recolor(k, wall, "wall_dark", _DARK)


def wall_arrow_dark(k):
    return _recolor(k, wall_arrow, "wall_arrow_dark", _DARK)


def wall_machicol_dark(k):
    return _recolor(k, wall_machicol, "wall_machicol_dark", _DARK)


def wall_corner_dark(k):
    return _recolor(k, wall_corner, "wall_corner_dark", _DARK)


def tower_round_dark(k):
    return _recolor(k, tower_round, "tower_round_dark", _DARK)


def tower_round_tall_dark(k):
    return _recolor(k, tower_round_tall, "tower_round_tall_dark", _DARK)


def tower_square_dark(k):
    return _recolor(k, tower_square, "tower_square_dark", _DARK)


def tower_gate_dark(k):
    return _recolor(k, tower_gate, "tower_gate_dark", _DARK)


def turret_dark(k):
    return _recolor(k, turret, "turret_dark", _DARK)


def cap_cone_green(k):
    """A verdigris copper spire (round tower)."""
    return _recolor(k, cap_cone_slate, "cap_cone_green", {"slate": "moss"})


def cap_cone_dark(k):
    """A charred black spire."""
    return _recolor(k, cap_cone_slate, "cap_cone_dark", {"slate": "charwood"})


def cap_pyramid_green(k):
    return _recolor(k, cap_pyramid_slate, "cap_pyramid_green", {"slate": "moss"})


def cap_dome_gold(k):
    """A gilded dome."""
    return _recolor(k, cap_dome, "cap_dome_gold", {"slate": "gold"})


def cap_dome_red(k):
    return _recolor(k, cap_dome, "cap_dome_red", {"slate": "roof_red"})


def gatehouse_dark(k):
    """A blackened GrimForge gatehouse."""
    return _recolor(k, gatehouse, "gatehouse_dark", _DARK)


def keep_dark(k):
    """A blackened GrimForge keep."""
    return _recolor(k, keep, "keep_dark", _DARK)


def round_keep_dark(k):
    return _recolor(k, round_keep, "round_keep_dark", _DARK)


def great_hall_red(k):
    """A great hall with a red-tile roof."""
    return _recolor(k, great_hall, "great_hall_red", {"slate": "roof_red"})


def chapel_red(k):
    return _recolor(k, chapel, "chapel_red", {"slate": "roof_red"})


def tower_house_slate(k):
    """A tower-house with a slate roof."""
    return _recolor(k, tower_house, "tower_house_slate", {"roof_red": "slate"})


def wall_gate_dark(k):
    return _recolor(k, wall_gate_arch, "wall_gate_dark", _DARK)


def tower_square_tall_dark(k):
    return _recolor(k, tower_square_tall, "tower_square_tall_dark", _DARK)


def watchtower_dark(k):
    return _recolor(k, watchtower, "watchtower_dark", {"wood_dk": "charwood", "wood": "wood_dk"})


def great_hall_dark(k):
    return _recolor(k, great_hall, "great_hall_dark", _DARK)


def chapel_dark(k):
    return _recolor(k, chapel, "chapel_dark", _DARK)


def brazier_witch(k):
    """A brazier burning ghostfire (occult)."""
    return _recolor(k, brazier, "brazier_witch", {"ember": "witchlight", "fire": "ghostfire"})


def cap_cone_tall_red(k):
    """A tall red-tile witch-hat spire."""
    return _recolor(k, cap_cone_tall, "cap_cone_tall_red", {"slate": "roof_red"})


def tower_base_dark(k):
    return _recolor(k, tower_base, "tower_base_dark", _DARK)


def barbican_dark(k):
    return _recolor(k, barbican, "barbican_dark", _DARK)


def gate_arch_dark(k):
    return _recolor(k, gate_arch, "gate_arch_dark", _DARK)


def stable_slate(k):
    """A stable with a slate lean-to roof."""
    return _recolor(k, stable, "stable_slate", {"shake": "slate"})


PIECES = [
    ("wall", wall), ("wall_arrow", wall_arrow), ("wall_window", wall_window),
    ("wall_machicol", wall_machicol), ("wall_low", wall_low), ("wall_corner", wall_corner),
    ("wall_stairs", wall_stairs), ("wall_buttress", wall_buttress),
    ("wall_ruined", wall_ruined), ("parapet", parapet), ("wall_gate_arch", wall_gate_arch),
    ("tower_round", tower_round), ("tower_round_tall", tower_round_tall),
    ("tower_round_mid", tower_round_mid), ("tower_square", tower_square),
    ("tower_square_tall", tower_square_tall), ("turret", turret), ("tower_base", tower_base),
    ("tower_gate", tower_gate), ("watchtower", watchtower),
    ("tower_spire", tower_spire), ("tower_spire_red", tower_spire_red),
    ("tower_spire_tall", tower_spire_tall),
    ("cap_cone_slate", cap_cone_slate), ("cap_cone_red", cap_cone_red),
    ("cap_cone_tall", cap_cone_tall), ("cap_pyramid_slate", cap_pyramid_slate),
    ("cap_pyramid_red", cap_pyramid_red), ("cap_crenel", cap_crenel),
    ("cap_dome", cap_dome), ("finial", finial),
    ("gatehouse", gatehouse), ("keep", keep), ("great_hall", great_hall),
    ("chapel", chapel), ("tower_house", tower_house),
    # --- details ---
    ("window_gothic", window_gothic), ("window_rose", window_rose),
    ("door_arch", door_arch), ("buttress_flying", buttress_flying), ("pillar", pillar),
    ("balcony", balcony), ("arrow_loop", arrow_loop), ("corbel_strip", corbel_strip),
    ("banner", banner), ("dormer", dormer),
    # --- gate / defence ---
    ("portcullis", portcullis), ("gate_arch", gate_arch), ("drawbridge", drawbridge),
    ("barbican", barbican),
    # --- buildings ---
    ("stable", stable), ("well_house", well_house), ("round_keep", round_keep),
    ("siege_tower", siege_tower),
    # --- props ---
    ("brazier", brazier), ("torch_wall", torch_wall), ("barrel", barrel), ("crate", crate),
    ("well", well), ("statue", statue), ("tree", tree), ("shield", shield), ("cart", cart),
    ("banner_pole", banner_pole), ("pennant_pole", pennant_pole), ("market_stall", market_stall),
    # --- tiles ---
    ("floor_cobble", floor_cobble), ("floor_flagstone", floor_flagstone),
    ("floor_grass", floor_grass), ("floor_dirt", floor_dirt),
    ("stairs_stone", stairs_stone), ("ramp", ramp),
    # --- recolour variants (grimforge-dark stone & alternate roofs) ---
    ("wall_dark", wall_dark), ("wall_arrow_dark", wall_arrow_dark),
    ("wall_machicol_dark", wall_machicol_dark), ("wall_corner_dark", wall_corner_dark),
    ("wall_gate_dark", wall_gate_dark), ("tower_round_dark", tower_round_dark),
    ("tower_round_tall_dark", tower_round_tall_dark), ("tower_square_dark", tower_square_dark),
    ("tower_square_tall_dark", tower_square_tall_dark), ("tower_gate_dark", tower_gate_dark),
    ("turret_dark", turret_dark), ("tower_base_dark", tower_base_dark),
    ("watchtower_dark", watchtower_dark), ("gatehouse_dark", gatehouse_dark),
    ("keep_dark", keep_dark), ("round_keep_dark", round_keep_dark),
    ("barbican_dark", barbican_dark),
    ("great_hall_dark", great_hall_dark), ("chapel_dark", chapel_dark),
    ("great_hall_red", great_hall_red), ("chapel_red", chapel_red),
    ("tower_house_slate", tower_house_slate),
    ("cap_cone_green", cap_cone_green), ("cap_cone_dark", cap_cone_dark),
    ("cap_cone_tall_red", cap_cone_tall_red),
    ("cap_dome_gold", cap_dome_gold), ("cap_dome_red", cap_dome_red),
    ("brazier_witch", brazier_witch),
]
