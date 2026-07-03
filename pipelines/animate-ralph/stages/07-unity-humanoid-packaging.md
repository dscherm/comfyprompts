# Stage 7: Unity Humanoid Packaging (the SHIPPABLE animation route)

This stage takes a **rigged character** (AccuRIG / CC_Base or any Humanoid-mappable
skeleton) and produces a **playable, retargetable animation set in Unity** by using
**Unity's Humanoid (Mecanim) muscle-space retargeting** with **free Mixamo clips** as
the motion source. It is the SHIP path — it replaces the headless hand-rolled
`retarget_mocap.py` / `batch_retarget.py` output, which is **previz-only** (it
mishandles the limb plane; see lesson `hand-rolled-retarget-limb-plane` and
`pipelines/animate-ralph/UNITY-IMPORT-NOTES.md`).

> **Why this stage, not the headless retarget:** Unity Humanoid normalizes both the
> source clip and the target rig through a canonical T-pose muscle space, so arm/leg
> planes come out natural — the exact thing the hand-rolled transfer cannot do. It
> also keeps the rigger's clean weights (AccuRIG).

## Inputs

| Input | Source |
|-------|--------|
| Rigged character FBX (Humanoid-mappable) | AccuRIG export, e.g. `barbarian_fists_textured_accurig.fbx` |
| Albedo texture (UVs preserved by AccuRIG) | `barbarian_tex.png` (Hunyuan3D 2048²) |
| Motion clips | **Mixamo** (free, royalty-free for embedded commercial use) — manual download, no API |
| Unity project | `../soapbox-unity` (Unity 6000.4; Coplay plugin `com.coplaydev.coplay` present) |

## Tooling: live (coplay-mcp) vs manual

This stage is **automatable when coplay-mcp is connected to a live Unity Editor**
(drive imports, avatar config, Animator build, and run the validator from Claude).
When coplay is not connected, every step below is a documented manual GUI action plus
the in-editor C# validator. **Establishing the coplay testing env:** open the Unity
Editor on `../soapbox-unity` with the Coplay plugin signed in, then start/refresh a
Claude session so `coplay-mcp` (already in `~/.claude.json`) handshakes with the live
editor — only then do its tools appear.

### Reconnect / coplay round-trip (verified — UH1)

Because `coplay-mcp` handshakes **at Claude-session start**, the Unity Editor must
already be open on `../soapbox-unity` with the Coplay plugin signed in *before* the
session launches (or refresh the session after opening Unity). To re-establish and
verify the link from a fresh session, run this round-trip in order:

1. **Discover the live editor** — `list_unity_project_roots` → expect
   `{count:1, projectRoots:[{projectRoot:"D:\\Projects\\soapbox-unity", ...}]}`.
   `count:0` means coplay didn't connect: confirm Unity is open + Coplay signed in,
   then refresh the Claude session (MCP only loads on start).
2. **Confirm the editor responds** — `get_unity_editor_state` → expect
   `playMode:false, hasCompilationErrors:false` in edit mode.
3. **Round-trip a real call** — run the validator:
   `execute_script(filePath="Assets/Editor/ValidateBarbarianHumanoid.cs", methodName="Execute")`.
   A `Success:true` with the full validation report back in `Result` proves the
   round-trip. **A `RESULT: FAIL` here is the expected UH1 baseline** — the character
   reports `animationType=Generic` until UH2, clips are missing until UH3, and Animator
   states are unbound until UH4. UH1 verifies the *channel*, not a passing validation.

Verified 2026-06-30 against Unity `6000.4.0f1`; baseline validator returned
`Success:true` / `RESULT: FAIL` (Generic rig, no Mixamo folder) as expected.

## Steps

### 7.1 Stage assets (headless)
Copy the rigged FBX + texture into the project:
```
Assets/Animations/Barbarian/Source/barbarian_accurig.fbx
Assets/Animations/Barbarian/Source/barbarian_tex.png
```

### 7.2 Import the character as Humanoid
- Model FBX → **Rig ▸ Animation Type = Humanoid**, **Avatar Definition = Create From
  This Model** → Apply → **Configure…** confirm the avatar is valid/green (Enforce
  T-Pose if a bone reads red).
- Materials ▸ assign `barbarian_tex.png` to the body material **Base Color** (UVs align).
- **Do NOT hand-write the avatar `.meta`** — that caused the GS4 "Transform 'Armature'
  not found in HumanDescription" error. Let Unity build the avatar.
- CC_Base→Mecanim bone map: see `UNITY-IMPORT-NOTES.md` §3.

