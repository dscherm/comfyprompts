"""GrimForge Occult — dark-fantasy demo spec for kit_pipeline.

Showcases the occult aesthetic levers: the charred/shroud/rot/blood sub-palette,
emissive occult accents (witchlight eyes, ember dread-glow, rune sigils, glow
leaking through broken timber), and creepy construction motifs (crooked posts,
sagging/broken roofs, bones, hanging tatters).

    blender -b --python kit_pipeline.py -- kit_occult.py <out_dir>
"""

import math

TITLE = "GrimForge Occult (dark-fantasy preview)"
AESTHETIC = "occult"


def skull(k, P, cx, cy, cz, r, glow_eyes=False, scream=False):
    """Append a low-poly skull (faces -y) centered at (cx, cy, cz) with cranium
    radius r: rounded cranium, recessed face, dark eye sockets + nose cavity,
    and a jaw with teeth gaps (or a gaping maw when ``scream``). Shared by every
    piece that needs a skull so they all read consistently."""
    eye = "amber" if glow_eyes else "soot"
    k.ico(P, r, (cx, cy, cz), "bone", sub=1)                                       # cranium
    k.box(P, r * 1.5, r * 1.0, r * 1.15, (cx, cy - r * 0.25, cz - r * 0.55), "bone")  # face
    k.box(P, r * 1.2, r * 0.85, r * 0.5, (cx, cy - r * 0.4, cz - r * 1.05), "bone")   # jaw
    for s in (-1, 1):                                                               # eye sockets
        k.box(P, r * 0.42, r * 0.42, r * 0.4,
              (cx + s * r * 0.42, cy - r * 0.78, cz - r * 0.28), eye)
    k.box(P, r * 0.24, r * 0.34, r * 0.32, (cx, cy - r * 0.82, cz - r * 0.66), "soot")  # nose
    if scream:
        k.box(P, r * 0.55, r * 0.4, r * 0.72, (cx, cy - r * 0.8, cz - r * 0.95), "soot")
    else:
        for tx in (-r * 0.45, -r * 0.15, r * 0.15, r * 0.45):                       # teeth gaps
            k.box(P, r * 0.05, r * 0.2, r * 0.4, (cx + tx, cy - r * 0.8, cz - r * 1.05), "soot")


def dark_scarecrow(k):
    P = []
    # crooked charred post + sagging cross-arm
    k.box(P, 0.09, 0.09, 1.5, (0, 0, 0.72), "charwood", rot=(math.radians(3), 0, math.radians(3)))
    k.box(P, 1.0, 0.08, 0.08, (0, 0, 1.06), "charwood", rot=(0, math.radians(5), 0))
    # ragged shroud body + dangling tatters
    k.box(P, 0.36, 0.22, 0.46, (0, 0, 0.96), "shroud")
    for sx, zz in [(-0.13, 0.66), (0.05, 0.62), (0.14, 0.68)]:
        k.box(P, 0.08, 0.04, 0.24, (sx, -0.1, zz), "shroud")
    # tattered crimson cape draped off the back (GrimForge signature accent)
    k.box(P, 0.34, 0.05, 0.5, (0, 0.13, 0.95), "crimson", rot=(math.radians(7), 0, 0))
    for sx, zz in [(-0.12, 0.6), (0.13, 0.57)]:
        k.box(P, 0.1, 0.04, 0.26, (sx, 0.14, zz), "crimson")
    # bony dead-branch arms reaching along the cross
    for s in (-1, 1):
        k.cyl(P, 5, 0.03, 0.5, (s * 0.3, 0, 1.06), "bone", rot=(0, math.radians(90), 0))
        k.cyl(P, 5, 0.02, 0.18, (s * 0.5, 0, 1.08), "bone",
              rot=(0, math.radians(90), math.radians(s * 22)))
    # screaming skull head — glowing amber eyes + a gaping maw
    skull(k, P, 0, 0, 1.34, 0.16, glow_eyes=True, scream=True)
    # tattered wide-brim hat
    k.cyl(P, 7, 0.3, 0.04, (0, 0, 1.47), "charwood")
    k.cone(P, 7, 0.17, 0.02, 0.2, (0, 0, 1.58), "charwood")
    # a crow perched on the cross-arm tip (legs gripping the arm; faces -y)
    cx = 0.46
    for lx in (-0.03, 0.03):
        k.cyl(P, 4, 0.012, 0.1, (cx + lx, -0.01, 1.13), "charwood")       # legs
    k.box(P, 0.1, 0.24, 0.12, (cx, 0.03, 1.2), "charwood")               # body (leans back)
    k.ico(P, 0.06, (cx, -0.13, 1.27), "charwood", sub=1)                 # head
    k.cone(P, 4, 0.03, 0, 0.12, (cx, -0.22, 1.26), "charwood",           # beak (tip -> -y)
           rot=(math.radians(90), 0, 0))
    k.box(P, 0.08, 0.16, 0.04, (cx, 0.18, 1.24), "charwood",             # fanned tail, up
          rot=(math.radians(30), 0, 0))
    for ex in (-0.035, 0.035):
        k.box(P, 0.022, 0.022, 0.022, (cx + ex, -0.15, 1.29), "amber")   # glowing eyes
    # a dark blood-stained ground at its feet (ritual dread, no occult-glow —
    # the LoRA never uses purple sigils; it uses blood-red)
    k.box(P, 0.55, 0.55, 0.03, (0, 0, 0.015), "rot")
    k.box(P, 0.4, 0.4, 0.02, (0, 0, 0.03), "blood")
    k.box(P, 0.22, 0.22, 0.02, (0, 0, 0.04), "crimson")
    return k.join(P, "dark_scarecrow")


