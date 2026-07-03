"""GrimForge Arsenal — dark-fantasy low-poly weapons, magic items & dungeon props.

Built on the shared kitlib DSL (atlas texturing + GrimForge palette), in the same
occult / dark-fantasy voice as the building kits: blackened steel, bone, crimson
gems, gold fittings, and glowing enchantments (ghostfire / witchlight / ember).

Every piece is authored UPRIGHT — base/pommel at z=0, extending +Z — centred on
the origin, so they stand on a weapon-rack grid and turntable cleanly.
"""

import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

TITLE = "GrimForge Arsenal — Weapons, Magic & Props (25 pieces)"
AESTHETIC = "occult"
HERO_VIEW = "3q"   # weapons/items are vertical — catalog from a 3/4 corner

R45 = math.radians(45)


# --------------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------------- #

def _grip(k, P, z0, z1, r=0.036, color="beam"):
    """A wrapped leather/wood grip cylinder + binding rings."""
    k.cyl(P, 8, r, z1 - z0, (0, 0, (z0 + z1) / 2), color)
    for zz in (z0 + 0.03, (z0 + z1) / 2, z1 - 0.03):
        k.cyl(P, 8, r + 0.006, 0.012, (0, 0, zz), "wood_dk")


def _haft(k, P, z0, z1, r=0.03, color="wood_dk"):
    """A long weapon haft/shaft."""
    k.cyl(P, 8, r, z1 - z0, (0, 0, (z0 + z1) / 2), color)


def _axe_bit(k, P, cx, cz, sgn=1):
    """A single axe blade (dark cheek at the haft flaring to a bright steel edge),
    bit facing ±x per ``sgn``."""
    k.box(P, 0.06, 0.11, 0.24, (cx, 0, cz), "gunmetal")               # eye / cheek
    k.box(P, 0.2, 0.03, 0.3, (cx + sgn * 0.15, 0, cz), "steel")       # blade plate
    for zsgn in (-1, 1):                                              # crescent bevels
        k.box(P, 0.09, 0.032, 0.09, (cx + sgn * 0.24, 0, cz + zsgn * 0.12),
              "steel", rot=(0, sgn * zsgn * math.radians(30), 0))
    k.box(P, 0.03, 0.036, 0.34, (cx + sgn * 0.26, 0, cz), "gunmetal")  # edge spine


# --------------------------------------------------------------------------- #
# melee weapons
# --------------------------------------------------------------------------- #

def sword(k):
    """An arming sword — steel blade with a fuller, crossguard + crimson gem."""
    P = []
    k.ico(P, 0.05, (0, 0, 0.02), "gold")                              # pommel
    _grip(k, P, 0.05, 0.26)
    k.box(P, 0.28, 0.055, 0.05, (0, 0, 0.28), "iron")                # crossguard
    k.ico(P, 0.03, (0, 0, 0.28), "crimson")                          # guard gem
    k.box(P, 0.09, 0.03, 0.6, (0, 0, 0.6), "steel")                  # blade
    k.box(P, 0.018, 0.034, 0.58, (0, 0, 0.6), "gunmetal")            # fuller
    k.cone(P, 4, 0.046, 0, 0.16, (0, 0, 0.98), "steel", rot=(0, 0, R45))  # tip
    return k.join(P, "sword")


def greatsword(k):
    """A two-handed greatsword — long broad blade, ricasso, ringed guard."""
    P = []
    k.ico(P, 0.055, (0, 0, 0.02), "gold")
    _grip(k, P, 0.05, 0.4)
    k.box(P, 0.34, 0.06, 0.06, (0, 0, 0.42), "gunmetal")            # guard
    for s in (-1, 1):
        k.ico(P, 0.03, (s * 0.15, 0, 0.42), "crimson")             # guard gems
    k.box(P, 0.12, 0.035, 0.9, (0, 0, 0.92), "steel")              # blade
    k.box(P, 0.02, 0.04, 0.88, (0, 0, 0.92), "gunmetal")           # fuller
    k.cone(P, 4, 0.06, 0, 0.2, (0, 0, 1.47), "steel", rot=(0, 0, R45))
    return k.join(P, "greatsword")


