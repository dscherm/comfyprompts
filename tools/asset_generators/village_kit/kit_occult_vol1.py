"""GrimForge Occult Vol.1 — a full sellable dark-fantasy kit (14 pieces).

Reuses the approved dark_scarecrow + creepy_barn + the shared skull() helper,
and adds 12 occult props. Built on kitlib with the occult palette + emissive
accents tuned to the grimforge_style LoRA. Run via kit_pipeline / productize.py.
"""

import math

from kit_occult import creepy_barn, dark_scarecrow, skull  # shared hero pieces + skull

TITLE = "GrimForge Occult Vol.1 — Dark-Fantasy Kit (14 pieces)"
AESTHETIC = "occult"


def _pentagram(k, P, cx, cy, cz, rr, col, w=0.04):
    """Draw a glowing pentagram (5 connected star edges) flat in the XY plane."""
    verts = [(cx + rr * math.cos(math.radians(90 + i * 72)),
              cy + rr * math.sin(math.radians(90 + i * 72))) for i in range(5)]
    for i in range(5):
        ax, ay = verts[i]
        bx, by = verts[(i + 2) % 5]
        ln = math.hypot(bx - ax, by - ay)
        ang = math.atan2(by - ay, bx - ax)
        k.box(P, ln, w, 0.02, ((ax + bx) / 2, (ay + by) / 2, cz), col, rot=(0, 0, ang))
    return verts


def ritual_altar(k):
    P = []
    k.box(P, 1.0, 0.5, 0.5, (0, 0, 0.28), "stone")              # base
    k.box(P, 1.2, 0.7, 0.16, (0, 0, 0.55), "stone_dk")          # top slab
    k.box(P, 1.0, 0.5, 0.04, (0, 0, 0.64), "blood")             # blood-stained top
    for sx in (-0.45, 0.45):                                    # candles
        k.cyl(P, 6, 0.05, 0.22, (sx, -0.22, 0.74), "bone")
        k.cone(P, 5, 0.05, 0, 0.1, (sx, -0.22, 0.92), "ember")
    skull(k, P, 0.34, 0.16, 0.74, 0.12)                         # skull offering
    # open occult tome with a glowing pentagram + scrawls on the pages
    k.box(P, 0.46, 0.36, 0.05, (-0.18, 0.04, 0.66), "charwood")  # cover
    for s in (-1, 1):                                           # two splayed pages
        k.box(P, 0.21, 0.34, 0.02, (-0.18 + s * 0.115, 0.04, 0.69),
              "plaster", rot=(0, math.radians(-s * 7), 0))
    _pentagram(k, P, -0.07, 0.04, 0.71, 0.09, "witchlight", w=0.012)  # right page
    for mx, my in [(-0.29, -0.06), (-0.3, 0.05), (-0.28, 0.14)]:      # left-page scrawls
        k.box(P, 0.1, 0.012, 0.02, (mx, my, 0.71), "rune")
    return k.join(P, "ritual_altar")


def summoning_circle(k):
    P = []
    k.box(P, 1.6, 1.6, 0.03, (0, 0, 0.015), "stone_dk")
    for a in range(16):                                         # outer ring — witchlight green
        an = math.radians(a * 22.5)
        k.box(P, 0.12, 0.05, 0.02, (math.cos(an) * 0.62, math.sin(an) * 0.62, 0.035),
              "witchlight", rot=(0, 0, an))
    verts = _pentagram(k, P, 0, 0, 0.04, 0.5, "rune", w=0.05)   # star — rune purple
    for a in range(12):                                         # inner ring — ghostfire cyan
        an = math.radians(a * 30)
        k.box(P, 0.08, 0.04, 0.02, (math.cos(an) * 0.3, math.sin(an) * 0.3, 0.045),
              "ghostfire", rot=(0, 0, an))
    for vx, vy in verts:                                        # a lit candle at each star point
        k.cyl(P, 6, 0.04, 0.2, (vx, vy, 0.13), "bone")
        k.cone(P, 5, 0.04, 0, 0.1, (vx, vy, 0.29), "ember")
    return k.join(P, "summoning_circle")


