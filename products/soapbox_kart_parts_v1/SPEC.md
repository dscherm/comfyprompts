# Soapbox Kart Parts Kit — SPEC

*Modular, swappable soapbox-kart parts + junkyard weapons, in the `gritty_comic`
character art style, built 2D-concept → image-to-3D. Draft for approval, 2026-07-18.*

---

## 1. Vision

A **modular kart kit**: a library of interchangeable 3D parts — chassis, wheels,
engines, roofs, side panels, noses, tails, seats, plus **12 junkyard weapons** — that
snap together to build endless soapbox karts. Trade a wheel, swap an engine, bolt on a
chainsaw arm. Like `products/parts_kit_grimforge_v1` does for buildings (44 modular
GLB/OBJ parts), but for karts, and self-describing via **attachment metadata** so any
engine (starting with `soapbox-unity`) can auto-assemble.

Two output tiers (user decision — "both"):
- **Isolated parts** — the kit: one clean part per file, for swapping.
- **Whole karts** — hero/marketing renders + assembled references showing parts in situ.

## 2. Inputs (what grounds this)

| Input | Path | Role |
|---|---|---|
| **`gritty_comic` LoRA** | `ComfyUI/models/loras/style/soapbox_char_final_v1` | THE style — heavy-ink cel-shaded full-color comic (trained this session) |
| **Old kart sprites** | `soapbox-unity/Assets/Sprites/Karts/*_kart_old.png` | FORM reference — hot-rod shape, fat tires, tubular frame, per-character themes. Restyled, not copied. |
| **Parts kit** | `products/parts_kit_grimforge_v1` | Modularity model — 44 parts, per-part GLB/OBJ/FBX + shared atlas + catalog |
| **Weapons PRD** | `soapbox-unity/weapons-ralph/prd.md` | 12 weapons, mount points, junkyard scrap aesthetic, per-character accents |

## 3. Style contract

**Every part rendered in `gritty_comic`:** heavy black ink linework, cel + rendered
shading, full saturated color, weathered/junkyard scrap surfacing (rust, gunmetal,
copper, charred, duct tape — the weapons PRD palette, which harmonizes). NOT the
painterly semi-realism of the old sprites; NOT the bold-cartoon low-poly of the existing
`soapbox_kart_kit_v1`. Per-character **signature colors** carry as accents (crank=orange/
brass, pip=red+olive, sparks=electric-blue, smog=toxic-green, punk_king=purple/blood-red,
rust=rust-orange, grit=grey+leather, bones=bone-white).

## 4. Modular architecture — the attachment metadata system

The heart of the kit. Every part is self-describing so assembly is data-driven, not
hand-wired.

### 4.1 Socket-type vocabulary (defines compatibility)

A part **plugs into** exactly one socket type and may **expose** further sockets. Two
things connect iff the plug's `socket_type` matches an open socket's `type`.

| socket type | on | accepts |
|---|---|---|
| `wheel_mount` | chassis ×4 (FL/FR/RL/RR) | wheels; wheel-weapons (spinning spikes) |
| `engine_mount` | chassis | engines / powerplants |
| `nose_mount` | chassis (front) | nose parts (grille, ram); **Front** weapons |
| `cockpit_mount` | chassis | seats (which expose `steering_mount`) |
| `roof_mount` | chassis / cockpit | roofs, canopies, roll-cages; **Top** weapons |
| `rear_mount` | chassis (rear) | tails, spoilers; **Rear** weapons |
| `side_mount` | chassis ×2 (L/R) | side panels; **Side** weapons |
| `steering_mount` | seat | steering wheel / tiller |
| `decor_mount` | many parts | decals, numbers, lights, mascot ornaments |

