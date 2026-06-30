# Unity Humanoid Bone-Roll Normalize (auto-rig → Unity retarget)

**Problem:** Auto-rigged characters (AccuRIG / CC_Base, via Hunyuan3D→AccuRIG)
import into Unity as Humanoid and *look* fine in bind pose, but Mixamo/Humanoid
clips retarget onto them with **twisted elbows** ("forearm perpendicular to
upperarm") and an unstable foot. Root cause: the rig's **limb bone ROLL axes are
inconsistent down the chain** (e.g. upperarm roll 48.7°, forearm 24.1°, hand
95.5°). The bind pose hides it (rest deformation is identity regardless of roll),
but Unity's muscle-space retarget reads the roll axes and skews the joint planes
on every clip. One bad rig → all clips wrong downstream.

Observed in: comfyui-toolchain / animate-ralph (barbarian: Hunyuan3D→AccuRIG→Unity).

## Fix

1. **Normalize bone ROLLS in EDIT mode — do NOT re-pose the rig.** Match the
   forearm/hand (and forearm-twist) rolls to the upperarm roll so the chain is
   consistent. Edit-mode roll changes are **safe for the mesh**: at rest, pose ==
   rest so deformation is identity — geometry and legs are untouched. This is the
   load-bearing, low-risk fix. (`pipelines/animate-ralph/tools/normalize_rig_rolls_for_unity.py`)

2. **DO NOT "Apply Pose as Rest Pose" to force a T-pose** unless you correctly
   re-bind. Posing arms to horizontal + bake-modifier + `armature_apply` leaves the
   skinned mesh's **bind matrices desynced from the new armature rest** → Unity
   deforms the character into **arms-up / legs-merged**. The exported FBX bind reads
   correct in Blender (arms horizontal, legs symmetric) yet Unity collapses it —
   that's the bind-mismatch signature, not a Unity-solver or "limbs too straight"
   issue (tested: adding elbow/knee bend did NOT help). A pure no-edit FBX
   round-trip is clean, which proves the *edit* breaks it, not the export.

3. **After re-exporting a rig, REBUILD the Unity avatar fresh** — set
   `animationType=Generic / avatarSetup=NoAvatar`, reimport, then
   `Human / CreateFromThisModel`, reimport. A stale humanoid config validates the
   old skeleton and the new build comes back `isHuman=False`. Cycling fixes it.

4. **Develop rig edits with HEADLESS Blender, not the blender-mcp socket.**
   Blender 5.0's FBX importer fails over the socket with
   `mode_set.poll() Context missing active object` (no window context). Headless
   (`blender --background --python`) imports/exports reliably and is what the
   pipeline stage runs anyway. Develop on a COPY to a `_rigtest/` path, verify in
   Unity, only then touch production.

5. **The foot flap is a SEPARATE issue** — it persists through roll normalization
   (left-foot localEuler swings ~90–110° vs right's ~30° on a symmetric rig). Root
   cause is the Unity avatar's per-side **muscle config**, not the rig roll or bind
   pose. Needs its own pass (symmetric left/right muscle setup), independent of this.

## Where it belongs

Rig finalization, **immediately after AccuRIG, before engine import** — so every
character leaves rigging engine-ready. Headless, deterministic; the LoRA/generation
should stay tuned for Hunyuan3D reconstruction (separated limbs, closed fists), NOT
burdened with exact-T-pose precision (stochastic stages can't guarantee geometry).
