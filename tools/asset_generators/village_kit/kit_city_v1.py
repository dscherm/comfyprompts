"""GrimForge City Vol.1 — dark-fantasy urban kit (12 pieces).

Grander stone monuments — gatehouse, towers, walls, cathedral, keep — in the
occult GrimForge aesthetic (ember-lit windows, ghost-glow water, grim stone).
Built on kitlib via kit_pipeline / productize.
"""

import math

from kit_occult import skull as _occult_skull  # shared low-poly skull (gated below)
from kit_village_v1 import _flame_banner  # shared warding banner (sigil gated by OCCULT)

TITLE = "GrimForge City Vol.1 — Dark-Fantasy Urban Kit (12 pieces)"
AESTHETIC = "occult"

# Medieval variant sets OCCULT = False (here + on kit_village_v1) to drop skulls
# and switch the banner sigil — see kit_city_medieval.py.
OCCULT = True


def skull(k, P, *args, **kwargs):
    """Skull dressing — suppressed when OCCULT is False (medieval variant)."""
    if OCCULT:
        _occult_skull(k, P, *args, **kwargs)

# Darken the whole kit to the grim/occult tone (one override darkens all
# pieces; ember/crimson/ghost accents still pop against the dark stone).
PALETTE_OVERRIDE = {
    "stone": "414640",
    "stone_dk": "2a2e2a",
    "plaster": "564f44",
    "slate": "2f353c",
    "thatch": "4a3c22",
    "thatch_dk": "342a16",
}


def _merlons(k, P, cx, cy, span, d, z, n=5, col="stone_dk"):
    """A row of battlement merlons of total width `span` (along x) at height z."""
    for i in range(n):
        x = cx + (i - (n - 1) / 2.0) * (span / n)
        k.box(P, span / n * 0.6, d, 0.26, (x, cy, z), col)


def _spire_turret(k, P, x, y, base_z, top_z, r=0.22, cap="slate"):
    """A slender stone turret capped with a tall conical spire + iron finial."""
    k.cyl(P, 8, r, top_z - base_z, (x, y, (base_z + top_z) / 2), "stone")
    k.cyl(P, 8, r + 0.03, 0.08, (x, y, top_z), "stone_dk")               # corbel ring
    k.cone(P, 8, r + 0.06, 0.0, 0.7, (x, y, top_z + 0.35), cap)          # witch-hat spire
    k.cyl(P, 6, 0.02, 0.22, (x, y, top_z + 0.78), "iron")               # finial
    k.box(P, 0.07, 0.05, 0.2, (x, y - r, base_z + (top_z - base_z) * 0.6), "ember")  # slit


def _arch_win(k, P, cx, cz, fy, w=0.18, h=0.34, glow="ember"):
    """A pointed-arch lancet window on a -y face: stone surround + glow + point."""
    k.box(P, w + 0.08, 0.05, h + 0.06, (cx, fy + 0.03, cz), "stone_dk")   # surround
    k.box(P, w, 0.04, h, (cx, fy + 0.01, cz), glow)                      # lit pane
    k.cone(P, 4, w * 0.7, 0.0, w * 0.9, (cx, fy + 0.01, cz + h / 2 + w * 0.35), glow)  # point


def _arch_win_x(k, P, cy, cz, fx, w=0.16, h=0.3, glow="ember"):
    """A pointed-arch lancet window on a side (±x) face, proud of the wall."""
    s = 1 if fx > 0 else -1
    k.box(P, 0.05, w + 0.08, h + 0.06, (fx + s * 0.02, cy, cz), "stone_dk")   # surround
    k.box(P, 0.04, w, h, (fx + s * 0.035, cy, cz), glow)                     # lit pane
    k.cone(P, 4, w * 0.7, 0.0, w * 0.9, (fx + s * 0.035, cy, cz + h / 2 + w * 0.35), glow)


def _gargoyle(k, P, x, y, z, a):
    """A crouching stone gargoyle jutting outward, facing angle ``a`` in the XY
    plane: hunched body, horned head, a jutting snout, folded wings, forelegs."""
    ox, oy = math.cos(a), math.sin(a)
    px, py = -math.sin(a), math.cos(a)

    def at(f, s, u):
        return (x + ox * f + px * s, y + oy * f + py * s, z + u)

    k.box(P, 0.18, 0.18, 0.12, at(0.02, 0, 0.06), "stone_dk")            # ledge slab
    k.box(P, 0.13, 0.13, 0.16, at(0.12, 0, 0.16), "stone_dk", rot=(0, 0, a))  # hunched body
    k.box(P, 0.1, 0.1, 0.1, at(0.24, 0, 0.22), "stone_dk", rot=(0, 0, a))     # head
    k.box(P, 0.12, 0.06, 0.05, at(0.34, 0, 0.19), "stone_dk", rot=(0, 0, a))  # jutting snout
    for s in (-1, 1):
        k.cone(P, 4, 0.03, 0, 0.09, at(0.24, s * 0.05, 0.31), "stone_dk")     # horns
        k.box(P, 0.02, 0.09, 0.2, at(0.0, s * 0.1, 0.2), "stone_dk", rot=(0, 0, a))  # wing
        k.box(P, 0.05, 0.05, 0.12, at(0.26, s * 0.06, 0.04), "stone_dk", rot=(0, 0, a))  # foreleg


