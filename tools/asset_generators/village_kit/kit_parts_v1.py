"""GrimForge Modular Building Parts — a snap-together building system.

Ships the shared ``kit_parts`` vocabulary (walls / floors / roofs / openings /
structure) plus a demo house assembled from those parts, so a whole settlement
can be built on the grid from a small set of components.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from kit_parts import ALL_PARTS, house_demo  # noqa: E402

TITLE = "GrimForge Modular Building Parts (30 pieces)"
AESTHETIC = "medieval"
HERO_VIEW = "3q"   # parts are vertical (walls) — catalog from a 3/4 corner, not top-down
PIECES = ALL_PARTS + [("house_demo", house_demo)]
