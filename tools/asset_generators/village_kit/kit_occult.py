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
    # skull head with glowing witchlight eyes + jaw
    k.ico(P, 0.17, (0, 0, 1.34), "bone", sub=1)
    k.box(P, 0.13, 0.08, 0.05, (0, -0.12, 1.25), "bone")
    for s in (-1, 1):
        k.box(P, 0.045, 0.03, 0.05, (s * 0.06, -0.15, 1.37), "amber")
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
    """A LARGE dilapidated barn. It reads as a barn first — a big gable mass
    with board-and-batten siding, a tall doorway, and a projecting hayloft
    hoist beam (the iconic barn silhouette) — then carries a few DELIBERATE
    decay cues: a crooked hanging door with ember-lit interior gaping behind
    it, one missing wall board, rot, and weathered near-black timber. The
    decay is restrained and aligned, not random clutter."""
    P = []
    W, D, Hw, RH = 3.0, 3.8, 2.4, 1.5
    fy = -D / 2                       # front wall face (-y)
    fyg = -(D + 0.3) / 2              # gable front face (incl. overhang)
    # rotten ground pad
    k.box(P, W + 0.3, D + 0.3, 0.1, (0, 0, 0.05), "rot")
    # dark interior + an ember forge so the doorway and gaps glow from within
    k.box(P, W - 0.3, D - 0.3, Hw - 0.1, (0, 0, Hw / 2), "shroud")
    k.box(P, 1.2, 1.2, 0.9, (0, 0.3, 0.55), "ember")
    # solid walls (back + two sides)
    k.box(P, W, 0.18, Hw, (0, D / 2, Hw / 2), "charwood")
    for s in (-1, 1):
        k.box(P, 0.18, D, Hw, (s * W / 2, 0, Hw / 2), "charwood")
    # front wall: two segments flanking a tall doorway, plus a header beam
    door_w, door_h = 1.3, 1.9
    seg = (W - door_w) / 2
    for s in (-1, 1):
        k.box(P, seg, 0.18, Hw, (s * (door_w + seg) / 2, fy, Hw / 2), "charwood")
    k.box(P, door_w + 0.2, 0.2, Hw - door_h, (0, fy, (Hw + door_h) / 2), "charwood")
    # board-and-batten battens — regular spacing reads as siding, not noise
    for s in (-1, 1):
        base = s * (door_w + seg) / 2
        for bx in (-seg / 2 + 0.13, 0.0, seg / 2 - 0.13):
            k.box(P, 0.07, 0.04, Hw - 0.1, (base + bx, fy - 0.1, Hw / 2), "wood_dk")
        for yy in (-1.5, -0.75, 0.0, 0.75, 1.5):
            k.box(P, 0.04, 0.07, Hw - 0.1, (s * (W / 2 + 0.1), yy, Hw / 2), "wood_dk")
    # a broken-out gap in the right wall, set in the clear bay BETWEEN battens
    # (battens sit at y = -0.75 / 0.0), ember glowing through
    k.box(P, 0.22, 0.6, 0.8, (W / 2, -0.375, 1.35), "ember")
    # left door leaf hangs crooked; the right half gapes open (ember pours out)
    k.box(P, door_w / 2 - 0.06, 0.08, door_h, (-door_w / 4, fy - 0.04, door_h / 2 + 0.05),
          "wood_dk", rot=(0, 0, math.radians(-5)))
    for zz in (0.5, door_h - 0.15):
        k.box(P, door_w / 2 - 0.04, 0.05, 0.13, (-door_w / 4, fy - 0.09, zz), "charwood")
    # skull nailed beside the doorway
    k.ico(P, 0.14, (door_w / 2 + 0.3, fy - 0.06, 1.05), "bone", sub=1)
    # big weathered gable roof + ridge cap
    k.gable(P, W, D, RH, (0, 0, Hw), "ash", over=0.3)
    k.box(P, 0.12, D + 0.3, 0.12, (0, 0, Hw + RH), "charwood")
    # hayloft door in the front gable + projecting hoist beam (a barn signature)
    k.box(P, 0.8, 0.14, 0.8, (0, fyg + 0.12, Hw + 0.55), "charwood")     # frame
    k.box(P, 0.55, 0.12, 0.55, (0, fyg - 0.06, Hw + 0.55), "ember")      # opening glow
    k.box(P, 0.12, 0.8, 0.12, (0, fyg - 0.4, Hw + 1.05), "wood_dk")      # hoist beam out
    k.box(P, 0.34, 0.03, 0.55, (0, fyg - 0.62, Hw + 0.82), "crimson")    # banner
    return k.join(P, "creepy_barn")


PIECES = [
    ("dark_scarecrow", dark_scarecrow),
    ("creepy_barn", creepy_barn),
]
