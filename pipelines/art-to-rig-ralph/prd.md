# Art-to-Rig — Soapbox Sabotage Kart Assets

## Overview

Generate 10 wheelless kart chassis bodies for "Soapbox Sabotage," a post-apocalyptic soapbox derby racing game. Each kart is a unique chassis reflecting its driver's personality. All karts are chassis-only (no wheels, no driver, open top, low to ground). Output: 2D reference illustrations, 3D meshes, and rigged GLBs for Unity.

**Source spec:** `D:\Projects\soapbox-unity\karts-ralph\kart-asset-spec.md`

## Style Guide

### Style
Underground comix illustration, post-apocalyptic junkyard aesthetic. 5 style variants used across 10 karts:

| Variant | Used By | Description |
|---------|---------|-------------|
| v2_mad_mag_racer | Punk King, Rust | Mad Magazine x Speed Racer. Bold ink, warm earth tones, chrome/red accents |
| v4_wasteland_zap | Bones, Pip, Smog, Sparks | R. Crumb Zap Comix. Black brushstrokes, dense crosshatching, sienna/oxidized palette |
| v5_fury_mag | Player, Soup Box | Mad Magazine x Fury Road. Confident ink, desaturated earth, vivid accent pops |
| v7_neo_mad | Crank | Mad Magazine x Akira. High contrast, neon glow on dark earth, cyberpunk wiring |
| v9_crumb_fury | Grit | Pure R. Crumb x Fury Road. Wobbly outlines, obsessive crosshatching, chrome/orange |

### Influences
- R. Crumb (Zap Comix) — dense crosshatching, wobbly organic outlines, obsessive grime
- Jack Davis (Mad Magazine) — exaggerated caricature, energetic loose brushwork
- Mad Max: Fury Road — welded scrap, improvised engineering
- Soapbox derby — gravity-powered, handmade, open-cockpit

### Color Palette
Burnt earth tones: sienna, oxidized orange, rust brown, gunmetal gray. Per-kart accent colors specified in asset list.

### Mood
Gritty, playful, chaotic. Junkyard contraptions held together by stubbornness and duct tape.

## Asset List

| # | Name | Description | Body Type | Variations | Style | Accent | Size (LxWxH) |
|---|------|-------------|-----------|------------|-------|--------|---------------|
| 1 | player_kart | "The Soapbox Racer" — Classic soapbox derby chassis from wooden crates and scrap planks. Mismatched boards, rope steering, hand-painted racing number, duct tape patches. | mech | 1 | v5_fury_mag | Warm orange (0.9,0.5,0.15) | 1.8x0.7x0.5 |
| 2 | bones_kart | "The Coffin Racer" — Coffin-shaped chassis. Dark stained wood, skull ornament, bone fragments tied with wire, tattered dark cloth. | mech | 1 | v4_wasteland_zap | Bone white (0.85,0.8,0.7) | 1.9x0.65x0.45 |
| 3 | crank_kart | "The Battle Wagon" — Heavy chassis reinforced with thick scrap metal plates. Spiked front bumper, welded frame, crude steering wheel, neon wires. Widest/most brutish. | mech | 1 | v7_neo_mad | Copper (0.72,0.45,0.2) | 1.6x0.9x0.6 |
| 4 | grit_kart | "The Precision Build" — Neatly built from salvaged wood and metal. Tool rack, hand-painted measuring marks, organized cables. Every joint deliberate. | mech | 1 | v9_crumb_fury | Desert tan (0.76,0.6,0.42) | 1.7x0.7x0.5 |
| 5 | pip_kart | "The Tiny Cart" — Smallest kart. Tin cans and small wooden boards. Barely big enough for a child. Rope steering. Comically small but aerodynamic. | mech | 1 | v4_wasteland_zap | Scavenger green (0.3,0.7,0.2) | 1.2x0.55x0.4 |
| 6 | punk_king_kart | "The Chrome Throne" — Chrome scrap and gold paint. Crown ornament from car parts. Salvaged car seat as throne. Racing flag banners. Most ostentatious. | mech | 1 | v2_mad_mag_racer | Royal purple (0.6,0.2,0.8) | 1.8x0.8x0.6 |
| 7 | rust_kart | "The Iron Tank" — Thick riveted iron plates. Heavy steel bumpers. Welding marks on every seam. Built like a small tank. Nothing fancy, just indestructible. | mech | 1 | v2_mad_mag_racer | Rust red (0.8,0.25,0.15) | 1.7x0.85x0.55 |
| 8 | smog_kart | "The Toxic Hauler" — Toxic green/yellow paint. Chemical canisters strapped to sides. Rubber tubes, corroded body, acid burn marks, hazard symbols. | mech | 1 | v4_wasteland_zap | Toxic green (0.4,0.75,0.15) | 1.75x0.75x0.5 |
| 9 | sparks_kart | "The Electric Skeleton" — Bare skeletal tube frame. No body panels. Battery packs, exposed wires sparking. Lightning bolt scratched into metal. Lightest/most fragile. | mech | 1 | v4_wasteland_zap | Electric blue (0.2,0.6,1.0) | 1.85x0.6x0.45 |
| 10 | soup_box_kart | "The Can Kart" — Giant industrial soup can laid on side IS the chassis. Open top for cockpit. Smaller cans as bumpers. Tin lid as rear spoiler. Literal "soapbox." | mech | 1 | v5_fury_mag | Tomato red (0.85,0.2,0.15) | 1.5x0.7x0.6 |