def manor(k):
    """The city's grand occult manor: a battlemented stone hall crowned by a
    leaded DOME + lantern cupola, four spired corner TURRETS, ranks of ember-lit
    Gothic lancet windows, a great pointed-arch doorway, and climbing ivy."""
    P = []
    W, D = 2.2, 1.6
    k.box(P, W + 0.2, D + 0.2, 0.24, (0, 0, 0.12), "stone_dk")           # footing
    k.box(P, W, D, 1.9, (0, 0, 0.24 + 0.95), "stone")                   # main block
    for cz in (0.9, 1.5):
        k.box(P, W + 0.06, D + 0.06, 0.06, (0, 0, cz), "stone_dk")       # string courses
    ptop = 0.24 + 1.9
    k.box(P, W + 0.1, D + 0.1, 0.12, (0, 0, ptop), "stone_dk")           # parapet
    for s in (-1, 1):
        _merlons(k, P, 0, s * (D / 2), W, 0.12, ptop + 0.14, n=9)        # battlements
    # central leaded dome + lantern cupola
    dz = ptop + 0.1
    k.cyl(P, 12, 0.52, 0.5, (0, 0, dz + 0.25), "stone")                 # rotunda drum
    for a in range(6):
        an = math.radians(a * 60 + 30)
        k.box(P, 0.08, 0.08, 0.22, (math.cos(an) * 0.52, math.sin(an) * 0.52,
              dz + 0.28), "ember")                                       # drum windows
    k.cyl(P, 12, 0.56, 0.06, (0, 0, dz + 0.5), "stone_dk")              # cornice
    dbase = dz + 0.53                                                   # rounded leaded dome
    zc = dbase
    for r, hh in ((0.5, 0.14), (0.44, 0.13), (0.36, 0.12), (0.26, 0.12), (0.15, 0.1)):
        k.cyl(P, 12, r, hh, (0, 0, zc + hh / 2), "slate")
        zc += hh
    for a in range(8):                                                 # dome ribs
        an = math.radians(a * 45)
        k.box(P, 0.03, 0.03, 0.34, (math.cos(an) * 0.44, math.sin(an) * 0.44,
              dbase + 0.16), "stone_dk")
    k.cyl(P, 8, 0.13, 0.2, (0, 0, zc + 0.1), "stone")                 # lantern cupola
    k.cone(P, 8, 0.15, 0, 0.24, (0, 0, zc + 0.32), "slate")           # cupola cap
    k.cyl(P, 6, 0.02, 0.3, (0, 0, zc + 0.55), "iron")                 # finial
    # four spired corner turrets
    for sx in (-1, 1):
        for sy in (-1, 1):
            _spire_turret(k, P, sx * (W / 2 + 0.06), sy * (D / 2 + 0.02), 0.3, ptop + 0.25)
    # ranks of ember-lit Gothic lancet windows on the front (-y)
    fy = -D / 2
    for cz in (0.75, 1.35):
        for cx in (-0.7, -0.35, 0.35, 0.7):
            _arch_win(k, P, cx, cz, fy)
    # side (±x) lancet windows
    for fx in (-W / 2, W / 2):
        for cy in (-0.4, 0.4):
            for cz in (0.75, 1.35):
                _arch_win_x(k, P, cy, cz, fx)
    # gargoyles jutting from the parapet (front pair + one each side)
    gz = ptop - 0.02
    _gargoyle(k, P, -0.5, fy, gz, -math.pi / 2)
    _gargoyle(k, P, 0.5, fy, gz, -math.pi / 2)
    _gargoyle(k, P, W / 2, 0.0, gz, 0.0)
    _gargoyle(k, P, -W / 2, 0.0, gz, math.pi)
    # great pointed-arch doorway
    k.box(P, 0.5, 0.06, 0.9, (0, fy + 0.02, 0.66), "stone_dk")          # portal surround
    k.box(P, 0.34, 0.06, 0.7, (0, fy - 0.01, 0.56), "charwood")         # dark door
    k.cone(P, 4, 0.28, 0, 0.34, (0, fy - 0.01, 1.12), "stone_dk")       # arch point
    for sx in (-1, 1):                                                  # climbing ivy
        for iz in (0.4, 0.7, 1.0):
            k.ico(P, 0.12, (sx * (W / 2 - 0.05), fy + 0.05, iz), "leaf_dk")
    return k.join(P, "manor")


def gatehouse(k):
    P = []
    for s in (-1, 1):
        k.box(P, 0.7, 0.9, 2.4, (s * 0.85, 0, 1.2), "stone")            # flanking towers
        _merlons(k, P, s * 0.85, 0, 0.7, 0.9, 2.65, n=3)
        k.box(P, 0.18, 0.06, 0.42, (s * 0.85, -0.46, 1.5), "ember")     # ember windows
    k.box(P, 1.05, 0.9, 0.5, (0, 0, 2.15), "stone")                     # arch block
    for x in (-0.3, -0.1, 0.1, 0.3):                                    # portcullis bars
        k.box(P, 0.05, 0.12, 1.3, (x, 0, 0.85), "iron")
    for z in (0.5, 1.0, 1.5):
        k.box(P, 0.72, 0.12, 0.05, (0, 0, z), "iron")
    k.box(P, 0.75, 0.1, 0.4, (0, -0.05, 1.6), "ember")                  # glow within the gate
    return k.join(P, "gatehouse")


def corner_tower(k):
    P = []
    k.cyl(P, 8, 0.6, 2.6, (0, 0, 1.3), "stone")
    k.cyl(P, 8, 0.68, 0.16, (0, 0, 2.62), "stone_dk")                   # corbel ring
    for a in range(8):                                                 # merlon ring
        an = math.radians(a * 45)
        k.box(P, 0.18, 0.18, 0.28, (math.cos(an) * 0.6, math.sin(an) * 0.6, 2.84), "stone_dk")
    for z in (1.0, 1.7):                                               # arrow-slit ember windows
        k.box(P, 0.08, 0.08, 0.42, (0, -0.6, z), "ember")
    k.box(P, 0.32, 0.08, 0.62, (0, -0.6, 0.41), "charwood")            # door
    return k.join(P, "corner_tower")


def wall_segment(k):
    P = []
    k.box(P, 2.0, 0.5, 1.4, (0, 0, 0.7), "stone")
    k.box(P, 2.0, 0.74, 0.1, (0, 0, 1.45), "stone_dk")                 # walkway lip
    for s in (-1, 1):
        _merlons(k, P, 0, s * 0.3, 2.0, 0.12, 1.64, n=5)
    k.box(P, 0.1, 0.08, 0.5, (0, -0.26, 0.8), "ember")                 # an arrow slit
    return k.join(P, "wall_segment")


