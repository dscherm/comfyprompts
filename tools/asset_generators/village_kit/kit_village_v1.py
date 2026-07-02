"""GrimForge Village Vol.1 — dark-fantasy rural settlement kit (12 pieces).

Charred timber + thatch buildings with ember-lit windows, in the occult
GrimForge aesthetic. Built on kitlib via kit_pipeline / productize.
"""

import math

from kit_occult import skull as _occult_skull  # shared low-poly skull (gated below)

TITLE = "GrimForge Village Vol.1 — Dark-Fantasy Settlement (12 pieces)"
AESTHETIC = "occult"

# Medieval variants import these builders and set OCCULT = False to drop the
# occult/derelict dressing (skulls, flame-sigil banners, boarded/broken/leaning
# elements) — see kit_village_medieval.py.
OCCULT = True


def skull(k, P, *args, **kwargs):
    """Skull dressing — suppressed when OCCULT is False (medieval variants)."""
    if OCCULT:
        _occult_skull(k, P, *args, **kwargs)

# Darken the whole kit to the grim/occult tone: remap the light building
# material names to dark values so every piece reads grim (ember/crimson
# accents still pop). One override darkens all 12 pieces at once.
PALETTE_OVERRIDE = {
    "stone": "414640",
    "stone_dk": "2a2e2a",
    "plaster": "564f44",
    "slate": "2f353c",
    "thatch": "4a3c22",
    "thatch_dk": "342a16",
}


def _timber_house(k, P, w, d, wall_h, roof_h, roof="thatch_dk", chimney=True):
    """Shared shell: stone footing, charred timber walls with corner studs,
    a gable roof, and (optionally) a stone chimney."""
    k.box(P, w, d, 0.24, (0, 0, 0.12), "stone")                      # footing
    k.box(P, w - 0.08, d - 0.08, wall_h, (0, 0, 0.24 + wall_h / 2), "charwood")
    for sx in (-1, 1):
        for sy in (-1, 1):
            k.box(P, 0.08, 0.08, wall_h, (sx * (w / 2 - 0.06), sy * (d / 2 - 0.06),
                  0.24 + wall_h / 2), "wood_dk")
    k.gable(P, w, d, roof_h, (0, 0, 0.24 + wall_h), roof, over=0.18)
    if chimney:
        k.box(P, 0.2, 0.2, wall_h + 0.5, (w * 0.35, d * 0.28, (0.24 + wall_h + 0.5) / 2), "stone")
        k.cone(P, 4, 0.1, 0, 0.16, (w * 0.35, d * 0.28, 0.24 + wall_h + 0.55), "ember")


def _ember_win_y(k, P, cx, cz, fy, w=0.22, h=0.26):
    """Thin FLUSH ember window on a front/back wall (face at y=fy, -y outward)."""
    k.box(P, w + 0.06, 0.05, h + 0.06, (cx, fy + 0.04, cz), "soot")   # recessed dark frame
    k.box(P, w, 0.04, h, (cx, fy + 0.01, cz), "ember")               # glow, ~flush (1cm proud)


def _boarded_win_y(k, P, cx, cz, fy, w=0.22, h=0.26):
    """A boarded-up window (dark recess + askew planks); a clean lit window when
    OCCULT is False."""
    k.box(P, w + 0.06, 0.05, h + 0.06, (cx, fy + 0.04, cz), "soot")
    if not OCCULT:
        k.box(P, w, 0.04, h, (cx, fy + 0.005, cz), "ember")          # clean lit pane
        return
    for i, bz in enumerate((-h * 0.32, 0.0, h * 0.32)):
        k.box(P, w + 0.05, 0.05, 0.07, (cx, fy + 0.005, cz + bz), "wood_dk",
              rot=(0, math.radians((i - 1) * 7), 0))


def _ember_win_x(k, P, cy, cz, fx, w=0.22, h=0.26):
    """Thin FLUSH ember window on a LEFT wall (face at x=fx, -x outward)."""
    k.box(P, 0.05, w + 0.06, h + 0.06, (fx + 0.04, cy, cz), "soot")
    k.box(P, 0.04, w, h, (fx + 0.01, cy, cz), "ember")


def _boarded_win_x(k, P, cy, cz, fx, w=0.22, h=0.26):
    """Boarded-up window on a RIGHT wall; a clean lit window when OCCULT is False."""
    k.box(P, 0.05, w + 0.06, h + 0.06, (fx - 0.04, cy, cz), "soot")
    if not OCCULT:
        k.box(P, 0.04, w, h, (fx - 0.005, cy, cz), "ember")          # clean lit pane
        return
    for i, bz in enumerate((-h * 0.32, 0.0, h * 0.32)):
        k.box(P, 0.06, w + 0.05, 0.07, (fx - 0.005, cy, cz + bz), "wood_dk",
              rot=(0, 0, math.radians((i - 1) * 7)))


def cottage(k):
    P = []
    w, d, wall_h, roof_h = 1.3, 1.1, 0.7, 0.55
    ffy = -(d - 0.08) / 2                                            # front wall face
    bfy = (d - 0.08) / 2                                             # back wall face
    lfx = -(w - 0.08) / 2                                            # left wall face
    rfx = (w - 0.08) / 2                                             # right wall face
    bt = 0.24                                                        # base top
    k.box(P, w, d, 0.24, (0, 0, 0.12), "stone")                     # footing
    k.box(P, w + 0.06, d + 0.06, 0.09, (0, 0, 0.22), "moss")        # moss at the base
    k.box(P, w - 0.08, d - 0.08, wall_h, (0, 0, bt + wall_h / 2), "charwood")     # walls
    for sx in (-1, 1):                                              # corner studs
        for sy in (-1, 1):
            k.box(P, 0.08, 0.08, wall_h, (sx * (w / 2 - 0.06), sy * (d / 2 - 0.06),
                  bt + wall_h / 2), "wood_dk")
    k.gable(P, w, d, roof_h, (0, 0, bt + wall_h), "thatch_dk", over=0.18)
    # side windows (flush): lit on the left, boarded on the right
    _ember_win_x(k, P, 0.05, 0.7, lfx)
    _boarded_win_x(k, P, 0.05, 0.7, rfx)
    # --- covered FRONT PORCH (occult cottage only): deck, posts, plates, shed roof ---
    if OCCULT:
        pd = 0.55
        k.box(P, w, pd + 0.08, 0.14, (0, ffy - pd / 2, 0.2), "wood")           # deck
        for px in (-w / 2 + 0.12, w / 2 - 0.12):
            k.box(P, 0.08, 0.08, 0.74, (px, ffy - pd + 0.06, 0.6), "wood_dk")   # posts
            k.box(P, 0.06, pd, 0.06, (px, ffy - pd / 2, 0.96), "wood_dk")       # plates
        k.box(P, w + 0.16, pd + 0.22, 0.06, (0, ffy - pd / 2 + 0.02, 0.98),
              "thatch_dk", rot=(math.radians(-15), 0, 0))                      # shed roof
    # centered plank door under the porch (slightly ajar, no glowing pane)
    dz = 0.46
    k.box(P, 0.34, 0.06, 0.66, (0, ffy + 0.06, dz), "soot")                   # dark doorway recess
    drot = (0, math.radians(6), 0)
    k.box(P, 0.3, 0.05, 0.62, (0, ffy - 0.02, dz), "wood_dk", rot=drot)       # plank door slab
    for rz in (-0.24, 0.0, 0.24):                                             # plank braces
        k.box(P, 0.32, 0.04, 0.05, (0, ffy - 0.05, dz + rz), "wood", rot=drot)
    k.box(P, 0.04, 0.05, 0.06, (0.11, ffy - 0.06, dz), "iron", rot=drot)      # iron handle
    # --- solid STEPPED stone chimney (no gaps): broad breast -> shoulders -> narrow flue ---
    byy = bfy + 0.16
    segs = [(0.16, 0.66, 0.72, 0.42), (0.60, 0.92, 0.60, 0.40),
            (0.86, 1.14, 0.46, 0.36), (1.08, 1.36, 0.34, 0.32),
            (1.30, 1.80, 0.24, 0.28)]
    for i, (z0, z1, wd, dp) in enumerate(segs):
        k.box(P, wd, dp, z1 - z0, (0, byy, (z0 + z1) / 2),
              "stone" if i % 2 == 0 else "stone_dk")
    k.box(P, 0.3, 0.32, 0.08, (0, byy, 1.84), "stone")                        # cap
    obj = k.join(P, "cottage")
    if OCCULT:
        obj.rotation_euler = (math.radians(2.5), 0, math.radians(2))         # slight lean
    return obj


