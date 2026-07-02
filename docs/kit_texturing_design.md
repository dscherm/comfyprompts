# Texturing & modularity design — matching KayKit (exploration)

Follow-up to `docs/kaykit_research.md`. Two things KayKit does that our procedural
kits don't yet: (a) they ship **individual modular parts** (wall / floor / door /
door-frame / window / roof / stairs …) that snap together, and (b) they texture
with a **shared color-atlas**, and premium tiers add **alternative textures**.
This doc explores how to integrate both into `kitlib` — no ComfyUI required.

## What KayKit actually does (verified)
- **Color-atlas technique (one texture per kit).** Every model is UV-mapped into a
  single shared gradient/palette atlas (1024×1024, downsampleable to 128×128).
  There are no per-object PBR maps — the whole kit uses one texture, so it's one
  material / near-one-draw-call and re-skinning is a texture swap.
  *(Dungeon Remastered: 283 models, 52–2212 tris, "1024×1024 texture UV mapped
  using the color atlas technique"; Adventurers/Hexagon: same atlas, →128².)*
- **"Alternative textures".** Premium tiers ship extra atlases (recolors / themes)
  — same UVs, different atlas = instant re-skin. This is the texture-space version
  of our `PALETTE_OVERRIDE` variants.
- **Modular parts.** Buildings/scenes are decomposed into the smallest reusable
  snap pieces — "modular walls with decorative variations, floors, stairs, doors,
  chests, barrels, …" — assembled LEGO-style on a grid. That's how one pack
  reaches 200–283 discrete models.
- Sources: kaylousberg.itch.io/kaykit-dungeon-remastered · /kaykit-adventurers ·
  github KayKit-Medieval-Hexagon-Pack-1.0 · KayKit-Dungeon-Remastered-1.0.

## A. Texture integration for `kitlib` (the color-atlas technique)
Today `kitlib.Kit.mat(name)` makes one flat Principled material per palette color
and assigns it per-face — N materials, no texture. To match KayKit, invert it:
**one atlas texture + one material for the whole object, faces UV'd to swatches.**

1. **Atlas generator (procedural, PIL/Blender — NOT ComfyUI).**
   `build_atlas(palette, emission) -> atlas.png` lays the ≤~32 palette colors out
   as a grid of **swatch cells**. Each cell is not a flat colour but a **vertical
   gradient** (light top → base → slightly darker bottom) to give KayKit's soft
   top-lit look, with an optional **baked-AO darkening** toward cell edges. Emissive
   names get a bright cell (+ a matching cell in an optional emission atlas).
   Output 1024² master; downsample to 128² for the shipping/mobile variant.
2. **UV assignment in the builders.** Add an atlas mode to `Kit`: instead of
   `mat(color)`, assign the single shared `atlas` material and set each new
   primitive's UVs so all its faces land inside that colour's swatch cell. For the
   gradient to read as top-lit, map the primitive's **world-Z extent → the cell's
   vertical axis** (top faces sample the light band, bottoms the dark band). Keep
   flat shading; the gradient comes from the texture, not smoothing.
3. **Variant = atlas swap.** Regenerate the atlas from a `PALETTE_OVERRIDE`
   (medieval / occult / snow / autumn / wasteland) → identical UVs, new skin. This
   folds our existing variant system into KayKit's "alternative textures".
4. **Export.** Ship the atlas PNG with the GLB/glTF (embedded) and reference it
   from OBJ `.mtl`; include the 128² downsample. One texture per kit.
5. **Payoff.** Closes rubric §4 (soft gradient/AO shading), gives ~1 draw call,
   tiny download, trivial recolors, and true KayKit-parity texturing — all
   procedural.

### Migration / risk
- Keep the current per-material path as the default; add `Kit(atlas=True)` so the
  swap is opt-in and reviewable piece-by-piece. Validate one piece (e.g. cottage)
  visually before converting the kit.
- UV-per-primitive is the real work: each `box/cyl/cone` needs a small UV-set step
  mapping its faces into the swatch (a `uv.new()` loop in `_finish`).

## B. Modular parts (to hit 200+ and true snap-modularity)
Convert whole-building pieces into **snap parts** on a grid so scenes assemble
LEGO-style (and the piece count multiplies toward KayKit's 200+):
- **Wall family:** `wall`, `wall_window`, `wall_door`, `wall_half`, `wall_corner`,
  `wall_gate` — all one grid unit wide, base-origin, seamless at the seam.
- **Openings:** `door`, `door_frame`, `window`, `shutter`, `arch`.
- **Floors/roofs:** `floor`, `floor_edge`, `roof_slope`, `roof_ridge`,
  `roof_corner`, `roof_end`, `dormer`, `chimney`.
- **Verticals/connectors:** `stairs`, `railing`, `post`, `beam`, `foundation`.
- Keep the current whole-building pieces as **pre-assembled showcases** built FROM
  the parts (so we ship both parts and ready buildings).
- Author every part with a **base-centre origin on the grid** (ties to the
  rubric §3 grid-quantize task) so parts interlock without gaps.

## Plan hooks (see `fix_plan.md` §E)
- Refine the "gradient/AO atlas" task to the **color-atlas technique** above
  (atlas generator + per-primitive UVs + atlas-swap variants + export).
- Add a **modular-parts decomposition** task (wall/floor/door/frame families,
  base-origin on grid) — the main lever to reach 200+ pieces.

## ComfyUI follow-ups (NOTED — not run)
- Optional: stylised hand-painted atlas art or hero normal-map bakes. The core
  gradient/AO atlas is fully procedural (PIL/Blender) and needs no ComfyUI.