def cathedral(k):
    """A towering occult cathedral: a slate nave with flying buttresses + ember
    lancets, a dominant bell-tower spire + cross, a ghostfire rose window,
    eave gargoyles, the flame-sigil banner, and moss/ivy."""
    P = []
    k.box(P, 1.6, 2.6, 0.3, (0, 0, 0.15), "stone_dk")                  # base
    k.box(P, 1.4, 2.4, 2.0, (0, 0, 1.2), "stone")                     # nave
    k.gable(P, 1.4, 2.4, 0.8, (0, 0, 2.2), "slate", over=0.22)
    sw = (1.4 + 0.22) / 2
    for f in (0.3, 0.65):                                             # roof course battens
        for sgn in (-1, 1):
            k.box(P, 0.03, 2.6, 0.05, (sgn * sw * (1 - f), 0, 2.2 + 0.8 * f),
                  "stone_dk", rot=(0, sgn * math.atan2(0.8, sw), 0))
    k.box(P, 0.8, 0.8, 3.0, (0, -1.4, 1.5), "stone")                  # bell tower
    for z in (2.2, 2.7):                                              # tower lancets
        k.box(P, 0.1, 0.1, 0.5, (0, -1.81, z), "ember")
    k.cone(P, 4, 0.56, 0, 1.3, (0, -1.4, 3.65), "slate", rot=(0, 0, math.radians(45)))
    k.box(P, 0.08, 0.08, 0.5, (0, -1.4, 4.5), "gold")                 # finial cross
    k.box(P, 0.3, 0.08, 0.08, (0, -1.4, 4.6), "gold")
    for s in (-1, 1):                                                 # flying buttresses
        for yy in (-0.6, 0.4):
            k.box(P, 0.2, 0.2, 1.6, (s * 0.82, yy, 0.95), "stone_dk")
        for yy in (-0.4, 0.4, 1.0):
            _arch_win_x(k, P, yy, 1.4, s * 0.72, w=0.12, h=0.5)      # arched ember windows
    k.cyl(P, 8, 0.3, 0.04, (0, -1.79, 2.3), "stone_dk", rot=(math.radians(90), 0, 0))  # rose frame
    k.cyl(P, 8, 0.26, 0.06, (0, -1.81, 2.3), "gem", rot=(math.radians(90), 0, 0))  # stained glass
    k.box(P, 0.5, 0.04, 0.05, (0, -1.83, 2.3), "stone_dk")            # rose bar h
    k.box(P, 0.05, 0.04, 0.5, (0, -1.83, 2.3), "stone_dk")            # rose bar v
    _gargoyle(k, P, 0.7, -1.2, 2.0, 0.0)                             # eave gargoyles
    _gargoyle(k, P, -0.7, -1.2, 2.0, math.pi)
    _flame_banner(k, P, 0.0, -1.85, 1.2, s=0.5)                      # warding banner
    for sx in (-1, 1):                                               # moss / ivy
        for iz in (0.4, 0.8):
            k.ico(P, 0.12, (sx * 0.7, -1.2, iz), "leaf_dk")
    return k.join(P, "cathedral")


def townhouse(k):
    """A tall occult Victorian townhouse: dark clapboard body on a stone stoop, a
    rounded bay-window tower, wrought-iron balconies, ember windows all round, a
    steep mansard roof with dormers + chimney, and ivy."""
    P = []
    W, D = 1.1, 1.0
    k.box(P, W + 0.14, D + 0.14, 0.3, (0, 0, 0.15), "stone")             # stone stoop base
    k.box(P, W, D, 2.1, (0, 0, 0.3 + 1.05), "charwood")                 # clapboard body
    for cz in (0.75, 1.4, 2.05):
        k.box(P, W + 0.03, D + 0.03, 0.04, (0, 0, cz), "wood_dk")        # belt courses
    fy = -D / 2
    k.cyl(P, 8, 0.28, 1.5, (0, fy - 0.1, 0.3 + 0.75), "charwood")       # rounded bay tower
    for cz in (0.6, 1.05, 1.45):
        for a in (-32, 0, 32):
            an = math.radians(a)
            k.box(P, 0.11, 0.04, 0.26, (math.sin(an) * 0.28,
                  fy - 0.1 - math.cos(an) * 0.28, cz), "ember", rot=(0, 0, an))
    for cz in (1.5, 2.05):                                              # wrought balconies
        k.box(P, W + 0.18, 0.05, 0.04, (0, fy - 0.05, cz - 0.02), "iron")
        for bx in (-0.45, -0.15, 0.15, 0.45):
            k.box(P, 0.02, 0.02, 0.16, (bx, fy - 0.08, cz + 0.06), "iron")
        k.box(P, W + 0.18, 0.02, 0.02, (0, fy - 0.08, cz + 0.14), "iron")
    for fx in (-W / 2, W / 2):                                          # side ember windows
        s = 1 if fx > 0 else -1
        for cz in (0.7, 1.35, 2.0):
            k.box(P, 0.04, 0.16, 0.3, (fx + s * 0.02, 0.12, cz), "ember")
    top = 0.3 + 2.1
    k.box(P, W + 0.06, D + 0.06, 0.5, (0, 0, top + 0.25), "slate")      # mansard roof
    k.box(P, W - 0.28, D - 0.28, 0.16, (0, 0, top + 0.55), "slate")
    for dx in (-0.28, 0.28):                                            # dormers
        k.box(P, 0.2, 0.18, 0.22, (dx, fy + 0.12, top + 0.22), "charwood")
        k.gable(P, 0.24, 0.2, 0.12, (dx, fy + 0.12, top + 0.33), "slate", over=0.03)
        k.box(P, 0.1, 0.05, 0.14, (dx, fy + 0.03, top + 0.24), "ember")
    k.box(P, 0.16, 0.16, 0.5, (0.34, 0.34, top + 0.45), "stone_dk")     # chimney
    for i in range(3):                                                 # stooped entrance
        k.box(P, 0.5 - i * 0.06, 0.16, 0.08, (0, fy - 0.22 + i * 0.05,
              0.1 + i * 0.08), "stone")
    k.box(P, 0.28, 0.08, 0.6, (0, fy + 0.06, 0.62), "wood_dk")          # door
    for sx in (-1, 1):                                                  # ivy
        for iz in (0.5, 0.9):
            k.ico(P, 0.1, (sx * (W / 2 - 0.02), fy + 0.05, iz), "leaf_dk")
    return k.join(P, "townhouse")