def _timber_frame_front(k, P, cw, fy, z0, h):
    """Tudor timber framing (dark charwood beams) on a -y plaster face."""
    for x in (-cw / 2 + 0.1, 0.0, cw / 2 - 0.1):                    # studs
        k.box(P, 0.06, 0.04, h, (x, fy - 0.04, z0 + h / 2), "charwood")
    for rz in (z0 + 0.05, z0 + h - 0.05):                          # rails
        k.box(P, cw, 0.04, 0.06, (0, fy - 0.04, rz), "charwood")
    for s in (-1, 1):                                              # braces
        k.box(P, 0.06, 0.04, h * 0.7, (s * cw * 0.26, fy - 0.04, z0 + h / 2),
              "charwood", rot=(0, math.radians(s * 30), 0))


def _x_window(k, P, cx, cz, fy, w=0.24, h=0.26):
    """Shuttered/leaded window with an X muntin on a -y plaster face."""
    k.box(P, w + 0.05, 0.05, h + 0.05, (cx, fy + 0.02, cz), "soot")       # recess
    k.box(P, w, 0.04, h, (cx, fy, cz), "ember")                          # warm glow
    if OCCULT:                                                          # X muntins (occult only)
        for dd in (1, -1):
            k.box(P, w, 0.03, 0.03, (cx, fy - 0.03, cz), "wood_dk",
                  rot=(0, math.radians(dd * 45), 0))


def tavern(k):
    """The Red Roc-style fantasy tavern: coursed-stone ground floor, a jettied
    cream-plaster + dark-timber upper, a steep RED roof with dormers + curled
    eaves, a tall stone chimney, an X-braced arched door, and a hanging sign."""
    P = []
    bt = 0.2
    # === gray coursed-stone ground floor ===
    gw, gd, gh = 1.8, 1.5, 0.85
    gfy = -gd / 2
    k.box(P, gw + 0.16, gd + 0.16, bt, (0, 0, bt / 2), "stone_dk")        # plinth
    k.box(P, gw, gd, gh, (0, 0, bt + gh / 2), "stone")                   # stone walls
    for cz in (bt + 0.3, bt + 0.6):                                      # course lines
        k.box(P, gw + 0.02, gd + 0.02, 0.04, (0, 0, cz), "stone_dk")
    # arched X-braced door + transom glow + small sign
    dz = bt + 0.36
    k.box(P, 0.44, 0.06, 0.72, (0, gfy + 0.05, dz), "soot")              # doorway recess
    k.box(P, 0.4, 0.05, 0.64, (0, gfy - 0.02, dz), "wood_dk")            # door slab
    for dd in (1, -1):
        k.box(P, 0.42, 0.04, 0.07, (0, gfy - 0.06, dz), "wood", rot=(0, math.radians(dd * 50), 0))
    k.box(P, 0.34, 0.06, 0.1, (0, gfy - 0.04, dz + 0.36), "ember")       # transom
    k.box(P, 0.16, 0.04, 0.12, (0.42, gfy - 0.05, dz + 0.12), "crimson")  # ALE sign
    # === jettied cream-plaster + timber upper floor ===
    uw, ud, uh = gw + 0.24, gd + 0.24, 0.72
    z1 = bt + gh
    ufy = -ud / 2
    k.box(P, uw, ud, uh, (0, 0, z1 + uh / 2), "bone")                    # cream plaster
    for s in (-1, 1):                                                    # side framing only
        k.box(P, 0.05, ud, uh, (s * uw / 2, 0, z1 + uh / 2), "charwood")
    _x_window(k, P, -0.55, z1 + 0.4, ufy)
    _x_window(k, P, 0.55, z1 + 0.4, ufy)
    # === steep RED roof + dormers (left slope) + curled eaves ===
    rz = z1 + uh
    rh = 1.05
    k.gable(P, uw + 0.14, ud + 0.14, rh, (0, 0, rz), "roof_red", over=0.26)
    k.box(P, 0.1, ud + 0.5, 0.1, (0, 0, rz + rh), "charwood")            # ridge
    for sy in (-0.4, 0.4):                                               # 2 dormers on the -x slope
        dx, dzz = -uw / 2 * 0.55, rz + rh * 0.36
        k.box(P, 0.24, 0.26, 0.3, (dx, sy, dzz), "bone")
        k.box(P, 0.16, 0.3, 0.1, (dx - 0.12, sy, dzz + 0.18), "roof_red")
        k.box(P, 0.04, 0.16, 0.16, (dx - 0.14, sy, dzz + 0.02), "ember")
    for sy in (-1, 1):                                                   # curled eave tips
        for sx in (-1, 1):
            k.cone(P, 4, 0.13, 0.02, 0.22, (sx * (uw / 2 + 0.05), sy * (ud / 2 + 0.07), rz + 0.04),
                   "roof_red", rot=(math.radians(sy * 26), 0, 0))
    # === tall gray stone chimney (right side) with cap + iron finials ===
    cxx = uw / 2 + 0.04
    for i, (a, b, wd) in enumerate([(0.2, 1.6, 0.52), (1.4, 2.2, 0.4), (2.0, 3.0, 0.3)]):
        k.box(P, wd, 0.58, b - a, (cxx, 0.3, (a + b) / 2), "stone" if i % 2 == 0 else "stone_dk")
    k.box(P, 0.38, 0.64, 0.08, (cxx, 0.3, 3.05), "stone")               # cap
    for fx in (-0.12, 0.0, 0.12):                                       # iron finials ON the cap
        k.cyl(P, 4, 0.018, 0.2, (cxx + fx, 0.3, 3.19), "iron")
    # === hanging sign: wall bracket -> crossbar -> chains -> board (all connected) ===
    sbx = -uw / 2 + 0.16
    arm_y0, arm_len, sz = ufy - 0.04, 0.4, z1 + 0.55
    endy = arm_y0 - arm_len
    k.box(P, 0.05, arm_len, 0.05, (sbx, arm_y0 - arm_len / 2, sz), "wood_dk")   # bracket arm
    k.box(P, 0.42, 0.05, 0.05, (sbx, endy, sz), "wood_dk")                      # crossbar
    for ex in (-0.16, 0.16):                                                    # chains
        k.box(P, 0.02, 0.02, 0.18, (sbx + ex, endy, sz - 0.13), "iron")
    k.box(P, 0.42, 0.05, 0.32, (sbx, endy, sz - 0.38), "crimson")              # board
    k.box(P, 0.22, 0.06, 0.18, (sbx, endy - 0.03, sz - 0.38), "gold")          # emblem
    obj = k.join(P, "tavern")
    if OCCULT:
        obj.rotation_euler = (math.radians(1.5), 0, math.radians(-2))   # gentle crooked lean
    return obj


def _cow_skull(k, P, cx, cy, cz, s=0.12):
    """A long ox/cow skull facing -y with two big up-and-out curved horns
    (suppressed when OCCULT is False)."""
    if not OCCULT:
        return
    k.box(P, s * 1.5, s * 1.4, s * 1.0, (cx, cy, cz), "bone")                  # cranium
    k.box(P, s * 0.9, s * 0.9, s * 0.7, (cx, cy - s * 0.95, cz - s * 0.35), "bone")  # snout
    for sx in (-1, 1):
        k.box(P, s * 0.44, s * 0.4, s * 0.44, (cx + sx * s * 0.42, cy - s * 0.72, cz + s * 0.14),
              "soot")                                                          # hollow eye socket
        k.cone(P, 5, s * 0.18, 0.0, s * 1.5, (cx + sx * s * 0.72, cy + s * 0.05, cz + s * 1.0),
               "bone", rot=(math.radians(-14), math.radians(sx * 40), 0))      # big horn


