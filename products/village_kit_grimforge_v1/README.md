# GrimForge Village — Low-Poly Medieval Kit (Vol. 1)

28 modular low-poly 3D pieces for building grim, weathered medieval villages.
Solid-color flat-shaded style, grid-modular, game-ready.

## Contents (28 pieces)

**Buildings (8):** cottage, house_small, house_tall, tavern, church, barn,
watchtower, blacksmith — Tudor timber framing, jetty overhangs, gable roofs,
stone chimneys, glowing windows.

**Walls & structures (3):** wall segment (crenellated), gatehouse, wall corner.

**Ground & paths (4):** grass tile, dirt tile, cobble path (straight), cobble
path (corner).

**Props (13):** well, market stall, barrel, crate, fence, tree, dead tree,
lamppost, brazier (glowing), signpost, cart, haystack, gravestone.

## Formats
- `models_glb/` — **GLB** (recommended; native in Godot, imports to Unity/Unreal/Blender)
- `models_obj/` — OBJ (+ .mtl)
- `models_fbx/` — FBX

Every piece is one mesh with solid-color materials (no textures — nothing to
mip-blur or break across engines).

## Modular system
All pieces are built on a **1-unit grid**, centered at origin with the base at
Y=0 (Godot) / Z=0 (Blender). Wall and path pieces tile edge-to-edge; rotate in
90° steps to build layouts. Buildings sit on a tile.

## Use
- **Godot 4:** drag the `.glb` files into your project; instance them as scenes.
  A ready example village scene is in `examples/godot_village/` (open `village.tscn`).
- **Unity:** import the GLBs (glTF) or the FBX; drop prefabs on a grid.
- **Blender / Unreal:** import GLB or FBX.
- Flat-shaded low-poly — use a single directional light + soft ambient for the
  intended look; the brazier/forge/windows are emissive.

## Style
GrimForge dark-fantasy palette: weathered timber, mossy stone, slate/thatch
roofs, muted earth tones with torch-orange glow accents. Pairs with the
GrimForge concept-art LoRA and texture pack.

## License
Royalty-free for personal & commercial projects. Do not resell/redistribute the
raw kit files as an asset pack. Procedurally generated; no third-party IP.

## Images
- `hero.png` — assembled village (dusk).
- `gallery_buildings.png` — hero-building close-ups.
- `catalog.png` — all 28 pieces.
- `examples/godot_village/` — runnable Godot 4 scene.
