# Soapbox Sabotage Character Gen-to-Rig Pipeline Plan

## Overview

Hybrid pipeline for generating 10 fully rigged driver characters for Soapbox Sabotage.
Uses **character-ralph stages 1-4** (art consistency) then **art-to-rig-ralph stages 5-7**
(batch processing + back-pressure).

## Reference: MK Shy Guy Skeleton

Shy Guy is the best reference — 29 bones, 3,759 verts, 5 meshes. Clean simplified humanoid.

### Shy Guy Bone Hierarchy (29 bones)
```
Skl_Root
├── Hip
│   ├── LegL → KneeL → FootL
│   └── LegR → KneeR → FootR
└── Spine1 → Spine2
    ├── Head → Hair1 → Hair2
    ├── ShoulderL → ArmL → ElbowL → HandL
    │   ├── Finger1L → Finger2L
    │   └── Thumb1L → Thumb2L
    └── ShoulderR → ArmR → ElbowR → HandR
        ├── Finger1R → Finger2R
        └── Thumb1R → Thumb2R
```

### Shy Guy Mesh Details
- **Body**: 2,262 verts, 2,366 faces — weighted to 20 bones (no finger/thumb weights)
- **Eyes**: 520 verts, 638 faces — weighted to Head bone only
- **Total**: 2,782 character verts + 977 kart verts in same file

### Key Insight
Shy Guy's fingers (8 bones) have NO vertex weights on the body mesh — they're pure
chain bones for item-holding animation. The body only deforms on 20 bones. This matches
the Soapbox spec exactly: "Fingers are NOT needed (hands are cube-like in the art style)."

---

## Target Skeleton: Soapbox Driver (29 bones, MK-compatible)

Map Shy Guy naming to Unity Mecanim while keeping the same structure:

### Bone Mapping Table

| # | MK Shy Guy | Soapbox (Blender) | Unity Mecanim | Unreal | Weighted? |
|---|-----------|-------------------|---------------|--------|-----------|
| 1 | Skl_Root | Root | — (root) | root | No |
| 2 | Hip | Hips | Hips | pelvis | Yes |
| 3 | Spine1 | Spine | Spine | spine_01 | Yes |
| 4 | Spine2 | Chest | Chest | spine_02 | Yes |
| 5 | Head | Head | Head | head | Yes |
| 6 | Hair1 | Hair.001 | — (extra) | — | Yes (characters with long hair) |
| 7 | Hair2 | Hair.002 | — (extra) | — | Yes (characters with long hair) |
| 8 | ShoulderL | Shoulder.L | LeftShoulder | clavicle_l | Yes |
| 9 | ArmL | UpperArm.L | LeftUpperArm | upperarm_l | Yes |
| 10 | ElbowL | LowerArm.L | LeftLowerArm | lowerarm_l | Yes |
| 11 | HandL | Hand.L | LeftHand | hand_l | Yes |
| 12 | Finger1L | Finger.L | — (extra) | — | No (cube hands) |
| 13 | Finger2L | Finger.L.001 | — (extra) | — | No |
| 14 | Thumb1L | Thumb.L | — (extra) | — | No |
| 15 | Thumb2L | Thumb.L.001 | — (extra) | — | No |
| 16 | ShoulderR | Shoulder.R | RightShoulder | clavicle_r | Yes |
| 17 | ArmR | UpperArm.R | RightUpperArm | upperarm_r | Yes |
| 18 | ElbowR | LowerArm.R | RightLowerArm | lowerarm_r | Yes |
| 19 | HandR | Hand.R | RightHand | hand_r | Yes |
| 20 | Finger1R | Finger.R | — (extra) | — | No |
| 21 | Finger2R | Finger.R.001 | — (extra) | — | No |
| 22 | Thumb1R | Thumb.R | — (extra) | — | No |
| 23 | Thumb2R | Thumb.R.001 | — (extra) | — | No |
| 24 | LegL | UpperLeg.L | LeftUpperLeg | thigh_l | Yes |
| 25 | KneeL | LowerLeg.L | LeftLowerLeg | calf_l | Yes |
| 26 | FootL | Foot.L | LeftFoot | foot_l | Yes |
| 27 | LegR | UpperLeg.R | RightUpperLeg | thigh_r | Yes |
| 28 | KneeR | LowerLeg.R | RightLowerLeg | calf_r | Yes |
| 29 | FootR | Foot.R | RightFoot | foot_r | Yes |