def _shield(k, P, cx, cy, cz, r=0.17, col="crimson"):
    """A round Viking shield facing -y (planks + painted field + cross + iron boss)."""
    k.cyl(P, 12, r, 0.04, (cx, cy, cz), "wood_dk", rot=(math.radians(90), 0, 0))      # back/rim
    k.cyl(P, 12, r * 0.9, 0.05, (cx, cy - 0.02, cz), col, rot=(math.radians(90), 0, 0))  # field
    k.box(P, r * 1.7, 0.04, 0.05, (cx, cy - 0.05, cz), "bone")                        # cross stripe
    k.box(P, 0.05, 0.04, r * 1.7, (cx, cy - 0.05, cz), "bone")
    k.cyl(P, 6, r * 0.24, 0.07, (cx, cy - 0.06, cz), "iron", rot=(math.radians(90), 0, 0))  # boss


def blacksmith(k):
    """A Norse/Viking smithy: steep dark gable with exposed rafter tails + carved
    curl bargeboards, a round whitewashed stone chimney with smoke, mounted round
    shields + cow/human skulls, an open-front glowing forge with an anvil + hammer,
    a water bucket on a stand, barrels and firewood."""
    P = []
    bt = 0.2
    mw, md, wh = 1.5, 1.7, 0.9
    fy = -md / 2
    k.box(P, mw + 0.16, md + 0.16, bt, (0, 0, bt / 2), "stone_dk")             # stone base
    k.box(P, mw, md, wh, (0, 0, bt + wh / 2), "plaster")                       # plaster hall
    _timber_frame_front(k, P, mw, fy, bt, wh)
    for s in (-1, 1):
        k.box(P, 0.06, md, wh, (s * mw / 2, 0, bt + wh / 2), "charwood")       # side beams
    # steep dark gable roof + ridge + exposed rafter tails + gable curls
    rz, rh = bt + wh, 1.0
    k.gable(P, mw + 0.12, md + 0.12, rh, (0, 0, rz), "ash", over=0.28)
    k.box(P, 0.1, md + 0.5, 0.1, (0, 0, rz + rh), "charwood")
    for s in (-1, 1):
        for yy in (-0.7, -0.2, 0.3, 0.8):
            k.box(P, 0.3, 0.06, 0.06, (s * (mw / 2 + 0.16), yy, rz - 0.02), "charwood",
                  rot=(0, math.radians(s * 40), 0))
        k.cone(P, 4, 0.09, 0.02, 0.3, (s * (mw / 2 + 0.04), fy - 0.06, rz + 0.05),
               "wood_dk", rot=(math.radians(-42), 0, math.radians(s * 18)))    # bargeboard curl
    _cow_skull(k, P, 0, fy - 0.3, 1.62, s=0.2)                                 # cow skull on gable
    # open-front work porch over the forge + anvil
    pd = 0.7
    for px in (-mw / 2 + 0.1, mw / 2 - 0.1):
        k.box(P, 0.1, 0.1, 0.85, (px, fy - pd + 0.1, bt + 0.42), "charwood")   # porch posts
    k.box(P, mw + 0.2, pd + 0.24, 0.06, (0, fy - pd / 2, bt + 0.92), "ash",
          rot=(math.radians(-16), 0, 0))                                       # porch shed roof
    k.box(P, 0.45, 0.42, 0.5, (-0.42, fy - 0.22, bt + 0.25), "stone_dk")       # forge mass
    k.box(P, 0.34, 0.3, 0.32, (-0.42, fy - 0.42, bt + 0.3), "ember")           # glowing fire
    ax, ay = 0.42, fy - 0.52
    k.cyl(P, 8, 0.13, 0.28, (ax, ay, bt + 0.14), "wood_dk")                    # oak stump
    k.box(P, 0.12, 0.16, 0.09, (ax, ay, bt + 0.32), "gunmetal")               # waist
    k.box(P, 0.16, 0.42, 0.1, (ax, ay, bt + 0.41), "gunmetal")                # flat top face
    k.cone(P, 6, 0.08, 0.0, 0.22, (ax, ay - 0.3, bt + 0.43), "gunmetal",
           rot=(math.radians(90), 0, 0))                                       # pointed horn
    k.box(P, 0.16, 0.11, 0.16, (ax, ay + 0.24, bt + 0.42), "gunmetal")        # squared heel
    k.box(P, 0.035, 0.035, 0.28, (ax + 0.13, ay + 0.02, bt + 0.5), "wood_dk",
          rot=(math.radians(26), 0, 0))                                        # hammer handle
    k.box(P, 0.07, 0.16, 0.07, (ax + 0.17, ay - 0.05, bt + 0.66), "iron")      # hammer head
    # round whitewashed stone chimney (back-left) with iron cap, smoke, a shield
    cxx, cyy = -mw / 2 - 0.16, 0.35
    k.cyl(P, 10, 0.26, 2.3, (cxx, cyy, 1.15), "plaster")
    for cz in (0.7, 1.4):
        k.cyl(P, 10, 0.27, 0.05, (cxx, cyy, cz), "stone_dk")                  # course bands
    k.cyl(P, 10, 0.22, 0.16, (cxx, cyy, 2.35), "iron")                        # iron cap
    for sm in range(4):                                                       # connected smoke wisp
        k.ico(P, 0.13 - sm * 0.022, (cxx + sm * 0.07, cyy + sm * 0.02, 2.45 + sm * 0.15),
              "ash", sub=1)
    _shield(k, P, cxx, fy + 0.1, 1.3, 0.18, "crimson")                        # shield
    # mounted shield + human skulls on the hall front
    _shield(k, P, 0.45, fy - 0.02, bt + 0.62, 0.16, "cloth")
    skull(k, P, -0.5, fy - 0.02, bt + 0.66, 0.1)
    skull(k, P, mw / 2 + 0.01, -0.3, bt + 0.6, 0.09)                          # skull on side beam
    # water bucket on a stand (front-left)
    wsx, wsy = -0.62, fy - 0.5
    for lx in (-0.13, 0.13):
        for ly in (-0.13, 0.13):
            k.box(P, 0.05, 0.05, 0.8, (wsx + lx, wsy + ly, 0.4), "wood_dk")
    k.cyl(P, 8, 0.2, 0.24, (wsx, wsy, 0.92), "wood")                          # bucket
    k.cyl(P, 8, 0.16, 0.05, (wsx, wsy, 1.02), "water")
    # barrels + firewood
    for bx, by in [(0.72, fy - 0.55), (-0.78, fy - 0.18)]:
        k.cyl(P, 10, 0.14, 0.32, (bx, by, bt + 0.16), "wood")
        for cz in (bt + 0.08, bt + 0.24):
            k.cyl(P, 10, 0.15, 0.04, (bx, by, cz), "iron")
    for i in range(3):
        k.cyl(P, 6, 0.05, 0.4, (0.85, fy - 0.15 + i * 0.05, bt + 0.06 + i * 0.045), "wood",
              rot=(0, math.radians(90), 0))
    # tool rack on the right porch post (hanging tongs + hammer) + forge soot
    trx = mw / 2 - 0.12
    k.box(P, 0.16, 0.04, 0.04, (trx, fy - pd + 0.08, bt + 0.72), "wood_dk")    # rack bar
    k.box(P, 0.03, 0.03, 0.24, (trx - 0.05, fy - pd + 0.05, bt + 0.58), "iron")  # tongs
    k.box(P, 0.05, 0.03, 0.2, (trx + 0.04, fy - pd + 0.05, bt + 0.6), "iron")    # hung hammer
    k.box(P, 0.05, 0.05, 0.05, (trx + 0.04, fy - pd + 0.05, bt + 0.48), "wood")  # hammer head
    k.box(P, 0.42, 0.04, 0.5, (-0.42, fy + 0.02, bt + 0.72), "soot")            # soot above forge
    obj = k.join(P, "blacksmith")
    obj.rotation_euler = (math.radians(1.5), 0, math.radians(1.5))
    return obj


