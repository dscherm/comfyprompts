# AutoRig Ralph -- Resume Point (2026-03-31)

## Session Summary

### Complete Pipeline: 2D Art → 3D Mesh → Rigged → Kart Posed
8 of 10 characters fully processed through the entire pipeline:

| Character | 2D Art | 3D Mesh | Merged | UniRig | Weights | Boot Clean | Kart Pose | Bones |
|-----------|--------|---------|--------|--------|---------|------------|-----------|-------|
| **player** | YES | YES | YES | YES | GOOD | YES | YES | 52 |
| **bones** | YES | YES | YES | YES | GOOD | YES | YES | 52 |
| **crank** | YES | YES | YES | YES | BAD | YES | SKIP | 52 |
| **grit** | YES | YES | YES | YES | GOOD | YES | YES | 28 |
| **pip** | YES | YES | YES | YES | GOOD | YES | YES | 52 |
| **punk_king** | YES | YES | YES | YES | GOOD | YES | YES | 58 |
| **rust** | YES | YES | YES | YES | GOOD | YES | YES | 46 |
| **smog** | YES | YES | YES | YES | GOOD | YES | YES | 58 |
| **sparks** | YES | YES | YES | YES | GOOD | YES | YES | 57 |
| **soup_box** | YES | — | — | — | — | — | HOLD | — |

### Key Learnings

1. **FBX throughout** — GLB export loses weight data. Use FBX from UniRig output through kart assembly.
2. **UniRig bone counts vary** — 28, 46, 52, 57, 58 bones depending on character mesh complexity. Each has different bone numbering.
3. **Arm posing must be manual** — UniRig bone local axes are arbitrary. Euler rotations produce unpredictable results. Each character needs a manual Blender posing session.
4. **Boot sole cleanup needed for all** — Hunyuan3D generates ground shadow artifacts. Delete downward-facing faces in bottom 8%, flat cut bottom 4%, and fill holes.
5. **Weight cleanup** — Remove arm bone weights from below-hip vertices to prevent pants moving with arms.
6. **Crank failed** — Stocky body shape confused UniRig's ML skinning. Needs re-run or manual weight painting.
7. **Kart front = +Y** in Blender. Characters face +Y from Hunyuan3D. No rotation needed.
8. **Blender top view: +Y = top of screen** (standard math convention).
9. **`transform_apply(rotation=True)` doesn't work on armatures** — apply manually.

### What Needs To Happen Next

#### 1. Hand Off to Soapbox Unity
All kart pose data is captured in `kart-assembly-ralph/scripts/batch_assemble.py`.
Export assembled FBX files and copy to `soapbox-unity/Assets/Models/Characters/`.
This should be done inside the soapbox-unity project folder.

#### 2. Fix Unity Integration
- Kart FBX orientation (facing sky) — pre-existing issue
- Driver GLB not visible — AttachDriverModel() needs debugging
- No textures on geometry-only meshes — need materials in Unity

#### 3. Crank Weight Fix
Re-run UniRig on cleaner mesh or manual weight paint. Stocky body shape confused ML skinning.

#### 4. Soup Box
Barrel body needs special handling — skip standard humanoid rigging pipeline.

#### 5. Pipeline Improvements
- Switch to FBX throughout (not GLB) to preserve weight data
- Add boot cleanup to batch_unirig.py as automated step
- Add weight cleanup (arm weights from pants) as automated step

### Key File Locations

| File | Purpose |
|------|---------|
| `kart-assembly-ralph/scripts/batch_assemble.py` | All 8 character pose data + batch assembly script |
| `autorig-ralph/output/{id}/weighted/{id}_skinned.fbx` | UniRig skinned FBX per character (USE THIS, not GLB) |
| `autorig-ralph/output/{id}/rigged/{id}-rigged-tpose.glb` | Exported rigged GLB (weight data may be incomplete) |
| `art-to-rig-ralph/output/final/{id}_kart/{id}_kart_blender.glb` | Kart models |
| `character-ralph/output/{id}/fullbody/fullbody.png` | 2D T-pose art per character |
| `character-ralph/output/{id}/3d/character-raw.glb` | Raw Hunyuan3D mesh |
| `kart-assembly-ralph/output/player_in_kart_v3.glb` | Player assembled in kart |
