# Berserkr — extra animation clips (isolated working copy)

Built 2026-07-17. An **isolated copy** so `D:\Projects\berserkr-godot-v2` and the
canonical `products/berserkr_v2_chars_v1/` assets stay untouched.

## What this is

20 NEW Meshy library animation clips for the berserkr (on top of its existing
idle/walk/run/attack), merged with idle/walk/run into one engine GLB.

- **Method:** Meshy `POST /openapi/v1/animations` by `action_id` (`_work/meshy_animate.py`)
  against the existing rig task `019f70f9-1b2c-76d7-b138-c44054733b7c`, then
  `_work/merge_clips.py` (headless Blender, `export_animation_mode="ACTIONS"`).
  Cloud API — **no local GPU**. **60 credits** (3 × 20).
- **Deliverable:** `berserkr_anims.glb` — **23 clips**, one textured mesh + armature.

## Clips (23)

| category | clips |
|---|---|
| locomotion | walk, run, casual_walk, confident_walk, strut, hello_run, monster_walk |
| combat | sword_slash_r, sword_slash_l, sword_judgment, axe_chop_charged, combo_double, combo_triple, blade_spin |
| reactions | hit_reaction, behit_flyup, knock_down, death |
| idle / emotes | idle, idle_3, angry_stomp, victory_cheer, cheer |

action_id map (Meshy library): sword_slash_r=219, sword_slash_l=97, sword_judgment=102,
axe_chop_charged=237, combo_double=92, combo_triple=105, blade_spin=91, hit_reaction=178,
behit_flyup=7, knock_down=187, death=8, idle_3=243, angry_stomp=26, victory_cheer=59,
cheer=49, confident_walk=106, strut=107, hello_run=110, monster_walk=112, casual_walk=30.
(idle=0, walk/run bundled with the rig.)

## Verified

- `berserkr_anims.glb` holds 23 glTF animations (json-chunk check).
- Per-clip deformation eyeballed via `render_anim_poses.py` (blender-mcp, 3070) —
  `poses/*.png`: all clips deform cleanly, distinct poses, no scramble/melt. Mesh
  renders clay (colour is applied downstream in Godot, per the char pipeline).

## To use in the game (when ready)

Copy `berserkr_anims.glb` into `berserkr-godot-v2` and import
(`godot --headless --import`); load via the Model3DLoader (LOOP fixup + material +
whole-scene ink). Colour/toon-ink is the Godot Track B step, not baked here.
