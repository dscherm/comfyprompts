# Animate-Ralph -- Animation Reference Library

Reference animations improve the pipeline by providing retarget-from-reference instead of building animations from scratch. A Mixamo walk cycle retargeted to a UniRig skeleton produces better results in seconds than procedural generation does in minutes.

## Directory Structure

```
references/
├── humanoid/
│   ├── locomotion/        walk, run, strafe, sprint, sneak, crouch_walk
│   ├── combat/            attack, block, dodge, hit_reaction, death, combo
│   ├── idle/              standing, seated, fidget, breathing, look_around
│   ├── gesture/           wave, point, nod, shrug, celebrate, clap
│   ├── driving/           seated_idle, steer_left, steer_right, brake, boost
│   ├── emotion/           happy, angry, scared, confident, taunt
│   └── sex/               intimate/adult animation references
├── quadruped/
│   └── locomotion/        walk, run, gallop, idle, eat
├── mocap_raw/
│   └── cmu_bvh/           raw BVH for custom retargeting
└── retarget_maps/
    ├── mixamo_to_unirig.json      bone name mapping
    ├── quaternius_to_unirig.json  bone name mapping
    └── cmu_to_unirig.json         bone name mapping
```

---

## Source 1: Mixamo (Primary -- 2,453 Animations)

**License**: Free with Adobe account, royalty-free for any project
**Format**: FBX (download "Without Skin" for animation-only files)
**URL**: https://www.mixamo.com/

### Bulk Download Tools

| Tool | URL | Method |
|------|-----|--------|
| **mixamo-downloader** (GUI) | https://github.com/juanjo4martinez/mixamo-downloader | Python GUI, filter by category |
| **mixamo_anims_downloader** | https://github.com/gnuton/mixamo_anims_downloader | Python script, uses Mixamo API |
| **Browser console script** | https://gist.github.com/gnuton/ec2c3c2097f7aeaea8bb7d1256e4b212 | JavaScript in Chrome DevTools |

### Priority Animations to Download

Download these as FBX "Without Skin" from https://www.mixamo.com/:

#### Locomotion (save to `references/humanoid/locomotion/`)
| Animation | Mixamo Search | Duration | Loop |
|-----------|---------------|----------|------|
| Walk | "Walking" | ~1.0s | Yes |
| Run | "Running" | ~0.8s | Yes |
| Sprint | "Sprinting" | ~0.7s | Yes |
| Strafe Left | "Left Strafe Walking" | ~1.0s | Yes |
| Strafe Right | "Right Strafe Walking" | ~1.0s | Yes |
| Crouch Walk | "Crouch Walking" | ~1.2s | Yes |
| Sneak | "Sneaking" | ~1.5s | Yes |
| Jog | "Jogging" | ~0.9s | Yes |

#### Combat (save to `references/humanoid/combat/`)
| Animation | Mixamo Search | Duration | Loop |
|-----------|---------------|----------|------|
| Punch | "Cross Punch" | ~0.5s | No |
| Kick | "Roundhouse Kick" | ~0.8s | No |
| Sword Slash | "Sword And Shield Slash" | ~0.7s | No |
| Block | "Standing React" | ~0.5s | No |
| Dodge Left | "Left Dodge" | ~0.5s | No |
| Hit Reaction | "Hit Reaction" | ~0.5s | No |
| Death Forward | "Dying Forward" | ~2.0s | No |
| Death Backward | "Dying Backward" | ~2.0s | No |

#### Idle & Seated (save to `references/humanoid/idle/`)
| Animation | Mixamo Search | Duration | Loop |
|-----------|---------------|----------|------|
| Standing Idle | "Idle" | ~3.0s | Yes |
| Breathing Idle | "Breathing Idle" | ~4.0s | Yes |
| Look Around | "Looking Around" | ~3.0s | Yes |
| Fidget | "Idle Fidget" | ~2.0s | Yes |
| Sitting Idle | "Sitting Idle" | ~3.0s | Yes |
| Sitting Talking | "Sitting Talking" | ~3.0s | Yes |

