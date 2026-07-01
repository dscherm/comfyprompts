# village_kit — procedural GrimForge low-poly 3D kit pipeline

LLM-authorable procedural pipeline for the GrimForge low-poly 3D asset line
(the `village_kit_grimforge_*` products). Pieces are built from a small,
style-locked primitive DSL — not a generative mesh model — so output is clean,
grid-modular, flat-shaded, watertight game geometry every time.

## Why procedural, not a trained model
Clean modular kit pieces (1-unit grid, flat shading, locked palette, named
parts, single joined mesh) are exactly what generative 3D models are bad at.
The GrimForge style is defined by *constraint*, so we enforce it in code: an
LLM (or a human) writes builder functions against `kitlib`, and the style holds
by construction.

## Layers

| File | Role |
|------|------|
| `kitlib.py` | The DSL. Pure helpers (`hex_to_rgba`, `PALETTE`, `EMISSION`, `validate_palette`) import without Blender; the `Kit` class wraps `bpy` lazily (`box/cyl/cone/ico/gable/join/export_glb`). Palette covers medieval staples + a dark-fantasy/occult sub-palette tuned to the `grimforge_style` Flux LoRA. |
| `kit_pipeline.py` | Generic runner: a *spec* module → build each piece → export GLB → render a catalog PNG under a named aesthetic profile. |
| `kit_<name>.py` | A **spec**: `PIECES = [(name, fn(kit) -> obj), ...]`, optional `TITLE`, `AESTHETIC`, `PALETTE_OVERRIDE`, `EMISSION_OVERRIDE`. `kit_full.py`/`kit_vol2.py` reproduce shipped Vol.1/Vol.2; `kit_farmstead.py`/`kit_occult.py` are demos. |
| `godot_verify/` | Reusable Godot 4.6 project that imports the GLBs and renders an in-engine showcase under a matching aesthetic profile. |

## Aesthetic profiles
A spec declares `AESTHETIC = "medieval"` (default) or `"occult"`. The profile
sets palette bias, ground/lighting and (in `godot_verify`) the in-engine look:

- **medieval** — neutral key+fill, muted ground (the Vol.1/Vol.2 catalog look).
- **occult** — dark-fantasy: deep cool ambient + warm key, ember/amber/crimson
  accents. Derived from the `grimforge_style` LoRA (forge glow, dire-wolf amber
  eyes, crimson cape, cyan gems; no purple).

## Run

```bash
BLENDER="/c/Program Files/Blender Foundation/Blender 5.0/blender.exe"
# build pieces + catalog from a spec
"$BLENDER" -b --python kit_pipeline.py -- kit_occult.py /tmp/occult
# -> /tmp/occult/glb/*.glb  +  /tmp/occult/catalog.png
```

Then verify in Godot via `godot_verify/` (see its README).

Tests: `pytest tests/test_kitlib.py` (Blender-free); `kitlib_smoke.py` exercises
the `Kit` builders headless in Blender.

## Building conventions (for reproduction)

Patterns that recur across specs — reuse them so pieces stay consistent and
reproducible:

- **Flush windows, not protruding blocks.** A lit window is a *thin* emissive
  panel ~1cm proud of the wall face inside a `soot` recess frame — never a fat
  `ember` box poking out. See `_ember_win_x/_y`, `_boarded_win_x/_y`,
  `_x_window` (shuttered), `_gothic_window` (pointed lancet) in `kit_village_v1.py`.
- **Darken a whole kit at once** with a spec-level `PALETTE_OVERRIDE` remapping
  the light material names (`stone`, `plaster`, `slate`, `thatch*`) to dark
  values — one dict darkens every piece for the occult look without touching
  builders. Bright accents (`ember`/`amber`/`crimson`/`ghostfire`) still pop.
- **Stepped stone chimney (no gaps).** Stack solid boxes that *overlap in z* and
  narrow toward the top (broad breast → shoulders → narrow flue), alternating
  `stone`/`stone_dk` for courses. Angled shoulder blocks leave gaps — avoid them.
- **Derelict lean** = set `obj.rotation_euler` on the joined object before
  returning (a few degrees). It shows in per-piece close-ups; the showcase
  builder overrides instance rotation, so it's a per-asset (not scene) tilt.
- **Composite props are shared helpers**, so they read the same everywhere:
  `skull` (human, from kit_occult), `_cow_skull`, `_shield`, `_timber_frame_front`.
  A skull needs `soot` eye sockets pushed proud of the face to read as hollow.
- **Attach hanging things.** A hanging sign = wall bracket → crossbar → chains →
  board, each overlapping the next; a chimney finial sits *on* the cap, not in
  front of it. Floating/disconnected sub-pieces are the #1 review reject.
- **Match a reference:** save the image locally and read it, extract the
  silhouette + material blocks (e.g. stone base / timber upper / red dormered
  roof), build to that, then iterate from per-piece close-ups.
- **Shared warding standard.** `_flame_banner(k, P, ox, oy, oz, s)` draws the
  tattered blood banner + amber Cthugha "living-flame" sigil (mirrored on both
  faces) at a translated/scaled position. The watchtower and palisade gate both
  call it so they fly the *same* banner — factor recurring dressing into one
  helper rather than copy-pasting geometry.
- **Sigil on a flat cloth reads from any angle** only if you mirror it on *both*
  faces (draw each glyph element at `face ± 0.02`); a one-sided decal vanishes
  when the camera sees the back. Place it on the *hanging* part of a banner, not
  behind a rail/deck that occludes it.
- **Occult apothecary wares.** Green potion bottles = a `pine` (non-emissive
  green) body with a thin `witchlight` band at the liquid surface + `shroud`
  neck + `wood_dk` cork — a fully-emissive bottle blows out white. Round out a
  stall with a skull raised on a grimoire stack, mortar & pestle, candle, and a
  packed shelf.
- **A "hole" is a disc on top, not a recess.** A solid `k.cyl` drum has a solid
  top; a dark shaft reads only if you stack a `soot` centre disc over a glowing
  ring *on* the rim surface. Slide any occluder (a hanging bucket) off-centre —
  the rope can leave the roller at any x and still hang vertically.
- **Rope / cable / guy-line** = `_rope(x, y1, z1, y2, z2)` chaining short boxes
  along a curve in the YZ plane (single X-rotation per segment). Sample a
  parabola `z(y)` for a catenary sag (suspension-bridge cables, hangers); guy
  the pylons out to angled ground stakes on an extended bank so posts read as
  anchored, not free-standing.
- **Moss is `leaf_dk` (green), not `rot`** (khaki). Tilt-projected appliqués on a
  sloped face (e.g. an awning sigil) go through a small local→world helper that
  adds the tilt rotation and a proud-of-surface normal offset.
