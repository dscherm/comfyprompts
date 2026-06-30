# Barbarian → Unity Humanoid — import prep packet

**Decision (2026-06-30):** animate the AccuRIG-rigged barbarian via **Unity Humanoid
retargeting** with **free Mixamo clips** as the source. This keeps AccuRIG's clean
weights, uses Unity's robust muscle-space retarget (fixes the limb-plane artifacts the
hand-rolled `retarget_mocap.py` produced), and validates in the real ship target.
`retarget_mocap.py` is now previz-only. See lessons `hand-rolled-retarget-limb-plane`,
`unirig-skin-weights-melt-use-accurig`.

## 1. The character to import (rigged, AccuRIG, clean weights)
`E:/ai-training/_rigtest/bakeoff/barbarian_fists_textured_accurig.fbx`
- 71-bone CC_Base (Reallusion) skeleton, UVs preserved, no embedded material.
- Texture to assign in Unity: `E:/ai-training/_rigtest/bakeoff/barbarian_tex.png`
  (extracted 2048² Hunyuan3D albedo). Assign to the body material's Base Color (UVs align).

**Import settings (character FBX):**
- Model ▸ **Scale Factor**: leave 1 first; if tiny, set ~100 (UniRig/CC export quirk) — but
  AccuRIG FBX usually imports at correct meters. Check against a 1.8 m capsule.
- Rig ▸ **Animation Type = Humanoid**, **Avatar Definition = Create From This Model**, Apply.
- Click **Configure…** → confirm the avatar is green/valid (see bone map below). Use
  **Enforce T-Pose** if a bone reads red.
- Materials ▸ extract/assign `barbarian_tex.png` to Base Color.

## 2. Free Mixamo clips to grab (mixamo.com, free, royalty-free for embedded commercial use)
Download as **FBX (no skin / "Without Skin")** — we only need the animation:
- **Idle** (e.g. "Breathing Idle"), **Walking** (in-place or with motion),
  **Running**, plus actions: **Sword And Shield Slash / Great Sword Slash**,
  **Hit Reaction**, **Dodge / Roll**, **Block Idle**, **Waving**, **Victory**.
- Mixamo clips use the `mixamorig:` skeleton; they import as Humanoid and Unity
  retargets them onto the barbarian's Humanoid avatar.

**Import settings (each animation FBX):**
- Rig ▸ **Animation Type = Humanoid**, **Avatar Definition = Copy From Other Avatar**
  → pick the **barbarian's avatar** (from step 1). Apply.
- Animation ▸ enable **Loop Time** on idle/walk/run. (Root motion: enable "Bake Into Pose"
  toggles as needed; Mixamo "in-place" clips + Unity root motion is the clean combo.)

## 3. CC_Base → Mecanim bone map (for avatar Configure, if auto-map misses any)
Unity auto-maps CC skeletons well; key required bones:
- Hips ← `CC_Base_Hip` · Spine ← `CC_Base_Waist`/`Spine01` · Chest ← `CC_Base_Spine02`
- Head ← `CC_Base_Head`
- L/R UpperArm ← `CC_Base_{L,R}_Upperarm` · LowerArm ← `..._Forearm` · Hand ← `..._Hand`
- L/R Shoulder ← `CC_Base_{L,R}_Clavicle`
- L/R UpperLeg ← `CC_Base_{L,R}_Thigh` · LowerLeg ← `..._Calf` · Foot ← `..._Foot`
- Twist/share/toe/breast bones map to optional slots or stay unmapped (fine).

## 4. Animator
- Create an Animator Controller: default **Idle**; `Speed` float drives Idle↔Walk↔Run;
  triggers (Attack/Hit/Dodge/Block/Wave/Celebrate) from AnyState → clip → exit to Idle.
  (Mirror the kart `package_for_unity.py` controller pattern, but let Unity own the avatar.)

## Why not the old GS4 path
GS4's hand-written `.meta` (skeleton:[] + manual human map) caused the
"Transform 'Armature' not found in HumanDescription" error. Import the FBX **normally**
and let Unity build the avatar — do NOT hand-write the avatar `.meta`.