def dagger(k):
    """A bone-hilted dagger."""
    P = []
    k.ico(P, 0.035, (0, 0, 0.02), "bone")                         # bone pommel
    k.cyl(P, 8, 0.03, 0.14, (0, 0, 0.1), "bone")                   # bone grip
    for zz in (0.06, 0.14):
        k.cyl(P, 8, 0.034, 0.012, (0, 0, zz), "gold")            # grip rings
    k.box(P, 0.14, 0.04, 0.035, (0, 0, 0.18), "gunmetal")        # dark guard
    k.box(P, 0.06, 0.022, 0.28, (0, 0, 0.33), "steel")           # blade
    k.box(P, 0.016, 0.026, 0.26, (0, 0, 0.33), "gunmetal")       # fuller
    k.cone(P, 4, 0.032, 0, 0.1, (0, 0, 0.5), "steel", rot=(0, 0, R45))
    return k.join(P, "dagger")


def axe(k):
    """A war axe — wooden haft, blackened head flaring to a steel crescent edge."""
    P = []
    _haft(k, P, 0.0, 0.95, 0.028, "wood")
    k.cyl(P, 8, 0.032, 0.06, (0, 0, 0.05), "iron")                # butt cap
    zc = 0.82
    _axe_bit(k, P, 0.03, zc, 1)
    k.box(P, 0.045, 0.045, 0.15, (-0.02, 0, zc + 0.18), "steel")  # top spike
    return k.join(P, "axe")


def battleaxe(k):
    """A double-bitted battleaxe."""
    P = []
    _haft(k, P, 0.0, 1.0, 0.03, "wood_dk")
    zc = 0.82
    k.cyl(P, 8, 0.05, 0.1, (0, 0, zc), "gunmetal", rot=(math.radians(90), 0, 0))  # central eye
    _axe_bit(k, P, 0.02, zc, 1)
    _axe_bit(k, P, -0.02, zc, -1)
    k.box(P, 0.04, 0.04, 0.16, (0, 0, zc + 0.18), "steel")        # top spike
    return k.join(P, "battleaxe")


def mace(k):
    """A flanged mace."""
    P = []
    _haft(k, P, 0.0, 0.7, 0.028, "wood_dk")
    _grip(k, P, 0.0, 0.24, 0.032, "beam")
    zc = 0.78
    k.cyl(P, 8, 0.075, 0.16, (0, 0, zc), "iron")                  # head core
    for i in range(6):
        an = math.radians(i * 60)
        k.box(P, 0.04, 0.09, 0.17, (math.cos(an) * 0.08, math.sin(an) * 0.08, zc),
              "gunmetal", rot=(0, 0, an))                          # flanges
    k.ico(P, 0.05, (0, 0, zc + 0.1), "steel")                     # top knob
    return k.join(P, "mace")


def warhammer(k):
    """A warhammer — hammer head + back spike."""
    P = []
    _haft(k, P, 0.0, 0.95, 0.03, "wood")
    _grip(k, P, 0.0, 0.22, 0.034, "beam")
    zc = 0.85
    k.box(P, 0.14, 0.14, 0.14, (0.08, 0, zc), "gunmetal")         # hammer face
    k.box(P, 0.05, 0.05, 0.05, (0.17, 0, zc), "iron")
    k.cone(P, 4, 0.06, 0, 0.2, (-0.16, 0, zc), "steel", rot=(0, math.radians(-90), R45))  # spike
    k.box(P, 0.06, 0.06, 0.16, (0, 0, zc + 0.12), "iron")         # top spike
    return k.join(P, "warhammer")


def spear(k):
    """A leaf-bladed spear."""
    P = []
    _haft(k, P, 0.0, 1.2, 0.024, "wood")
    for zz in (0.3, 0.7):
        k.cyl(P, 8, 0.028, 0.02, (0, 0, zz), "iron")              # binding
    k.cyl(P, 6, 0.03, 0.1, (0, 0, 1.22), "iron")                 # socket
    k.box(P, 0.07, 0.02, 0.24, (0, 0, 1.4), "steel")            # leaf blade
    k.cone(P, 4, 0.037, 0, 0.14, (0, 0, 1.58), "steel", rot=(0, 0, R45))
    return k.join(P, "spear")


