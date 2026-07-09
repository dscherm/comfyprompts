---
name: equip-character-assets
description: Attach a weapon, shield, tool, or other prop to an already-rigged character in Godot so it follows a hand/bone through every animation. Uses BoneAttachment3D + a screenshot-tuned grip transform. Use when the user wants a rigged character (from the character-pipeline / bestiary / AccuRIG route) to hold or wear a kit asset (arsenal_kit weapons, lanterns, etc.). Proven on the GrimForge knight sword, 2026-07-09.
---

# Equip Character Assets (weapons / props on rigged characters)

Attaches a kit asset (GLB) to a bone of an already-rigged, animated character
so it tracks that bone through idle/walk/run/attack. The asset rides a
`BoneAttachment3D` parented under the character's `Skeleton3D`; a small
grip transform (position/rotation/scale, in bone-local space) seats it in the
hand. Grip values are found by fast screenshot iteration, not guessed.

**Reference implementation**: `products/grimforge_playable_demo_v1/scripts/player.gd`
(`_attach_weapon`, `_apply_weapon_overrides`) + `scripts/diag_weapon.gd`.
Assets: `products/arsenal_kit_grimforge_v1/models_glb/` (sword, axe, mace,
shield-less — 24 weapons/props). Rig bone names are AccuRIG `CC_Base_*`.

## When to use

- The character is already rigged (has a `Skeleton3D`) and animating in Godot.
- You want it to HOLD (hand bone) or WEAR (spine/head/back bone) a mesh asset.
- Not for: rigging the character itself (see `character-pipeline`), or baking
  new clips (see the `_tools/bake_*_locomotion.cs` Unity bake scripts).

## Prerequisites

- Rigged character scene in the Godot project (e.g. a Unity-baked `_anim.fbx`
  or `_idle.fbx`, native ufbx import — see memory
  `project_ccbase_retarget_scramble`).
- The asset as a self-contained GLB copied into the project (arsenal_kit GLBs
  embed their own textures, so they render correctly with no atlas wiring).
- The Godot windowed-run harness for screenshots (memory
  `project_godot_windowed_run_harness`): CLI flags after `--`, PowerShell
  `Start-Process` on the `_console.exe` with `-RedirectStandardOutput`.

## Step 1 — Find the target bone + asset dimensions

Run a diagnostic (copy `scripts/diag_weapon.gd`) headless:
```
godot --headless --path <project> --script res://scripts/diag_weapon.gd
```
It prints the character's bone list (grep hand/spine/head) and the asset's
AABB. AccuRIG hands are `CC_Base_R_Hand` / `CC_Base_L_Hand`. Note the asset's
native size vs the character's native rig height — an asset already
proportional to the rig needs `scale ≈ 1.0` (it inherits the rig's display
scale because the BoneAttachment lives under the scaled rig).

## Step 2 — Attach via BoneAttachment3D

In the character controller's rig-build step, after the skeleton exists:
```gdscript
var skel := <find Skeleton3D under rig>
if skel.find_bone(BONE) < 0: return   # guard
var ba := BoneAttachment3D.new()
ba.bone_name = BONE                    # e.g. "CC_Base_R_Hand"
skel.add_child(ba)
var asset := load("res://weapons/<asset>.glb").instantiate()
ba.add_child(asset)
asset.position = _grip_pos             # bone-local offset
asset.rotation_degrees = _grip_rot
asset.scale = Vector3.ONE * _grip_scale
```
Make the three grip values **CLI-overridable** (`--wpos=x,y,z --wrot=x,y,z
--wscale=s`) so you can tune without recompiling — this is what makes step 3
fast.

## Step 3 — Tune the grip by screenshot iteration

The bone's local axes are not obvious (AccuRIG hand-Y is roughly vertical), so
find the transform empirically. Capture a close-up (`--camsize=2.0`,
`--shot=grip.png:1.2`, `--quit-after=2.5`) for a few candidates in one batch:
```
foreach rot in (0,0,0) (0,0,180) (25,0,0) ...:
  Start-Process <godot_console> --path <proj> -- --wrot=$rot --camsize=2.0 --shot=grip_$tag.png:1.2 --quit-after=2.5
```
Read the PNGs, pick the natural one, refine (2-3 rounds). **Proven knight
sword grip**: `pos=(0,0.06,0) rot=(25,0,0) scale=0.8` — blade lowered and
angled forward, tip clear of the ground. Bake the winner as the default in
the controller.

**Look for**: grip seated in the fist (not floating/behind), blade/tool
pointing a natural direction, and the tip CLEARING THE GROUND (a point-down
blade at full length clips the floor while walking — angle it forward or scale
down ~0.8).

## Step 4 — Verify it tracks the bone through animation

Drive the character through each clip and screenshot mid-cycle (two frames
apart) to confirm the asset follows the hand (arm swing moves the sword):
```
Start-Process <godot_console> --path <proj> -- --drive=up:6 --camsize=2.4 \
  --shot=a.png:1.5 --shot=a2.png:2.4 --quit-after=4         # walk
Start-Process <godot_console> --path <proj> -- --run --drive=up:6 ...        # run
```
Both frames must show the asset in the hand at different arm positions. Done.

## Gotchas

- **Scale inheritance**: the BoneAttachment is under the rig, which is display-
  scaled (e.g. 0.486 for the miniature knight). Set `scale` in *native rig
  units* — the rig scale is applied on top. An asset already sized to the
  native rig uses `scale ≈ 1.0`.
- **Textures**: arsenal_kit GLBs are self-contained — load directly, no atlas
  override (unlike the castle kit env pieces which need the fixed atlas).
- **Which hand**: AccuRIG `.l`/`.r` labels can be anatomically swapped on
  -Y-facing TRELLIS/UniRig rigs (memory `project_unirig_mirrored_side_labels`)
  — verify visually, don't trust the label.
- **Multiple items**: repeat for shield on `CC_Base_L_Hand`, quiver/cape on a
  spine bone, helm on `CC_Base_Head`. Same pattern, different bone + grip.
```