def town_hall(k):
    """A grim civic hall: a long stone block with a mansard roof + dormers, a
    central CLOCK tower with a leaded cap, a columned portico flying the flame
    banner, ember windows, gargoyles, and moss."""
    P = []
    W, D = 2.6, 1.5
    fy = -D / 2
    k.box(P, W + 0.2, D + 0.2, 0.24, (0, 0, 0.12), "stone_dk")           # footing
    k.box(P, W, D, 1.7, (0, 0, 0.24 + 0.85), "stone")                   # main block
    for cz in (0.85, 1.45):
        k.box(P, W + 0.05, D + 0.05, 0.05, (0, 0, cz), "stone_dk")       # string courses
    top = 0.24 + 1.7
    k.box(P, W, D, 0.46, (0, 0, top + 0.23), "slate")                   # mansard roof mass
    k.box(P, W - 0.6, D - 0.5, 0.14, (0, 0, top + 0.53), "slate")       # flat top
    for dx in (-0.85, 0.0, 0.85):                                       # front dormers
        k.box(P, 0.26, 0.2, 0.24, (dx, fy + 0.06, top + 0.24), "stone")
        k.gable(P, 0.3, 0.24, 0.13, (dx, fy + 0.06, top + 0.36), "slate", over=0.04)
        k.box(P, 0.12, 0.05, 0.15, (dx, fy - 0.02, top + 0.26), "ember")
    tw = 0.66                                                          # central clock tower
    k.box(P, tw, tw, 1.0, (0, -0.1, top + 0.5), "stone")
    k.box(P, tw + 0.08, tw + 0.08, 0.08, (0, -0.1, top + 1.02), "stone_dk")
    k.cone(P, 4, tw * 0.8, 0.1, 0.7, (0, -0.1, top + 1.45), "slate", rot=(0, 0, math.radians(45)))
    k.cyl(P, 6, 0.02, 0.3, (0, -0.1, top + 1.9), "iron")               # finial
    cf = -0.1 - tw / 2                                                 # clock face on the front
    k.cyl(P, 12, 0.2, 0.03, (0, cf - 0.01, top + 0.75), "bone", rot=(math.radians(90), 0, 0))
    k.box(P, 0.02, 0.02, 0.14, (0, cf - 0.03, top + 0.79), "iron", rot=(math.radians(90), 0, 0))
    k.box(P, 0.1, 0.02, 0.02, (0.05, cf - 0.03, top + 0.75), "iron")
    for sx in (-1, 1):                                                 # columned portico
        for px in (0.25, 0.55):
            k.cyl(P, 8, 0.06, 0.8, (sx * px, fy - 0.26, 0.64), "stone")
    k.box(P, 1.3, 0.42, 0.12, (0, fy - 0.26, 1.08), "stone_dk")         # portico roof
    k.box(P, 0.5, 0.1, 0.9, (0, fy + 0.04, 0.66), "charwood")           # doors
    for cz in (0.7, 1.25):                                             # ember windows
        for cx in (-1.0, -0.6, 0.6, 1.0):
            k.box(P, 0.16, 0.05, 0.34, (cx, fy - 0.02, cz), "ember")
    for fx in (-W / 2, W / 2):
        s = 1 if fx > 0 else -1
        for cy in (-0.4, 0.4):
            k.box(P, 0.04, 0.16, 0.32, (fx + s * 0.02, cy, 1.0), "ember")
    _gargoyle(k, P, -W / 2, 0.0, top - 0.02, math.pi)
    _gargoyle(k, P, W / 2, 0.0, top - 0.02, 0.0)
    _flame_banner(k, P, 0.0, fy - 0.28, 0.98, s=0.5)                    # banner on the portico
    for sx in (-1, 1):
        for iz in (0.4, 0.8):
            k.ico(P, 0.12, (sx * (W / 2 - 0.05), fy + 0.05, iz), "leaf_dk")
    return k.join(P, "town_hall")


def rowhouse(k):
    """A tall narrow stone row house: a stepped Flemish gable, three storeys of
    ember windows (big at street level) with small wrought balconies, side
    windows, a wood door, a pillar-box out front, and moss."""
    P = []
    W, D = 1.0, 0.9
    fy = -D / 2
    k.box(P, W + 0.12, D + 0.12, 0.2, (0, 0, 0.1), "stone_dk")           # footing
    k.box(P, W, D, 2.4, (0, 0, 0.2 + 1.2), "stone")                     # body
    for cz in (0.9, 1.55, 2.2):
        k.box(P, W + 0.04, D + 0.04, 0.05, (0, 0, cz), "stone_dk")       # string courses
    zt = 0.2 + 2.4                                                      # stepped Flemish gable
    for i, r in enumerate((1.0, 0.72, 0.46, 0.22)):
        k.box(P, W * r, D + 0.02, 0.16, (0, 0, zt + 0.08 + i * 0.16), "stone")
    k.cone(P, 6, 0.1, 0, 0.2, (0, 0, zt + 0.74), "stone_dk")            # gable finial
    _arch_win(k, P, 0.0, 0.62, fy, w=0.34, h=0.5)                       # big ground window
    for cz in (1.3, 1.95):                                              # upper windows + balconies
        for cx in (-0.24, 0.24):
            _arch_win(k, P, cx, cz, fy, w=0.16, h=0.32)
        k.box(P, W + 0.1, 0.05, 0.04, (0, fy - 0.05, cz - 0.24), "iron")
        for bx in (-0.35, 0.0, 0.35):
            k.box(P, 0.02, 0.02, 0.14, (bx, fy - 0.07, cz - 0.16), "iron")
        k.box(P, W + 0.1, 0.02, 0.02, (0, fy - 0.07, cz - 0.1), "iron")
    for fx in (-W / 2, W / 2):                                          # side windows
        for cz in (0.7, 1.3, 1.95):
            _arch_win_x(k, P, 0.0, cz, fx, w=0.13, h=0.26)
    k.box(P, 0.3, 0.08, 0.66, (0, fy + 0.04, 0.53), "wood_dk")          # door
    if OCCULT:
        k.cyl(P, 8, 0.12, 0.5, (0.8, fy - 0.25, 0.25), "crimson")       # pillar-box
        k.cone(P, 8, 0.13, 0.04, 0.1, (0.8, fy - 0.25, 0.55), "crimson")
        k.box(P, 0.08, 0.02, 0.03, (0.8, fy - 0.37, 0.45), "soot")      # post slot
    else:
        k.cyl(P, 10, 0.14, 0.42, (0.8, fy - 0.25, 0.21), "wood_dk")     # water barrel
        k.cyl(P, 10, 0.142, 0.03, (0.8, fy - 0.25, 0.34), "iron")
    for sx in (-1, 1):
        for iz in (0.5, 1.0):
            k.ico(P, 0.1, (sx * (W / 2 - 0.02), fy + 0.05, iz), "leaf_dk")
    return k.join(P, "rowhouse")


