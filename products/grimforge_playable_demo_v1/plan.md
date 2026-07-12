# GrimForge Playable Demo — plan.md

Track-B game-building tasks for ralph-universal interactive bridge mode. Each
task is verified by the headless gate (`tests/test_gameplay_gate.py`), which
drives the Godot build via its CLI harness and asserts on the structured stdout
event log. Acceptance = a new/updated pytest assertion goes green **and** the
existing regression tests (3 worlds boot clean, courtyard combat) stay green.

See the wiki pattern set (`$RALPH_HOME/wiki/`):
`code-first-testable-godot-is-ai-friendly` and its five linked pages.

```json
{
  "id": "G1",
  "category": "feature",
  "priority": "HIGH",
  "description": "Navigation: enemies path AROUND buildings instead of sliding straight into colliders. Add a NavigationRegion3D per world (baked from the env/interior/town collider geometry) and give npc.gd a NavigationAgent3D so _combat_step chases along a computed path. Straight-line chase (current) gets stuck on the keep, walls, and houses.",
  "steps": [
    "Add a NavigationRegion3D to each world builder (env.gd/interior.gd/town.gd); bake a nav mesh over the walkable floor, carving out building/wall colliders",
    "Give npc.gd a NavigationAgent3D; in _combat_step, set target_position to the player and move along agent.get_next_path_position() instead of the raw direction",
    "Keep wander (_pick_waypoint) on the nav mesh too, so idle NPCs don't clip geometry",
    "Verify via harness: drive the knight behind the keep; enemies still reach and hit him (PLAYER_HURT fires) rather than piling on the wall",
    "Add tests/test_gameplay_gate.py::test_enemies_navigate_around_building asserting PLAYER_HURT after the knight is driven to a spot with a building between him and a spawn"
  ],
  "passes": true
}
```

```json
{
  "id": "G2",
  "category": "refactor",
  "priority": "HIGH",
  "description": "Data-driven enemies: move the hardcoded ENEMY_HP / ENEMY_DMG dicts (npc.gd) and the POP roster rows (bestiary.gd) into custom Resource (.tres) files loaded at runtime. This is the hardcoded->data-driven maturity step and the one that makes new enemy content agent-generatable (a new enemy = a new .tres, no code edit).",
  "steps": [
    "Define an EnemyDef Resource script (class_name EnemyDef) with fields: name, kind, target_h, hp, dmg, home, world, hostile",
    "Author one .tres per creature under a data/enemies/ folder; port the current HP/DMG/home values verbatim",
    "Rewrite bestiary.gd to load the .tres set and spawn per world from the resource data; npc.gd reads hp/dmg from the injected def instead of the const dicts",
    "Verify via harness: all three worlds spawn the same rosters and the same combat markers (PLAYER_HURT damage values unchanged) — a pure refactor, behavior identical",
    "Add tests/test_gameplay_gate.py::test_enemy_stats_from_resources asserting a known creature's damage value still appears (e.g. ghoul -12, dire_rat -6)"
  ],
  "passes": true
}
```

```json
{
  "id": "G3",
  "category": "feature",
  "priority": "MEDIUM",
  "description": "AnimationTree + root motion for the player: replace the manual _ap.play() calls and WALK_ANIM_SPEED=2.0 foot-skate hand-tuning with an AnimationTree state machine driving root motion, so ground speed comes from the clip and feet track the floor. Fixes the skating the demo currently fights.",
  "steps": [
    "Build an AnimationTree with an AnimationNodeStateMachine (idle/walk/run) over the merged clips; enable root motion (set root_motion_track to the hip/root bone)",
    "Drive movement from get_root_motion_position() * scale instead of a fixed velocity; keep camera-relative input mapping",
    "Re-measure ground speed with the measure_walk.gd approach; confirm feet no longer skate at the walk/run transition",
    "Verify via harness: --drive still moves the knight, locomotion animates, no SCRIPT ERROR",
    "Add tests/test_gameplay_gate.py::test_player_locomotion_root_motion asserting PLAYER_POS advances under --drive and no error tokens"
  ],
  "passes": true,
  "note": "AnimationTree state machine shipped + gate-green + visually confirmed. Root motion found NOT viable: the revenant_knight walk/run clips were baked in-place (hip net horizontal travel ~0.02u; run hip identical first=last), so get_root_motion_position() is ~zero. Foot-skate remains speed-matched (WALK_ANIM_SPEED). The skate fix requires re-baked clips with root translation — spun out to G6."
}
```