#### Gesture & Emotion (save to `references/humanoid/gesture/` and `emotion/`)
| Animation | Mixamo Search | Duration | Loop | Folder |
|-----------|---------------|----------|------|--------|
| Wave | "Waving" | ~2.0s | No | gesture |
| Celebrate | "Victory" | ~2.0s | No | gesture |
| Clap | "Clapping" | ~2.0s | Yes | gesture |
| Point | "Pointing" | ~1.5s | No | gesture |
| Shrug | "Shrug" | ~1.5s | No | gesture |
| Taunt | "Taunting" | ~2.0s | No | emotion |
| Angry | "Angry Gesture" | ~2.0s | No | emotion |
| Happy Bounce | "Happy" | ~2.0s | Yes | emotion |

#### Driving-Specific (save to `references/humanoid/driving/`)
| Animation | Mixamo Search | Duration | Loop |
|-----------|---------------|----------|------|
| Seated Idle | "Sitting Idle" | ~3.0s | Yes |
| Lean Forward | "Sitting Reaching Forward" | ~1.0s | No |
| Fist Pump | "Fist Pump" | ~1.5s | No |
| Head Nod | "Head Nod Yes" | ~1.0s | No |

**How to download from Mixamo:**
1. Go to https://www.mixamo.com/ and sign in (free Adobe account)
2. Click "Animations" tab
3. Search for each animation name
4. Select it, click "Download"
5. Format: **FBX Binary**, Skin: **Without Skin**, Frames per Second: **30**
6. Save to the appropriate `references/` subfolder

---

## Source 2: Quaternius (CC0 -- 250+ Animations)

**License**: CC0 (public domain)
**Format**: FBX, GLB, Blend

### Packs to Download

| Pack | Animations | URL |
|------|-----------|-----|
| **Universal Animation Library** | 120+ (locomotion, combat, actions, idles) | https://quaternius.itch.io/universal-animation-library |
| **Universal Animation Library 2** | 130+ (combat combos, parkour, farming, zombie) | https://quaternius.itch.io/universal-animation-library-2 |

**Note**: You already downloaded UAL 1 -- it's at `pipelines/autorig-ralph/references/humanoid/quaternius_animation_lib.fbx`. Copy the GLB version to animate-ralph references.

**Download UAL 2**: Visit the itch.io page, click "Download Now" (free, name-your-price).

---

## Source 3: RancidMilk CMU Conversion (2,000+ Animations, Pre-Retargeted)

**License**: Free to use/modify/redistribute
**Format**: FBX and GLB (already retargeted to Quaternius humanoid rig)
**URL**: https://rancidmilk.itch.io/free-character-animations

This is the **most valuable single download** -- 2,000+ animations already converted from CMU mocap BVH data and retargeted to a standard humanoid rig. GLB format works directly in Blender.

**Categories included**: Walking (dozens of styles), running, jumping, dancing, martial arts, everyday actions, sports, climbing, swimming motions, and more.

---

## Source 4: CMU Motion Capture Database (Raw BVH)

**License**: Free for any purpose
**Format**: BVH (community conversions available)

### Download Options

| Format | URL |
|--------|-----|
| **Original ASF/AMC** | https://mocap.cs.cmu.edu/ |
| **BVH (Daz-friendly)** | https://sites.google.com/a/cgspeed.com/cgspeed/motion-capture/the-daz-friendly-bvh-release-of-cmus-motion-capture-database |
| **FBX (full dataset)** | https://huggingface.co/datasets/gbionics/cmu-fbx |
| **FBX (torrent)** | https://academictorrents.com/details/8e21416d1584981ef3e9d8a97ee4278f93390623 |

### Key CMU Subjects for Game Animations

| Subject | Motion Type | Files |
|---------|-------------|-------|
| 02 | Sword/martial arts | 02_01 (walk), 02_05 (punch), 02_07-09 (swordplay) |
| 09 | Running variations | 09_01 (run) |
| 16 | Walking/running variations | 16_15 (walk), 16_35 (run) |
| 35 | Walking styles | 35_01 (casual walk), 35_17 (jog) |
| 76 | Punching/dodging | 76_01 (punch), 76_03 (dodge) |
| 85 | Falling/stumbling | 85_15 (fall forward) |
| 90 | Reactions | 90_16 (stumble) |