def standing_stone(k):
    P = []
    k.box(P, 0.6, 0.55, 0.12, (0, 0, 0.06), "moss")             # mossy base
    k.box(P, 0.5, 0.35, 1.6, (0, 0, 0.85), "stone",             # leaning menhir
          rot=(math.radians(3), 0, math.radians(-5)))
    # carved purple rune strokes around a glowing crystal
    k.box(P, 0.06, 0.05, 0.42, (0, -0.2, 1.0), "rune")
    k.box(P, 0.24, 0.05, 0.06, (0, -0.2, 1.12), "rune")
    k.box(P, 0.18, 0.05, 0.06, (0.04, -0.2, 0.9), "rune", rot=(0, 0, math.radians(42)))
    # the rune-gem: a faceted purple crystal (two cones tip-to-tip = a diamond)
    k.cone(P, 6, 0.11, 0, 0.18, (0, -0.25, 1.34), "rune")
    k.cone(P, 6, 0.11, 0, 0.13, (0, -0.25, 1.16), "rune", rot=(math.radians(180), 0, 0))
    return k.join(P, "standing_stone")


def hanged_tree(k):
    P = []
    k.box(P, 0.8, 0.8, 0.12, (0, 0.1, 0.06), "rot")             # disturbed earth
    k.cyl(P, 7, 0.2, 2.5, (-0.35, 0.1, 1.25), "charwood", rot=(0, math.radians(6), 0))   # trunk
    k.cyl(P, 6, 0.12, 1.4, (0.2, 0.1, 2.15), "charwood", rot=(0, math.radians(80), 0))  # branch
    for s, zz, an in [(-1, 1.7, 50), (1, 2.3, -34)]:            # a couple dead limbs
        k.cyl(P, 5, 0.06, 0.6, (-0.35 + s * 0.2, 0.1, zz), "charwood", rot=(0, math.radians(an), 0))
    # a nondescript hanged figure in puritan clothes — a CONNECTED stack
    # (coat -> collar -> neck -> head -> hat) hung by a VISIBLE hollow noose
    nx, ny = 0.5, 0.1
    hz = 1.18
    k.box(P, 0.22, 0.16, 0.52, (nx, ny, hz), "shroud")          # coat
    k.box(P, 0.26, 0.2, 0.09, (nx, ny, hz + 0.28), "plaster")   # collar (overlaps coat)
    k.cyl(P, 6, 0.055, 0.08, (nx, ny, hz + 0.36), "bone")       # tiny neck (barely visible)
    znk = hz + 0.38
    for a in range(8):                                         # hollow noose ring on the neck
        an = math.radians(a * 45)
        k.box(P, 0.055, 0.032, 0.032, (nx + math.cos(an) * 0.11, ny + math.sin(an) * 0.11, znk),
              "bone", rot=(0, 0, an))
    k.cyl(P, 5, 0.022, 2.15 - (znk + 0.05), (nx, ny + 0.05, (2.15 + znk + 0.05) / 2), "bone")
    # head cleanly on the neck, lolled only slightly; hat sits on it undistorted
    tilt = math.radians(13)
    hx = nx + 0.05
    k.ico(P, 0.13, (hx, ny, hz + 0.46), "bone", sub=1)
    k.cyl(P, 7, 0.17, 0.05, (hx + 0.02, ny, hz + 0.57), "charwood", rot=(0, 0, tilt))
    k.cone(P, 7, 0.11, 0.02, 0.13, (hx + 0.04, ny, hz + 0.62), "charwood", rot=(0, 0, tilt))
    for s in (-1, 1):                                           # limp legs + arms
        k.box(P, 0.08, 0.08, 0.46, (nx + s * 0.06, ny, hz - 0.44), "shroud")
        k.box(P, 0.06, 0.06, 0.32, (nx + s * 0.13, ny, hz + 0.06), "shroud",
              rot=(0, math.radians(s * 16), 0))
    return k.join(P, "hanged_tree")


def bone_pile(k):
    P = []
    skull(k, P, -0.18, 0.0, 0.16, 0.14)
    skull(k, P, 0.2, 0.12, 0.16, 0.12)
    skull(k, P, 0.02, -0.16, 0.36, 0.11)
    for x, y, an in [(-0.3, 0.14, 45), (0.28, -0.08, -32), (0.0, 0.24, 12), (-0.08, -0.04, 70)]:
        k.cyl(P, 6, 0.035, 0.6, (x, y, 0.08), "bone", rot=(0, math.radians(an), math.radians(22)))
    return k.join(P, "bone_pile")


