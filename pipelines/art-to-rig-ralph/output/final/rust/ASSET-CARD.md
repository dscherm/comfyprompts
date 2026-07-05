# Rust — The Ironclad

## Description
Heavy-set male in rusted metal armor plates bolted together over his body.
Welding mask pushed up revealing scarred face. Thick chain around neck. Metal
gauntlets. Steel-toed boots. Red-brown color scheme. Short cropped hair.
Oldest, most experienced racer.

Racer for Soapbox Sabotage (kart racer). Companion kart asset:
`output/final/rust_kart/`.

## Provenance
- T-pose inputs: `artwork/rust_tpose_front.png` / `_back.png` — mv_ortho Flux
  LoRA (strength 1.0, 768×1024, fists recipe; bulky armor fought the T prior —
  needed seed rerolls + shortened outfit description)
- Reconstruction: **TRELLIS.2-4B multi-view**, `rust_MV_00001_.glb`, seed 12345
- Texture: TRELLIS MeshTexturing_MultiView + **metallic-zeroed** diffuse bake —
  critical here: the armor is metallic and baked pitch-black before the fix
- Prep: `prep_character.py` (weld-first, guarded manifold pass)

## Mesh Details (prepared)
| Metric | Value |
|--------|-------|
| Face Count | 48,346 |
| Vertex Count | 24,157 (welded) |
| Dimensions (m) | 1.53 × 0.40 × 1.80 (Z-up, grounded) |
| UVs | Smart-projected, single layer (pre-AccuRIG) |
| Texture | `textures/rust_albedo.png` (2048², baked diffuse) |

## Rig Details (ship path — AccuRIG 2)
| Metric | Value |
|--------|-------|
| Rig | AccuRIG 2 (CC_Base skeleton, 71 bones, 31 deform vgroups) |
| Input | `mesh/rust_for_accurig.obj` (cm units, UVs included) |
| Bind gate | `check_accurig_fbx.py` spread **1.00** (rigid) — ACCURIG_FBX OK |
| FBX | `rigged/rust_accurig.fbx` |

Gate note: the embedded AccuRIG `0_T-Pose` action read spread 16.2 on this rig
(false shred — the bind itself is rigid). Gate fixed 2026-07-05 to clear the
action before measuring; two "failed" re-exports were actually fine.

## Unity Package (soapbox-unity)
`Assets/Animations/Rust/` — Humanoid avatar (isValid/isHuman),
`Rust.controller` (Idle default, Speed locomotion + 6 triggers), shared Generic
Mixamo clip set. `ValidateRustHumanoid` = **RESULT: PASS** (9/9 clips, 27/27
sampled poses, strict 3-layer protocol, 2026-07-05).