def _gothic_window(k, P, cx, cz, fy, w=0.13, h=0.4, glow="gem"):
    """A tall pointed-arch lancet window on a -y face (surround + glow + point)."""
    k.box(P, w + 0.06, 0.05, h + 0.05, (cx, fy + 0.04, cz), "stone_dk")
    k.box(P, w, 0.04, h, (cx, fy + 0.01, cz), glow)
    k.cone(P, 4, w * 0.62, 0.0, w * 0.85, (cx, fy + 0.01, cz + h / 2 + w * 0.3), glow)


def chapel(k):
    """A tall crumbling Gothic church: a dominant stone STEEPLE with corner
    pinnacles + a cross, pointed-arch lancets, a glowing rose window, a recessed
    arched portal, a steep nave with buttresses, moss + cracks. Ghost-lit."""
    P = []
    bt = 0.2
    # === nave (body) behind the tower ===
    nw, nd, nh, ncy = 1.2, 2.0, 1.4, 0.5
    k.box(P, nw + 0.24, nd + 0.24, bt, (0, ncy, bt / 2), "stone_dk")       # plinth
    k.box(P, nw, nd, nh, (0, ncy, bt + nh / 2), "stone")                   # nave walls
    k.gable(P, nw, nd, 0.75, (0, ncy, bt + nh), "ash", over=0.16)          # steep roof
    for s in (-1, 1):
        for yy in (ncy - 0.6, ncy + 0.2, ncy + 0.9):                       # buttresses
            k.box(P, 0.16, 0.16, nh * 0.8, (s * nw / 2, yy, bt + nh * 0.4), "stone_dk")
        for yy in (ncy - 0.3, ncy + 0.5):                                  # side lancets
            k.box(P, 0.05, 0.12, 0.42, (s * nw / 2, yy, bt + 0.85), "gem")
    # === dominant STEEPLE tower (front) ===
    tw, tz, tcy = 0.95, 3.6, -0.85
    tfy = tcy - tw / 2
    k.box(P, tw + 0.16, tw + 0.16, bt, (0, tcy, bt / 2), "stone_dk")       # tower plinth
    k.box(P, tw, tw, tz, (0, tcy, bt + tz / 2), "stone")                  # tower shaft
    for cz in (bt + 1.2, bt + 2.4):                                       # string courses
        k.box(P, tw + 0.04, tw + 0.04, 0.06, (0, tcy, cz), "stone_dk")
    for cx in (-0.22, 0.22):                                              # belfry lancets
        _gothic_window(k, P, cx, bt + tz - 0.55, tfy, w=0.1, h=0.55)
    # rose window on the front
    rwz = bt + tz * 0.52
    k.cyl(P, 12, 0.28, 0.05, (0, tfy + 0.03, rwz), "stone_dk", rot=(math.radians(90), 0, 0))
    k.cyl(P, 12, 0.22, 0.05, (0, tfy + 0.01, rwz), "gem", rot=(math.radians(90), 0, 0))
    for a in range(6):                                                    # tracery spokes
        k.box(P, 0.42, 0.03, 0.03, (0, tfy - 0.02, rwz), "stone_dk",
              rot=(0, math.radians(a * 30), 0))
    # recessed Gothic portal at the base
    pz = bt + 0.55
    for rr, yy, col in [(0.32, tfy + 0.02, "stone"), (0.24, tfy + 0.12, "stone_dk")]:
        for a in range(7):
            an = math.radians(180 * a / 6)
            k.box(P, 0.1, 0.1, 0.13, (math.cos(an) * rr, yy, pz + 0.18 + math.sin(an) * rr),
                  col, rot=(0, 0, an))
    k.box(P, 0.46, 0.3, 0.62, (0, tfy + 0.16, pz - 0.05), "charwood")     # dark recess
    for s in (-1, 1):                                                     # wooden double doors
        k.box(P, 0.15, 0.06, 0.52, (s * 0.08, tfy - 0.03, pz - 0.05), "wood_dk")
    k.box(P, 0.08, 0.04, 0.42, (0, tfy - 0.07, pz - 0.03), "wood")        # cross (vertical)
    k.box(P, 0.26, 0.04, 0.07, (0, tfy - 0.07, pz + 0.06), "wood")        # cross (horizontal)
    # === tower top: cornice + pinnacles + central spire + cross ===
    ttz = bt + tz
    k.box(P, tw + 0.1, tw + 0.1, 0.16, (0, tcy, ttz + 0.08), "stone_dk")  # cornice
    for sx in (-1, 1):
        for sy in (-1, 1):
            px, py = sx * tw / 2, tcy + sy * tw / 2
            k.box(P, 0.12, 0.12, 0.3, (px, py, ttz + 0.3), "stone")       # pinnacle
            k.cone(P, 4, 0.09, 0, 0.32, (px, py, ttz + 0.6), "stone_dk")
    k.cone(P, 4, 0.34, 0, 0.85, (0, tcy, ttz + 0.5), "ash", rot=(0, 0, math.radians(45)))  # spire
    k.box(P, 0.07, 0.07, 0.42, (0, tcy, ttz + 1.05), "stone")             # cross post
    k.box(P, 0.3, 0.07, 0.07, (0, tcy, ttz + 1.15), "stone")              # cross arm
    # === crumbling: moss + cracks ===
    k.box(P, nw + 0.3, nd + 0.3, 0.08, (0, ncy, 0.22), "moss")
    k.box(P, tw + 0.24, tw + 0.24, 0.08, (0, tcy, 0.22), "moss")
    return k.join(P, "chapel")