def dead_tree(k):
    P = []
    k.cyl(P, 7, 0.24, 2.6, (0, 0, 1.3), "charwood")             # tall, thick trunk
    # gaping dark hollow in the trunk, faintly lit from within
    k.box(P, 0.26, 0.22, 0.6, (0, -0.16, 1.35), "soot")
    k.box(P, 0.14, 0.1, 0.4, (0, -0.22, 1.35), "amber")
    for s, zz, an, ln in [(-1, 1.8, 55, 1.0), (1, 1.5, -46, 0.9), (-1, 2.35, 34, 0.7),
                          (1, 2.2, -30, 0.78), (-1, 2.5, 18, 0.5)]:
        k.cyl(P, 5, 0.08, ln, (s * 0.28, 0, zz), "charwood", rot=(0, math.radians(an), 0))
    for a in range(5):                                          # twisted roots
        an = math.radians(a * 72)
        k.cyl(P, 4, 0.06, 0.45, (math.cos(an) * 0.3, math.sin(an) * 0.3, 0.1), "charwood",
              rot=(math.radians(70), 0, an))
    return k.join(P, "dead_tree")


def iron_brazier(k):
    P = []
    k.cone(P, 6, 0.18, 0.1, 0.75, (0, 0, 0.37), "gunmetal")
    k.cyl(P, 8, 0.27, 0.16, (0, 0, 0.76), "gunmetal")
    k.cone(P, 6, 0.21, 0, 0.36, (0, 0, 0.96), "ember")
    k.cone(P, 5, 0.1, 0, 0.28, (0.05, 0, 1.05), "amber")
    return k.join(P, "iron_brazier")


def crypt_entrance(k):
    P = []
    MW, MD, MH = 1.9, 1.3, 1.7
    cy = 0.12                                   # mass centre y
    ff = cy - MD / 2                            # front face y (= -0.53)
    bf = cy + MD / 2                            # back face y  (=  0.77)
    # full base plinth + a second plate, both extending under the whole crypt
    k.box(P, 2.4, 2.2, 0.18, (0, 0.05, 0.09), "stone_dk")
    k.box(P, 2.05, 1.9, 0.16, (0, 0.0, 0.26), "stone")
    # main mass
    k.box(P, MW, MD, MH, (0, cy, 0.18 + MH / 2), "stone")
    # stonework "texture": horizontal mortar courses wrapping the mass
    for cz in (0.55, 0.92, 1.29, 1.66):
        k.box(P, MW + 0.03, MD + 0.03, 0.05, (0, cy, cz), "stone_dk")
    # vertical block joints on the side walls
    for s in (-1, 1):
        for yy in (-0.25, 0.4):
            k.box(P, 0.04, 0.05, MH - 0.12, (s * MW / 2, cy + yy, 0.18 + MH / 2), "stone_dk")
    # heavy capstone + stepped pediment + crowning cross
    k.box(P, MW + 0.3, MD + 0.3, 0.24, (0, cy, 2.08), "stone_dk")
    k.box(P, 1.1, 0.9, 0.34, (0, cy, 2.38), "stone")
    k.box(P, 0.12, 0.12, 0.5, (0, cy, 2.75), "stone")
    k.box(P, 0.38, 0.12, 0.12, (0, cy, 2.84), "stone")
    # --- BACK detail: corner buttresses + a carved relief + a barred window ---
    for s in (-1, 1):
        k.box(P, 0.24, 0.3, MH - 0.2, (s * (MW / 2 - 0.14), bf + 0.04, 0.18 + (MH - 0.2) / 2),
              "stone_dk")
    k.box(P, 0.9, 0.06, 1.0, (0, bf + 0.04, 1.15), "stone_dk")       # relief panel
    k.box(P, 0.08, 0.06, 0.42, (0, bf + 0.07, 1.3), "stone")         # carved cross
    k.box(P, 0.32, 0.06, 0.08, (0, bf + 0.07, 1.38), "stone")
    k.box(P, 0.36, 0.08, 0.42, (0, bf + 0.02, 0.62), "soot")         # barred window recess
    for bx in (-0.1, 0.0, 0.1):
        k.box(P, 0.03, 0.06, 0.42, (bx, bf + 0.07, 0.62), "iron")    # bars
    # flanking columns (front)
    for s in (-1, 1):
        k.cyl(P, 8, 0.17, 1.6, (s * 0.74, ff + 0.05, 0.95), "stone_dk")
        k.cyl(P, 8, 0.22, 0.12, (s * 0.74, ff + 0.05, 1.72), "stone")    # capital
        k.cyl(P, 8, 0.22, 0.12, (s * 0.74, ff + 0.05, 0.22), "stone")    # base
    # nested recessed arches over the doorway (receding inward)
    for rr, yy, col in [(0.62, ff + 0.04, "stone"), (0.5, ff + 0.15, "stone_dk"),
                        (0.4, ff + 0.26, "stone")]:
        for a in range(9):
            an = math.radians(180 * a / 8)
            k.box(P, 0.15, 0.13, 0.2, (math.cos(an) * rr, yy, 0.95 + math.sin(an) * rr),
                  col, rot=(0, 0, an))
    # --- DARKENED recessed entrance: a deep near-black void with a faint glow ---
    k.box(P, 0.8, 0.6, 1.05, (0, ff + 0.28, 0.6), "soot")            # dark void (front ~flush)
    k.box(P, 0.4, 0.05, 0.7, (0, ff - 0.02, 0.56), "ghostfire")      # faint glow within
    k.box(P, 1.2, 0.8, 0.06, (0, -0.4, 0.06), "moss")
    return k.join(P, "crypt_entrance")


