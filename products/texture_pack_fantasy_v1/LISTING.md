# Texture pack — marketplace listing copy (ready to paste)

*Draft for B0.8. Use the labeled contact sheet (`_contact_sheet_labeled.png`) as
the cover/thumbnail; add a few per-material PBR strips as gallery images. Toggle
AI-disclosure ON wherever asked.*

---

## Title
`Fantasy Environment Materials — Vol. 1 (12 Seamless PBR Textures, 2K)`

## Short description
> 12 seamless, tileable 2K PBR materials for fantasy game environments —
> cobblestone, brick, planks, cracked earth, grass, granite, flagstone, bark,
> gravel, rusted metal, burlap, and sand. Each includes albedo + normal +
> roughness + AO. Drop-in ready for Unity, Unreal, and Godot.

## Full description (paste, markdown)
> **Fantasy Environment Materials — Vol. 1** is a set of **12 seamless, tileable
> PBR materials** built for stylized-realistic fantasy environments.
>
> **Each material includes 4 maps at 2048×2048 (2K):**
> - Albedo / Base Color
> - Normal (OpenGL, +Y up)
> - Roughness
> - Ambient Occlusion
>
> **Materials:** mossy cobblestone · stone brick wall · wood planks · cracked
> earth · forest grass · granite rock · castle flagstone · tree bark · gravel &
> pebbles · rusted metal · burlap cloth · desert sand.
>
> **Seamless guaranteed.** Generated with circular-padding diffusion and
> seam-preserving upscaling; every map tiles edge-to-edge with no visible seam.
>
> **Engine-ready.** Works in Unity (URP/HDRP), Unreal Engine, and Godot 4.
> Normal maps are OpenGL convention — flip green for DirectX projects.
>
> **License:** royalty-free for personal & commercial projects. AI-generated
> textures; no third-party IP used.

## Tags
`textures`, `PBR`, `seamless`, `tileable`, `materials`, `fantasy`, `environment`,
`game-ready`, `2K`, `stone`, `terrain`, `Unity`, `Unreal`, `Godot`

## Pricing (suggested)
- **$9.99** one-time (12-material 2K PBR pack is squarely in the $8–15 indie band), OR
- **Pay-what-you-want** / a free 3-material teaser as a lead magnet that links to
  the full pack + your other products (GrimForge LoRA, build-log).

## Platform notes
- **Fab (Epic):** category 3D → Materials/Textures. Mandatory AI-disclosure toggle ON.
- **Unity Asset Store:** category 2D → Textures & Materials. Fill the AI-content
  disclosure + "AI description" field (tools: SDXL + ESRGAN upscale; maps derived).
  Avoid "hand-painted" keywords.
- **Gumroad / itch.io:** zip the 12 material folders + README; cover = labeled
  contact sheet.

## Gallery (upload order)
1. `_contact_sheet_labeled.png` (cover)
2. `_2k_seam_check_mossy.png` (proves seamless tiling)
3. `_pbr_strip_burlap_cloth.png` (shows the 4-map PBR set)
4. 2–3 individual hero albedos (e.g. mossy_cobblestone, castle_flagstone, tree_bark)

## Pre-publish checklist
- [ ] Zip the 12 `<material>/` folders (each: albedo/normal/roughness/ao).
- [ ] Include `README.md` (usage + license + OpenGL-normal note).
- [ ] Cover image = labeled contact sheet.
- [ ] **Toggle AI-disclosure ON.**
- [ ] Set price + license to royalty-free commercial.
- [ ] (Recommended) validate one material in-engine/Blender first — confirm normal
      orientation reads correct before publishing (carryover: B0.7 PBR-viewer check).