```json
{
  "id": "G4",
  "category": "feature",
  "priority": "MEDIUM",
  "description": "Persistent player HP across world transitions via an autoload singleton (GameState). Currently main.gd frees + respawns the player each transition, resetting HP to 100 (each world is a free heal). Persist hp (and death state) so a fight carries across the courtyard/keep/town boundaries.",
  "steps": [
    "Add an autoload singleton (GameState.gd) holding player hp / max_hp / dead",
    "player.gd reads its starting hp from GameState on _ready and writes back on damage/death; main.gd no longer implies a full heal on rebuild",
    "Decide + implement the heal policy (e.g. no heal on travel, or a small heal) and document it in the README",
    "Verify via harness: drive courtyard (take damage) -> town; assert the carried hp is < 100 on arrival",
    "Add tests/test_gameplay_gate.py::test_hp_persists_across_worlds"
  ],
  "passes": true
}
```

```json
{
  "id": "G5",
  "category": "feature",
  "priority": "LOW",
  "description": "Ranged caster projectiles: give the necromancer / skeleton_mage / lich_king an actual spell attack instead of the melee lunge. Spawn an Area3D projectile that travels to the player and deals damage on contact, so the keep fight has ranged pressure. Teaches runtime instancing + Area3D projectile lifetimes.",
  "steps": [
    "Add a projectile scene/script (Area3D + mesh + travel + lifetime) spawned from a caster's hand toward the player's position at cast time",
    "In npc.gd, route casters (a 'ranged' flag on the enemy def from G2) to a _cast_projectile attack path instead of _start_swipe",
    "Tune damage/speed/cooldown so ranged chip damage is fair vs melee",
    "Verify via harness: in the keep, the knight takes damage from beyond melee range (PLAYER_HURT while dist-to-nearest-caster > ATTACK_RANGE)",
    "Add tests/test_gameplay_gate.py::test_caster_ranged_damage"
  ],
  "passes": true
}
```

```json
{
  "id": "G6",
  "category": "feature",
  "priority": "LOW",
  "description": "Fix the player foot-skate at the source: re-bake the revenant_knight walk/run locomotion clips WITH root translation (currently baked in-place, so G3's AnimationTree could not use root motion). This is an asset-pipeline task (Unity re-bake of the ActorCore walk/run onto the AccuRIG knight with root motion enabled, re-export FBX), not a code task. Once the clips carry hip travel, wire the AnimationTree root_motion_track and drive velocity from get_root_motion_position(), removing WALK_ANIM_SPEED. BLOCKED pending a user decision to spend the re-bake — the demo currently looks fine speed-matched.",
  "steps": [
    "Decision gate: confirm the re-bake is worth it vs. the current speed-matched look",
    "Re-bake walk + run onto the knight rig with root motion (Unity, _tools/bake_*_locomotion.cs) and re-export the FBX",
    "Set the AnimationTree root_motion_track to the hip; drive velocity from get_root_motion_position() * rig_scale; remove WALK_ANIM_SPEED",
    "Verify feet track the ground via measure_walk.gd; gate stays green"
  ],
  "passes": false,
  "resolution": "SKIPPED — not viable with available assets (investigated 2026-07-11 via scripts/diag_rootsrc.gd on the D:/Projects/Animations sources). walk_relaxed_loop is CC_Base (70/71 bones match the knight) but authored IN PLACE (root net travel ~0.001) — no forward translation to extract, so root motion cannot fix the walk skate regardless of tool. run_forward carries real root motion (hips travel 3.13u) but is a Mixamo rig (0 bones shared) needing a Unity Humanoid retarget, and would only fix run, not the walk. Decision: keep the speed-matched walk (correct handling for an in-place loop). Revisit only if a forward-translating, knight-compatible (CC_Base) walk clip is sourced."
}
```

