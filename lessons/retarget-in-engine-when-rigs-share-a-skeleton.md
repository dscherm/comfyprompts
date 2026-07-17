---
title: An external retargeter's rejection is not a dead end when a working rig shares the skeleton
severity: medium
tags: [rigging, animation, godot, unity, accurig, retarget, pipeline]
source: hand-authored
created: 2026-07-17
project: comfyui-toolchain
---

## Symptom

An external tool refuses to produce an animation clip for a specific rig,
leaving that character stuck (no walk clip -> stationary idler, or no attack
clip -> inert enemy). Observed 2026-07-17: two bestiary mages (lich_king,
skeleton_mage) had no `<name>_walk.fbx` because Unity's Humanoid retarget
rejected their AccuRIG avatars (`isHuman=False`), and the documented Unity-side
fix (`ModelImporter.sourceAvatar` + `CopyFromOtherAvatar`) is a hard dead end on
Unity 6000.4 (`sourceAvatar` is `[Obsolete]`-as-ERROR, CS0619 — pragma cannot
suppress it). The instinct is to keep fighting the external tool (hand-map the
avatar in the UI, hunt the replacement API) or to ship the character broken.

## Root cause

The rejection is a limitation of the *external tool's* import path, not a fact
about the rig. If a DIFFERENT character that the tool DID accept shares the same
skeleton (same bone names, same rest hierarchy), then a clip authored for that
working rig is already valid animation data for the rejected one — the bone-local
rotations transfer directly. The clip does not have to be re-baked by the tool
that refuses this rig; it only has to be re-pathed onto this rig inside the engine
that will play it. The whole external round-trip was avoidable.

## Mitigation

1. **Before fighting the external retargeter, compare skeletons.** Dump bone
   names + the node path down to the skeleton for the rejected rig and for a
   working donor (a quick headless script — `scripts/diag_mage_rigs.gd` is the
   reference). If the rejected rig is a SUBSET of the donor (same bones, the
   donor may have extra ones the target lacks, e.g. finger bones irrelevant to a
   walk) and the intermediate track path to `Skeleton3D` matches, an in-engine
   retarget will work.
2. **Retarget in the playback engine, not the authoring tool.** Copy the donor
   clip and rewrite each track's node path to point at THIS rig's skeleton node.
   When only the first path segment differs (`<donor>/root/Skeleton3D:bone` vs
   `<target>/root/Skeleton3D:bone`), a first-segment prefix remap is enough
   (see [[project_godot_cross_fbx_anim_merge]]); the demo's `npc.gd`
   `_merge_walk` / `_merge_named` already do exactly this. Tracks targeting bones
   the rig lacks simply resolve to nothing and no-op — harmless.
3. **Prefer a shared donor over per-rig external bakes** when every character is
   the same base skeleton (all AccuRIG CC_Base here). One donor clip covers any
   current or future rig on that skeleton, needs no new binary asset, and removes
   the external tool from the loop entirely.
4. **Verify the retarget visually, not just by "it plays".** Confirm an upright
   mid-stride pose (legs split fore/aft) and no exploded bbox — a scrambled
   retarget still "plays". Position logs proving locomotion + zero
   unresolved-track errors + one bent-joint screenshot is the full check.

## Notes (optional)

This is the "measure/reuse what you have, don't assume the tool is the only path"
family — cousin to the rig-scanner lessons that measure conventions instead of
guessing them. It applies when a compatible skeleton EXISTS; if no working rig
shares the skeleton, the in-engine shortcut is unavailable and you are back to
fixing the external tool (or authoring the clip). Also note the transfer is clean
only for bone-LOCAL rotation tracks on a shared rest hierarchy; a donor with a
different rest pose or proportions can transfer poorly, and root-translation
tracks may need scaling. Related: [[project_ccbase_retarget_scramble]] (which
cross-tool paths scramble a CC_Base skin and which don't).
