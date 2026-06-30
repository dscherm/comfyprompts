# Fantasy Environment Materials — Vol. 1

12 seamless, tileable PBR material sets for game engines (Unity / Unreal / Godot)
and 3D DCC tools. Built for stylized-realistic fantasy environments.

## Contents

12 materials, each with 4 maps (PNG):

| | | |
|---|---|---|
| mossy_cobblestone | stone_brick_wall | wood_planks |
| cracked_earth | forest_grass | granite_rock |
| castle_flagstone | tree_bark | gravel_pebbles |
| rusted_metal | burlap_cloth | desert_sand |

Per material (`<material>/`):
- `<material>_albedo.png` — base color
- `<material>_normal.png` — tangent-space normal (**OpenGL / +Y up**)
- `<material>_roughness.png` — roughness (grayscale)
- `<material>_ao.png` — ambient occlusion (grayscale)

**Resolution:** 2048×2048 (2K) — ESRGAN-upscaled (NMKD-Siax 4×) from SDXL-native
1024, with wrap-pad seam preservation so tiling survives the upscale.
**Tiling:** all maps are seamless — generated with circular-padding diffusion;
PBR maps derived with wrap-around filters so they tile identically to the albedo.
Verified via an edge-wrap continuity metric (`_seam_report.json`).

## Usage

- **Unity (URP/HDRP):** assign albedo→Base Map, normal→Normal Map (set texture
  type to Normal map), roughness→Smoothness source (invert if your shader uses
  smoothness), ao→Occlusion.
- **Unreal:** albedo→Base Color, normal→Normal (it's OpenGL — if your project is
  DirectX-normal, flip green), roughness→Roughness, ao→Ambient Occlusion.
- **Godot 4:** albedo→Albedo, normal→Normal Map (enable), roughness→Roughness,
  ao→AO.

> Normal maps are **OpenGL** convention (+Y up). For DirectX engines, invert the
> green channel.

## Notes / honesty

- Albedos are AI-generated (Stable Diffusion XL). **Disclose AI generation where
  your storefront requires it.**
- Normal/roughness/AO are **procedurally derived from the albedo** (height-from-
  luminance), not photometric scans — excellent for stylized work; for hero
  surfaces you may want hand-authored height. `rusted_metal` ships without a
  metallic map (treat as dielectric or add your own metallic mask).

## License

Royalty-free for personal and commercial projects (use in games/renders/products).
Do not resell or redistribute the raw texture files as a texture pack. AI-generated
content; no third-party IP used in prompts.
