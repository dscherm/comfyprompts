# GrimForge Arsenal — Game-Ready Weapon & Loot Props (25, PBR)

25 low-poly, **game-ready**, PBR-textured fantasy weapon & loot props — the
Stream-C (static-prop) tier of the GrimForge line. Every asset is validated to the
`MESH-PRODUCT` spec and ships as **GLB + FBX** with a baked PBR texture set.

Produced by the toolchain's mesh-product pipeline:
`scripts/mesh_product_check.py` (validate + weld/decimate/UV/base-center) →
`scripts/mesh_pbr_bake.py` (bake albedo/AO/normal/roughness → GLB+FBX). This is the
**PBR game-ready version** of the `arsenal_kit_grimforge_v1` meshes.

## Contents (25)

Weapons: sword, greatsword, dagger, axe, battleaxe, halberd, spear, scythe, mace,
warhammer, flail. Magic/gear: wizard_staff, skull_staff, crystal_wand, spellbook,
orb, runestone, amulet, key. Loot: chest, coin_pile, potion (red/green/blue), lantern.

## Specs (every asset PASSES MESH-PRODUCT — see `mesh_validation_report.json`)

- **Poly budget:** 25 assets, **4,286 tris total** (~171 avg, max 456) — well under
  the 5,000-tri game-ready cap; low-poly, decimated cleanly.
- **Scale:** real meters, sane sizes (0.18–1.66 m), origin **base-centered**.
- **UVs:** unwrapped, in-bounds (non-overlapping by construction).
- **Normals:** consistent (recalculated outside).
- **PBR set per asset (1024²):** `albedo` + `ambient-occlusion` + `normal` +
  `roughness` in `textures/<name>_textures/`. GLB embeds albedo/roughness/normal on
  a Principled material; AO is provided as a separate occlusion map.
- **Formats:** `models_glb/` (textures embedded) + `models_fbx/`. Both open clean in
  Blender; GLB imports clean in Godot/Unity/Unreal.

## Import notes

- **Godot / Unity / Unreal:** import the GLBs directly (PBR material is wired).
- **FBX:** import at Scale Factor 1.0 (assets are already real-meter scaled).
- **AO map:** plug `<name>_ao.png` into your engine's occlusion slot if desired.
- Origins are base-centered — drop onto a surface at Y/Z=0.

## License & disclosure

Original IP (our own generated GrimForge assets). The **geometry was AI-generated**
(image→3D) and hand-finished + validated to spec; textures baked in Blender.
Disclose "Created with AI" where the platform requires it (Fab/Unity/itch). No
third-party IP.
