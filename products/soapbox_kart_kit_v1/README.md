# Soapbox Kart Kit — Low-Poly Cartoon Racing Kit

**26 modular low-poly racing pieces** (karts, track, hazards, pickups) **plus 5
textured mascot-racer characters** — a complete cartoon soapbox-racing set in the
*Soapbox Sabotage* style: bold, chunky, saturated. Karts, ramps, and hazards are
procedurally generated in Blender; the mascot racers are AI-generated (see below).

## Contents

### Karts (4)
- kart racer · kart rocket · kart tub · kart crate

### Track (7)
- track straight · track corner · track start (checkered) · ramp up · jump ramp
- finish gate · checkpoint arch

### Hazards & props (12)
- cone · tire stack · crate · barrier · barrel · haybale · oil slick · puddle
- boost pad · sign arrow · flag pole · banner

### Pickups (3, floating + glowing)
- pickup boost · pickup shield · pickup wrench

### Mascot racers (5, textured)
- robot · frog · wizard · shark · skeleton — each a character seated in a soapbox kart.

## Formats
- `models_glb/` — glTF binary (Godot, Unity, Unreal, Blender) — **recommended**
- `models_obj/` — Wavefront OBJ + MTL
- `models_fbx/` — Autodesk FBX
- `mascots/` — the 5 mascot racers as **textured GLB** (baked color; GLB only)

Kit pieces are flat-shaded solid-color low-poly on a **2-unit grid** — track and
ground tiles tile edge-to-edge (rotate in 90° steps); karts, hazards, and props
drop straight onto the grid.

## Mascot racers — how they were made
The 5 mascots were generated with a custom **`soapbox_style` Flux LoRA** (the
gritty cartoon kart-mascot look), then converted to 3D via **Hunyuan3D v2.0**
(image → textured mesh) and cleaned/recentered in Blender. They are ~20k-face
textured base meshes — great as static racers or as a starting point for your own
rig. Because they are AI-derived they are rougher than the hand-authored procedural
kit; disclose AI assistance where your platform requires it.

## Gallery
`gallery/` has a per-piece **turntable GIF** + **still PNG** for every item.
`catalog.png` is the labelled contact-sheet; `hero.png` is an assembled race scene.

## License
Royalty-free for personal & commercial projects. Do not resell or redistribute the
raw kit files. Procedural pieces are original Blender geometry; mascot racers are
AI-generated (Flux + Hunyuan3D) from original prompts — no third-party IP. Disclose
AI assistance where required.