You already have 4 BVH files in `packages/mcp-server/scripts/mocap_samples/`.

---

## Source 5: Rokoko Free Motion Library (150 Studio-Quality Animations)

**License**: Free for commercial use
**Format**: FBX/BVH (via Rokoko Studio download)
**URL**: https://www.rokoko.com/products/motion-library

Professional studio-captured mocap from Audiomotion and Centroid studios. Higher quality than CMU data. Requires free Rokoko Studio account.

---

## Retargeting Tools

### Recommended: Keemap Blender Addon (Free)

**URL**: https://github.com/nkeeline/Keemap-Blender-Rig-ReTargeting-Addon
**Why**: Saves reusable bone mapping files. Create a Mixamo→UniRig mapping once, reuse for all 2,453 animations.

### Alternative: Retarget Extension (Blender 5+ compatible)

**URL**: https://extensions.blender.org/add-ons/retarget/
**Why**: Has built-in presets for Mixamo, Unreal, VRoid, MMD skeletons.

### Other Free Options

| Tool | URL | Notes |
|------|-----|-------|
| Blender Animation Retargeting (Mwni) | https://github.com/Mwni/blender-animation-retargeting | Simple bone-to-bone |
| ReNim | https://github.com/anasrar/ReNim | Node-based visual retargeting |
| blender-retarget (igelbox) | https://github.com/igelbox/blender-retarget | Real-time bone sync |
| Rokoko Blender Plugin | https://github.com/Rokoko/rokoko-studio-live-blender | Auto bone-name matching |

### Existing in Pipeline

`packages/mcp-server/scripts/retarget_mocap.py` (770 lines) already handles CMU BVH→UniRig retargeting with rest-pose correction. This can be extended to support Mixamo and Quaternius skeletons.

---

## Priority Download Order

### Phase 1: Core Library (download these first)
1. **Quaternius UAL 2** -- https://quaternius.itch.io/universal-animation-library-2 (130+ anims, CC0)
2. **RancidMilk CMU pack** -- https://rancidmilk.itch.io/free-character-animations (2,000+ anims, GLB)
3. **Mixamo essentials** -- ~40 key animations from the table above (free Adobe account)

### Phase 2: Extended Library
4. **Rokoko free library** -- https://www.rokoko.com/products/motion-library (150 studio-quality)
5. **CMU FBX full dataset** -- https://huggingface.co/datasets/gbionics/cmu-fbx (2,548 motions)
6. **Mixamo bulk download** -- Use https://github.com/juanjo4martinez/mixamo-downloader for remaining animations

### Phase 3: Retargeting Setup
7. **Keemap addon** -- https://github.com/nkeeline/Keemap-Blender-Rig-ReTargeting-Addon
8. Create bone mapping files: Mixamo→UniRig, Quaternius→UniRig, CMU→UniRig
9. Batch-retarget all downloaded animations to UniRig skeleton

---

## Integration with autorig-ralph

autorig-ralph produces rigged GLBs with:
- ML-predicted skeleton matching one of 50 reference templates
- IK chains for arms + legs
- Twist bones for smooth rotation
- 95%+ weight coverage

The bone naming from autorig-ralph's skeleton maps to retargeting maps in this library. When autorig-ralph uses UniRig, the `retarget_maps/mixamo_to_unirig.json` mapping file enables instant retargeting of any Mixamo animation to the character.

### Handoff Flow

```
autorig-ralph → rigged GLB → animate-ralph Stage 1 reads rig-report.json
                                              ↓
                              Stage 2 selects reference animations
                              from this library based on clip spec
                                              ↓
                              Stage 3 retargets references to the
                              character's skeleton using bone maps
                                              ↓
                              Stage 4 refines timing and arcs
                                              ↓
                              Stage 5 exports per-platform
```
