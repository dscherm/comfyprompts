# KayKit quality research (deep-research report)

Source: `/deep-research` workflow `wf_0b532bb7-bed` (106 agents, multi-source web
search + 3-vote adversarial verification). Question: what measurable criteria
define "KayKit-level" low-poly kit quality, and how do our procedural kitlib kits
compare? Consumed by `tools/asset_generators/village_kit/QUALITY_RUBRIC.md`.

## Executive summary
KayKit-level quality rests on five cross-verified pillars:
1. **Asset density & breadth** — 200+ discrete stylised models per flagship kit.
2. **Uniform low-poly flat/solid-shaded aesthetic** at a low, mobile-suitable
   poly budget.
3. **Explicit modularity / grid-snapping.**
4. **A single shared gradient/palette atlas texture** (not per-object PBR).
5. **Multi-format export** (FBX/OBJ/DAE/GLTF) with broad engine compatibility.

Our flat-shaded-primitive DSL already matches pillar 2 (shading) and is
philosophically aligned with pillar 4 (locked palette → one atlas). The real
gaps are **density (200+ vs 12)**, **formalised grid-snapping**, **cross-kit
consistency**, the **shared gradient atlas**, and **DAE/glTF export**. None
require ComfyUI — this is pure procedural-geometry + export-pipeline work.

## Verified findings (confidence: high; adversarial votes noted)

1. **Density benchmark — 200+ discrete models per kit** (3-0). KayKit Dungeon:
   "over 200 stylised 3D dungeon assets", 4 character types (Knight/Mage/
   Barbarian/Rogue) with alternate heads, 24 weapons across 3 tiers, modular
   architecture. Medieval Hexagon: 200+ hex tiles/buildings/props, ~450 with
   recolors. → **recolors count toward apparent variety**, which our
   palette-variant system already exploits.
   Sources: kaylousberg.itch.io/kaykit-dungeon; GitHub KayKit-Medieval-Hexagon.

2. **Style/geometry — uniform low-poly stylised, mobile poly budget** (3-0 / 2-0).
   Brand tagline "low poly stylised 3D game assets". Measurable: Hexagon pack
   **min 20 tris / max 5659 tris**, "suitable for all ranges of games, including
   mobile". Nuance: the look is a gradient-atlas on low-poly geo — reads flat but
   isn't literally flat shading; a flat-shaded primitive kit is a faithful match.
   Sources: kaylousberg.itch.io; /kaykit-adventurers; GitHub Hexagon.

3. **Modularity / grid-snapping is defining** (3-0). Modular dungeon pieces
   (walls/floors/stairs/doors) snap together; Medieval Hexagon is a hex-grid tile
   system. → author every environment piece on a consistent snap grid with
   pivots at the grid origin so pieces interlock without seams. **Current gap.**
   Sources: kaylousberg.itch.io; /kaykit-dungeon-remastered; GitHub Hexagon.

4. **One shared gradient/palette atlas, 1024×1024 → 128×128** (2-0). Adventurers
   repo verbatim: "Textured using a single gradient atlas texture (1024x1024)
   that can be downsampled to 128x128 for further optimization." Encode our
   locked palette as one shared atlas that all models UV into — cross-kit colour
   discipline + cheap mobile downsampling. Sources: /kaykit-adventurers; GitHub
   Character-Pack-Adventures.

5. **Multi-format export — FBX/OBJ/DAE/GLTF** (verified; some votes hit provider
   rate-limits but corroborated by store metadata). We ship GLB/OBJ/FBX → add
   DAE + plain glTF. Sources: itch.io pack pages; Unity/Godot store listings.

## Implications for our kits (feeds QUALITY_RUBRIC.md §Known gaps)
- Grow each kit toward **200+ pieces** (structures + modular connectors + many
  small props/nature + recolor variants).
- Add a **grid-quantize + base-pivot** pass to `kitlib`/`kit_pipeline`.
- Add per-piece **tri-count reporting** and assert the 20–~5.7k band.
- Build a **shared gradient/AO atlas** + UV the pieces into it (procedural bake
  in Blender/PIL — **not** ComfyUI).
- Extend `productize.py` exporters with **DAE + glTF**.

## ComfyUI follow-ups (NOTED — not executed)
- Optional: AI-assisted gradient/AO atlas art, or normal-map bakes for hero
  pieces. The core atlas can be made procedurally without ComfyUI.