**Weapon mounts reuse the structural sockets** (per weapons PRD: Front→`nose_mount`,
Rear→`rear_mount`, Side→`side_mount`, Top→`roof_mount`, Wheels→`wheel_mount`). One socket
system, two uses. A socket may host EITHER a structural part or a weapon (or a structural
part that itself exposes a weapon sub-mount, e.g. a roof-rack roof exposing a `roof_mount`
for the Tesla coil).

### 4.2 Per-part metadata schema (`<part_id>.meta.json` sidecar)

```json
{
  "id": "wheel_fat_slick",
  "category": "wheel",
  "display_name": "Fat Slick Wheel",
  "plug": {
    "socket_type": "wheel_mount",
    "pivot": [0, 0, 0],            // local origin = the attach point (axle center)
    "up": [0, 1, 0],
    "forward": [0, 0, 1],
    "mirror_x_ok": true           // same mesh serves left & right (mirror in X)
  },
  "sockets": [],                  // secondary sockets THIS part exposes
  "theme": "universal",           // "universal" | character id
  "signature_color": null,        // hex, or null if universal
  "scale_unit": "kart",           // normalized to the kart bounding unit
  "bbox": [0.42, 0.42, 0.18],     // metres, for scale checks
  "source_2d": "wheel_fat_slick__front.png",
  "gen": {"lora": "gritty_comic", "strength": 1.0, "seed": 0}
}
```

The **chassis** is the root host and exposes the primary sockets:

```json
{
  "id": "chassis_rail",
  "category": "chassis",
  "plug": {"socket_type": "root", "pivot": [0,0,0]},
  "sockets": [
    {"name":"WheelFL","type":"wheel_mount","pos":[-0.55,0.0, 0.75],"rot":[0,0,0]},
    {"name":"WheelFR","type":"wheel_mount","pos":[ 0.55,0.0, 0.75],"rot":[0,180,0]},
    {"name":"WheelRL","type":"wheel_mount","pos":[-0.55,0.0,-0.75],"rot":[0,0,0]},
    {"name":"WheelRR","type":"wheel_mount","pos":[ 0.55,0.0,-0.75],"rot":[0,180,0]},
    {"name":"EngineBay","type":"engine_mount","pos":[0,0.25,-0.65]},
    {"name":"Nose","type":"nose_mount","pos":[0,0.2,1.05]},
    {"name":"Cockpit","type":"cockpit_mount","pos":[0,0.3,0.0]},
    {"name":"Roof","type":"roof_mount","pos":[0,0.85,0.0]},
    {"name":"RearTail","type":"rear_mount","pos":[0,0.3,-1.05]},
    {"name":"SideL","type":"side_mount","pos":[-0.62,0.3,0.0],"rot":[0,0,0]},
    {"name":"SideR","type":"side_mount","pos":[ 0.62,0.3,0.0],"rot":[0,180,0]}
  ]
}
```

**Assembly = snap:** parent the part's `plug.pivot` to the socket transform (local
position = socket `pos`, rotation = socket `rot`). Because each part's origin sits AT its
attach point, snapping is a parenting op with zero offset. A `kit.json` manifest lists all
parts + sockets so a loader/tool builds the compatibility graph automatically.

### 4.3 Orientation & scale conventions

- **Axes:** +Y up, +Z forward, +X right. **Kart faces +Z.** ⚠️ *Confirm against
  soapbox-unity's kart-forward convention before 3D export — project memory
  `feedback_kart_assembly` notes a kart used +Y forward; the exporter must match the
  game.*
- **Scale unit:** the chassis bbox defines 1 "kart". All parts normalized so a wheel,
  engine, etc. are correctly proportioned. image-to-3D output is auto-scaled to fit its
  socket's expected bbox (from the schema).
- **Mirroring:** L/R-symmetric parts (most wheels, side panels) ship ONE mesh + a
  `mirror_x_ok` flag; the other side is an X-mirror instance. Halves the part count where
  it applies.

## 5. Part taxonomy (proposed — editable)

### 5.1 Structural parts (~40)

