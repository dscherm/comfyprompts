# Kart Animation → Unity Translation Research

## Key Finding: Soapbox Sabotage is 100% Procedural

Unlike Mario Kart (which uses ~60% baked Animation Clips + ~40% procedural code),
Soapbox Sabotage uses **zero baked Animation Clips for karts**. Everything is procedural C#:

| Animation | Soapbox Implementation | Script |
|-----------|----------------------|--------|
| Idle bounce | `Mathf.Sin(phase) * idleChugAmplitude` | KartExhaustEffects.cs:202 |
| Engine vibrate | `Mathf.Sin(Time.time * freq) * amp` on EngineBay Y | KartExhaustEffects.cs:177 |
| Steering | `Lerp` front axle to ±25° | KartWheelSystem.cs |
| Wheel spin | `wheels[i].Rotate(-90 * dt * speed)` | KartWheelSystem.cs |
| Boost tilt | `FlexChassis(direction, intensity)` | KartWeaponReaction.cs |
| Hit reaction | `FlexChassis()` + particle burst | KartWeaponReaction.cs |
| Part detachment | `DetachPart()` → unparent + Rigidbody + force | IKartProvider.cs |
| Speed stretch | Z-axis scale at high speed | KartVisualPolish.cs |
| Drift skids | Trail renderers on rear wheels | KartVisualPolish.cs |

**No Animator component. No AnimatorController. No .anim clip files.**

## Mario Kart Comparison

MK uses a 4-layer Animator Controller (KartV2.controller):
- **Base Layer**: Idle, boost, collision states
- **Shake Layer** (additive): Impact shake overlay
- **AntigravSpin Layer** (additive): 360° spin
- **UnderWaterDrift Layer** (additive): Drift tilt

14 parameters drive state transitions (ShellHit, BananaHit, HitLeft/Right, etc.)
Clips are Transform animations on the kart body — object-level, not skeletal.

## Translation Strategy: 3 Options

### Option A: Stay Procedural (Current Approach)
Keep everything in C#. Our baked GLB clips serve as **documentation/reference** for the
exact MK-style curves, but Unity consumes them as parameter tables, not as AnimationClips.

**Pros:** No import workflow changes, zero Animator overhead, full runtime control
**Cons:** Can't preview in Unity Animation window, harder to tweak visually

### Option B: Hybrid — Add Animator for Impact/Event Clips Only
Keep idle/steering/wheels procedural. Add an Animator Controller for one-shot events
that benefit from precise artist-tuned timing:
- `kart_boost` (pitch tilt with overshoot and settle)
- `kart_drift_hop` (hop arc)
- `kart_hit_left` / `kart_hit_right` (collision reaction)
- `kart_banana_spin` (360° spin with pitch oscillation)
- `kart_shell_tumble` (complex multi-axis tumble)

This matches MK's architecture exactly.

**Pros:** Artist-tunable impact timing, layer blending for overlapping reactions
**Cons:** Need Animator Controller setup, potential fight between procedural and baked

### Option C: Full Animator Controller (MK-Style)
Create a KartAnimator.controller with 4 layers matching MK:
- Base Layer (idle, boost)
- Impact Layer (additive: hit_left, hit_right, banana_spin, shell_tumble)
- Drift Layer (additive: drift_hop)
- Engine Layer (additive: engine_vibrate)

**Pros:** Full MK parity, visual editing in Unity, layer blending
**Cons:** Major refactor of existing procedural scripts, import workflow complexity

## Recommendation: Option B (Hybrid)

Keep `KartExhaustEffects`, `KartWheelSystem`, `KartVisualPolish` procedural (they work well).
Add an additive Animator layer for **impact events only**, which have complex multi-keyframe
curves that are hard to replicate procedurally (especially banana_spin and shell_tumble).

## FBX Animation Import for Unity

### How Unity Imports Object-Level Animations

When Unity imports an FBX with object-level animations (no armature), it creates:
- One `AnimationClip` per action/take in the FBX
- Curves target `Transform` properties by **hierarchy path**
- Path format: `"ParentName/ChildName"` relative to the Animator's root

For our karts, the animation curves would target:
```
""                          → KartRoot (rotation, position)
"Chassis"                   → Chassis mesh
"Chassis/EngineBay"         → EngineBay empty
"Axle_Front"                → Front axle steering
```

### Import Settings Required

In Unity's FBX import settings for animated karts:
- **Animation Type**: None (no humanoid/generic rig — these are object animations)
- **Import Animation**: Yes
- **Anim. Compression**: Optimal
- **Clips**: Split by name if multiple takes, or import as single clip

