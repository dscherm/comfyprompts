# Asset Generators

Procedural generators for the sellable asset products under `products/`. These
are the reproducible "source" for the binary outputs (GLB/PNG) shipped in each
product folder. Run with the Blender 5.0 / ComfyUI-venv Python noted per script.

## village_kit/ — GrimForge Village (low-poly 3D modular kit)
Blender 5.0 (`blender -b --python <script>`). Solid/vertex-color flat-shaded,
1-unit grid, GLB export.
- `kit_full.py` — Vol.1 (28 base pieces: buildings, walls, ground/paths, props).
- `kit_vol2.py` — Vol.2 expansion (windmill, ruins, bridge, fountain, grimdark props…).
- `improved.py … improved4.py` — feedback-driven reworks (Tudor framing, stained
  glass, detailed tower, solid arched gate, stone-block walls, lattice windmill).
- `apply_shading.py` — post-process: bakes the vertex-color gradient ("texture")
  onto every GLB + swaps in improved pieces.
- `village_demo.py` / `village_hero_v2.py` / `closeups.py` — marketing renders
  (catalog, assembled-village hero, building close-ups).

## tileset/ — 16×16 Fantasy RPG Tileset (pixel art)
ComfyUI-venv Python (PIL/numpy).
- `tileset_lib.py` — terrain tiles, Wang autotile transitions, object sprites.
- `tileset_build.py` — packs the atlas + metadata.json + mockup + Godot map export.

## texture/ — Fantasy Environment Materials (2K seamless PBR)
ComfyUI-venv Python.
- `derive_pbr.py` — normal/roughness/AO from albedo (wrap-padded, stays seamless).
- `upscale_to_2k.py` — seam-preserving 4× ESRGAN upscale (wrap-pad → crop → 2K).
(The seamless albedos themselves are generated via the comfyui-mcp `generate_texture_tile`
workflow — see `workflows/mcp/generate_texture_tile.json`.)