## Reference Images

Style references are defined by the 5 variant descriptions above. No external reference image files — rely on prompt engineering per variant.

## Background Preference

`remove_after` — Generate on solid grey background per the spec, then remove background in post-processing. The underground comix style benefits from free-form composition on grey, then clean removal.

## 2D Generation Settings

| Parameter | Value |
|-----------|-------|
| Resolution | 768 x 512 (landscape) |
| Model | Flux dev fp8 (preferred), SDXL (fallback) |
| Steps | 25 |
| CFG | 1.0 (Flux) or 7.0 (SDXL) |
| Background | Solid grey, removed in post-processing |

### Prompt Template
```
{art_style_for_kart}, {kart_description}, no wheels, no tires, wheelless chassis only, floating body without wheels, three-quarter front view of the vehicle only, empty vehicle with no driver no passenger no person no character sitting in it, empty open cockpit, vacant seat, product shot on solid grey background, vibrant full color illustration
```

### Negative Prompt (all karts)
```
blurry, low quality, deformed, ugly, photorealistic, 3D render, smooth digital art, anime, chibi, cute, Disney, Saturday morning cartoon, watermark, text, signature, frame, border, multiple vehicles, crowd, black and white, grayscale, monochrome, desaturated, pencil sketch, person, people, driver, character, face, human, figure, rider, motorcycle, bike, Mario, Nintendo, cartoon character, mascot, clean, pristine, new, shiny, speech bubble, text bubble, word balloon, dialogue bubble, comic text, letters, words, ground shadow, drop shadow, floor shadow, mud puddle, ground plane, closed roof, windshield, canopy, enclosed cockpit, car roof, closed top, wheels, tires, rubber tires, round wheels, spoked wheels, hubcaps, rims
```

## 3D Mesh Generation

Image-conditioned (no text prompt). Feed cleaned 2D reference.

| Parameter | Value |
|-----------|-------|
| Preferred model | Hunyuan3D v2.0 (textured) |
| Fallback chain | v2.5 PBR > v2.0 > Turbo > TripoSG > TripoSR |
| guidance_scale | 5.5 |
| steps | 50 |
| octree_resolution | 256 |
| max_faces | 20000 |

## Assembly Spec (Modular Hierarchy — MK-Style)

**Body type:** mech (modular prefab hierarchy, no armature/bones)

**Reference:** Mario Kart Standard Kart (`D:/Projects/mario-kart-reference/`) — 3 flat meshes, no skeleton, transform hierarchy in Unity prefab. Our approach: generate single mesh via ComfyUI, split by bounding-box region analysis in Blender, assemble into parent-child hierarchy with empties.

### Object Hierarchy (7 meshes + 16 empties per kart)
```
KartRoot (Empty @ origin)
├── Chassis (Mesh — center ~60% of geometry)
│   ├── Hood (Mesh — front section, detachable)
│   ├── Bumper_Front (Mesh — front bumper, detachable)
│   ├── Bumper_Rear (Mesh — rear bumper, detachable)
│   ├── Panel_L (Mesh — left side panel, detachable)
│   ├── Panel_R (Mesh — right side panel, detachable)
│   ├── Spoiler (Mesh — rear wing, detachable)
│   ├── Seat (Empty — driver attachment point)
│   └── EngineBay (Empty — exhaust particle anchor)
├── Axle_Front (Empty — steers left/right)
│   ├── WheelMount_FL (Empty — front-left wheel)
│   ├── WheelMount_FR (Empty — front-right wheel)
│   └── SteeringColumn (Empty — steering visual pivot)
├── Axle_Rear (Empty — fixed)
│   ├── WheelMount_RL (Empty — rear-left wheel)
│   ├── WheelMount_RR (Empty — rear-right wheel)
│   ├── Exhaust_L (Empty — particle anchor)
│   └── Exhaust_R (Empty — particle anchor)
├── FX_Boost_L (Empty — left boost particle spawn)
├── FX_Boost_R (Empty — right boost particle spawn)
├── FX_Drift_L (Empty — left drift spark spawn)
└── FX_Drift_R (Empty — right drift spark spawn)
```