### Export from Blender: FBX vs GLB

| Format | Unity Animation Support | Notes |
|--------|------------------------|-------|
| FBX | Full — split clips, import settings, Animator integration | Preferred for Unity |
| GLB | Limited — single animation, no clip splitting in import UI | Blender preview only |

**For Unity: Export animated FBX, not GLB.**

## Required Export Changes

Our current `animate_kart.py` exports GLB only. For Unity integration we need:

1. **FBX export per clip** with Unity-compatible settings:
   ```python
   bpy.ops.export_scene.fbx(
       filepath=output_path,
       use_selection=True,
       object_types={'MESH', 'EMPTY'},
       bake_anim=True,
       bake_anim_use_all_bones=False,
       bake_anim_use_nla_strips=False,
       bake_anim_use_all_actions=True,
       bake_anim_force_startend_keying=True,
       apply_scale_options='FBX_SCALE_ALL',
       axis_forward='-Z',
       axis_up='Y',
   )
   ```

2. **Hierarchy paths must match** what GLBKartEnhancer creates at runtime.
   Currently our hierarchy is:
   ```
   KartRoot > Chassis > Hood/Bumper_Front/...
   KartRoot > Axle_Front > WheelMount_FL/FR
   ```
   The animation curves reference these paths. If GLBKartEnhancer creates proxy
   transforms with different names, the clips won't bind.

3. **Recommended: FBX per clip + combined FBX**
   ```
   Assets/Animations/Karts/{kart_id}/
   ├── {kart_id}_kart_boost.fbx
   ├── {kart_id}_kart_hit_left.fbx
   ├── {kart_id}_kart_hit_right.fbx
   ├── {kart_id}_kart_banana_spin.fbx
   ├── {kart_id}_kart_shell_tumble.fbx
   └── {kart_id}_kart_drift_hop.fbx
   ```

## Unity Integration Script: KartAnimationBridge.cs

New MonoBehaviour that bridges our baked FBX clips with the existing procedural system:

```csharp
public class KartAnimationBridge : MonoBehaviour
{
    [Header("Impact Clips (from Blender pipeline)")]
    public AnimationClip boostClip;
    public AnimationClip driftHopClip;
    public AnimationClip hitLeftClip;
    public AnimationClip hitRightClip;
    public AnimationClip bananaSpinClip;
    public AnimationClip shellTumbleClip;

    private Animation legacyAnimation; // Unity Legacy Animation component

    void Start()
    {
        // Use Legacy Animation (not Animator) for additive one-shot playback
        legacyAnimation = gameObject.AddComponent<Animation>();
        legacyAnimation.playAutomatically = false;

        AddClip(boostClip, "boost");
        AddClip(driftHopClip, "drift_hop");
        AddClip(hitLeftClip, "hit_left");
        AddClip(hitRightClip, "hit_right");
        AddClip(bananaSpinClip, "banana_spin");
        AddClip(shellTumbleClip, "shell_tumble");
    }

    void AddClip(AnimationClip clip, string name)
    {
        if (clip == null) return;
        clip.legacy = true;
        legacyAnimation.AddClip(clip, name);
    }

    // Called by KartDamageVisuals, KartWeaponReaction, etc.
    public void PlayImpact(string clipName)
    {
        if (legacyAnimation.GetClip(clipName) != null)
        {
            legacyAnimation.Play(clipName);
        }
    }
}
```

## Soapbox Scripts That Would Consume These Clips

| Script | Current Method | With Baked Clips |
|--------|---------------|------------------|
| KartExhaustEffects | `FlexChassis()` for boost | `bridge.PlayImpact("boost")` |
| KartDamageVisuals | `FlexChassis()` for hit | `bridge.PlayImpact("hit_left")` or `"banana_spin"` |
| KartWeaponReaction | `FlexChassis()` for weapon deploy | Keep procedural (per-weapon directional) |
| KartWheelSystem | Procedural steering/spin | Keep procedural (speed-dependent) |
| KartVisualPolish | Procedural speed stretch | Keep procedural |

## Next Steps

1. Add FBX export to `animate_kart.py` for the 6 impact clips
2. Write `KartAnimationBridge.cs` for soapbox-unity
3. Create Animator Controller OR use Legacy Animation for additive playback
4. Update `KartDamageVisuals.cs` to call bridge for banana/shell hits
5. Deploy animated FBX files to `Assets/Animations/Karts/`
6. Test in Unity via coplay-mcp
