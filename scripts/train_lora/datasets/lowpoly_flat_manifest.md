# lowpoly_flat dataset manifest

Built 2026-07-17, swords added 2026-07-18 (SL8). **96 renders** = 32 subjects x 3 views. Kits: arsenal 10, generated 3, soapbox 6, village 13.

## Origin

Owned grimforge/soapbox game assets (IP-clean) + 3 GENERATED swords (SL8). Rendered
flat-shaded (per-face normals), even 3-light rig, neutral grey bg, orthographic, EEVEE
via blender-mcp (3070). Tooling: `build_lowpoly_flat_dataset.py` + `render_multiview.py --flat`.
Captions filename-derived: `lowpoly_flat, <subject>, low-poly, flat shading, <view>,
neutral background, even lighting`.

## Camera angles

- Most subjects: front + two three-quarter.
- Anvil + blade weapons (anvil, arming_sword, battleaxe, dagger, halberd, saber, scythe, spear): elevated 3/4 HERO angles.

## Generated swords (SL8, 2026-07-18)

`arming sword`, `saber`, `dagger` — GENERATED to replace the arsenal sword/greatsword
(whose shared blade mesh had a baked dark-fuller stripe reading as a split blade). Pipeline:
Flux1-dev-fp8 concept -> TRELLIS.2 image-to-3D -> weld+decimate (~3-9k faces) -> steel blade
+ brown grip. Scripts: sl8_gen_sword_concepts.py, sl8_lowpoly_sword.py, sl8_color_sword.py.
A broadsword was also generated but DROPPED (its geometry defeated the grip auto-colour;
blade was clean).

## Subjects by kit

- **arsenal** (10): battleaxe, halberd, lantern, potion bottle, scythe, spear, spellbook, treasure chest, warhammer, wizard staff
- **generated** (3): arming sword, dagger, saber
- **soapbox** (6): barrel, crate, frog, kart racer, robot, skeleton
- **village** (13): anvil, crypt, fountain, guard tower, pine tree, rocks, ruined house, stone bridge, torch, tree stump, weapon rack, windmill, wood pile

## Per-subject provenance

| subject | kit | source mesh | license |
|---|---|---|---|
| battleaxe | arsenal | products/arsenal_kit_grimforge_v1/models_glb/battleaxe.glb | owned (generated IP) |
| halberd | arsenal | products/arsenal_kit_grimforge_v1/models_glb/halberd.glb | owned (generated IP) |
| lantern | arsenal | products/arsenal_kit_grimforge_v1/models_glb/lantern.glb | owned (generated IP) |
| potion bottle | arsenal | products/arsenal_kit_grimforge_v1/models_glb/potion_red.glb | owned (generated IP) |
| scythe | arsenal | products/arsenal_kit_grimforge_v1/models_glb/scythe.glb | owned (generated IP) |
| spear | arsenal | products/arsenal_kit_grimforge_v1/models_glb/spear.glb | owned (generated IP) |
| spellbook | arsenal | products/arsenal_kit_grimforge_v1/models_glb/spellbook.glb | owned (generated IP) |
| treasure chest | arsenal | products/arsenal_kit_grimforge_v1/models_glb/chest.glb | owned (generated IP) |
| warhammer | arsenal | products/arsenal_kit_grimforge_v1/models_glb/warhammer.glb | owned (generated IP) |
| wizard staff | arsenal | products/arsenal_kit_grimforge_v1/models_glb/wizard_staff.glb | owned (generated IP) |
| arming sword | generated | E:/ai-training/_raw/lowpoly_flat_swords/meshes_colored/arming_sword.glb (Flux concept -> TRELLIS.2 -> weld/decimate/color) | generated (SL8, our own pipeline) |
| dagger | generated | E:/ai-training/_raw/lowpoly_flat_swords/meshes_colored/dagger.glb (Flux concept -> TRELLIS.2 -> weld/decimate/color) | generated (SL8, our own pipeline) |
| saber | generated | E:/ai-training/_raw/lowpoly_flat_swords/meshes_colored/saber.glb (Flux concept -> TRELLIS.2 -> weld/decimate/color) | generated (SL8, our own pipeline) |
| barrel | soapbox | products/soapbox_kart_kit_v1/models_glb/barrel.glb | owned (generated IP) |
| crate | soapbox | products/soapbox_kart_kit_v1/models_glb/crate.glb | owned (generated IP) |
| frog | soapbox | products/soapbox_kart_kit_v1/mascots/frog.glb | owned (generated IP) |
| kart racer | soapbox | products/soapbox_kart_kit_v1/models_glb/kart_racer.glb | owned (generated IP) |
| robot | soapbox | products/soapbox_kart_kit_v1/mascots/robot.glb | owned (generated IP) |
| skeleton | soapbox | products/soapbox_kart_kit_v1/mascots/skeleton.glb | owned (generated IP) |
| anvil | village | products/village_kit_grimforge_v2/examples/godot_village/models/anvil.glb | owned (generated IP) |
| crypt | village | products/village_kit_grimforge_v2/examples/godot_village/models/crypt.glb | owned (generated IP) |
| fountain | village | products/village_kit_grimforge_v2/examples/godot_village/models/fountain.glb | owned (generated IP) |
| guard tower | village | products/village_kit_grimforge_v2/examples/godot_village/models/guard_tower.glb | owned (generated IP) |
| pine tree | village | products/village_kit_grimforge_v2/examples/godot_village/models/pine.glb | owned (generated IP) |
| rocks | village | products/village_kit_grimforge_v2/examples/godot_village/models/rocks.glb | owned (generated IP) |
| ruined house | village | products/village_kit_grimforge_v2/examples/godot_village/models/ruined_house.glb | owned (generated IP) |
| stone bridge | village | products/village_kit_grimforge_v2/examples/godot_village/models/stone_bridge.glb | owned (generated IP) |
| torch | village | products/village_kit_grimforge_v2/examples/godot_village/models/torch.glb | owned (generated IP) |
| tree stump | village | products/village_kit_grimforge_v2/examples/godot_village/models/stump.glb | owned (generated IP) |
| weapon rack | village | products/village_kit_grimforge_v2/examples/godot_village/models/weapon_rack.glb | owned (generated IP) |
| windmill | village | products/village_kit_grimforge_v2/examples/godot_village/models/windmill.glb | owned (generated IP) |
| wood pile | village | products/village_kit_grimforge_v2/examples/godot_village/models/wood_pile.glb | owned (generated IP) |

## Notes

- **Bestiary creatures excluded** (`_lp` untextured = white; `_tex` = off-aesthetic).

- **CC0 augmentation** optional/future (owned + generated only, no external meshes).

- **Dual use (SL7):** sellable LoRA + cleaner silhouette source for image->3D.

- Trigger `lowpoly_flat`; Flux LoRA (SL6, deferred — training).