def guild_hall(k):
    P = []
    k.box(P, 1.8, 1.3, 0.9, (0, 0, 0.45), "stone")
    k.box(P, 1.7, 1.2, 0.7, (0, 0, 1.25), "charwood")
    for x in (-0.6, 0.0, 0.6):
        k.box(P, 0.08, 1.22, 0.7, (x, 0, 1.25), "wood_dk")
    k.gable(P, 1.8, 1.3, 0.6, (0, 0, 1.6), "slate", over=0.2)
    k.box(P, 0.5, 0.08, 0.8, (0, -0.65, 0.4), "wood_dk")             # big door
    for wx in (-0.55, 0.55):
        k.box(P, 0.24, 0.06, 0.3, (wx, -0.66, 0.55), "ember")
        k.box(P, 0.2, 0.05, 0.24, (wx * 0.9, -0.61, 1.25), "ember")
    k.box(P, 0.04, 0.04, 0.4, (0.0, -0.72, 1.0), "wood_dk")          # sign bracket + sign
    k.box(P, 0.34, 0.04, 0.24, (0.0, -0.74, 0.82), "crimson")
    k.box(P, 0.16, 0.05, 0.12, (0.0, -0.76, 0.82), "gold")
    return k.join(P, "guild_hall")


def keep(k):
    P = []
    k.box(P, 2.0, 2.0, 0.3, (0, 0, 0.15), "stone_dk")
    k.box(P, 1.7, 1.7, 2.6, (0, 0, 1.3), "stone")
    for sx in (-1, 1):                                               # corner turrets
        for sy in (-1, 1):
            k.cyl(P, 6, 0.28, 2.9, (sx * 0.85, sy * 0.85, 1.45), "stone")
            for a in range(6):
                an = math.radians(a * 60)
                k.box(P, 0.12, 0.12, 0.22,
                      (sx * 0.85 + math.cos(an) * 0.27, sy * 0.85 + math.sin(an) * 0.27, 2.96),
                      "stone_dk")
    for s in (-1, 1):                                                # main battlements
        _merlons(k, P, 0, s * 0.82, 1.7, 0.16, 2.76, n=5)
    for z in (1.0, 1.8):
        k.box(P, 0.1, 0.06, 0.5, (0, -0.86, z), "ember")
    k.box(P, 0.42, 0.06, 0.8, (0, -0.86, 0.5), "charwood")           # door
    return k.join(P, "keep")


def fountain(k):
    """An occult city fountain: a cracked stone basin of dark, faintly
    ghostfire-glowing water, a central column topped by a skull spout, rim
    gargoyles, and moss."""
    P = []
    k.cyl(P, 10, 0.8, 0.3, (0, 0, 0.15), "stone")                  # basin wall
    k.cyl(P, 10, 0.84, 0.08, (0, 0, 0.3), "stone_dk")              # rim lip
    k.cyl(P, 10, 0.7, 0.05, (0, 0, 0.28), "cloth")                 # water base
    k.cyl(P, 12, 0.66, 0.02, (0, 0, 0.31), "ghostfire")           # glowing lower water
    k.cyl(P, 8, 0.18, 0.8, (0, 0, 0.65), "stone_dk")               # central column
    k.cyl(P, 8, 0.34, 0.08, (0, 0, 1.0), "stone")                 # upper basin
    k.cyl(P, 8, 0.26, 0.04, (0, 0, 1.05), "cloth")                # upper water
    k.cyl(P, 10, 0.2, 0.015, (0, 0, 1.07), "ghostfire")          # upper glow
    skull(k, P, 0.0, -0.34, 0.72, 0.12)                          # skull on the column
    for a in (30, 150, 270):                                      # rim gargoyles + moss
        an = math.radians(a)
        _gargoyle(k, P, math.cos(an) * 0.72, math.sin(an) * 0.72, 0.22, an)
        k.ico(P, 0.1, (math.cos(an + 1.0) * 0.8, math.sin(an + 1.0) * 0.8, 0.08), "leaf_dk")
    return k.join(P, "fountain")


def gallows_platform(k):
    P = []
    k.box(P, 1.6, 1.2, 0.4, (0, 0, 0.2), "wood_dk")                 # platform
    for i in range(3):                                             # side steps
        k.box(P, 1.6, 0.22, 0.13, (0, 0.7 + i * 0.2, 0.33 - i * 0.13), "wood_dk")
    for sx in (-0.6, 0.6):
        k.box(P, 0.12, 0.12, 1.6, (sx, 0, 1.2), "wood_dk")         # uprights
    k.box(P, 1.4, 0.12, 0.12, (0, 0, 1.95), "wood_dk")             # top beam
    for nx in (-0.4, 0.0, 0.4):                                    # three hollow nooses
        k.cyl(P, 5, 0.02, 0.4, (nx, 0, 1.62), "bone")
        for a in range(6):
            an = math.radians(a * 60)
            k.box(P, 0.04, 0.04, 0.05, (nx + math.cos(an) * 0.08, math.sin(an) * 0.08, 1.4),
                  "bone", rot=(0, 0, an))
    return k.join(P, "gallows_platform")