> **Verified (UH2, 2026-06-30, coplay):** `barbarian_accurig.fbx` →
> `animationType=Human`, `avatarSetup=CreateFromThisModel`; built
> `barbarian_accurigAvatar` **isValid=True isHuman=True, 22 bones** (no Configure /
> Enforce-T-Pose needed). The embedded URP/Lit material was **extracted** to
> `Source/Materials/Material_0.mat` (embedded sub-assets aren't editable) and
> `barbarian_tex.png` bound to `_BaseMap` (+`_MainTex`) — UVs align, no grey.
> Validator §1 passes. A front scene capture confirms the textured Humanoid.
>
> **Caution on the legacy previz clips as a motion source:** sampling the Jun-27
> `walk` previz clip onto this avatar (Humanoid retarget) renders the character pitched
> ~45° back with arms splayed up/out — the `hand-rolled-retarget-limb-plane` defect,
> baked into the motion and *not* fixed by muscle-space retarget. It confirms the previz
> set is throwaway (UH4 deletes it); shippable motion must come from Mixamo (UH3). Also
> note `idle.fbx` carries **no animation take** (static) — only walk/attack/etc. have one.

### 7.3 Download + import the Mixamo clip set (manual download)
Grab the core gameplay set from mixamo.com as **FBX "Without Skin"** into
`Assets/Animations/Barbarian/Mixamo/`:
`idle` (Breathing Idle), `walk`, `run`, `attack` (Sword/Great Sword Slash),
`hit` (Hit Reaction), `dodge`/`roll`, `block`, `wave`, `celebrate`/`victory`.
For each clip FBX → **Rig ▸ Animation Type = Humanoid**, then pick the avatar method by
how the clip was downloaded:
- **Generic clips (the usual free download — Mixamo's Y-Bot, `mixamorig:` skeleton):**
  **Avatar Definition = Create From This Model**. Each clip builds its OWN Humanoid
  avatar and Unity retargets onto the barbarian through muscle space **at runtime**.
  *Copy-From-Other does NOT work here* — Mixamo's bone names don't match the AccuRIG
  avatar, so the retarget finds no bones and **emits no AnimationClip** (silently:
  sub-assets come back `GameObject,Transform,ImportLog` only).
- **Clips downloaded onto the character's own skeleton** (uploaded the barbarian mesh
  to Mixamo): **Avatar Definition = Copy From Other Avatar → the barbarian avatar**.

Enable **Loop Time** on idle/walk/run. Apply.

> Mixamo has **no API** — the download is the one irreducibly manual web step. Naming
> the file with the motion stem (e.g. `walk.fbx`) lets the validator match it.
>
> **Verified (UH3, 2026-06-30, coplay):** 9/9 clips (idle/walk/run/attack/hit/dodge/
> block/wave/celebrate) imported **Create From This Model**, each with its own humanoid
> avatar and a `mixamo.com` clip (`human=True`; loop on idle/walk/run). Validator §2
> passes. Sampling the Mixamo `walk` onto the barbarian shows **natural carriage** —
> arms swinging at the sides, torso upright, clean stride — i.e. the
> `hand-rolled-retarget-limb-plane` defect is gone. `ValidateBarbarianHumanoid` §2 was
> corrected to accept **either** CreateFromThisModel (own humanoid avatar) **or**
> CopyFromOther → barbarian avatar.

### 7.4 Build the Animator controller
`Assets/Animations/Barbarian/Barbarian.controller`: default **Idle**; a `Speed` float
drives Idle↔Walk↔Run; triggers (Attack/Hit/Dodge/Block/Wave/Celebrate) fire from
AnyState → clip → exit to Idle. Mirror the kart `package_for_unity.py` controller
pattern, but **let Unity own the avatar** (Humanoid, retargetable/mirrorable in-engine).

### 7.5 Validate
Run `Assets/Editor/ValidateBarbarianHumanoid.cs`:
- Live (coplay): `ValidateBarbarianHumanoid.Execute()`
- Headless: `Unity.exe -batchmode -projectPath . -executeMethod ValidateBarbarianHumanoid.RunBatch -quit`
  → writes `barbarian_humanoid_validation.txt`, exit 0=pass.

It asserts: character avatar **isValid && isHuman** (catches the GS4 bad-avatar
regression), each Mixamo clip is Humanoid + **Copy From Other Avatar = the barbarian
avatar** with a usable clip, the Animator (if built) binds motions, and the rig builds
Humanoid.

### 7.6 Cleanup
Remove the stale arms-up previz clips from `Assets/Animations/Barbarian/` (the Jun-27
hand-rolled-retarget bake) so the Humanoid set is the only shippable one.

## Gate (PASS criteria) — STRICT animation validation protocol
Three layers, ALL required; no layer may be skipped or eyeballed away
(the 2026-07-02 GS1 report "passed" while every clip was scrambled — gates
that don't measure the animation itself rubber-stamp):

1. **Blender/previz layer** (`batch_retarget.py`, automatic per clip): bones
   matched >= 18, travel fidelity (dir err <= 15°, mag 0.7–1.4 vs
   EXPECTED_TRAVEL), and **mesh integrity under motion**
   (`validate_animation_mesh.py`: p99 edge stretch <= 2.0, bounds within
   [0.5, 1.8] of rest — catches weight melting/scramble; calibrated AccuRIG
   walk 1.80 OK vs UniRig walk 2.76 MELT).
2. **Unity/ship layer** (`ValidateBarbarianHumanoid` / `ValidateRookieHumanoid`,
   exit 0 required): character avatar isValid+isHuman, clips Humanoid with
   usable motion, Animator states bound, **§5 sampled-pose sanity** — every
   clip sampled onto the avatar at 25/50/75% with joint plausibility asserted
   (head above hips, feet below, hands within 1.6× body span, span ratio
   0.35–1.4). A visually-broken retarget fails §5 headlessly.
3. **Human layer** (required, not optional): live play-mode or proof renders
   show natural arm/leg carriage — limb-plane quality has no numeric gate.

## Outputs
- `Assets/Animations/Barbarian/Source/` (rig + texture), `.../Mixamo/` (clips),
  `Barbarian.controller`, `ANIMATION-MANIFEST.json` (clip → file → dur → loop →
  avatar), `barbarian_humanoid_validation.txt`.

## See also
- `pipelines/animate-ralph/UNITY-IMPORT-NOTES.md` — the import packet (paths, bone map).
- `pipelines/animate-ralph/PROMPT.md` §"Motion Sources — Shippable vs Previz".
- Lessons: `hand-rolled-retarget-limb-plane`, `unirig-skin-weights-melt-use-accurig`.
