# GrimForge Playable Demo

A playable isometric castle-courtyard scene assembled entirely from GrimForge
kit assets: castle tiles/buildings from **castle_kit_grimforge_v1**, populated
with **grimforge_bestiary_v1** creatures, and a player-controlled
**revenant knight** with baked idle/walk animation.

![hero](hero.png)

## Run

```
godot --path products/grimforge_playable_demo_v1
```

(Godot 4.6+, native ufbx import — no Blender round-trip.)

## Controls

| Key | Action |
|---|---|
| Arrow keys | Move the knight (camera-relative, isometric) |

The knight plays its walk cycle while moving and returns to idle when you
stop. Buildings, walls, and props are solid.

## Scene contents

- **Environment** (`scripts/env.gd`): 14x14 measured-pitch tile grid (cobble
  court, flagstone cross, grass ring), perimeter walls + corner towers +
  gatehouse, keep, great hall, chapel, stable, market stall, well, props.
  Isometric orthographic camera (35 deg pitch / 45 deg yaw).
- **Bestiary** (`scripts/bestiary.gd`): 9 animated bipeds (Unity-baked clips,
  albedo re-applied) + 4 quadrupeds (UniRig + Blender walk cycles via
  runtime GLTFDocument load).
- **Player** (`scripts/player.gd`): CharacterBody3D; idle FBX rig with the
  walk clip merged at runtime from the twin walk FBX export.

## Asset provenance

- Castle pieces: `products/castle_kit_grimforge_v1/models_glb/` (copied into
  `kit/`). Two demo-side patches, kit untouched: `atlas_color_fixed.png`
  row-normalizes baked gradients in the floor swatches (they tile into
  stripes otherwise), and `env.gd` rebuilds meshes with per-face normals
  (kit GLBs ship smoothed normals that pillow-shade flat surfaces).
- Bestiary bipeds: `products/grimforge_bestiary_v1/_anim_viewer/chars/`
  (AccuRIG rigs, Unity Humanoid retarget, binary FBX, Godot native ufbx).
- Quadrupeds: `products/grimforge_bestiary_v1/_quad_viewer/quads/*_v2.glb`.
- Knight locomotion: idle = shared Mixamo set; walk = ActorCore
  `walk-relaxed-loop-378936` — both baked onto the AccuRIG knight rig in
  Unity (`_tools/bake_knight_locomotion.cs`) and exported as binary FBX.

## Verification harness

CLI flags after `--` for scripted checks: `--shot=name.png[:delay]`,
`--quit-after=S`, `--drive=S` / `--drive=up+left:S` (simulated input),
`--zoom=N`, `--topdown`, `--flat`, `--overview`, `--noshadow`.
`scripts/check_knight.gd` validates the knight FBX imports (clip names +
skeleton bbox scramble check).