def street_brazier(k):
    P = []
    k.box(P, 0.32, 0.32, 0.2, (0, 0, 0.1), "stone_dk")
    k.cyl(P, 8, 0.1, 1.1, (0, 0, 0.65), "stone")
    k.cyl(P, 8, 0.24, 0.16, (0, 0, 1.25), "gunmetal")
    k.cone(P, 6, 0.2, 0, 0.3, (0, 0, 1.45), "ember")
    k.cone(P, 5, 0.1, 0, 0.2, (0.04, 0, 1.52), "amber")
    return k.join(P, "street_brazier")


def statue(k):
    P = []
    k.box(P, 0.7, 0.7, 0.4, (0, 0, 0.2), "stone_dk")               # pedestal
    k.box(P, 0.5, 0.5, 0.16, (0, 0, 0.48), "stone")
    k.box(P, 0.3, 0.26, 0.8, (0, 0, 1.0), "stone")                 # robed body
    k.box(P, 0.12, 0.12, 0.7, (0.28, 0, 1.05), "stone",            # outstretched arm + staff
          rot=(0, math.radians(20), 0))
    k.cone(P, 6, 0.22, 0.08, 0.34, (0, 0, 1.55), "stone")          # hooded shoulders
    k.ico(P, 0.13, (0, 0.02, 1.78), "stone", sub=1)                # head
    k.cone(P, 6, 0.17, 0, 0.18, (0, 0.02, 1.9), "stone_dk")        # hood point
    return k.join(P, "statue")


def stone_bridge(k):
    P = []
    k.box(P, 1.2, 2.2, 0.3, (0, 0, -0.15), "water")               # dark water
    k.box(P, 1.2, 2.4, 0.26, (0, 0, 0.6), "stone")                 # deck
    k.cyl(P, 12, 0.5, 1.2, (0, 0, 0.12), "stone", rot=(math.radians(90), 0, 0))  # arch under
    for s in (-1, 1):
        k.box(P, 0.14, 2.4, 0.32, (s * 0.5, 0, 0.85), "stone_dk")  # parapets
        for yy in (-0.8, 0.0, 0.8):
            k.box(P, 0.16, 0.16, 0.16, (s * 0.5, yy, 1.04), "stone")  # posts
    return k.join(P, "stone_bridge")


def shopfront(k):
    """A derelict porched wooden store: clapboard body with a gabled shingle roof
    (battens + dormers + a big arched gable window), a deep covered porch with
    posts + railing, ember shop windows, a hung sign, barrels/crate, a bare tree,
    and moss."""
    P = []
    W, D = 1.8, 1.2
    fy = -D / 2
    k.box(P, W + 0.3, D + 1.2, 0.14, (0, -0.3, 0.07), "stone_dk")   # pavement (front apron)
    k.box(P, W, D, 1.3, (0, 0, 0.14 + 0.65), "charwood")           # clapboard body
    for cz in (0.5, 0.95):
        k.box(P, W + 0.03, D + 0.03, 0.04, (0, 0, cz), "wood_dk")   # clapboard courses
    rh = 0.7
    zt = 0.14 + 1.3
    k.gable(P, W, D, rh, (0, 0, zt), "slate", over=0.2)
    sw = (W + 0.2) / 2
    for f in (0.3, 0.6):                                            # shingle battens
        for sgn in (-1, 1):
            k.box(P, 0.03, D + 0.22, 0.05, (sgn * sw * (1 - f), 0, zt + rh * f),
                  "stone_dk", rot=(0, sgn * math.atan2(rh, sw), 0))
    gfy = -(D + 0.2) / 2                                            # arched gable window
    k.box(P, 0.5, 0.05, 0.4, (0, gfy + 0.02, zt + 0.32), "stone_dk")
    k.cyl(P, 8, 0.22, 0.04, (0, gfy, zt + 0.36), "ember", rot=(math.radians(90), 0, 0))
    for dx in (-0.55, 0.55):                                        # dormers
        k.box(P, 0.22, 0.2, 0.22, (dx, 0, zt + 0.05), "charwood")
    fp = fy - 0.28                                                  # covered porch
    k.box(P, W + 0.3, 0.62, 0.06, (0, fp, 0.94), "wood")           # porch roof
    for px in (-0.8, -0.27, 0.27, 0.8):
        k.box(P, 0.07, 0.07, 0.9, (px, fy - 0.5, 0.47), "wood_dk")  # porch posts
        k.box(P, 0.05, 0.05, 0.32, (px, fp, 0.28), "wood_dk")       # rail posts
    k.box(P, W + 0.1, 0.04, 0.04, (0, fp, 0.42), "wood_dk")         # porch rail
    for wx in (-0.6, 0.6):                                          # shop windows
        k.box(P, 0.34, 0.05, 0.42, (wx, fy + 0.02, 0.62), "ember")
    k.box(P, 0.3, 0.08, 0.6, (0, fy + 0.04, 0.44), "wood_dk")       # door
    k.box(P, 0.04, 0.24, 0.04, (W / 2 + 0.02, fy - 0.5, 0.98), "iron")   # sign bracket
    for cx in (-0.1, 0.1):
        k.box(P, 0.02, 0.02, 0.12, (W / 2 + 0.14 + cx, fy - 0.5, 0.88), "iron")   # chains
    k.box(P, 0.28, 0.02, 0.18, (W / 2 + 0.14, fy - 0.5, 0.76), "crimson")   # sign board
    k.cyl(P, 10, 0.12, 0.26, (-0.7, fp, 0.27), "wood_dk")          # barrel
    k.cyl(P, 10, 0.122, 0.02, (-0.7, fp, 0.34), "iron")
    k.box(P, 0.2, 0.2, 0.2, (0.75, fp - 0.02, 0.24), "wood")       # crate
    tx = W / 2 + 0.5                                               # bare tree
    k.cyl(P, 6, 0.05, 1.2, (tx, -0.2, 0.6), "charwood")
    for ang, zz in ((32, 1.0), (-42, 1.1), (12, 1.25)):
        k.box(P, 0.03, 0.03, 0.4, (tx, -0.2, zz), "charwood", rot=(math.radians(ang), 0, 0))
    for iz in (0.3, 0.6):
        k.ico(P, 0.1, (-W / 2 + 0.05, fy + 0.05, iz), "leaf_dk")
    return k.join(P, "shopfront")


