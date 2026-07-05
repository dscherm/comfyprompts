# Character Batch Resume — pip / punk_king / rust (written 2026-07-05, pre-compaction)

Resume doc for the `/character-pipeline` batch. Read this + invoke the
`character-pipeline` skill; it has every command and gate. The Rookie
(player_char) is DONE end-to-end and is the reference implementation.

## WHERE WE ARE (the moment of compaction)

**In flight:** background job queueing THREE TRELLIS `MeshOnly_MultiView`
mesh generations (seed 12345), prefixes `pip_MV`, `punk_king_MV`, `rust_MV`.
Outputs will land as `D:/Projects/ComfyUI/output/<name>_MV_*.glb`.
If they aren't on disk when resuming, re-run per character:

```
py -3.11 pipelines/art-to-rig-ralph/scripts/trellis_queue.py \
  --workflow MeshOnly_MultiView --front <name>_T_front.png \
  --back <name>_T_back.png --prefix <name>_MV --seed 12345
```

**Why we restarted from images:** the first batch used single-view,
arms-angled, spread-finger sources (`var_*_fullbody`). Meshes/textures were
OK but two of three AccuRIG rigs came back shredded and the T-poses were
never clean. New canonical inputs are generated and staged in
`D:/Projects/ComfyUI/input/`:
`pip_T_front/back.png`, `punk_king_T_front/back.png`, `rust_T_front/back.png`.

**The winning image recipe** (mv_ortho LoRA, use for the remaining 5 chars too):
- tool `generate_image_lora`, lora `style/mv_ortho.safetensors`, **strength 1.0**,
  768×1024, fixed seeds (used 1103/1104 pip, 1105/1141-view punk_king, 1113/1115 rust)
- prompt: `mv_ortho, front view, wide T-pose, arms outstretched horizontally at
  shoulder height, hands clenched into fists, legs apart, <desc>, plain neutral
  background, strict letter-T pose with both arms straight out horizontal`
  (back views: `back view, seen directly from behind` + `face` in negatives)
- negative: `open palms, spread fingers, arms lowered, arms at sides, A-pose`
- Bulky characters (rust) fight the T prior — shorten the outfit description,
  keep pose tokens first AND last, and reroll seeds; judge every image before use.
- Character descriptions: `output/intake/characters-intake.json`.

## NEXT STEPS (skill phases, per character)

1. **Phase-1 gate** on the new meshes: identity + hand close-up renders →
   show user. Fists should reconstruct clean (Rookie precedent).
2. **Phase 2**: `prep_character.py` (NOT mesh_prep.py) → `output/prepared/<name>_v1_prepared.glb`.
3. **Phase 3**: `trellis_queue.py --workflow MeshTexturing_MultiView --front
   <name>_T_front.png --back <name>_T_back.png --mesh <full-res _MV glb>
   --prefix <name>_Textured --seed 12345` (front+back this time).
4. **Phase 4**: `uv_and_bake.py` (metallic-zeroed diffuse bake — fixed) →
   albedo + previews + `<name>_for_accurig.obj`. SHOW PREVIEWS (gate).
   Copy albedo → `soapbox-unity/Assets/Animations/<name>/Source/<name>_albedo.png`
   (overwrites the stale first-batch albedos already there).
5. **Phase 5 (USER)**: AccuRIG per char → export FBX to
   `soapbox-unity/Assets/Animations/<name>/Source/<name>_accurig.fbx`.
   **Export-pose trap (cost us 2 rigs):** if AccuRIG previewed a motion or is
   in "current pose", the FBX binds shredded. Export in bind/T-pose only.
   Gate EACH immediately: `check_accurig_fbx.py` must print `ACCURIG_FBX OK`
   (good ref: Rookie spread 1.97, pip-old 3.73; threshold 4.0; shredded = 7-19).
6. **Phase 6**: Unity tools ALREADY COMMITTED for all three
   (`Tools ▸ Pip / PunkKing / Rust` — Setup Humanoid Import → Build Animator →
   Assign Texture → Validate Humanoid (strict)). Validation report readable at
   `%LOCALAPPDATA%/Unity/Editor/Editor.log`. RESULT: PASS required per char.
7. **Phase 7**: package `output/final/<name>/` (model: player_char's
   ASSET-CARD.md) + commit both repos — **always commit with explicit
   pathspec** (a parallel session stages unrelated kit work).

## STATE NOTES

- **Rookie/player_char: COMPLETE + validated PASS** (textured, rigged,
  animated). Unity `dbfd57f`, toolchain `4a078a9`/`78b51d0→4a078a9` fixed.
- **Old first-batch artifacts** (single-view meshes `Pistol_0000{2,3,4}_`,
  their prepared/textured/albedo files, pip's old PASSING `pip_accurig.fbx`,
  punk_king/rust's SHREDDED FBXs) are superseded once the new meshes pass —
  overwrite paths as the new runs produce files; pip's old rig FBX must also
  be replaced (it rigs the OLD mesh).
- **Unity is open** on soapbox-unity usually; headless Unity batch requires
  it closed. Menu clicks by user are the normal path (coplay needs a session
  started while Unity+Coplay are up).
- Task list in-session: phases tracked as tasks #1-#7 (restarted upstream at
  image gen; old #1-#4 completions refer to the superseded first batch).
- Remaining 5 Soapbox characters (bones, crank, grit, smog, sparks) follow
  the same recipe when the user asks; kart assets already exist for all.

## KEY COMMITS (this arc)

- `a282830` /character-pipeline skill + trellis_queue/uv_and_bake/check_accurig_fbx
- `8343905` prep_character.py + metallic-zeroed bake + skill phase-2 fix
- `39785b8` (soapbox-unity) editor tools ×3 chars; `fed7c0c` texture tool;
  `ea70ac8` Animator builder + acrobatic §5; `dbfd57f` Rookie textured package
- Retarget fixes arc (previz path): `ed35aee`, `a22947f`, `4f0eb49`, `5cccbe3`, `eeef910`

## RELEVANT MEMORIES / LESSONS

`project-accurig-input-format` (OBJ in cm WITH UVs), `project_mv_ortho_fists`,
`project_mv_ortho_lora`, `project-unirig-mirrored-side-labels`,
`unirig-skin-weights-melt-use-accurig`, `hand-rolled-retarget-limb-plane`,
`unity-humanoid-bone-roll-normalize`.