def well(k):
    """A cursed grim well: a cracked, coursed octagonal stone drum with a mossy
    base and a glowing (ghostfire) water surface; a windlass (roller + crank)
    hanging an ironbound bucket over the mouth; a dark shingled roof; and occult
    dressing — a skull on the rim, a draped chain, and a witchlight rune."""
    P = []
    # cracked, coursed stone drum + rim lip + glowing water + moss
    k.cyl(P, 8, 0.5, 0.5, (0, 0, 0.25), "stone")                     # drum
    for cz in (0.18, 0.38):
        k.cyl(P, 8, 0.51, 0.04, (0, 0, cz), "stone_dk")              # course band
    k.cyl(P, 8, 0.53, 0.06, (0, 0, 0.52), "stone")                   # rim lip (stone cap)
    k.cyl(P, 12, 0.44, 0.03, (0, 0, 0.54), "ghostfire")              # faint glow rim
    k.cyl(P, 12, 0.42, 0.08, (0, 0, 0.56), "soot")                   # black shaft hole (inside)
    if OCCULT:
        for a in (35, 150, 250):                                     # vertical cracks
            an = math.radians(a)
            k.box(P, 0.03, 0.02, 0.3, (math.cos(an) * 0.5, math.sin(an) * 0.5, 0.3),
                  "soot", rot=(0, 0, an))
    for a in (10, 65, 120, 175, 230, 300):                           # moss clumps around base
        an = math.radians(a)
        k.ico(P, 0.09, (math.cos(an) * 0.5, math.sin(an) * 0.5, 0.05), "leaf_dk")
    for a in (40, 200, 290):                                         # moss climbing the drum
        an = math.radians(a)
        k.ico(P, 0.07, (math.cos(an) * 0.5, math.sin(an) * 0.5, 0.26), "leaf_dk")
    # posts + cross-beam + dark shingled roof
    for sx in (-1, 1):
        k.box(P, 0.08, 0.08, 0.85, (sx * 0.42, 0, 0.7), "charwood")
    k.box(P, 0.95, 0.08, 0.08, (0, 0, 1.12), "charwood")             # cross-beam
    k.gable(P, 1.0, 0.7, 0.34, (0, 0, 1.16), "slate", over=0.14)
    sw = (1.0 + 0.14) / 2
    theta = math.atan2(0.34, sw)
    for i in range(4):                                              # shingle courses
        f = 0.15 + i * 0.2
        for sgn in (-1, 1):
            k.box(P, 0.02, 0.84, 0.05, (sgn * sw * (1 - f), 0, 1.16 + 0.34 * f),
                  "stone_dk", rot=(0, sgn * theta, 0))
    for mx, my, mz in ((0.22, 0.15, 1.41), (-0.18, -0.12, 1.44),     # moss patches on the roof
                       (0.34, -0.22, 1.35), (-0.3, 0.18, 1.37)):
        k.ico(P, 0.06, (mx, my, mz), "leaf_dk")
    # windlass: roller + crank, rope, ironbound hanging bucket
    k.cyl(P, 8, 0.06, 0.7, (0, 0, 0.98), "wood_dk", rot=(0, math.radians(90), 0))  # roller
    k.box(P, 0.05, 0.05, 0.16, (0.4, 0, 0.9), "iron")               # crank arm
    k.cyl(P, 6, 0.02, 0.1, (0.45, 0, 0.84), "wood_dk", rot=(0, math.radians(90), 0))  # grip
    bx = -0.28                                                      # off-centre so the mouth shows
    k.box(P, 0.02, 0.02, 0.18, (bx, 0, 0.89), "ash")               # rope
    k.cyl(P, 8, 0.11, 0.16, (bx, 0, 0.64), "wood_dk")              # bucket body
    for bz in (0.57, 0.71):
        k.cyl(P, 8, 0.113, 0.02, (bx, 0, bz), "iron")              # iron bands
    for hs in (-1, 1):
        k.box(P, 0.02, 0.02, 0.12, (bx + hs * 0.1, 0, 0.77), "iron")  # bucket handle side
    k.box(P, 0.22, 0.02, 0.02, (bx, 0, 0.82), "iron")             # handle top
    # occult dressing: skull on the rim + a draped chain
    skull(k, P, -0.3, -0.34, 0.62, 0.09)                            # skull on the rim
    for cz in (0.62, 0.5, 0.38):
        k.box(P, 0.03, 0.03, 0.06, (0.34, 0.34, cz), "iron")        # draped chain links
    return k.join(P, "well")


def market_stall(k):
    """A grim apothecary market stall: dark timber posts + front counter legs
    under a solid pale awning bearing a blood-red flame sigil; a plank counter and
    a packed back shelf of green potion bottles, a raised skull on a grimoire
    stack, a mortar & pestle, a candle; hung herb bundles; and a barrel/crate/
    cauldron/sack below with a hung lantern."""
    P = []

    def _vial(x, y, bz, h=0.16, liquid="pine"):                            # corked green potion
        k.cyl(P, 8, 0.055, h, (x, y, bz + h / 2), liquid)                   # green potion body
        k.cyl(P, 8, 0.05, 0.03, (x, y, bz + h - 0.03), "witchlight")        # glowing potion surface
        k.cyl(P, 6, 0.026, 0.06, (x, y, bz + h + 0.02), "shroud")           # glass neck
        k.cyl(P, 6, 0.033, 0.035, (x, y, bz + h + 0.06), "wood_dk")         # cork

    # posts (awning) + front counter legs for a stable table
    for sx in (-1, 1):
        k.box(P, 0.06, 0.06, 1.45, (sx * 0.6, 0.38, 0.72), "charwood")       # back post
        k.box(P, 0.06, 0.06, 1.2, (sx * 0.6, -0.4, 0.6), "charwood")         # front post
    # counter + front apron + back shelf
    k.box(P, 1.25, 0.42, 0.08, (0, -0.16, 0.62), "wood_dk")                  # counter top
    k.box(P, 1.25, 0.06, 0.34, (0, -0.36, 0.45), "charwood")                 # front apron
    k.box(P, 1.2, 0.05, 0.52, (0, 0.41, 0.76), "charwood")                   # back board
    k.box(P, 1.2, 0.24, 0.05, (0, 0.32, 0.86), "wood_dk")                    # back shelf
    # ---- solid pale awning + blood flame sigil ----
    at = math.radians(14)
    ca, sa = math.cos(at), math.sin(at)

    def _awn(u, v, dn):                                                      # point on awning plane
        return (u, 0.05 + v * ca - dn * sa, 1.33 + v * sa + dn * ca)

    k.box(P, 1.42, 0.98, 0.04, (0, 0.05, 1.33), "bone", rot=(at, 0, 0))      # solid awning
    for cx in (-0.62, -0.31, 0.0, 0.31, 0.62):
        k.box(P, 0.24, 0.03, 0.14, (cx, -0.45, 1.19), "bone")               # scalloped valance
    if OCCULT:                                                             # blood flame sigil
        fl = [(-0.2, 0.1), (-0.13, 0.17), (-0.06, 0.21), (0.01, 0.19),
              (0.08, 0.14), (0.15, 0.09), (0.22, 0.04)]
        for dv, w in fl:
            k.box(P, w, 0.07, 0.02, _awn(max(0, dv) * 0.5, dv, 0.03), "blood", rot=(at, 0, 0))
        k.box(P, 0.08, 0.07, 0.02, _awn(0.22, -0.16, 0.03), "blood", rot=(at, 0, 0))  # dot
    # ---- wares on the counter ----
    bz0 = 0.66
    if OCCULT:
        for i, col in enumerate(("charwood", "gore", "soot")):              # grimoire stack
            k.box(P, 0.22 - i * 0.02, 0.17, 0.05, (-0.42, -0.2, bz0 + 0.025 + i * 0.05), col)
        skull(k, P, -0.42, -0.2, bz0 + 0.25, 0.1)                           # raised skull
        _vial(0.2, -0.26, bz0, h=0.17)                                      # counter potions
        _vial(0.35, -0.22, bz0, h=0.13)
    else:
        k.ico(P, 0.1, (-0.42, -0.2, bz0 + 0.08), "thatch")                  # sack of grain
        for lx in (0.18, 0.34):
            k.box(P, 0.12, 0.1, 0.16, (lx, -0.24, bz0 + 0.08), "wood_dk")   # produce crates
    k.cyl(P, 8, 0.07, 0.09, (-0.05, -0.24, bz0 + 0.045), "stone")           # mortar
    k.cyl(P, 8, 0.045, 0.05, (-0.05, -0.24, bz0 + 0.08), "soot")            # mortar hollow
    k.cyl(P, 6, 0.016, 0.13, (0.0, -0.22, bz0 + 0.11), "wood_dk", rot=(math.radians(28), 0, 0))
    k.cyl(P, 6, 0.03, 0.13, (0.5, -0.26, bz0 + 0.065), "bone")              # candle
    k.cone(P, 5, 0.035, 0, 0.08, (0.5, -0.26, bz0 + 0.16), "ember")         # candle flame
    if OCCULT:
        for i, sx3 in enumerate((-0.45, -0.27, -0.09, 0.09, 0.27, 0.45)):  # shelf of potions
            _vial(sx3, 0.34, 0.885, h=0.12, liquid="amber" if i == 3 else "witchlight")
    else:
        for sx3 in (-0.4, -0.15, 0.15, 0.4):                               # shelf of goods
            k.box(P, 0.16, 0.16, 0.22, (sx3, 0.34, 0.86), "thatch")
    # hung herb bundles off the front awning edge
    for hx in (-0.55, 0.55):
        k.box(P, 0.02, 0.02, 0.12, (hx, -0.44, 1.1), "wood_dk")             # twine
        k.cone(P, 5, 0.02, 0.08, 0.2, (hx, -0.44, 0.98), "rot")            # dried herbs
    # ---- barrel / crate / cauldron / sack below + hung lantern ----
    k.cyl(P, 10, 0.16, 0.36, (0.5, 0.05, 0.18), "wood_dk")                   # barrel
    for bz in (0.08, 0.28):
        k.cyl(P, 10, 0.162, 0.03, (0.5, 0.05, bz), "iron")                   # barrel hoops
    k.box(P, 0.3, 0.3, 0.3, (-0.5, 0.02, 0.15), "wood")                      # crate
    k.box(P, 0.32, 0.05, 0.05, (-0.5, -0.13, 0.2), "wood_dk")                # crate slat
    k.cyl(P, 10, 0.13, 0.15, (-0.06, 0.06, 0.12), "gunmetal")               # small cauldron
    k.ico(P, 0.12, (0.2, -0.05, 0.12), "shroud")                            # sack
    k.box(P, 0.03, 0.03, 0.16, (-0.6, -0.4, 0.94), "iron")                   # lantern chain
    k.box(P, 0.11, 0.11, 0.14, (-0.6, -0.4, 0.8), "soot")                    # lantern box
    k.box(P, 0.06, 0.06, 0.09, (-0.6, -0.4, 0.8), "amber")                   # lantern flame
    return k.join(P, "market_stall")


