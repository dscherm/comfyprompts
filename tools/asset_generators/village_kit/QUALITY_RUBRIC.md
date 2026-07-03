# Kit Quality Rubric — "KayKit-grade" bar for the procedural kits

The target quality bar for every GrimForge/procedural kit (village_kit, kit_city,
characters, future kits) is the polish level of the **KayKit** low-poly packs by
Kay Lousberg (e.g. *KayKit Medieval Hexagon*, *Dungeon*, *Adventurers*, *City
Builder*). This rubric turns that bar into explicit, mostly-measurable criteria
and maps each to our `kitlib` DSL so it can be used as a review gate in the build
workflow (see `kit_quality_check.py` for the automated subset).

> **Research status: COMPLETE** (`/deep-research` run `wf_0b532bb7-bed`, 106
> agents, cross-verified). Full report: `docs/kaykit_research.md`. Verified,
> cited findings (all 3-0 or 2-0 adversarial votes):
>
> 1. **Density** — a KayKit flagship kit ships **200+ discrete models** (~450
>    with recolors) across modular architecture + props + furniture + characters
>    + weapons. *(KayKit Dungeon 200+; Medieval Hexagon 200+/~450.)* **This is
>    our single biggest gap: our kits ship 12 pieces, not 200+.**
> 2. **Poly budget** — **20–5659 tris/model** (Medieval Hexagon), explicitly
>    mobile-suitable. Our flat-shaded primitives already match the shading
>    philosophy; keep most pieces far below ~5–6k tris.
> 3. **Modularity/grid** — pieces are authored on an explicit **snap grid**
>    (square for village/city; hex for hex kits) with **pivots at the grid
>    origin** so they interlock seamlessly. We do not yet grid-quantize.
> 4. **Texturing** — ONE shared **gradient/palette atlas, 1024×1024
>    (downsampleable to 128×128)**, UV-mapped by every model — *not* per-object
>    PBR. Our locked palette should become one shared atlas.
> 5. **Formats** — KayKit ships **FBX + OBJ + DAE + GLTF**. We ship GLB/OBJ/FBX
>    (add DAE + a plain-glTF option).
>
> Sources: kaylousberg.itch.io/kaykit-dungeon · /kaykit-adventurers ·
> github.com/KayKit-Game-Assets/KayKit-Medieval-Hexagon-Pack-1.0 ·
> /KayKit-Character-Pack-Adventures-1.0. None require ComfyUI.

## How to use it
- **Authoring / review:** score a kit against §1–§8; a piece "passes" only if it
  meets every MUST and ≥80% of SHOULD items.
- **Automated gate:** `python kit_quality_check.py <build_dir>` checks the
  machine-checkable rows (formats, naming, counts, palette, catalog/docs) and
  exits non-zero on a MUST failure. Wire it into `productize.py` / CI.
- **Manual gate:** the silhouette / detail-density / consistency rows are scored
  by eye from the per-piece close-ups (the item-by-item review workflow).

---

## 1. Geometry & poly budget
- **MUST** — flat/hard-surface low-poly: clean quad/tri faces, no n-gon artifacts,
  watertight single joined mesh per piece (we already `k.join`).
- **MUST** — poly budget bands (tris): small prop ≤ 300 · large prop 300–800 ·
  building 800–3000 · hero building ≤ 5000. Report tri-count per piece.
  *(kitlib gap: we never measure tris — add a tri-count line to the pipeline.)*
- **SHOULD** — **chamfered/beveled edges** on primary silhouette edges (KayKit's
  signature soft-catch highlight). *(kitlib gap: our `box/cyl/cone` are sharp —
  add an optional `bevel=` pass or a beveled-box helper.)*
- **SHOULD** — no interpenetration/z-fighting; parts overlap cleanly (already a
  review reject for us — keep enforcing).

## 2. Silhouette & readability
- **MUST** — the piece is identifiable in one glance from its silhouette alone
  (test: greyscale/black cutout still reads).
- **SHOULD** — 3-tier detail hierarchy: bold primary mass → secondary forms
  (roof, dormers, chimney) → tertiary greebles (trim, brackets, fixtures).
- **SHOULD** — avoid tangents & symmetric monotony; add asymmetric hero details.

## 3. Modularity & grid
- **MUST** — pieces snap to a consistent grid; footprints are whole/half units,
  origins at the base-centre, +Y-up on export (glTF). Consistent unit scale
  across the whole kit and across kits.
- **SHOULD** — connective/modular pieces (walls, floors, roads, corners, tiles)
  tile seamlessly with no gaps or overlaps at the seam.
- **SHOULD (hex kits)** — hex tiles share a single radius + edge profile.

