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