| Category | socket | Proposed parts | count |
|---|---|---|---|
| **Chassis** | root | rail (hot-rod), tub (bathtub), crate (wooden), plank (barebones) | 4 |
| **Wheels** | wheel_mount | fat_slick, knobby_offroad, spoked_vintage, solid_disc, mag, wooden_wagon, monster, caster | 8 |
| **Engines** | engine_mount | v8_exposed, rocket_jet, electric_coils, steam_boiler, propeller, pedal_none | 6 |
| **Noses** | nose_mount | radiator_grille, bumper_ram, pointed, plow, headlight_rig | 5 |
| **Roofs** | roof_mount | open_none, roll_cage, hardtop, bubble_canopy, umbrella, roof_rack* | 6 |
| **Side panels** | side_mount | number_panel, door, armor_plate, sponsor_board, exhaust_pipes | 5 |
| **Tails** | rear_mount | spoiler, exhaust_stacks, tail_fin, cargo_rack | 4 |
| **Seats** | cockpit_mount | bucket, bench, throne (punk_king) | 3 |
| **Steering** | steering_mount | wheel, tiller | 2 |

\* `roof_rack` exposes a secondary `roof_mount` so a Top weapon can mount above it.

### 5.2 Weapons (12, from the PRD) — each a mountable part

