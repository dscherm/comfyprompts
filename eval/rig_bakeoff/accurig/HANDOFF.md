# RB2 — AccuRIG lane: the one manual step

AccuRIG has no CLI/API, so the rig itself is a GUI step (documented here for
reproducibility, per protocol). Everything before and after is automated.

## What to do (est. 5 min)

1. Open **AccuRIG** (Reallusion ActorCore app).
2. Import **`eval/rig_bakeoff/inputs/berserkr_cm.obj`** — plain OBJ, already
   centimeter-scale (180 cm tall). Do NOT convert or rescale on import.
3. Run the standard auto-rig flow (body markers → rig). Use the same settings
   as the original berserkr rig session — defaults, no manual weight painting
   (the bake-off measures the automatic result).
4. Export FBX (binary) to **`eval/rig_bakeoff/accurig/berserkr_accurig_bakeoff.fbx`**.
5. Say the word and Claude takes it from there (diagnostic renders via
   `scripts/rig_bakeoff/blender_render_protocol.py` + the bone map in this dir).

## Why not reuse products/.../berserkr_accurig.fbx?

It was rigged from the OLDER prep OBJ (Jul 13); the bake-off input is the v3
mesh (Jul 14). Lanes must share the identical input mesh or deltas stop being
attributable to the rigger. If re-rigging is a hassle, we can fall back to the
existing FBX as a provisional lane — but the mesh-version difference gets
recorded on the score sheet.

## Timing note

Record roughly how long the GUI session takes — "manual effort" is a scored
lane fact in docs/rig_bakeoff_protocol.md.