def draped_statue(k):
    """A shrouded verdigris memorial statue: a robed, blindfolded figure with
    flowing drapery on a cracked, mossy stone plinth, holding scales and a
    downturned sword."""
    P = []
    k.box(P, 0.8, 0.8, 0.3, (0, 0, 0.15), "stone_dk")           # plinth tiers
    k.box(P, 0.64, 0.64, 0.5, (0, 0, 0.55), "stone")
    k.box(P, 0.52, 0.52, 0.1, (0, 0, 0.85), "stone_dk")
    for a in (40, 210):
        an = math.radians(a)
        k.box(P, 0.02, 0.03, 0.4, (math.cos(an) * 0.32, math.sin(an) * 0.32, 0.55), "soot")
    for a in (100, 300):
        an = math.radians(a)
        k.ico(P, 0.09, (math.cos(an) * 0.42, math.sin(an) * 0.42, 0.05), "leaf_dk")
    vg = "cloth"                                                # weathered verdigris bronze
    k.cone(P, 8, 0.26, 0.12, 0.9, (0, 0, 1.35), vg)            # flaring robe
    for s in (-1, 1):
        k.box(P, 0.06, 0.16, 0.5, (s * 0.22, 0.06, 1.3), vg, rot=(math.radians(s * 14), 0, 0))
    k.box(P, 0.2, 0.14, 0.3, (0, 0, 1.9), vg)                  # torso
    k.ico(P, 0.11, (0, -0.02, 2.15), vg)                       # head
    k.box(P, 0.2, 0.05, 0.06, (0, -0.11, 2.16), "bone")       # blindfold
    k.box(P, 0.28, 0.06, 0.06, (0.18, -0.05, 2.05), vg, rot=(0, math.radians(-30), 0))  # arm up
    k.box(P, 0.24, 0.04, 0.03, (0.34, -0.05, 2.2), "iron")    # scale beam
    for sx in (-1, 1):
        k.box(P, 0.02, 0.02, 0.1, (0.34 + sx * 0.1, -0.05, 2.14), "iron")   # chains
        k.cyl(P, 6, 0.05, 0.02, (0.34 + sx * 0.1, -0.05, 2.09), "iron")     # pans
    k.box(P, 0.06, 0.06, 0.3, (-0.2, -0.05, 1.85), vg)        # arm down
    k.box(P, 0.03, 0.04, 0.5, (-0.24, -0.08, 1.55), "steel")  # sword blade
    k.box(P, 0.14, 0.04, 0.03, (-0.24, -0.08, 1.78), "iron")  # crossguard
    return k.join(P, "draped_statue")


def canal_bridge(k):
    """A humped stone canal bridge over dark, faintly glowing water: an arched
    deck with balustrade railings, a carved skull keystone, an iron lamp, and
    mossy abutments."""
    P = []
    k.box(P, 1.4, 2.4, 0.5, (0, 0, -0.28), "cloth")           # dark water
    for gy in (-0.5, 0.3, 0.8):
        k.box(P, 0.4, 0.12, 0.02, (gy * 0.2, gy, -0.02), "ghostfire")   # glints
    for sy in (-1, 1):                                         # mossy abutments
        k.box(P, 1.2, 0.5, 0.6, (0, sy * 0.95, 0.1), "stone")
        for mx in (-0.4, 0.3):
            k.ico(P, 0.1, (mx, sy * 0.9, 0.4), "leaf_dk")
    k.cyl(P, 12, 0.34, 0.9, (0, 0, 0.32), "stone_dk", rot=(0, math.radians(90), 0))  # arch
    k.box(P, 0.9, 0.9, 0.2, (0, 0, 0.62), "stone")           # deck crown
    for sy in (-1, 1):                                         # ramps
        k.box(P, 0.9, 0.7, 0.16, (0, sy * 0.6, 0.5), "stone", rot=(math.radians(-sy * 12), 0, 0))
    for sx in (-1, 1):                                         # balustrade
        k.box(P, 0.06, 1.9, 0.06, (sx * 0.42, 0, 0.78), "stone")
        for by in (-0.6, -0.2, 0.2, 0.6):
            k.box(P, 0.05, 0.05, 0.24, (sx * 0.42, by, 0.68), "stone_dk")
    skull(k, P, 0.0, -0.46, 0.66, 0.1)                        # skull keystone
    k.cyl(P, 6, 0.03, 0.5, (0.42, -0.85, 0.9), "iron")        # lamp post
    k.box(P, 0.1, 0.1, 0.12, (0.42, -0.85, 1.18), "soot")
    k.box(P, 0.06, 0.06, 0.08, (0.42, -0.85, 1.18), "amber")
    return k.join(P, "canal_bridge")


def streetlamp(k):
    """A wrought-iron Victorian gaslamp: stepped base, fluted post with a collar,
    a scroll crossbar, a caged amber lantern head with a slate cap, and a raven."""
    P = []
    k.box(P, 0.3, 0.3, 0.12, (0, 0, 0.06), "stone_dk")        # base slab
    k.cyl(P, 8, 0.09, 0.16, (0, 0, 0.18), "iron")             # plinth
    k.cyl(P, 6, 0.05, 1.4, (0, 0, 0.9), "iron")               # fluted post
    k.cyl(P, 8, 0.07, 0.06, (0, 0, 0.95), "iron")             # collar
    for s in (-1, 1):
        k.box(P, 0.18, 0.03, 0.03, (s * 0.09, 0, 1.6), "iron")   # scroll crossbar
    k.box(P, 0.16, 0.16, 0.04, (0, 0, 1.66), "iron")          # lantern base
    k.box(P, 0.13, 0.13, 0.18, (0, 0, 1.77), "amber")        # glowing core
    for sx in (-1, 1):
        for sy in (-1, 1):
            k.box(P, 0.02, 0.02, 0.2, (sx * 0.07, sy * 0.07, 1.77), "soot")  # cage bars
    k.cone(P, 4, 0.12, 0, 0.14, (0, 0, 1.93), "slate")       # cap
    k.cyl(P, 6, 0.015, 0.14, (0, 0, 2.05), "iron")           # finial
    k.ico(P, 0.06, (0.16, 0, 1.62), "soot")                  # raven
    k.cone(P, 4, 0.03, 0, 0.08, (0.24, 0, 1.62), "soot", rot=(0, math.radians(90), 0))
    return k.join(P, "streetlamp")