Detachable parts are separate mesh objects parented to Chassis — detachment in Unity is simply unparenting + enabling physics. Wheel mounts are empties where wheel prefabs are instantiated at runtime (same pattern as Mario Kart).

### Region Split Rules (Bounding Box Fractions)

| Region | Length | Width | Height | Priority |
|--------|--------|-------|--------|----------|
| Bumper_Front | 0.90–1.0 | 0.1–0.9 | 0.0–0.4 | 1 |
| Bumper_Rear | 0.0–0.10 | 0.1–0.9 | 0.0–0.4 | 2 |
| Hood | 0.75–1.0 | 0.15–0.85 | 0.3–1.0 | 3 |
| Spoiler | 0.0–0.15 | 0.15–0.85 | 0.6–1.0 | 4 |
| Panel_L | 0.15–0.85 | 0.0–0.15 | 0.2–0.8 | 5 |
| Panel_R | 0.15–0.85 | 0.85–1.0 | 0.2–0.8 | 6 |
| Chassis | everything else | — | — | 7 |

### Back-Pressure Controls

| Failure | Recovery |
|---------|----------|
| ComfyUI timeout | Retry 3x with backoff |
| VRAM OOM | Halve octree_resolution (256→128→64→32) |
| Model failure | Fallback chain: Hunyuan3D v2.0 → Turbo → TripoSG → TripoSR |
| Blender crash | Retry 3x, checkpoint after each stage |
| Region < 10 verts | Merge back to Chassis |
| Mesh < 100 faces | Skip split, keep as single Chassis |
| Max concurrent ComfyUI | 2 jobs (semaphore) |
| Max concurrent Blender | 3 jobs (semaphore) |

### Pipeline Modes

| Mode | Script | Use Case |
|------|--------|----------|
| Headless batch | `mesh_split.py` + `kart_assembler.py` | Automated batch processing |
| Interactive | `kart_pipeline_interactive.py` via blender-mcp | Dev/iteration with visual feedback |

## Target Platforms

- [x] Unity (FBX — primary target, prefab hierarchy import)
- [x] Blender (GLB with matching object names)
- [x] Unreal Engine (FBX with UE axis conventions)
- [x] Static mesh (GLB, no hierarchy)
- [ ] 3D Print (STL) — not needed for this project

## Output Paths

| File | Location |
|------|----------|
| 2D reference PNGs | `output/final/{id}/artwork/{id}_kart.png` |
| Static GLBs | `output/final/{id}/mesh/{id}_kart.glb` |
| Split GLBs | `output/split/{id}_split.glb` |
| Assembled GLBs (Blender) | `output/final/{id}/{id}_kart_blender.glb` |
| Assembled FBX (Unity) | `output/final/{id}/{id}_kart_unity.fbx` |
| Assembled FBX (Unreal) | `output/final/{id}/{id}_kart_unreal.fbx` |
| Assembly reports | `output/final/{id}/{id}_assembly_report.json` |

## Acceptance Criteria

1. All 10 karts have: 2D reference PNG, cleaned PNG, static GLB, assembled GLB, Unity FBX, Unreal FBX
2. All 2D artwork matches assigned style variant (v2/v4/v5/v7/v9)
3. All illustrations show wheelless chassis only — no wheels, no driver, no roof
4. All 3D models are manifold with 0 non-manifold edges
5. All meshes have ≤20,000 faces (per spec)
6. All assembled karts have 7 mesh objects + 16 empties matching the specified hierarchy
7. WheelMount empties have no geometry (empty attachment points)
8. Chassis mesh has ~60% of total geometry
9. Detachable parts are separate mesh objects parented to Chassis
10. All exports importable in Unity/Blender/Unreal without errors
11. Background fully removed from all 2D references (transparent PNG)
12. BATCH-MANIFEST.md documents all 10 karts with quality scores
13. Back-pressure test suite passes (25 tests: failure recovery + throughput)
14. Pipeline supports both interactive (blender-mcp) and headless batch modes