def creepy_barn(k):
    """A large CHARRED, dilapidated barn: board-and-batten siding, X-braced
    double doors with pale weathered bracing, a framed roof (ridge cap +
    purlins + rafter tails), an ember-lit interior leaking through the doors
    and a lowered broken window, soot scorch/smoke around the openings, and a
    projecting hayloft hoist beam."""
    P = []
    W, D, Hw, RH = 3.0, 3.8, 2.4, 1.5
    fy = -D / 2                       # front wall face (-y)
    fyg = -(D + 0.3) / 2              # gable front face (incl. overhang)
    # rotten ground pad
    k.box(P, W + 0.3, D + 0.3, 0.1, (0, 0, 0.05), "rot")
    # dark interior + an ember forge so the doorway and gaps glow from within
    k.box(P, W - 0.3, D - 0.3, Hw - 0.1, (0, 0, Hw / 2), "shroud")
    k.box(P, 1.2, 1.2, 0.9, (0, 0.3, 0.55), "ember")
    # charred timber walls (back + two sides)
    k.box(P, W, 0.18, Hw, (0, D / 2, Hw / 2), "charwood")
    for s in (-1, 1):
        k.box(P, 0.18, D, Hw, (s * W / 2, 0, Hw / 2), "charwood")
    # front wall: two segments flanking a tall doorway, plus a header beam
    door_w, door_h = 1.3, 1.95
    seg = (W - door_w) / 2
    for s in (-1, 1):
        k.box(P, seg, 0.18, Hw, (s * (door_w + seg) / 2, fy, Hw / 2), "charwood")
    k.box(P, door_w + 0.2, 0.2, Hw - door_h, (0, fy, (Hw + door_h) / 2), "charwood")
    # board-and-batten battens
    for s in (-1, 1):
        base = s * (door_w + seg) / 2
        for bx in (-seg / 2 + 0.13, 0.0, seg / 2 - 0.13):
            k.box(P, 0.07, 0.04, Hw - 0.1, (base + bx, fy - 0.1, Hw / 2), "wood_dk")
        for yy in (-1.5, -0.75, 0.0, 0.75, 1.5):
            k.box(P, 0.04, 0.07, Hw - 0.1, (s * (W / 2 + 0.1), yy, Hw / 2), "wood_dk")
    # LOWERED broken window in the right wall — a THIN flush glowing panel set
    # in the clear bay between battens (does not stick out), with a soot frame
    k.box(P, 0.05, 0.62, 0.72, (W / 2 + 0.05, -0.375, 1.0), "soot")     # dark recess/frame
    k.box(P, 0.04, 0.5, 0.6, (W / 2 + 0.07, -0.375, 1.0), "ember")      # glow panel (flush)
    k.box(P, 0.05, 0.66, 0.5, (W / 2 + 0.04, -0.375, 1.5), "soot")      # scorch above
    # X-braced double doors (flat, closed): dark leaves with a pale plaster
    # frame + a real X. The diagonals rotate about Y so they lie ON the door
    # face. A thin centre gap lets the ember interior leak out.
    dl = door_w / 2 - 0.05                       # leaf width
    diag = math.atan2(door_h - 0.18, dl)         # corner-to-corner angle
    dlen = math.hypot(dl, door_h - 0.18)
    for s in (-1, 1):
        lx = s * (door_w / 4 + 0.015)
        k.box(P, dl, 0.07, door_h, (lx, fy - 0.04, door_h / 2 + 0.05), "wood_dk")   # leaf
        k.box(P, dl, 0.05, 0.09, (lx, fy - 0.1, 0.16), "plaster")                   # bottom rail
        k.box(P, dl, 0.05, 0.09, (lx, fy - 0.1, door_h - 0.04), "plaster")          # top rail
        for ex in (-dl / 2 + 0.04, dl / 2 - 0.04):                                  # stiles
            k.box(P, 0.07, 0.05, door_h, (lx + ex, fy - 0.1, door_h / 2 + 0.05), "plaster")
        for d in (1, -1):                                                           # the X brace
            k.box(P, dlen, 0.05, 0.07, (lx, fy - 0.12, door_h / 2 + 0.05),
                  "plaster", rot=(0, d * diag, 0))
    # soot / smoke staining around the doorway
    for sx in (-door_w / 2 - 0.02, door_w / 2 + 0.02):
        k.box(P, 0.1, 0.12, door_h, (sx, fy - 0.02, door_h / 2 + 0.05), "soot")
    k.box(P, door_w + 0.3, 0.1, 0.7, (0, fy - 0.04, door_h + 0.15), "soot")  # smoke above door
    k.box(P, 0.16, 0.06, 1.7, (-(door_w + seg) / 2, fy - 0.12, Hw / 2 + 0.1), "soot")
    # skull nailed beside the doorway
    skull(k, P, door_w / 2 + 0.32, fy - 0.12, 1.05, 0.13)
    # --- roof: gable + clean framing (ridge cap + eave fascia + rafter tails) ---
    k.gable(P, W, D, RH, (0, 0, Hw), "ash", over=0.3)
    k.box(P, 0.12, D + 0.4, 0.12, (0, 0, Hw + RH), "charwood")          # ridge cap
    for s in (-1, 1):
        k.box(P, 0.1, D + 0.4, 0.14, (s * (W / 2 + 0.16), 0, Hw + 0.04), "charwood")  # eave fascia
        for yy in (-1.6, -0.96, -0.32, 0.32, 0.96, 1.6):               # rafter tails poking out
            k.box(P, 0.3, 0.06, 0.06, (s * (W / 2 + 0.13), yy, Hw - 0.04), "charwood",
                  rot=(0, math.radians(s * 42), 0))
    # hayloft door in the front gable (thin flush glow) + projecting hoist beam
    k.box(P, 0.8, 0.14, 0.8, (0, fyg + 0.12, Hw + 0.5), "charwood")
    k.box(P, 0.5, 0.05, 0.5, (0, fyg - 0.005, Hw + 0.5), "ember")
    k.box(P, 0.12, 0.8, 0.12, (0, fyg - 0.4, Hw + 1.0), "wood_dk")
    k.box(P, 0.34, 0.03, 0.55, (0, fyg - 0.62, Hw + 0.77), "crimson")
    return k.join(P, "creepy_barn")


PIECES = [
    ("dark_scarecrow", dark_scarecrow),
    ("creepy_barn", creepy_barn),
]