def halberd(k):
    """A halberd — axe blade + long top spike + rear hook on a shaft."""
    P = []
    _haft(k, P, 0.0, 1.25, 0.026, "wood_dk")
    zc = 1.05
    _axe_bit(k, P, 0.0, zc, 1)
    k.box(P, 0.05, 0.05, 0.32, (0, 0, zc + 0.24), "steel")       # top spike
    k.cone(P, 4, 0.03, 0, 0.1, (0, 0, zc + 0.45), "steel", rot=(0, 0, R45))
    k.box(P, 0.13, 0.05, 0.05, (-0.08, 0, zc + 0.04), "gunmetal")  # rear hook base
    k.box(P, 0.05, 0.05, 0.1, (-0.14, 0, zc + 0.09), "steel",
          rot=(0, math.radians(38), 0))                            # hook point
    return k.join(P, "halberd")


def flail(k):
    """A spiked flail — handle, chain, spiked ball."""
    P = []
    _haft(k, P, 0.0, 0.55, 0.03, "wood_dk")
    _grip(k, P, 0.0, 0.24, 0.034, "beam")
    k.cyl(P, 8, 0.026, 0.03, (0, 0, 0.57), "iron")                # eye ring at haft top
    for i in range(4):                                            # connected chain links
        k.cyl(P, 6, 0.02, 0.06, (0, 0, 0.61 + i * 0.05),
              "iron", rot=(math.radians(90) if i % 2 else 0, 0, 0))
    k.ico(P, 0.085, (0, 0, 0.87), "gunmetal", sub=1)             # spiked ball
    for dx, dy, rx, ry in ((0.1, 0, 0, math.radians(90)), (-0.1, 0, 0, math.radians(-90)),
                           (0, 0.1, math.radians(-90), 0), (0, -0.1, math.radians(90), 0)):
        k.cone(P, 4, 0.026, 0, 0.08, (dx, dy, 0.87), "steel", rot=(rx, ry, 0))
    k.cone(P, 4, 0.026, 0, 0.08, (0, 0, 0.97), "steel")           # top spike
    return k.join(P, "flail")


def scythe(k):
    """A reaper's scythe — curved snath + curved blade (occult)."""
    P = []
    k.cyl(P, 8, 0.028, 1.1, (0, 0, 0.55), "charwood")            # snath
    k.box(P, 0.05, 0.05, 0.16, (0.06, 0, 0.3), "wood_dk", rot=(0, math.radians(30), 0))  # grip nub
    zc = 1.08
    k.cyl(P, 6, 0.035, 0.1, (0, 0, zc), "iron")                 # collar
    for i in range(6):                                          # curved blade (stepped)
        t = i / 5.0
        k.box(P, 0.13 - t * 0.02, 0.02, 0.06,
              (0.1 + t * 0.34, 0, zc + 0.06 + t * 0.22 - t * t * 0.14),
              "steel", rot=(0, math.radians(-20 - t * 40), 0))
    k.ico(P, 0.03, (0, 0, zc - 0.05), "witchlight")             # ghost rune
    return k.join(P, "scythe")


# --------------------------------------------------------------------------- #
# magic items
# --------------------------------------------------------------------------- #

def wizard_staff(k):
    """A wooden staff crowned with a glowing crystal held in claw prongs."""
    P = []
    k.cyl(P, 8, 0.032, 1.15, (0, 0, 0.575), "wood")
    for zz in (0.3, 0.6, 0.9):
        k.cyl(P, 8, 0.036, 0.02, (0, 0, zz), "wood_dk")          # knots
    for i in range(4):                                           # claw prongs
        an = math.radians(i * 90)
        k.box(P, 0.02, 0.02, 0.12, (math.cos(an) * 0.05, math.sin(an) * 0.05, 1.2),
              "iron", rot=(math.radians(20) * math.cos(an), math.radians(20) * math.sin(an), 0))
    k.ico(P, 0.07, (0, 0, 1.28), "ghostfire", sub=1)            # crystal
    return k.join(P, "wizard_staff")


def skull_staff(k):
    """A necromancer's staff topped with a glowing skull."""
    P = []
    k.cyl(P, 8, 0.034, 1.1, (0, 0, 0.55), "charwood")
    for zz in (0.28, 0.82):
        k.cyl(P, 8, 0.04, 0.03, (0, 0, zz), "bone")             # bone rings
    k.ico(P, 0.09, (0, 0, 1.16), "bone", sub=1)                 # skull
    k.box(P, 0.11, 0.02, 0.055, (0, -0.07, 1.14), "bone")       # jaw
    for s in (-1, 1):
        k.ico(P, 0.02, (s * 0.035, -0.06, 1.18), "witchlight")  # glowing eyes
    return k.join(P, "skull_staff")


