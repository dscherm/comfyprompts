# DissonantCity — Retro-Futurist Neon Low-Poly Kit

29 modular low-poly 3D pieces for building a retro-futurist neon city —
dark-navy bodies with glowing pink/cyan neon edge-outlines and window grids,
in the DissonantDreams synthwave aesthetic. Procedurally generated in Blender;
original work.

## Formats
- `models_glb/` — glTF binary (Godot, Unity, Unreal, Blender) — **recommended**
- `models_obj/` — Wavefront OBJ + MTL
- `models_fbx/` — Autodesk FBX

Emissive neon is baked into the materials. **GLB recommended** — Godot, Unity,
and Unreal read it natively and pick up the emission for in-engine glow/bloom;
FBX carries materials too; OBJ is flat geometry + MTL.

## Pieces (29)
- tower tall cyan
- tower tall purple
- tower short pink
- tower cyl
- tower spiral
- tower prism
- tower neon
- dome building
- arcology
- ziggurat
- slab shop pink
- slab shop cyan
- skybridge
- bridge support
- road straight
- road corner
- road junction
- plaza tile
- streetlight
- billboard
- neon arch
- hover car
- hover car2
- antenna
- holo pylon
- fountain pad
- crystals
- palm retro
- barrier

## Modular system
Pieces are centered at origin with the base at floor level on a 2-unit grid.
Roads, plaza tiles, and ground pieces tile edge-to-edge; rotate in 90° steps.
Towers, slabs, domes, and props drop straight onto the grid.

## Godot example
`examples/godot_city/` is a ready-to-run Godot 4 project:
- `viewer.tscn` — piece browser (turntable; cycle all 29 pieces with ← / →)
- `build.tscn` — full assembled neon city using the kit

Both scenes enable Godot's glow so the neon blooms in-engine.

## License
Royalty-free for personal & commercial projects. Do not resell or redistribute
the raw kit files. Pieces are procedurally generated Blender geometry — minimal
AI involvement; disclose AI assistance where required. No third-party IP.

*`hero.png` = assembled neon city · `catalog.png` = all 29 pieces.*
