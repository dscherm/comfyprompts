# lowpoly_flat dataset manifest

Built 2026-07-17 (SL5). **87 renders** = 29 subjects x 3 views. Kits: arsenal 10, soapbox 6, village 13.

## Origin — 100% OWNED, IP-clean

Every mesh is our OWN generated grimforge/soapbox game asset. Rendered flat-shaded
(per-face normals), even 3-light rig, neutral grey bg, orthographic, EEVEE via
blender-mcp (3070 GPU). Tooling: `build_lowpoly_flat_dataset.py` + `render_multiview.py --flat`.
Captions filename-derived (no Florence-2): `lowpoly_flat, <subject>, low-poly, flat shading,
<view>, neutral background, even lighting`.

## Camera angles

- Most subjects: front + two three-quarter (front_left/front_right).
- **Anvil + blade-family weapons** (anvil, battleaxe, halberd, scythe, spear): elevated 3/4 HERO angles — front shows them edge-on/end-on. (User feedback.)

## Subjects by kit

- **arsenal** (10): battleaxe, halberd, lantern, potion bottle, scythe, spear, spellbook, treasure chest, warhammer, wizard staff
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

- **sword + greatsword EXCLUDED:** they share one blade mesh with a baked dark-fuller
  stripe + spade tip that reads as a split/broken blade (confirmed NOT a render bug —
  flat and smooth shading are identical). Deferred: regenerate cleaner low-poly swords
  and swap them in (plan.md follow-up).

- **Bestiary creatures excluded** (`_lp` untextured = white; `_tex` = off-aesthetic).

- **CC0 augmentation** optional/future (owned-only v1).

- **Dual use (SL7):** sellable LoRA + cleaner-silhouette source for image->3D.

- Trigger `lowpoly_flat`; Flux LoRA (SL6, deferred).