def hovel(k):
    P = []
    k.box(P, 0.9, 0.8, 0.5, (0, 0, 0.27), "charwood", rot=(0, math.radians(3), 0))
    k.gable(P, 1.0, 0.9, 0.4, (0, 0, 0.52), "thatch_dk", over=0.2)
    k.box(P, 0.24, 0.06, 0.42, (0, -0.4, 0.33), "wood_dk")        # door
    k.box(P, 0.16, 0.06, 0.16, (0.28, -0.4, 0.5), "ember")        # tiny ember window
    return k.join(P, "hovel")


def stable(k):
    """A grim timber stable (Epic-Miniatures silhouette): a dark shingled gable
    with a timber-frame end + big shadowed window over an enclosed tack room, an
    open row of arched Dutch-door stalls on a stone base, feed troughs of hay out
    front, and occult dressing — a cow skull nailed to the gable, a hung lantern,
    a witchlight rune branded on the front post."""
    P = []
    W, D, fh = 1.3, 2.0, 0.9
    z0 = 0.2
    fy, by = -D / 2, D / 2
    postx = W / 2 - 0.06
    k.box(P, W + 0.1, D + 0.06, 0.2, (0, 0, 0.1), "stone")                    # stone footing
    # ---- enclosed tack room (front gable end, -y) ----
    k.box(P, W, 0.12, fh, (0, fy + 0.06, z0 + fh / 2), "charwood")            # front wall
    k.box(P, 0.5, 0.18, 0.42, (-W / 2 + 0.25, fy + 0.03, z0 + 0.21), "stone")  # stone corner
    for sx in (-1, 1):                                                       # front corner studs
        k.box(P, 0.06, 0.06, fh, (sx * (W / 2 - 0.05), fy + 0.02, z0 + fh / 2), "wood_dk")
    k.box(P, W, 0.05, 0.06, (0, fy + 0.01, z0 + fh - 0.03), "wood_dk")        # front top rail
    k.box(P, 0.5, 0.06, 0.44, (0.12, fy - 0.02, z0 + 0.52), "soot")           # big dark window
    for wz in (z0 + 0.3, z0 + 0.74):
        k.box(P, 0.56, 0.05, 0.06, (0.12, fy - 0.05, wz), "wood_dk")          # sill + lintel
    for wx in (-0.13, 0.12, 0.37):
        k.box(P, 0.05, 0.05, 0.44, (wx, fy - 0.05, z0 + 0.52), "wood_dk")     # mullions
    for sx in (-1, 1):                                                       # tack-room side walls
        k.box(P, 0.12, 0.7, fh, (sx * (W / 2 - 0.06), fy + 0.4, z0 + fh / 2), "charwood")
    k.box(P, W, 0.12, fh, (0, fy + 0.7, z0 + fh / 2), "charwood")             # divider wall
    # ---- open stalls (back, +y) ----
    k.box(P, 0.12, D * 0.62, fh, (-W / 2 + 0.06, 0.32, z0 + fh / 2), "charwood")  # -x back wall
    k.box(P, W, 0.12, fh, (0, by - 0.06, z0 + fh / 2), "charwood")            # +y back wall
    for py in (fy + 0.7, 0.3, by - 0.06):
        k.box(P, 0.12, 0.12, fh, (postx, py, z0 + fh / 2), "wood_dk")         # stall posts
    for a, b in ((fy + 0.7, 0.3), (0.3, by - 0.06)):                         # 2 arched openings
        mid = (a + b) / 2
        k.box(P, 0.14, abs(b - a), 0.1, (postx, mid, z0 + fh - 0.05), "wood_dk")  # header
        for side in (a, b):
            d = 1 if side < mid else -1
            k.box(P, 0.1, 0.34, 0.08, (postx, side + d * 0.17, z0 + fh - 0.14),
                  "wood_dk", rot=(math.radians(d * 32), 0, 0))               # arch corner brace
        for gz in (z0 + 0.14, z0 + 0.42):                                    # Dutch-door rails
            k.box(P, 0.1, abs(b - a) - 0.16, 0.05, (postx, mid, gz), "wood_dk")
        for gy in (a + 0.14, mid, b - 0.14):                                 # balusters
            k.box(P, 0.08, 0.05, 0.42, (postx, gy, z0 + 0.28), "wood_dk")
        k.box(P, 0.5, abs(b - a) - 0.2, 0.1, (postx - 0.35, mid, z0 + 0.06), "thatch")  # hay bed
    # ---- dark shingled gable roof + ridge/eave trim ----
    rh = 0.72
    k.gable(P, W, D, rh, (0, 0, z0 + fh), "slate", over=0.2)
    sw = (W + 0.2) / 2
    theta = math.atan2(rh, sw)
    for i in range(7):                                                       # shingle courses
        f = 0.1 + i * 0.12
        for sgn in (-1, 1):
            k.box(P, 0.025, D + 0.22, 0.06, (sgn * sw * (1 - f), 0, z0 + fh + rh * f),
                  "stone_dk", rot=(0, sgn * theta, 0))
    k.box(P, 0.09, D + 0.24, 0.09, (0, 0, z0 + fh + rh), "stone_dk")          # ridge cap
    # ---- timber-frame truss on the FRONT gable triangle ----
    k.box(P, W, 0.06, 0.07, (0, fy - 0.06, z0 + fh + 0.03), "charwood")       # tie beam
    k.box(P, 0.07, 0.06, rh - 0.05, (0, fy - 0.06, z0 + fh + rh / 2), "charwood")  # king post
    for s in (-1, 1):
        k.box(P, 0.06, 0.06, 0.72, (s * W * 0.22, fy - 0.06, z0 + fh + rh * 0.42),
              "charwood", rot=(0, math.radians(s * 34), 0))                  # diagonal strut
    # ---- occult dressing ----
    _cow_skull(k, P, 0.0, fy - 0.12, z0 + fh + 0.22, s=0.15)                # skull on the gable
    k.box(P, 0.03, 0.03, 0.2, (postx + 0.05, fy + 0.72, z0 + fh - 0.02), "iron")   # lantern chain
    k.box(P, 0.12, 0.12, 0.16, (postx + 0.08, fy + 0.72, z0 + fh - 0.22), "soot")  # lantern box
    k.box(P, 0.07, 0.07, 0.1, (postx + 0.08, fy + 0.72, z0 + fh - 0.22), "amber")  # lantern flame
    if OCCULT:
        for dx, dz in ((0, 0.11), (0, -0.11), (-0.08, 0), (0.08, 0)):        # witchlight rune
            k.box(P, 0.05, 0.03, 0.05, (postx + 0.07, fy + 0.7 + dx, z0 + 0.52 + dz),
                  "witchlight")
    # ---- feed troughs of hay out front ----
    for tx, ty in ((-0.22, fy - 0.5), (0.42, fy - 0.42)):
        k.box(P, 0.34, 0.24, 0.16, (tx, ty, 0.12), "wood_dk")                # trough body
        k.box(P, 0.28, 0.18, 0.1, (tx, ty, 0.2), "thatch")                   # hay
    return k.join(P, "stable")