## 4. Edge/shading & materials
- **MUST** — deliberate flat shading (we force `flat`); no accidental smoothing.
- **SHOULD** — KayKit look = a **small gradient/ramp + baked-AO texture atlas**
  giving soft top-lit gradients and contact shadows, *not* pure flat colour.
  *(kitlib gap: we use flat principled colours only. Options: (a) a vertical
  vertex-colour gradient + AO bake, (b) a shared ramp texture atlas. **ComfyUI
  follow-up candidate:** bake gradient/AO atlas — NOTE ONLY, do not run now.)*
- **MUST** — one shared material set per kit; ≤ ~16 palette entries in active use.

### 4a. Roof-material rule (structure → roof)
A roof's material must match the building's **status**, not default to slate. This
is codified in `kitlib.ROOF_RULES` / `roof_for(kind)` and enforced by construction
(each builder picks the roof colour for its class). Sloped roofs use the atlas
`shingle` pattern (board/tile courses) or `straw` (thatch); **stonework/masonry is
for walls and tower battlements only — never a sloped roof.**

| Structure class | Examples | Roof material |
|---|---|---|
| `humble` | cottage, hovel, barn, stable, well, shed | `thatch` (hay) |
| `dwelling` | common house, workshop, blacksmith, mill cap | `shake` (wood shingle) |
| `tradesman` | tavern, inn, shopfront, townhouse | `roof_red` (clay tile) |
| `grand` | manor, guild/town hall, church, cathedral, keep, gatehouse | `slate` |

- **MUST** — every sloped roof uses thatch / shake / roof_red / slate per the table;
  no `stone`/`stone_dk`/`plaster` on a roof surface.
- **SHOULD** — a kit shows ≥ 3 of the 4 roof materials so the settlement reads as a
  mix of statuses, not a uniform row.
- Victorian/urban kits (`kit_city_v1`) legitimately run slate-heavy (mansard roofs);
  the rule targets village/rural kits where humble buildings were over-roofed.

### 4b. House-assembly criteria (buildings & modular demos)
Derived by benchmarking the modular `house_demo` against the shipped kit houses
(`kit_full` cottage/house_tall, `kit_village_v1` cottage). A building — hand-built
or assembled from `kit_parts` — is only "done" when it passes all of these.

1. **Grounded — no hovering items (MUST).** The base sits on z=0; every element
   (door, chimney, trim, porch, sign) touches a supporting surface. The chimney
   rises *out of the roof*, not floating beside the mass; the door fills its
   opening down to the threshold. Nothing floats in air or stands off the wall.
2. **Closed shell — no unnatural gaps (MUST).** Four walls meet at corners with no
   daylight holes; the only openings are intended (doors/windows). No gap between
   the wall-top and the roof, and no step/gap between adjacent modular panels
   (seams should read as masonry joints, not cracks).
3. **Roof covers with modest, even eaves (MUST).** The roof spans the whole
   footprint and overhangs by a *small, uniform* eave — not an oversized flare.
   Ridge continuous; both slopes symmetric.
4. **Status-appropriate roof material (MUST).** Follow §4a: a cottage/humble house
   wears thatch or wood shake — **never slate**. Match the building's status, not
   a default.
5. **Textures per surface (MUST).** Walls = masonry/plaster/plank; roof =
   shingle/thatch courses; wood trim = planks; glass = gem/stained. Never a wall/
   roof wearing a ground pattern (cobble/gravel), never masonry on a roof.
6. **Openings aligned & framed (MUST).** Doors reach the ground, centred in a
   framed opening, correctly sized; windows framed + glazed at a consistent sill
   line; inserts fit their holes (no oversize/undersize/offset/proud floating).
7. **Believable proportions (SHOULD).** Wall ≈ one storey; for a cottage the roof
   height is ≤ the wall height (roof must not dominate); chimney small relative to
   the house; footprint reads as a home, not a tower.
8. **Continuous trim (SHOULD).** Base course/plinth, cornice, eave board, and
   ridge run continuously and align across panels; corner quoins tie the walls.
9. **Grid-aligned, base-centre origin (SHOULD).** Footprint on the unit grid;
   pivot at the base centre so the piece snaps and sits flush with neighbours.

**Quick reject test:** if you can see *through* the house, see *under* a floating
part, see a *masonry roof* or a *slate cottage*, or the roof *flares past* a tidy
eave — it fails and needs another pass.

### 4c. Physical plausibility — structures must obey physics (MUST)
Every piece must be buildable in stone: no element may hover, and no feature may
sit where there is no structure beneath it. Benchmarked against real castle
towers/gatehouses. A fortification is only "done" when it passes all of these.