```json
{
  "id": "G7",
  "category": "feature",
  "priority": "HIGH",
  "description": "Add a 4th world — a CURSED/OCCULT village — assembled from village_kit_grimforge_darkfantasy_v1 buildings (occult palette + emit atlas) dressed with village_kit_grimforge_occult_v1 ritual props (altars, summoning_circle, standing_stones, crypt_entrance, cauldrons, graves, hanged/dead trees). Must look intentional and natural per QUALITY_RUBRIC.md (§4b house-assembly, §4a roof rules) — NOT boxy stone blocks like the current town. Wired into main.gd's router (reached from the town; --occult start flag for testing) and populated with a hostile bestiary (occult roster: cultists/necromancers/skeleton_mage).",
  "steps": [
    "Copy the darkfantasy building GLBs + occult prop GLBs + both kits' atlases into products/grimforge_playable_demo_v1/occult/ (self-contained per kit); apply the two kit-render fixes from town.gd/env.gd (flat normals, atlas) only if tiling shows stripes/pillow-shading (verify with --flat)",
    "Write scripts/occult_town.gd (kit-scene-layout skill): grid-aligned darkfantasy houses with doors facing the paths (GrimForge convention door=+Z at yaw 0 — re-verify with a door inspector), a road/path spine, a central ritual plaza (summoning_circle + ritual_altar ringed by standing_stones), desecrated chapel as focal point, crypt + graveyard, witchlight braziers; box colliders on buildings",
    "main.gd: add the 'occult_town' world (build + a return trigger to town), a second exit from the 'town' world into occult_town, a --occult start flag mirroring --interior/--town, and a default spawn",
    "bestiary.gd + data/enemies: add an occult_town population (new EnemyDef .tres with world='occult_town' — an occult roster of cultists/necromancer/skeleton_mage/ghoul), spawned hostile like the other worlds",
    "gate: +test_occult_town_populated (--occult boots clean, no SCRIPT ERROR, occult roster present) and confirm the 4 existing worlds still pass",
    "Visual: capture isometric overview + top-down screenshots; iterate until it reads as an intentional cursed settlement that passes the rubric's house-assembly criteria (no floating parts, roofs cover, doors grounded, no daylight gaps)"
  ],
  "passes": true
}
```

```json
{
  "id": "G8",
  "category": "feature",
  "priority": "MEDIUM",
  "description": "Fix the town's cold 'grey stone blocks' read. Root cause (confirmed by close screenshots + kit comparison): the v1 village buildings are real houses (stone ground floor + timber upper + tiled roof) but the GLOBAL dim dusk lighting (sun energy 1.2, pitch -48, ambient 0.7) washes the whole village cold and grey. No cleaner village kit exists (v2 is walls, darkfantasy is now the occult town). Fix = per-world lighting/mood in main.gd instead of one global light: town = bright warm village day; occult_town = dark cursed (keep ~current, it uses emit glow); keep = dim torchlit; courtyard = neutral daylight.",
  "steps": [
    "Refactor main.gd _setup_lighting: store sun + WorldEnvironment refs, add _apply_world_lighting(world) with a per-world profile (sun energy/pitch/color, ambient energy, sky colors)",
    "Call _apply_world_lighting(world) from _build_world so each world sets its own mood",
    "Town profile: brighter warmer sun (higher energy, higher pitch for shorter shadows, slightly warm color), brighter ambient + bluer sky so the houses read as a warm living village, not grey dusk",
    "Occult profile: keep the dark cursed look the emit atlases carry (don't wash it out); keep interior dim/torchlit; courtyard neutral",
    "Verify: before/after town screenshots (reads warm/alive) + occult unchanged; gate stays green (all worlds boot clean)"
  ],
  "passes": true,
  "note": "Two-part fix. (1) Per-world lighting in main.gd (_LIGHT_PROFILES + _apply_world_lighting): town = bright warm village day, occult = dark cursed, keep = dim, courtyard = neutral. (2) Wooden buildings (user direction): the walls sample atlas cell (0,7) grey-stone (found via scripts/diag_walluv geometry-UV histogram); atlas_color_wood.png repaints that swatch with the kit's brown timber; town.gd applies it to WOOD_BUILDINGS (cottage/house_small/house_tall/tavern/blacksmith) — the church keeps stone. Roofs untouched."
}
```

```json
{
  "id": "G9",
  "category": "fix",
  "priority": "MEDIUM",
  "description": "Improve the walk/run animations. Measured (scripts/measure_loco.gd) the in-place clips' natural ground speed at 1.0x: walk 0.178 m/s, run 1.454 m/s. The old constants were mismatched — walk (WALK_SPEED 0.6, 2.0x -> foot-plant 0.356) SKATED (body faster than feet); run (RUN_SPEED 1.4, 1.5x -> foot-plant 2.18) MOONWALKED (feet faster than body). Fix = measured foot-plant match: WALK_SPEED 0.42 @ 2.36x, RUN_SPEED 1.4 @ 0.96x. Both now track the ground. NOTE the ceiling: in-place clips force a slower or busier-legged walk; a brisk walk with natural cadence needs root-motion clips (Unity retarget of the Mixamo walking.fbx/standard run.fbx) — offered as the follow-up.",
  "steps": [
    "measure_loco.gd: measure natural_1x foot-plant speed for walk + run",
    "player.gd: set WALK_SPEED/WALK_ANIM_SPEED and RUN_ANIM_SPEED so body_speed == natural_1x * playback (no skate/moonwalk)",
    "Gate stays green (locomotion still advances under --drive); user plays to judge feel",
    "If the in-place ceiling isn't enough: escalate to a Unity Humanoid retarget of the Mixamo forward clips -> true root motion (needs Unity open)"
  ],
  "passes": true
}
```