def _flame_banner(k, P, ox, oy, oz, s=1.0):
    """A tattered blood banner + amber Cthugha ("living flame") sigil, mirrored on
    both faces, hung on a pole and facing -y. ``(ox, oy, oz)`` is the cloth centre;
    ``s`` scales it. Shared warding standard flown by the watchtower and gate."""
    k.box(P, 0.92 * s, 0.05, 0.05, (ox, oy + 0.06, oz + 0.55 * s), "wood_dk")    # banner pole
    k.box(P, 0.8 * s, 0.02, 1.05 * s, (ox, oy, oz), "blood")                     # cloth panel
    if not OCCULT:
        for face_y in (oy - 0.02, oy + 0.02):                                   # heraldic lozenge
            k.box(P, 0.3 * s, 0.02, 0.3 * s, (ox, face_y, oz), "gold",
                  rot=(0, math.radians(45), 0))
            k.box(P, 0.16 * s, 0.02, 0.16 * s, (ox, face_y, oz), "blood",
                  rot=(0, math.radians(45), 0))
        return
    for tx in (-0.3, -0.1, 0.1, 0.3):                                           # tattered tips
        k.box(P, 0.16 * s, 0.02, 0.2 * s, (ox + tx * s, oy, oz - 0.62 * s), "blood")
    fcx, fcz = ox - 0.06 * s, oz - 0.2 * s
    slices = ((-0.22, 0.12), (-0.15, 0.2), (-0.08, 0.24), (-0.01, 0.22),
              (0.06, 0.16), (0.13, 0.1), (0.2, 0.05))
    for face_y in (oy - 0.02, oy + 0.02):                                      # flame sigil
        for i, (dz, w) in enumerate(slices):
            k.box(P, w * s, 0.02, 0.08 * s,
                  (fcx + max(0, i - 3) * 0.04 * s, face_y, fcz + dz * s), "amber")
        k.box(P, 0.08 * s, 0.02, 0.08 * s, (fcx + 0.24 * s, face_y, fcz - 0.14 * s), "amber")


def palisade_gate(k):
    """A grim warding gate: sharpened log walls flanking ironbound gate doors, a
    skull on a pike over the lintel, and the settlement's flame-sigil blood banner
    nailed over the gate."""
    P = []
    for s in (-1, 1):                                            # log walls flanking a gate
        for i in range(3):
            x = s * (0.55 + i * 0.22)
            k.cyl(P, 6, 0.11, 1.5, (x, 0, 0.75), "wood_dk")
            k.cone(P, 6, 0.11, 0, 0.16, (x, 0, 1.55), "wood_dk")  # sharpened tip
    k.box(P, 1.1, 0.14, 0.18, (0, 0, 1.4), "wood")               # gate lintel
    k.box(P, 0.9, 0.2, 1.2, (0, 0, 0.66), "charwood")            # gate doors
    skull(k, P, 0.0, -0.18, 1.75, 0.12)                          # skull on a pike over the gate
    _flame_banner(k, P, 0.0, -0.22, 0.95, s=0.72)                # warding standard on the gate
    return k.join(P, "palisade_gate")


def watchtower(k):
    """Dark-timber signal tower: charred legs with X-bracing, a side ladder, a
    railed platform, a hooded beacon brazier, and occult dressing (hung lantern,
    a skull spiked on a post, a tattered blood banner)."""
    P = []
    # dark-timber legs + horizontal ties
    for sx in (-1, 1):
        for sy in (-1, 1):
            k.box(P, 0.1, 0.1, 1.8, (sx * 0.45, sy * 0.45, 0.9), "charwood")  # legs
    for sy in (-1, 1):
        k.box(P, 0.9, 0.08, 0.08, (0, sy * 0.45, 0.95), "wood_dk")           # front/back tie
    for sx in (-1, 1):
        k.box(P, 0.08, 0.9, 0.08, (sx * 0.45, 0, 0.55), "wood_dk")           # side tie
    for d in (40, -40):                                                      # X-brace (left face)
        k.box(P, 0.06, 0.06, 1.3, (-0.45, 0, 0.9), "wood_dk", rot=(math.radians(d), 0, 0))
    # ladder up the right (+x) face — keeps the front banner face clear
    for ly in (-0.18, 0.18):
        k.box(P, 0.05, 0.05, 1.85, (0.6, ly, 0.92), "wood_dk")              # ladder rails
    for i in range(7):
        k.box(P, 0.05, 0.42, 0.04, (0.6, 0, 0.25 + i * 0.25), "wood_dk")     # rungs
    # platform + railing
    k.box(P, 1.2, 1.2, 0.12, (0, 0, 1.85), "charwood")
    for sx in (-1, 1):
        for sy in (-1, 1):
            k.box(P, 0.08, 0.08, 0.45, (sx * 0.5, sy * 0.5, 2.1), "wood_dk")  # rail posts
    for s in (-1, 1):
        k.box(P, 1.0, 0.05, 0.05, (0, s * 0.5, 2.05), "wood_dk")
        k.box(P, 0.05, 1.0, 0.05, (s * 0.5, 0, 2.05), "wood_dk")
    # beacon brazier
    k.cyl(P, 8, 0.2, 0.18, (0, 0, 2.0), "gunmetal")
    k.cone(P, 6, 0.18, 0, 0.32, (0, 0, 2.22), "ember")
    k.cone(P, 5, 0.1, 0, 0.2, (0.04, 0, 2.28), "amber")
    # open hood over the beacon (four posts + pyramid roof, sides open)
    for sx in (-1, 1):
        for sy in (-1, 1):
            k.box(P, 0.06, 0.06, 0.85, (sx * 0.34, sy * 0.34, 2.35), "wood_dk")  # hood posts
    k.box(P, 0.9, 0.9, 0.05, (0, 0, 2.78), "wood_dk")                         # hood plate
    k.cone(P, 4, 0.62, 0, 0.42, (0, 0, 3.0), "thatch_dk", rot=(0, 0, math.radians(45)))  # roof
    # occult dressing: hung lantern, spiked skull, tattered blood banner
    k.box(P, 0.03, 0.03, 0.18, (0.34, -0.34, 2.62), "iron")                  # lantern chain
    k.box(P, 0.12, 0.12, 0.16, (0.34, -0.34, 2.46), "soot")                  # lantern housing
    k.box(P, 0.07, 0.07, 0.1, (0.34, -0.34, 2.46), "amber")                  # lantern flame
    skull(k, P, -0.5, -0.5, 2.46, 0.11, glow_eyes=True)                      # skull on post
    # large tattered blood banner (flame sigil) on the FRONT (-y) face, hung proud
    # of the legs so nothing occludes it — the settlement's warding standard
    _flame_banner(k, P, 0.0, -0.56, 1.75)
    return k.join(P, "watchtower")