1. **Battlements have a continuous parapet sill (MUST).** Crenellations are
   *merlons rising from a continuous low parapet wall*, NOT free-standing teeth on
   the rim. The crenel gaps between merlons stop at the parapet sill — you must
   **never see through a crenel gap down to the tower floor / wall-walk**. Build
   the sill first (a solid ring/edge course), then the merlons on top of it.
   *Reject signature:* a ring of teeth with full-height gaps exposing the floor.
2. **No floating stone (MUST).** Every merlon, corbel, course, and block rests on
   the structure below it. A ring of merlons must sit on a tower/parapet of the
   *same radius and centre* — never orphaned around empty space (e.g. circling a
   rooftop flag). If a decorative ring has no wall under it, it is a bug.
   *Reject signature:* stone teeth encircling a flagpole or hovering mid-air.
3. **Merlons touch their base (MUST).** No air-gap between a merlon and the
   parapet/cap it stands on; no merlon proud of the wall line it defends.
4. **Machicolations corbel out from the wall face (SHOULD).** The projecting
   parapet rests on a continuous corbel course that grows out of the wall below —
   the overhang is supported, not cantilevered from nothing.
5. **Load path to the ground (SHOULD).** Towers/roofs/spires transfer onto walls
   that reach z=0. An upper feature (spire, turret, hoarding) sits on a footprint
   at least as wide as its base directly beneath it.

**Quick reject test:** if you can see the *floor through the battlement gaps*, if
*teeth float* around a flag or in the air, or if any block sits on *nothing* — it
defies physics and needs another pass.

## 5. Colour palette discipline
- **MUST** — locked palette, harmonised across the kit; accents used sparingly.
  (We have this: `PALETTE` + `PALETTE_OVERRIDE`; `validate_palette()`.)
- **SHOULD** — value contrast reads at thumbnail size; emissive accents don't
  blow out (our recurring note: dim ember/witchlight in-scene).
- **SHOULD** — variant palettes (medieval / occult / snow / autumn) share
  structure so a palette swap re-skins the whole kit (already implemented).

## 6. Detail / prop density
- **MUST** — every building carries functional trim: window frames, door frame +
  handle/hinges, roof ridge/eaves/gutters, a chimney or vent, a base course.
- **SHOULD** — set-dressing props per building (barrels, crates, signage,
  planters, lanterns) and standalone filler props to reach KayKit density.
- **SHOULD** — a kit ships enough pieces to build a scene: structures + modular
  connectors + ≥ 30% small props/nature.

## 7. Consistency (cross-piece & cross-kit)
- **MUST** — shared helpers for recurring elements so they read identically
  everywhere (we have `skull`, `_flame_banner`, `_gargoyle`, `_arch_win`, …).
- **MUST** — consistent naming (`snake_case` piece names), consistent orientation
  (front = −Y), consistent origin/scale.
- **SHOULD** — a documented style contract per kit (palette, motifs, scale).

## 8. Deliverables & presentation
- **MUST** — export **GLB + OBJ/MTL + FBX** per piece (we do via `productize.py`).
- **MUST** — a catalog render + README + LISTING (we do). Add per-piece
  close-ups gallery + a hero shot + a turntable/GIF for the store page.
- **SHOULD** — an in-engine demo scene (Godot showcase — we have `godot_verify`).
- **SHOULD** — clean file tree: `models_glb/ models_obj/ models_fbx/ gallery/`.

---

## Scorecard (per kit)
| # | Criterion | Weight | Auto? |
|---|-----------|--------|-------|
| 1 | Geometry & poly budget | ●●● | partial |
| 2 | Silhouette & readability | ●●● | manual |
| 3 | Modularity & grid | ●●● | partial |
| 4 | Edge/shading & materials | ●● | partial |
| 5 | Palette discipline | ●● | auto |
| 6 | Detail / prop density | ●●● | manual |
| 7 | Consistency | ●● | partial |
| 8 | Deliverables & presentation | ●● | auto |

## Known kitlib gaps to close (feeds `plan.md`)
1. **No tri-count reporting** → add per-piece tri count to `kit_pipeline` output +
   assert against §1 bands in `kit_quality_check.py`.
2. **Sharp edges** → add a beveled-box / edge-bevel helper for silhouette edges.
3. **Flat colour only (no AO/gradient)** → vertex-colour gradient + AO bake, or a
   ramp atlas. (Atlas bake = **ComfyUI follow-up**, noted, not run.)
4. **Trim density** → shared trim helpers (window frame, door frame, eaves/gutter,
   base course) applied uniformly.
5. **Presentation** → auto per-piece gallery + hero + turntable in `productize`.

## ComfyUI follow-ups (NOTED — do not run as part of this work)
- Bake a shared **gradient + AO texture atlas** matching KayKit's soft-shaded look.
- Optional AI up-detailing / normal-map bakes for hero pieces.
