# The Rookie (player)

## Description
Young male racer. Orange racing jacket with black stripes. Aviator goggles pushed up
on forehead. Fingerless brown leather gloves. Dark cargo pants. Heavy boots. Short
messy brown hair. Utility belt with tools. Confident stance. The everyman underdog.

Player character for Soapbox Sabotage (kart racer). Companion kart asset:
`output/final/player_kart/`.

## Provenance
- Concept: `artwork/player_char_v1_concept_front.png` / `_back.png` (arms-down detail refs)
- T-pose inputs: `artwork/player_char_v1_tpose_front.png` / `_back.png` (`A_front/A_back`)
- Reconstruction: **TRELLIS.2-4B multi-view** (front+back), fists-variant chosen over
  spread-fingers (spread collapsed to mitten/claw; fists gave thumb + separated fingers)
- Source mesh: `ComfyUI/output/Rookie_MV_fists_00001_.glb`

## Mesh Details
| Metric | Value |
|--------|-------|
| Face Count | 48,819 |
| Vertex Count | 23,356 (welded) |
| Dimensions (m) | 1.58 x 0.35 x 1.80 (Z-up) |
| Grounded/Centered | Yes (feet at Z=0, origin centered) |
| Watertight | Yes at fix sites; 7 tiny pre-existing TRELLIS boundary loops (head/waist, invisible) |
| Materials/UVs | None — geometry only (texturing is a downstream stage) |

## Rig Details
| Metric | Value |
|--------|-------|
| Skeleton Type | biped (UniRig, articulation-xl) |
| Bone Count | 40 (19 role-named for retarget; rest generic fingers/aux) |
| Weight Coverage | 100% (0 unweighted vertices) |
| Root Bone | hips |
| Post-fix | stray unrigged finger spur on right hand removed; mesh welded + resealed |

## Platform Compatibility
| Platform | File | Bone Convention | Notes |
|----------|------|-----------------|-------|
| Blender | `rigged/player_char_v1_blender.glb` | role names (hips, upperarm.l, ...) | retarget-map-ready (mixamo_to_unirig.json) |
| Unity | `rigged/player_char_v1_unity.fbx` | Mecanim Humanoid (19/19) | Avatar: use CreateFromThisModel |
| Unreal | `rigged/player_char_v1_unreal.fbx` | UE skeleton names | IK retarget compatible |

## Files
- `artwork/` — T-pose inputs + arms-down concept refs
- `mesh/player_char_v1_static.glb` — unrigged prepared mesh
- `mesh/player_char_v1_print.stl` — 3D-print STL (mm units, 1800mm tall — scale to taste)
- `rigged/` — platform rigged models

## Known Issues / Next Steps
- **No textures yet** — TRELLIS output is untextured geometry; run the texturing stage
  (Hunyuan3D paint / blender_normal_texturing) before shipping visuals.
- **Blender mocap retarget currently broken** (`retarget_mocap.py` mangles poses on ALL
  rigs incl. the GS1 barbarian set — pre-existing bug, misalign column 99-160° was
  rubber-stamped). Until fixed, do animation retargeting in Unity via the Humanoid
  avatar (Mixamo → CreateFromThisModel), not in Blender.
- IK posing works in Blender (2-bone chains on forearms proven live); direct Euler
  rotation of UniRig bones remains a trap (arbitrary local axes).

## Generation Metadata
- Generated: 2026-07-02
- 3D Tool: TRELLIS.2-4B (ComfyUI-Trellis2, multi-view mesh-only workflow)
- Rig Tool: UniRig (skeleton articulation-xl_quantization_256 + skin, seed 12345)
- Pipeline: art-to-rig-ralph (mesh-prep → rig → rename → export)