**20 weighted bones** (body deformation) + **8 chain bones** (fingers, for future item-holding)
+ **1 root bone** = **29 total**, matching MK Shy Guy exactly.

### DriverMount Empty

Added to character root hierarchy for kart attachment:

```
Root (Empty @ origin)
├── DriverMount (Empty @ hip height — aligns with kart Seat empty)
└── Armature
    └── [29-bone skeleton]
        └── [character mesh]
```

**DriverMount position:** At hip bone head position (0, 0, 0) in character local space.
At runtime, Unity parents this to the kart's Seat empty:
```csharp
driverMount.SetParent(kart.transform.Find("KartRoot/Chassis/Seat"), false);
```

---

## Hybrid Pipeline Flow

### Phase 1: Character Art (character-ralph stages 1-4)

Run character-ralph for each of the 10 characters. Each character goes through:

| Stage | Input | Output | Tool |
|-------|-------|--------|------|
| 1. Portrait | Character description + style variant | 512x512 portrait PNG | Flux/SDXL via ComfyUI |
| 2. Fullbody | Portrait + description | 768x768 extreme wide T-pose fullbody PNG | IP-Adapter + style transfer |
| 3. Multiview | Fullbody reference | Front/side/back orthographic PNGs | Multi-view generation |
| 4. 3D Convert + Split | Multiview images | Split GLB mesh (~20k faces, separate body objects) | Hunyuan3D v2.0 + Blender mesh split |

**Quality gates at each stage.** If a gate fails, retry that stage.

**Style variants per character** (from character-asset-spec.md):
- v1_otomo_crumb: Player, Soup Box, Sparks
- v2_mad_mag_racer: Grit
- v4_wasteland_zap: Crank, Smog
- v6_otomo_zap: Bones, Pip
- v8_kaneda_comix: Rust, Punk King

### Phase 2: Batch Rigging (art-to-rig-ralph stages 5-7)

All 10 characters processed in batch with back-pressure controls:

| Stage | Input | Output | Tool |
|-------|-------|--------|------|
| 5. Mesh Prep | Split GLB | Prepared multi-object GLB (20k faces, T-pose, scaled) | mesh_prep.py (Blender) |
| 6. Rig | Prepared split GLB | Rigged GLB with 29-bone skeleton (all objects parented) | UniRig (9/10 chars) or rig_soupbox.py (Soup Box) |
| 7. Export | Rigged GLB | Unity FBX + Blender GLB + animations | Blender + animate_unirig.py |

**Back-pressure controls** (same as kart pipeline):
- Max 2 concurrent ComfyUI jobs
- Max 3 concurrent Blender headless jobs
- UniRig timeout retry (3x)
- VRAM OOM fallback (halve resolution)
- Checkpoint after each character

### Phase 3: Animation Baseline

After rigging, apply 3 baseline animations per character via `animate_unirig.py`:

| Animation | Duration | Loop | Purpose |
|-----------|----------|------|---------|
| idle | 2-4 sec | Yes | Default in-kart state |
| walk | 1-2 sec | Yes | Pre-race lineup / garage |
| run | 0.8-1.5 sec | Yes | Victory celebration |

Unity adds procedural emotion overlays on top:
- Head tilt/swivel → EmotionAnimator
- Fist pump / wave → EmotionAnimator
- Spine lean → EmotionAnimator
- Hip bounce → EmotionAnimator

---

## Special Cases

### Soup Box ("The Mascot") — Custom Rig

UniRig will fail on a barrel with limbs. Custom `rig_soupbox.py`:

```
Root
├── DriverMount (Empty)
└── Armature
    └── Root bone
        ├── Hips (at barrel center)
        │   ├── UpperLeg.L → LowerLeg.L → Foot.L (stub legs from barrel holes)
        │   └── UpperLeg.R → LowerLeg.R → Foot.R
        └── Spine → Chest (barrel body — rigid, full weight)
            ├── Head (poking out top — full head geometry)
            ├── Shoulder.L → UpperArm.L → LowerArm.L → Hand.L (stub arms)
            └── Shoulder.R → UpperArm.R → LowerArm.R → Hand.R
```