def crystal_wand(k):
    """A short wand with a faceted glowing gem tip."""
    P = []
    k.cyl(P, 6, 0.02, 0.36, (0, 0, 0.18), "wood_dk")
    k.cyl(P, 6, 0.026, 0.03, (0, 0, 0.36), "gold")
    k.ico(P, 0.045, (0, 0, 0.42), "amber", sub=1)
    return k.join(P, "crystal_wand")


def orb(k):
    """A scrying orb on an ornate stand."""
    P = []
    k.cyl(P, 8, 0.13, 0.05, (0, 0, 0.025), "gunmetal")          # base
    for i in range(3):                                          # claw stand
        an = math.radians(i * 120)
        k.box(P, 0.03, 0.03, 0.18, (math.cos(an) * 0.09, math.sin(an) * 0.09, 0.13),
              "gold", rot=(math.radians(24) * math.cos(an), math.radians(24) * math.sin(an), 0))
    k.ico(P, 0.11, (0, 0, 0.27), "ghostfire", sub=2)           # glowing orb
    return k.join(P, "orb")


def spellbook(k):
    """A grimoire — leather tome with glowing runic pages + clasp."""
    P = []
    k.box(P, 0.34, 0.44, 0.06, (0, 0, 0.03), "blood")           # cover
    k.box(P, 0.3, 0.4, 0.05, (0, 0, 0.085), "bone")             # pages
    k.box(P, 0.36, 0.06, 0.07, (0, 0, 0.035), "wood_dk")        # spine
    k.ico(P, 0.03, (0, 0, 0.13), "witchlight")                 # glowing rune
    k.box(P, 0.06, 0.1, 0.02, (0.16, 0, 0.06), "gold")         # clasp
    return k.join(P, "spellbook")


def _potion(k, name, glow):
    P = []
    k.cyl(P, 8, 0.064, 0.02, (0, 0, 0.01), "gunmetal")         # base rim
    k.cyl(P, 8, 0.06, 0.13, (0, 0, 0.075), glow)               # bulb (glowing liquid)
    k.cyl(P, 6, 0.026, 0.09, (0, 0, 0.18), glow)               # neck
    k.cyl(P, 6, 0.03, 0.02, (0, 0, 0.145), "gunmetal")         # collar band
    k.cyl(P, 6, 0.032, 0.035, (0, 0, 0.235), "wood_dk")        # cork
    return k.join(P, name)


def potion_red(k):
    """A crimson potion."""
    return _potion(k, "potion_red", "ember")


def potion_green(k):
    """A witchlight potion."""
    return _potion(k, "potion_green", "witchlight")


def potion_blue(k):
    """A ghostfire potion."""
    return _potion(k, "potion_blue", "ghostfire")


def runestone(k):
    """A standing rune-carved stone with a glowing sigil."""
    P = []
    k.box(P, 0.05, 0.05, 0.06, (0, 0, 0.03), "moss")            # mossy base
    k.box(P, 0.22, 0.08, 0.34, (0, 0, 0.22), "stone")          # slab
    k.box(P, 0.24, 0.1, 0.05, (0, 0, 0.41), "stone_dk")        # cap
    k.box(P, 0.11, 0.02, 0.02, (0, -0.045, 0.28), "witchlight")  # carved sigil (horizontal)
    k.box(P, 0.02, 0.02, 0.14, (0, -0.045, 0.24), "witchlight")  # carved sigil (vertical)
    return k.join(P, "runestone")


def amulet(k):
    """An occult amulet — a gold-bezelled crimson gem on a coiled chain (lies flat)."""
    P = []
    for i in range(10):                                        # coiled chain
        an = math.radians(i * 36)
        k.cyl(P, 6, 0.009, 0.03, (math.cos(an) * 0.13, math.sin(an) * 0.13, 0.012),
              "gold", rot=(math.radians(90), 0, an))
    k.cyl(P, 8, 0.08, 0.028, (0, 0, 0.03), "gold")            # bezel disc
    for i in range(6):                                        # bezel points
        an = math.radians(i * 60)
        k.box(P, 0.022, 0.03, 0.022, (math.cos(an) * 0.085, math.sin(an) * 0.085, 0.03),
              "gold", rot=(0, 0, an))
    k.cyl(P, 8, 0.055, 0.02, (0, 0, 0.048), "gunmetal")       # inner ring
    k.ico(P, 0.042, (0, 0, 0.065), "crimson")                # gem
    k.cyl(P, 6, 0.024, 0.016, (0, 0.088, 0.035), "gold", rot=(math.radians(90), 0, 0))  # bail loop
    return k.join(P, "amulet")


