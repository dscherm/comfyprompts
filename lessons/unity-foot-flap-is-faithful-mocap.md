# Unity "flapping foot" on a retargeted character = faithful mocap, not a rig bug

**Problem / wrong turn:** A retargeted character's foot looked like it "flapped"
in Unity. It *seemed* left-specific and got theorized as a rig axis / Unity avatar
**muscle-config asymmetry**. That theory was WRONG — chasing it wasted effort.

**How it was actually diagnosed (do this FIRST next time):**
- Measure foot motion in **WORLD space**, not local euler. Local euler of L vs R
  feet is in **mirrored frames**, so it exaggerates asymmetry (left read 90–110°
  "twist" that was largely a frame artifact). In world space both feet rolled a
  similar large amount (L range 96° / R 76°).
- Compare **retargeted vs source**: instantiate the Mixamo clip's own model and
  sample the SAME clip on it. Result: source Mixamo walk rolled L 90° / R 79°,
  the barbarian rolled L 96° / R 76° — **nearly identical**. The retarget is
  FAITHFUL; the L/R asymmetry lives in the **Mixamo clip itself** (normal mocap —
  humans don't step symmetrically).

**Conclusion:** the "flap" is an energetic mocap walk **reproduced accurately**,
made visible by the character's **big fur boots** (boot geometry exaggerates the
foot's real rotation), with **no Foot IK** stabilizing ground contact. Not a rig,
avatar, or retarget defect.

## Options (none is a clean rig fix — because it isn't a rig problem)

1. **Swap to a calmer Mixamo walk/run clip** — best result; targets the actual
   source. Manual re-download (Mixamo has no API).
2. **Clamp the foot muscle limits** (avatar `humanDescription.human[].limit`,
   `useDefaultValues=false`, tight min/max). VERIFIED it sticks through reimport and
   IS scriptable — but effect is **modest** (roll 96°→81° at an aggressive ±12°)
   because most foot motion is legitimate heel-toe mechanics, and it's **global**
   (tightens the foot on attack/dodge too → risks stiff feet). Blunt knob, not
   recommended as the default.
3. **Foot IK** — helps foot planting/sliding but matches the source foot rotation,
   so it does NOT reduce the clip's inherent roll. Limited help for *this* symptom.
4. **Accept it** — it's faithful animation.

## Rule

Before blaming the rig/avatar for a "bad-looking" retarget, **measure world-space
motion and compare to the source clip.** If retarget ≈ source, the animation is
faithful and the fix is the CLIP (or accepting it), not the rig.
