# Pip — The Scavenger Kid

## Description
Small thin teenager. Green scavenger vest covered in patches and pockets. Oversized
backpack bulging with scrap parts. Nervously wide eyes. Patched cargo shorts.
Mismatched shoes. Fingerless gloves too big for his hands. Messy red hair sticking
up. Bandages on knees.

Racer for Soapbox Sabotage (kart racer). Companion kart asset: `output/final/pip_kart/`.

## Provenance
- T-pose inputs: `artwork/pip_tpose_front.png` / `_back.png` — mv_ortho Flux LoRA
  (strength 1.0, 768×1024, fists recipe; see CHARACTER-BATCH-RESUME.md)
- Reconstruction: **TRELLIS.2-4B multi-view** (front+back), `pip_MV_00001_.glb`, seed 12345
- Texture: TRELLIS MeshTexturing_MultiView on the full-res mesh, baked across
  topologies with metallic-zeroed diffuse bake (`uv_and_bake.py`)
- Prep: `prep_character.py` (weld-first; guarded interior-face deletion — this mesh
  is double-shelled and the unguarded manifold pass destroyed it, 50k→451 faces)

## Mesh Details (prepared)
| Metric | Value |
|--------|-------|
| Face Count | 50,166 |
| Vertex Count | 25,029 (welded) |
| Dimensions (m) | 1.45 × 0.45 × 1.80 (Z-up, grounded) |
| UVs | Smart-projected, single layer (pre-AccuRIG) |
| Texture | `textures/pip_albedo.png` (2048², baked diffuse) |

## Rig Details (ship path — AccuRIG 2)
| Metric | Value |
|--------|-------|
| Rig | AccuRIG 2 (CC_Base skeleton, 71 bones, 31 deform vgroups) |
| Input | `mesh/pip_for_accurig.obj` (cm units, UVs included) |
| Bind gate | `check_accurig_fbx.py` spread **1.00** (rigid) — ACCURIG_FBX OK |
| FBX | `rigged/pip_accurig.fbx` |

## Unity Package (soapbox-unity)
`Assets/Animations/Pip/` — Humanoid avatar (isValid/isHuman), `Pip.controller`
(Idle default, Speed locomotion + 6 triggers), shared Generic Mixamo clip set.
`ValidatePipHumanoid` = **RESULT: PASS** (9/9 clips, 27/27 sampled poses,
strict 3-layer protocol, 2026-07-05).