def windmill(k):
    """A stone-and-shingle fantasy windmill: a round coursed-STONE base, a
    wraparound wooden GALLERY (railing + brackets), a tapering RED-shingled upper
    tower with a pointed cap + finial, and four wooden LATTICE sails (X)."""
    P = []
    bh = 0.95
    k.cyl(P, 14, 0.62, bh, (0, 0, bh / 2), "stone")                    # round stone base
    for cz in (0.3, 0.6):
        k.cyl(P, 14, 0.63, 0.05, (0, 0, cz), "stone_dk")               # course bands
    k.box(P, 0.3, 0.12, 0.55, (0, -0.58, 0.3), "charwood")             # dark doorway
    for a in (55, 300):
        an = math.radians(a)
        k.box(P, 0.12, 0.12, 0.16, (math.cos(an) * 0.6, math.sin(an) * 0.6, 0.6), "soot")  # window
    # wraparound wooden gallery: brackets + deck + railing
    gz = bh
    for a in range(14):
        an = math.radians(a * 360 / 14)
        k.box(P, 0.06, 0.14, 0.06, (math.cos(an) * 0.66, math.sin(an) * 0.66, gz - 0.14),
              "wood_dk", rot=(math.radians(40), 0, an))                # support bracket
        k.box(P, 0.05, 0.05, 0.24, (math.cos(an) * 0.78, math.sin(an) * 0.78, gz + 0.13),
              "wood_dk")                                               # rail post
    k.cyl(P, 14, 0.82, 0.06, (0, 0, gz), "wood")                       # gallery deck
    k.cyl(P, 14, 0.8, 0.04, (0, 0, gz + 0.24), "wood_dk")             # rail top
    # tapering red-shingled tower + shingle courses + cap + finial
    th = 1.7
    k.cone(P, 14, 0.58, 0.16, th, (0, 0, gz + th / 2), "roof_red")
    for f in (0.25, 0.5, 0.75):
        k.cyl(P, 14, (0.58 - f * 0.42) + 0.015, 0.04, (0, 0, gz + th * f), "wood_dk")  # course
    k.cone(P, 14, 0.18, 0, 0.3, (0, 0, gz + th + 0.1), "roof_red")     # pointed cap
    k.cyl(P, 6, 0.03, 0.24, (0, 0, gz + th + 0.35), "iron")            # finial
    # sail hub + four LATTICE sails (X, flat/vertical), on an axle anchored to the tower
    hz = gz + 1.3
    hub = (0.0, -0.68, hz)
    R = 2.1                                                            # large sails
    k.box(P, 0.12, 0.66, 0.12, (0, -0.4, hz), "wood_dk")               # axle beam into tower
    k.cyl(P, 8, 0.12, 0.18, (0, -0.6, hz), "wood_dk", rot=(math.radians(90), 0, 0))  # hub
    for deg in (45, 135):
        an = math.radians(deg)
        sdx, sdz = math.sin(an), math.cos(an)                          # spar direction (XZ)
        k.box(P, 0.06, 0.06, R, hub, "wood_dk", rot=(0, an, 0))         # central spar
        k.box(P, 0.46, 0.02, R * 0.92, (hub[0], hub[1] - 0.03, hub[2]), "bone",
              rot=(0, an, 0))                                          # white sailcloth
        for fr in (-0.85, -0.6, -0.35, 0.35, 0.6, 0.85):              # sail battens
            k.box(P, 0.5, 0.02, 0.04,
                  (hub[0] + fr * sdx * (R / 2), hub[1] - 0.05, hub[2] + fr * sdz * (R / 2)),
                  "wood_dk", rot=(0, math.radians(deg + 90), 0))
    return k.join(P, "windmill")


def foot_bridge(k):
    """A derelict rope SUSPENSION footbridge over a dark, faintly glowing stream:
    end pylons carrying draped catenary cables with vertical hangers, a weathered
    slat deck that sags in the middle (with gaps + broken/missing planks), mossy
    stone abutments at the banks, and a lantern hung from a pylon."""
    P = []

    def _rope(x, y1, z1, y2, z2, color="ash", th=0.03):         # a rope segment in the YZ plane
        dy, dz = y2 - y1, z2 - z1
        k.box(P, th, math.hypot(dy, dz), th, (x, (y1 + y2) / 2, (z1 + z2) / 2),
              color, rot=(math.atan2(dz, dy), 0, 0))

    def deckz(y):
        return 0.3 + 0.12 * y * y                               # deck sags low in the middle

    def cablez(y):
        return 0.55 + 0.72 * y * y                              # cable catenary (parabola)

    ye, xs = 1.0, 0.52
    ys = [-1 + i * 0.25 for i in range(9)]
    # dark murky water with faint cursed glints
    k.box(P, 1.3, 2.3, 0.5, (0, 0, -0.28), "cloth")             # murky water
    for gy in (-0.5, 0.2, 0.7):
        k.box(P, 0.5, 0.14, 0.02, (gy * 0.3, gy, -0.02), "ghostfire")   # cursed glints
    # mossy stone banks that extend out into a trail on each side
    for sy in (-1, 1):
        k.box(P, 1.2, 1.3, 0.6, (0, sy * 1.4, 0.1), "stone")        # bank + trail
        for mx, my in ((-0.4, 1.0), (0.1, 1.15), (0.45, 0.95),
                       (-0.2, 1.6), (0.35, 1.75)):
            k.ico(P, 0.1, (mx, sy * my, 0.4), "leaf_dk")            # moss along the bank
    # end pylons: corner posts + top beam
    for sy in (-1, 1):
        for sx in (-1, 1):
            k.box(P, 0.08, 0.08, 1.0, (sx * xs, sy * ye, 0.85), "wood_dk")  # pylon post
        k.box(P, 2 * xs + 0.08, 0.08, 0.08, (0, sy * ye, 1.32), "wood_dk")  # top beam
    # anchor guy-ropes: post tops guyed out to angled stakes driven into the trail
    for sy in (-1, 1):
        for sx in (-1, 1):
            ay = sy * 1.7
            _rope(sx * xs, sy * ye, 1.28, ay, 0.46, color="rot", th=0.05)
            k.box(P, 0.06, 0.06, 0.42, (sx * xs, ay, 0.36), "wood_dk",
                  rot=(math.radians(-sy * 30), 0, 0))            # angled ground stake
    # draped catenary side cables (weathered) + vertical hangers
    for sx in (-1, 1):
        for i in range(len(ys) - 1):
            _rope(sx * xs, ys[i], cablez(ys[i]), ys[i + 1], cablez(ys[i + 1]),
                  color="rot", th=0.055)
        for y in ys[1:-1]:
            _rope(sx * xs, y, cablez(y), y, deckz(y) + 0.06, color="ash", th=0.02)
    # bearer ropes under the deck edges (follow the sag)
    for sx in (-1, 1):
        for i in range(len(ys) - 1):
            _rope(sx * 0.42, ys[i], deckz(ys[i]), ys[i + 1], deckz(ys[i + 1]),
                  color="rot", th=0.04)
    # weathered slat deck — gaps, plus askew / broken / missing planks
    for i in range(13):
        if OCCULT and i in (3, 8):
            continue                                            # missing plank (occult only)
        y = -0.95 + i * 0.155
        broken = OCCULT and i in (5, 10)
        w = 0.5 if broken else 0.9
        xo = 0.18 if broken else 0.0
        pitch = math.radians(9) if (OCCULT and i in (2, 7, 11)) else 0.0   # askew (occult)
        k.box(P, w, 0.12, 0.04, (xo, y, deckz(y) + 0.04 + (0.02 if pitch else 0)),
              "wood_dk", rot=(pitch, 0, 0))
    # lantern hung from a pylon top beam
    k.box(P, 0.03, 0.03, 0.18, (xs - 0.02, ye - 0.02, 1.22), "iron")    # chain
    k.box(P, 0.12, 0.12, 0.15, (xs - 0.02, ye - 0.02, 1.06), "soot")    # lantern box
    k.box(P, 0.07, 0.07, 0.1, (xs - 0.02, ye - 0.02, 1.06), "amber")    # lantern flame
    return k.join(P, "foot_bridge")


PIECES = [
    ("tavern", tavern),
    ("cottage", cottage),
    ("blacksmith", blacksmith),
    ("chapel", chapel),
    ("windmill", windmill),
    ("watchtower", watchtower),
    ("stable", stable),
    ("market_stall", market_stall),
    ("palisade_gate", palisade_gate),
    ("well", well),
    ("hovel", hovel),
    ("foot_bridge", foot_bridge),
]
