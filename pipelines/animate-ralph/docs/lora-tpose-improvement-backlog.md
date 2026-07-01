# mv_ortho LoRA — T-pose Improvement Backlog

**Status:** backlog / not started. **Type:** quality optimization (NOT a correctness fix).

## Framing (read first)

The `mv_ortho` Flux LoRA generates a separated-limb wide-T-pose character image that
feeds Hunyuan3D → rig → Unity. The rig arrives with a slight elbow bend / non-perfect
T-pose; that is now handled **deterministically** by the rig-roll normalizer
(`pipelines/animate-ralph/tools/normalize_rig_rolls_for_unity.py`, lesson
`unity-humanoid-bone-roll-normalize`).

So the LoRA is **not** where a clean T-pose is *guaranteed* — two stochastic stages
(LoRA gen, then Hunyuan3D) sit between intent and mesh. And the LoRA's separated-limb
pose is **load-bearing** for clean Hunyuan3D reconstruction (no limb fusion) — proven
end-to-end in the M5 eval. LoRA improvement is **polish** that makes the downstream
deterministic fix cheaper (less arm rotation to correct → less AccuRIG weight stress),
always **guarded against reconstruction regression.**

## Current setup (grounded — as of 2026-06)

- **LoRA:** `mv_ortho.safetensors`, checkpoint **1500** @ strength **0.8** (winner).
  Trained output under `E:\ai-training\flux-output`.
- **Trainer/config:** **ai-toolkit** (`sd_trainer`) — `scripts/train_lora/configs/mv_ortho.json`.
  Flux LoRA **rank 16 / alpha 16**, **1500 steps**, LR **1e-4**, adamw8bit, EMA 0.99,
  res **[512,768]**, base **FLUX.1-dev**, `train_text_encoder=false`.
- **Dataset:** `E:\ai-training\datasets\mv_ortho\` — **125 imgs = 25 meshes × 5 views**
  (`scripts/train_lora/datasets/mv_ortho_manifest.md`). Rendered ortho by
  `scripts/train_lora/render_multiview.py` (blender-mcp, neutral-grey, 768px). Sources:
  Mixamo xbot + 12 Quaternius modmen + 11 modwomen + 1 own wide-T geom. Trigger `mv_ortho`.
- **Generation prompt (pose is tied to TOKENS, not the bare trigger):**
  `mv_ortho, front view, wide T-pose, arms outstretched, fingers spread, legs apart, <subject>`
  Strength: **0.8** clean characters / **0.5–0.6** styled / **1.0** stronger pose.
- **Eval harness EXISTS:** `scripts/lora_eval_grid.py` +
  `scripts/train_lora/eval/mv_ortho_grid.md` (2D grid × checkpoints × strengths **+**
  Hunyuan3D mesh-separability test **+** Opus visual judge). Reuse it — don't rebuild.
- **Quadruple LoRA stub:** `scripts/train_lora/configs/mv_ortho_quad.json` (mv_ortho is
  biped-only; quadrupeds become bipedal werewolves).

## Backlog (grounded in this session's downstream findings)

1. **Reduce the taught arm-bend / elevation (highest value).** The manifest admits a
   few refs (e.g. `modmen_master`) have **arms angled BELOW horizontal** — that is the
   likely source of the ~27° upperarm droop + slight elbow bend the rig-normalizer had
   to correct downstream. Action: audit the 25 source meshes, prefer **true-horizontal
   T-pose** refs (or drop/re-caption the below-horizontal ones), re-render, retrain.
   Success = smaller normalizer correction (see step 4), separation unchanged.

2. **Resolve fingers-spread vs closed-fists.** Current dataset+prompt use *"fingers
   spread"* (xbot); but 3D wants **closed fists** — spread fingers → webbed/bad hands in
   Hunyuan3D (`project_mv_ortho_fists`, lesson `image-to-3d-spread-fingers-bad-hands`).
   The M5 eval said fingers "render fine" in 2D — but that's 2D, not the 3D mesh hand.
   Action: A/B `fingers spread` vs `relaxed closed fists` on the *mesh hand quality*
   (not the 2D image), keeping limb separation. Possibly a small closed-fist dataset pass.

3. **Fitted-clothing default.** M5 found loose robes/capes bridge the limb gaps and
   re-fuse the mesh. Action: bake a `fitted clothing, no loose cape` hint into the
   default generation prompt / tool for riggable characters.

4. **Close the eval loop to the NEW downstream metric.** The existing eval scores 2D
   pose + mesh separability, but **not** the rig-normalizer's correction magnitude
   (new this session). Action: extend `lora_eval_grid.py` to run generated chars through
   rig + `normalize_rig_rolls_for_unity.py` and log **upperarm elevation° / elbow bend°
   corrected**. That makes "cleaner T-pose" a *measured downstream* win, not eyeballing 2D.

5. **mv_ortho_quad** — finish the quadruped LoRA (`configs/mv_ortho_quad.json` exists) so
   non-biped characters get separated-limb coverage too. Separate track.

## Guardrail (every step)

Never regress reconstruction. If a change lowers T-pose deviation but causes limb
fusion, bad hands, or worse Hunyuan3D topology, **reject it** — separated limbs are the
reason mv_ortho exists (M5 Part B/C proved it rigs cleanly with no mesh-split). Score
every candidate on BOTH axes via the existing eval + step-4 metric.