Weapons attach to the shared sockets. All rendered in `gritty_comic` junkyard-scrap style
for a coherent kit. The PRD splits them procedural-vs-generated; **for style consistency
this kit generates 2D concepts for all 12**, then image-to-3D's the 6 complex ones and
lets the 6 simple ones be either generated meshes OR Unity primitives (game's choice).

| # | Weapon | socket | 3D via |
|---|---|---|---|
| 1 | Spinning Wheel Spikes | wheel_mount | primitive or gen |
| 2 | Chainsaw Arm | side_mount | **image-to-3D** |
| 3 | Battering Ram | nose_mount | primitive or gen |
| 4 | Wrecking Ball | rear_mount | **image-to-3D** |
| 5 | Flamethrower | nose_mount | **image-to-3D** |
| 6 | Thunderstick Launcher | roof_mount | **image-to-3D** |
| 7 | Nail Gun | nose_mount | primitive or gen |
| 8 | Junk Catapult | rear_mount | **image-to-3D** |
| 9 | Smoke Screen | rear_mount | primitive or gen |
| 10 | Oil Slick Sprayer | rear_mount | primitive or gen |
| 11 | Tesla Coil | roof_mount | primitive or gen |
| 12 | Molotov Cocktail | side_mount | **image-to-3D** |

Weapon metadata adds gameplay fields carried through from the PRD:
`{"deploy":"slide|swing|telescope|flip","active_s":5,"cooldown_s":30,"damage":..,
"category":"contact|ranged|area"}` — so the kit's metadata drives the existing
`WeaponMountPoints.cs` / `TrickManager.cs` directly.

**Kit total ≈ 40 structural + 12 weapons ≈ 52 parts** (before per-character accent
variants), comparable to the 44-piece GrimForge parts kit.

## 6. Consistency protocol (so parts actually assemble)

For clean per-part image-to-3D + assembly, every isolated-part concept is generated to a
fixed protocol:
- **One part, centered, on a plain white background**, no scene (name-the-white per the
  `name-what-you-want` lesson — no bg-negatives).
- **Fixed 3/4 hero camera**, consistent lighting, part's mount-face toward a known
  direction so the 3D pivot is predictable.
- **Consistent implied scale** — prompt an in-frame scale cue where useful; final mesh
  auto-scaled to the schema bbox.
- **TRELLIS.2 SINGLE-view** image-to-3D (per `project_trellis...` lessons — multiview
  corrupts), then weld/heal (`mesh_to_solid.py`), set pivot at the mount point, export.

## 7. Pipeline & phases

Mirrors the occult bootstrap + the low-poly/photo-to-3d 3D pipeline. Working dir:
`E:/ai-training/flux-output/soapbox_kart_parts/` (corpus + LoRA on E:); deliverable +
metadata + catalog here in `products/soapbox_kart_parts_v1/`.

- **P0 — Pilot (cheap validation):** does `gritty_comic` render kart parts (objects, not
  characters) in-style? Generate a handful — whole kart + isolated wheel/engine/seat —
  with `gritty_comic` and a base-Flux+style-prompt comparison. If `gritty_comic` imposes
  character-ness, adjust the bootstrap (img2img from old sprites / base + style prompt).
  **Gate: on-style isolated parts before scaling.**
- **P1 — Bootstrap corpus:** generate ~120–180 in-style images — whole karts (per
  character theme) + isolated parts across every category + the 12 weapons — curate to a
  clean set. Captions match pixels, trigger `soapbox_kart`.
- **P2 — Train the kart LoRA:** rank 32, [512,768], FLUX.1-dev. **Apply the soapbox VRAM
  lesson: disable in-training sampling (or 512-only) — tall/detailed images spilled at
  rank-32 otherwise.** Eval grid, pick checkpoint, deploy `soapbox_kart` LoRA.
- **P3 — Generate the final part set:** with the kart LoRA, render every part to the §6
  protocol (isolated) + whole-kart hero shots.
- **P4 — image-to-3D + kit:** TRELLIS per part → weld/clean → normalize scale → set pivot
  → write `.meta.json` per part + `kit.json` manifest → export GLB/OBJ/FBX → catalog +
  hero → quality gate (`kit_quality_check.py`).
- **P5 — Unity integration:** drop parts + metadata into `soapbox-unity`; sockets map to
  `WeaponMountPoints.cs`; verify a swap and a weapon mount in-engine.

**This session (automode):** execute P0 → P1 → P2 (the LoRA), checkpointing with montages
for review, exactly as occult/soapbox went. P3–P5 (the 3D kit) is the follow-up, since it
depends on the trained LoRA.

## 8. Deliverable structure (mirrors parts_kit_grimforge + metadata)

```
products/soapbox_kart_parts_v1/
  SPEC.md                       (this)
  kit.json                      (manifest: all parts + sockets + compatibility)
  <part_id>.meta.json           (per-part attachment + gameplay metadata)
  models_glb/ models_obj/ models_fbx/ models_gltf/
  atlas_color.png  atlas_emit.png
  concepts/                     (the 2D gritty_comic part renders)
  catalog.png  hero.png  README.md  LISTING.md
```

## 9. Lessons applied (this session's hard-won ones)

- **Bootstrap a corpus** from an existing LoRA + refs (occult method) — no dataset exists.
- **Name what you want; don't negate** — white background named, blacks/values named,
  ONE accent colour per part; no colour/bg negatives.
- **VRAM:** rank 32 fits, but disable in-training sampling for tall/detailed sets (soapbox
  spilled at ~step 1500 otherwise). Verify SUSTAINED s/it past step ~150.
- **TRELLIS is single-view**; weld unwelded meshes before smoothing.
- **Captions match pixels**; a fast training start ≠ it fits.
- **Verify from the raw source, not a derived metric** (a watcher misreported 60 s/it).

## 10. Open decisions / assumptions (flagging, not blocking)

1. **Kart-forward axis** — spec assumes +Z; confirm vs soapbox-unity before 3D export.
2. **Per-character accent variants** — kit ships universal parts + accent metadata (tint
   at runtime), NOT 8× duplicated meshes, unless you want per-character hero karts baked.
3. **Simple weapons** — generate meshes for all 12, or keep the PRD's 6 as Unity
   primitives? Spec generates concepts for all 12; 3D-models the 6 complex ones.
4. **Trigger word** — `soapbox_kart` (proposed) for the new LoRA.
5. **Part counts** — §5 numbers are a proposed target; trivially tunable.