def skull_totem(k):
    P = []
    k.box(P, 0.5, 0.5, 0.1, (0, 0, 0.05), "stone_dk")
    k.box(P, 0.1, 0.1, 1.5, (0, 0, 0.8), "wood_dk")
    for z in (0.55, 0.95, 1.35):
        skull(k, P, 0, 0, z, 0.15, glow_eyes=True)
    return k.join(P, "skull_totem")


def cauldron(k):
    P = []
    for s in (-1, 1):                                          # tripod legs
        k.cyl(P, 4, 0.04, 0.5, (s * 0.3, 0, 0.42), "iron", rot=(0, math.radians(s * 24), 0))
        k.cyl(P, 4, 0.04, 0.5, (0, s * 0.3, 0.42), "iron", rot=(math.radians(s * 24), 0, 0))
    k.cone(P, 6, 0.22, 0, 0.2, (0, 0, 0.14), "ember")          # embers beneath
    # rotund belly: stacked rings widen then narrow into a flared rim
    k.cyl(P, 12, 0.2, 0.12, (0, 0, 0.45), "gunmetal")
    k.cyl(P, 12, 0.34, 0.14, (0, 0, 0.56), "gunmetal")
    k.cyl(P, 12, 0.41, 0.16, (0, 0, 0.7), "gunmetal")          # widest belly
    k.cyl(P, 12, 0.34, 0.12, (0, 0, 0.84), "gunmetal")
    k.cyl(P, 12, 0.43, 0.08, (0, 0, 0.93), "gunmetal")         # flared rim
    k.cyl(P, 12, 0.33, 0.04, (0, 0, 0.97), "witchlight")       # bubbling brew
    return k.join(P, "cauldron")


def grave_cross(k):
    P = []
    k.box(P, 0.7, 0.5, 0.06, (0, 0.1, 0.04), "rot")            # disturbed earth
    k.box(P, 0.5, 0.32, 0.1, (0, 0.1, 0.07), "dirt")
    k.box(P, 0.1, 0.1, 0.95, (0, -0.1, 0.5), "wood_dk",        # leaning cross
          rot=(math.radians(-9), 0, math.radians(7)))
    k.box(P, 0.5, 0.08, 0.1, (0, -0.1, 0.72), "wood_dk",
          rot=(math.radians(-9), 0, math.radians(7)))
    return k.join(P, "grave_cross")


def candle_shrine(k):
    P = []
    k.box(P, 0.55, 0.55, 0.1, (0, 0, 0.05), "stone_dk")
    skull(k, P, -0.04, 0.12, 0.22, 0.11)                       # a skull
    for sx, sy, h in [(-0.16, -0.1, 0.32), (0.12, 0.02, 0.42), (-0.02, 0.18, 0.26),
                      (0.18, -0.14, 0.36)]:
        k.cyl(P, 6, 0.04, h, (sx, sy, h / 2 + 0.1), "bone")
        k.cone(P, 5, 0.04, 0, 0.08, (sx, sy, h + 0.1 + 0.03), "ember")
    return k.join(P, "candle_shrine")


PIECES = [
    ("creepy_barn", creepy_barn),
    ("dark_scarecrow", dark_scarecrow),
    ("crypt_entrance", crypt_entrance),
    ("ritual_altar", ritual_altar),
    ("hanged_tree", hanged_tree),
    ("standing_stone", standing_stone),
    ("dead_tree", dead_tree),
    ("iron_brazier", iron_brazier),
    ("cauldron", cauldron),
    ("skull_totem", skull_totem),
    ("summoning_circle", summoning_circle),
    ("bone_pile", bone_pile),
    ("grave_cross", grave_cross),
    ("candle_shrine", candle_shrine),
]
