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