# --------------------------------------------------------------------------- #
# dungeon / adventure props
# --------------------------------------------------------------------------- #

def chest(k):
    """A banded treasure chest with a gold lock (lid ajar, glowing within)."""
    P = []
    k.box(P, 0.4, 0.3, 0.22, (0, 0, 0.11), "wood")            # body
    for x in (-0.15, 0.15):
        k.box(P, 0.04, 0.32, 0.24, (x, 0, 0.11), "iron")     # bands
    k.box(P, 0.42, 0.32, 0.03, (0, 0, 0.02), "iron")         # foot band
    k.box(P, 0.4, 0.3, 0.1, (0, 0.02, 0.28), "wood_dk", rot=(math.radians(-22), 0, 0))  # lid ajar
    k.box(P, 0.42, 0.05, 0.11, (0, 0.14, 0.26), "iron", rot=(math.radians(-22), 0, 0))
    k.box(P, 0.08, 0.04, 0.08, (0, -0.16, 0.14), "gold")     # lock
    k.box(P, 0.34, 0.24, 0.02, (0, 0, 0.2), "amber")        # glowing gold within
    return k.join(P, "chest")


def key(k):
    """An ornate skeleton key."""
    P = []
    k.cyl(P, 8, 0.05, 0.02, (0, 0, 0.42), "gold", rot=(math.radians(90), 0, 0))  # bow
    k.cyl(P, 8, 0.028, 0.02, (0, 0, 0.42), "charwood", rot=(math.radians(90), 0, 0))
    k.cyl(P, 6, 0.014, 0.42, (0, 0, 0.21), "gold")          # shaft
    k.box(P, 0.06, 0.02, 0.04, (0.03, 0, 0.04), "gold")     # bit
    k.box(P, 0.04, 0.02, 0.03, (0.02, 0, 0.1), "gold")      # bit tooth
    return k.join(P, "key")


def coin_pile(k):
    """A pile of gold coins + a gem."""
    P = []
    import math as _m
    spots = [(0, 0, 0.02), (0.06, 0.03, 0.02), (-0.05, 0.04, 0.02),
             (0.03, -0.05, 0.02), (0.02, 0.02, 0.05), (-0.02, -0.01, 0.05),
             (0.04, 0.0, 0.08)]
    for i, (x, y, z) in enumerate(spots):
        k.cyl(P, 8, 0.035, 0.018, (x, y, z), "gold",
              rot=(0, _m.radians(12 * ((i % 3) - 1)), 0))
    k.ico(P, 0.03, (0.0, 0.0, 0.11), "crimson")            # gem on top
    return k.join(P, "coin_pile")


def lantern(k):
    """An iron hand-lantern with a caged flame."""
    P = []
    k.box(P, 0.12, 0.12, 0.03, (0, 0, 0.015), "iron")        # base
    for x in (-0.05, 0.05):
        for y in (-0.05, 0.05):
            k.cyl(P, 4, 0.008, 0.16, (x, y, 0.11), "iron")   # corner bars
    k.box(P, 0.09, 0.09, 0.09, (0, 0, 0.1), "ember")         # flame/glass
    k.cone(P, 4, 0.08, 0.02, 0.06, (0, 0, 0.22), "iron", rot=(0, 0, R45))  # cap
    k.cyl(P, 6, 0.015, 0.06, (0, 0, 0.28), "iron")           # ring
    return k.join(P, "lantern")


PIECES = [
    ("sword", sword), ("greatsword", greatsword), ("dagger", dagger),
    ("axe", axe), ("battleaxe", battleaxe), ("mace", mace),
    ("warhammer", warhammer), ("spear", spear), ("halberd", halberd),
    ("flail", flail), ("scythe", scythe),
    ("wizard_staff", wizard_staff), ("skull_staff", skull_staff),
    ("crystal_wand", crystal_wand), ("orb", orb), ("spellbook", spellbook),
    ("potion_red", potion_red), ("potion_green", potion_green),
    ("potion_blue", potion_blue), ("runestone", runestone), ("amulet", amulet),
    ("chest", chest), ("key", key), ("coin_pile", coin_pile), ("lantern", lantern),
]
