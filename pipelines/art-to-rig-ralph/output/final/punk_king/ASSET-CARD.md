# Punk King — The Wasteland Queen

## Description
Imposing female leader. Spiked leather crown worn tilted. Punk vest covered in
chains and studs over black leather jacket with thick studded sleeves and heavy
armored gauntlets. Short waist-length royal purple half-cape. Spiked shoulder
pads. Black shorts, thigh-high armored boots. Wild dark hair, partially shaved
on one side. Sharp eyeliner, arrogant smirk.

Racer for Soapbox Sabotage (kart racer). Companion kart asset:
`output/final/punk_king_kart/`.

**Design note:** the sleeved jacket + short cape are a reconstruction-driven
revision of the original sleeveless/full-cape concept — see Provenance.

## Provenance
- T-pose inputs: `artwork/punk_king_tpose_front.png` (seed 1111) / `_back.png`
  (seed 1112) — mv_ortho Flux LoRA (strength 1.0, 768×1024)
- Reconstruction: **TRELLIS.2-4B multi-view**, `punk_king_MV4_00001_.glb`, seed 12345
- **Took 4 mesh attempts.** MV1/MV3 lost BOTH arms, MV2 lost one. Root cause:
  thin BARE arms vanish in TRELLIS sparse reconstruction (the full cape was a
  red herring — cape-clear images still lost the arms). Fix: thick studded
  SLEEVES + gauntlets → arms reconstruct reliably (W/H ratio 0.37→0.69).
  Lesson for future characters: no thin bare limbs in concept images.
- Texture: TRELLIS MeshTexturing_MultiView + metallic-zeroed diffuse bake
- Prep: `prep_character.py` (weld-first, guarded manifold pass)

## Mesh Details (prepared)
| Metric | Value |
|--------|-------|
| Face Count | 50,146 |
| Vertex Count | 24,906 (welded) |
| Dimensions (m) | 1.24 × 0.62 × 1.80 (Z-up, grounded; slight A-pose) |
| UVs | Smart-projected, single layer (pre-AccuRIG) |
| Texture | `textures/punk_king_albedo.png` (2048², baked diffuse) |

## Rig Details (ship path — AccuRIG 2)
| Metric | Value |
|--------|-------|
| Rig | AccuRIG 2 (CC_Base skeleton, 71 bones, 31 deform vgroups) |
| Input | `mesh/punk_king_for_accurig.obj` (cm units, UVs included) |
| Bind gate | `check_accurig_fbx.py` spread **1.00** (rigid) — ACCURIG_FBX OK |
| FBX | `rigged/punk_king_accurig.fbx` |

Gate note: AccuRIG embeds a single-frame `0_T-Pose` action that re-poses the
skeleton to its canonical T — on this A-posed character it read spread 9.44
and looked shredded in Blender while the BIND was perfectly rigid. The gate
now clears that action before measuring (fixed 2026-07-05); Unity never plays it.

## Unity Package (soapbox-unity)
`Assets/Animations/PunkKing/` — Humanoid avatar (isValid/isHuman),
`PunkKing.controller` (Idle default, Speed locomotion + 6 triggers), shared
Generic Mixamo clip set. `ValidatePunkKingHumanoid` = **RESULT: PASS**
(9/9 clips, 27/27 sampled poses, strict 3-layer protocol, 2026-07-05).