**Weight painting strategy:**
- Barrel mesh → 100% Chest bone (rigid, no deformation)
- Arms/legs ��� standard humanoid weights at joints
- Head → 100% Head bone
- No Hair bones (Soup Box wears a tiny helmet)
- No Finger bones (stub hands)
- **22 bones total** (no hair, no fingers) — still Mecanim compatible

### Characters with Hair Physics

| Character | Hair Bones? | Notes |
|-----------|------------|-------|
| Player | No | Short messy hair, no physics needed |
| Bones | No | Mohawk, rigid |
| Crank | No | Flat cap |
| Grit | No | Braids pulled back tight |
| Pip | No | Short messy hair |
| Punk King | **Yes (2 bones)** | Wild dark hair flowing past shoulders |
| Rust | No | Short cropped |
| Smog | No | Hood up always |
| Sparks | No | Spiky short hair |
| Soup Box | No | Tiny helmet |

Only **Punk King** needs Hair.001 + Hair.002 bones for flowing hair simulation.
All others: Hair bones exist in skeleton but have zero weight.

---

## Scripts Needed

| Script | Purpose | Status |
|--------|---------|--------|
| `character_assembler.py` | Post-UniRig: rename bones to Soapbox convention, add DriverMount empty, validate hierarchy | **NEW** |
| `rig_soupbox.py` | Custom rig for Soup Box barrel character | **NEW** |
| `character_pipeline_batch.py` | Orchestrates hybrid pipeline: char-ralph 1-4 → art-to-rig-ralph 5-7 for all 10 characters | **NEW** |
| `test_character_backpressure.py` | Back-pressure tests adapted for humanoid pipeline | **NEW** |
| `animate_unirig.py` | Apply idle/walk/run animations | **EXISTS** in packages/mcp-server/scripts/ |
| `batch_animate_unirig.py` | Batch animation application | **EXISTS** |
| `mesh_prep.py` | Mesh preparation | **EXISTS** in pipelines/art-to-rig-ralph/scripts/ |

---

## Output Files Per Character

```
output/final/{character_id}/
├── artwork/
│   ├── {id}_portrait.png
│   ├── {id}_fullbody.png
│   └── {id}_multiview.png
├── mesh/
│   ├── {id}_raw.glb          (from Hunyuan3D)
│   └── {id}_prepared.glb     (after mesh prep)
├── rigged/
│   ├── {id}_rigged.glb       (Blender bone names)
│   ├── {id}_unity.fbx        (Mecanim bone names)
│   └── {id}_unreal.fbx       (UE bone names)
├── animated/
│   ├── {id}_idle.glb
│   ├── {id}_walk.glb
│   └── {id}_run.glb
└── {id}_character_report.json
```

Final delivery to soapbox-unity:
```
D:\Projects\soapbox-unity\Assets\Models\Characters\{id}_driver_rigged.glb
D:\Projects\soapbox-unity\Assets\Models\Characters\{id}_driver_unity.fbx
D:\Projects\soapbox-unity\Assets\Sprites\Characters\to3d\{id}_tpose.png
```

---

## Acceptance Criteria

1. All 10 characters have: portrait, fullbody, multiview, raw GLB, prepared GLB, rigged GLB, Unity FBX, 3 animation clips
2. 9/10 characters rigged via UniRig with 29-bone skeleton matching MK Shy Guy structure
3. Soup Box rigged via custom `rig_soupbox.py` with 22-bone simplified skeleton
4. All skeletons map to Unity Mecanim Humanoid configuration
5. DriverMount empty present on all characters, positioned at hip height
6. Punk King has weighted Hair.001/Hair.002 bones; all others have zero-weight hair bones
7. Weight coverage >90% on all characters
8. No finger vertex weights (cube hands) — finger chain bones present but unweighted
9. Baseline animations (idle, walk, run) validate clean deformation at shoulders, elbows, hips, knees
10. All FBX imports into Unity with Mecanim Avatar auto-detection
11. Back-pressure tests pass (timeout retry, VRAM fallback, concurrent limits)
12. BATCH-MANIFEST.md documents all 10 characters with quality scores
