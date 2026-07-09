---
name: kit-scene-layout
description: Assemble a coherent game scene from a modular building/tile kit (GrimForge castle/village kits) in Godot — grid-aligned buildings with doors facing paths, a seamless (gap-free) perimeter wall ring, and props. Covers the door-facing convention discovery, the wall-tiling math, and the two kit-asset render fixes (baked-gradient atlas, smoothed normals). Use when placing kit GLBs into a scene and the result must read as a real, connected settlement. Proven on the GrimForge playable demo, 2026-07-09.
---

# Kit Scene Layout (modular buildings + walls + props)

Turns a folder of modular kit GLBs into a coherent, connected scene: buildings
snapped to the tile grid with doors facing the paths, a perimeter wall ring
with NO gaps, and props that dress the space. The hard parts are (1) finding
each piece's door-facing direction, (2) tiling walls seamlessly, and (3) two
kit-render fixes that only bite once assets are TILED in-engine.

**Reference implementation**: `products/grimforge_playable_demo_v1/scripts/env.gd`
(`build`, wall ring, `_flatten_normals`, `_fixed_material`) +
`scripts/diag_buildings.gd` / `scripts/diag_doors.gd` (door-facing inspectors).
Kit source: `products/castle_kit_grimforge_v1/models_glb/` (~100 pieces).

## When to use

- Placing kit buildings/tiles/walls into a Godot scene (a courtyard, village,
  street) that must look intentional and connected.
- Not for: generating the kit itself, or rigging/animating characters (see
  `character-pipeline`, `equip-character-assets`).

## Step 0 — Instance from a layout table, don't hand-author .tscn

Build the scene at runtime: a `_place(model, pos, yaw)` helper that `load()`s
`res://kit/<model>.glb`, instances it, sets position + `rotation_degrees.y`.
Measure the tile pitch from the floor tile's AABB (`_footprint`) so the grid
adapts if the kit's scale changes. This keeps the layout in readable code, not
a giant resource file, and lets you re-tune fast.

## Step 1 — Fix the two kit-render defects (once per kit)

GrimForge kit GLBs have two latent issues that only show when TILED:
1. **Baked gradients in the atlas floor swatches** → tiles show row STRIPES.
   Fix: row-normalize the affected atlas regions into `atlas_color_fixed.png`
   and override the albedo on kit materials (`_fixed_material`). Do NOT edit
   the shipped kit — patch demo-side (memory `project_grimforge_products_predate_generators`).
2. **Smoothed vertex normals over hard box edges** → flat surfaces pillow-shade.
   Fix: rebuild each mesh non-indexed with per-face normals at load
   (`_flatten_normals`), orienting each face normal against the source normals.

Verify with a `--flat` debug mode (plain cobble grid, top-down) before/after.

## Step 2 — Discover the door-facing convention

Kits export pieces with a consistent "front". Find it once: render every
building at rotation 0 with axis markers (RED=+Z, BLUE=+X) in a labelled row
(`diag_buildings.gd` → a `.tscn`, run `godot --path . res://diag.tscn`
windowed). **GrimForge convention: the door/opening faces local +Z at yaw 0.**
For ambiguous pieces (great_hall's windowed facade, chapel), render just those
at yaw 0 vs 180, well-spaced (`diag_doors.gd`), to locate the entrance.

Godot Y-rotation maps local +Z to world by yaw:
`0 → +Z`, `90 → +X`, `180 → −Z`, `270 → −X`.
So to face a building's door toward the courtyard center:
- north edge (−Z) → yaw 0 (door +Z, inward)
- west edge (−X) → yaw 90 (door +X, inward)
- south edge (+Z) → yaw 180
- east edge (+X) → yaw 270

## Step 3 — Place buildings grid-aligned, doors to the paths

- Snap positions to whole tile pitches; use ONLY axis rotations
  (0/90/180/270) — odd angles (−120, 30) read as broken.
- Run the central paths (e.g. a flagstone cross) through the courtyard and
  put buildings along the edges facing those paths. A big piece (keep) can
  CAP a path (door facing down it).
- Keep footprints off the path tiles; leave the door tile clear.

## Step 4 — Seamless perimeter wall ring

Fixed-pitch loops leave gaps when the side length isn't a multiple of the wall
footprint, and corners don't meet. Instead:
```gdscript
var wpitch = wall_footprint.x
var span   = edge * 2.0
var count  = int(ceil(span / (wpitch * 0.97)))   # ~3% overlap => no seams
var step   = span / float(count)                  # exact division across the side
for i in range(count + 1):
    var t = -edge + i * step
    _place("wall", Vector3(t,0,-edge), 0)     # per side, yaw 0/90/180/270
    ...
_place("wall_corner", corner, 0)              # corners on top at exact ring corners
_place("gatehouse", south_center, 180)        # fills a sized gap in one side
```
Slight overlap is invisible on chunky low-poly walls; GAPS are the enemy.
Verify with a **top-down** screenshot — the ring must read as one continuous
line with corners closed.

## Step 5 — Colliders + props + verify

- Box collider from each building/wall AABB (StaticBody3D) so the player can't
  walk through; floors and thin decor stay non-solid.
- Props: braziers/torches flank the gate, banners/statue at the keep,
  barrels/crates by working buildings, trees in corners.
- Verify with an **isometric overview** + **top-down** (memory
  `project_godot_windowed_run_harness` for the screenshot harness). Iterate
  positions until it reads as an intentional, connected settlement.

## Gotchas

- Floor tile origin is at its center; walls' footprint differs from the floor
  pitch — measure each separately, don't assume one pitch.
- `rotation_degrees.y` only; keep buildings upright.
- Re-run the door-facing inspector when switching kits — the +Z convention is
  GrimForge-specific and may differ for another kit.
```