def street_kiosk(k):
    """Gaslamp street furniture on a cobbled base: a roofed newsstand booth with
    papers + an inner glow, a pillar-box, a fire hydrant, and an iron bench."""
    P = []
    k.box(P, 1.6, 1.0, 0.12, (0, 0, 0.06), "stone_dk")        # cobbled base
    bx = -0.5
    k.box(P, 0.6, 0.5, 0.7, (bx, 0.1, 0.47), "wood_dk")       # booth body
    k.box(P, 0.52, 0.3, 0.2, (bx, -0.18, 0.66), "soot")       # open counter (dark)
    k.box(P, 0.4, 0.24, 0.14, (bx, -0.16, 0.66), "amber")     # inner glow
    k.box(P, 0.72, 0.6, 0.06, (bx, 0.05, 0.86), "slate", rot=(math.radians(10), 0, 0))  # awning
    for i, px in enumerate((-0.16, 0.0, 0.16)):
        k.box(P, 0.1, 0.08, 0.02, (bx + px, -0.28, 0.6), "bone" if i % 2 else "crimson")
    if OCCULT:
        k.cyl(P, 10, 0.13, 0.6, (0.15, -0.2, 0.36), "crimson")    # pillar-box
        k.cone(P, 10, 0.14, 0.05, 0.1, (0.15, -0.2, 0.68), "crimson")
        k.box(P, 0.08, 0.02, 0.03, (0.15, -0.33, 0.5), "soot")   # slot
        k.cyl(P, 8, 0.06, 0.24, (0.55, -0.28, 0.18), "gunmetal")  # fire hydrant
        k.cone(P, 8, 0.07, 0.03, 0.06, (0.55, -0.28, 0.32), "gunmetal")
        for s in (-1, 1):
            k.cyl(P, 6, 0.03, 0.06, (0.55 + s * 0.07, -0.28, 0.22), "gunmetal",
                  rot=(0, math.radians(90), 0))
    else:
        k.cyl(P, 10, 0.14, 0.4, (0.18, -0.24, 0.2), "wood_dk")    # market barrel
        k.cyl(P, 10, 0.142, 0.03, (0.18, -0.24, 0.32), "iron")
        k.box(P, 0.22, 0.2, 0.2, (0.56, -0.26, 0.16), "wood")     # crate
    k.box(P, 0.5, 0.16, 0.04, (0.5, 0.3, 0.26), "iron")      # bench seat
    k.box(P, 0.5, 0.04, 0.16, (0.5, 0.37, 0.36), "iron")     # bench back
    for lx in (0.3, 0.7):
        k.box(P, 0.04, 0.14, 0.24, (lx, 0.3, 0.14), "wood_dk")   # bench legs
    return k.join(P, "street_kiosk")


def plague_column(k):
    """A baroque plague-memorial column: a stepped pedestal set with skulls, a
    fluted column with carved bands, a capital, a crowning gilt sunburst + spike,
    cracks + moss, and a faint ghostfire glow."""
    P = []
    for i, r in enumerate((0.6, 0.46, 0.34)):                 # stepped pedestal
        k.box(P, r * 2, r * 2, 0.24, (0, 0, 0.12 + i * 0.24), "stone")
        k.box(P, r * 2 + 0.04, r * 2 + 0.04, 0.05, (0, 0, 0.24 + i * 0.24), "stone_dk")
    skull(k, P, -0.3, -0.62, 0.24, 0.1)                       # skulls set on the base tier
    skull(k, P, 0.3, -0.62, 0.24, 0.1)
    skull(k, P, 0.0, -0.48, 0.5, 0.09)                        # skull on the second tier
    k.cyl(P, 8, 0.18, 1.6, (0, 0, 1.7), "stone")             # column
    for z in (1.1, 1.5, 1.9, 2.3):
        k.cyl(P, 8, 0.2, 0.04, (0, 0, z), "stone_dk")        # carved bands
    k.cyl(P, 8, 0.26, 0.1, (0, 0, 2.55), "stone")           # capital
    k.box(P, 0.3, 0.3, 0.1, (0, 0, 2.64), "stone_dk")
    k.ico(P, 0.12, (0, 0, 2.85), "gold")                     # gilt sunburst
    for a in range(8):
        an = math.radians(a * 45)
        k.box(P, 0.16, 0.04, 0.04, (math.cos(an) * 0.18, math.sin(an) * 0.18, 2.85),
              "gold", rot=(0, 0, an))
    k.cyl(P, 6, 0.02, 0.3, (0, 0, 3.05), "iron")            # spike
    k.cyl(P, 10, 0.14, 0.015, (0, 0, 2.7), "ghostfire")     # faint glow
    for a in (60, 200, 320):
        an = math.radians(a)
        k.ico(P, 0.09, (math.cos(an) * 0.6, math.sin(an) * 0.6, 0.06), "leaf_dk")
    return k.join(P, "plague_column")


# Re-spec in progress → Victorian-Gothic gaslamp city (see
# project_grimforge_city_direction memory). Building item-by-item; PIECES grows
# as each new piece is reviewed. Target 12: manor, town_hall, townhouse,
# rowhouse, shopfront, cathedral, draped_statue, canal_bridge, fountain,
# streetlamp, street_kiosk, plague_column.
PIECES = [
    ("manor", manor),
    ("town_hall", town_hall),
    ("townhouse", townhouse),
    ("rowhouse", rowhouse),
    ("shopfront", shopfront),
    ("cathedral", cathedral),
    ("draped_statue", draped_statue),
    ("canal_bridge", canal_bridge),
    ("fountain", fountain),
    ("streetlamp", streetlamp),
    ("street_kiosk", street_kiosk),
    ("plague_column", plague_column),
]
