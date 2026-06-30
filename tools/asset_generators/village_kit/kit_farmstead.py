"""GrimForge Farmstead — demo spec for kit_pipeline (6 new pieces, Vol.3 preview).

Every builder takes a kitlib.Kit and returns a single joined object, using only
the canonical palette so the style matches Vol.1/Vol.2. Run via::

    blender -b --python kit_pipeline.py -- kit_farmstead.py <out_dir>
"""

import math

TITLE = "GrimForge Farmstead (Vol.3 preview)"
AESTHETIC = "medieval"


def scarecrow(k):
    P = []
    k.box(P, 0.08, 0.08, 1.4, (0, 0, 0.7), "wood_dk")            # post
    k.box(P, 0.9, 0.08, 0.08, (0, 0, 1.05), "wood_dk")           # cross arm
    k.box(P, 0.34, 0.22, 0.4, (0, 0, 1.0), "thatch")            # straw body
    k.ico(P, 0.16, (0, 0, 1.35), "plaster", sub=1)              # sack head
    k.cone(P, 4, 0.26, 0, 0.18, (0, 0, 1.5), "wood_dk")         # hat
    for s in (-1, 1):                                           # straw hands
        k.cone(P, 5, 0.07, 0, 0.18, (s * 0.42, 0, 1.05), "thatch",
               rot=(0, math.radians(s * 90), 0))
    return k.join(P, "scarecrow")


def chicken_coop(k):
    P = []
    k.box(P, 0.9, 0.7, 0.5, (0, 0, 0.3), "wood")                # hut body
    k.gable(P, 0.9, 0.7, 0.35, (0, 0, 0.55), "thatch")         # roof
    k.box(P, 0.22, 0.05, 0.26, (0, -0.36, 0.22), "wood_dk")    # door hole
    k.box(P, 0.5, 0.18, 0.04, (0, -0.5, 0.05), "wood_dk",      # ramp
          rot=(math.radians(18), 0, 0))
    for x in (-0.5, 0.5):                                       # run fence
        k.box(P, 0.05, 0.05, 0.4, (x, -0.7, 0.2), "wood_dk")
    k.box(P, 1.0, 0.05, 0.04, (0, -0.7, 0.32), "wood_dk")
    return k.join(P, "chicken_coop")


def veg_garden(k):
    P = []
    k.box(P, 1.0, 0.9, 0.12, (0, 0, 0.06), "dirt")             # tilled bed
    for ry in (-0.28, 0.0, 0.28):                              # rows of sprouts
        k.box(P, 0.9, 0.06, 0.05, (0, ry, 0.13), "wood_dk")    # furrow edge
        for x in (-0.34, -0.12, 0.12, 0.34):
            col = "leaf" if (x + ry) > 0 else "leaf_dk"
            k.cone(P, 5, 0.07, 0.0, 0.18, (x, ry, 0.2), col)
    return k.join(P, "veg_garden")


def beehive(k):
    P = []
    k.box(P, 0.5, 0.5, 0.12, (0, 0, 0.06), "wood")             # stand
    for i, (r, z) in enumerate([(0.26, 0.22), (0.22, 0.4), (0.16, 0.55)]):
        k.cyl(P, 10, r, 0.18, (0, 0, z), "thatch" if i % 2 == 0 else "thatch_dk")
    k.cone(P, 8, 0.16, 0, 0.12, (0, 0, 0.68), "thatch")        # cap
    k.box(P, 0.14, 0.04, 0.06, (0, -0.2, 0.22), "wood_dk")     # entrance
    return k.join(P, "beehive")


def plow(k):
    P = []
    k.box(P, 0.1, 1.1, 0.08, (0, 0.0, 0.2), "wood")            # beam
    for s in (-1, 1):                                          # handles
        k.box(P, 0.05, 0.05, 0.6, (s * 0.12, 0.5, 0.45), "wood",
              rot=(math.radians(-22), 0, 0))
    k.cone(P, 4, 0.18, 0, 0.34, (0, -0.5, 0.14), "iron",       # plowshare
           rot=(math.radians(90), 0, math.radians(45)))
    k.cyl(P, 10, 0.22, 0.06, (0, 0.2, 0.22), "wood_dk",        # wheel
          rot=(0, math.radians(90), 0))
    return k.join(P, "plow")


def pig_pen(k):
    P = []
    k.box(P, 1.2, 1.0, 0.06, (0, 0, 0.03), "dirt")             # muddy ground
    k.box(P, 0.7, 0.5, 0.04, (0.1, 0.1, 0.06), "wood_dk")      # mud wallow
    # rail fence around the perimeter
    for x in (-0.6, 0.6):
        for y in (-0.42, 0.0, 0.42):
            k.box(P, 0.06, 0.06, 0.4, (x, y, 0.2), "wood")
        k.box(P, 0.06, 1.0, 0.05, (x, 0, 0.3), "wood_dk")
    for y in (-0.5, 0.5):
        for x in (-0.4, 0.0, 0.4):
            k.box(P, 0.06, 0.06, 0.4, (x, y, 0.2), "wood")
        k.box(P, 1.2, 0.06, 0.05, (0, y, 0.3), "wood_dk")
    # small feed trough in a corner
    k.box(P, 0.4, 0.18, 0.12, (-0.3, -0.3, 0.1), "wood")
    return k.join(P, "pig_pen")


PIECES = [
    ("scarecrow", scarecrow),
    ("chicken_coop", chicken_coop),
    ("veg_garden", veg_garden),
    ("beehive", beehive),
    ("plow", plow),
    ("pig_pen", pig_pen),
]
