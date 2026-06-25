# mv_ortho_quad eval — quadruped track

**Date:** 2026-06-25
**LoRA:** `mv_ortho_quad` (rank-16 Flux, 1500 steps) | **Trigger:** `mv_quad`
**Base:** `flux1-dev-fp8` | **Deployed:** `loras/style/mv_ortho_quad.safetensors` (+ `.txt`)
**Assets:** `eval/mv_quad_assets/`

## Why it exists

The humanoid `mv_ortho` forces *every* subject into a human biped T-pose — a "four-legged
wolf" prompt came out as a **bipedal werewolf** (`mv_quad_assets/before_biped_werewolf.png`).
Quadruped coverage needs its own pose concept, so this sibling LoRA was trained on
quadruped meshes.

## Dataset

48 orthographic **side + 3/4** renders of **12 Quaternius quadrupeds** (wolf, horse,
horse_white, stag, deer, fox, bull, cow, donkey, alpaca, husky, shibainu) via
`render_multiview.py`. Front views were dropped — a quadruped's narrow front silhouette
frames tiny against its body length, and side/3-4 are the useful Hunyuan3D inputs.
Captioned `mv_quad, <side|three-quarter> view, quadruped, neutral standing stance, four
legs, legs apart, <Florence>`.

## Result — PASS

Prompted at strength 0.8 (side view), all subjects render as **proper four-legged
creatures with clearly separated legs**, clean ortho profile, neutral bg:
- **wolf** (`quad_wolf.png`) — real quadruped on all fours (vs the biped werewolf before)
- **horse** (`quad_horse.png`), **stag** (`quad_stag.png`) — clean profiles, 4 distinct legs with gaps
- **dragon** (`quad_dragon.png`) — **generalized to a creature NOT in the training set**

So `mv_quad` does for quadrupeds what `mv_ortho` does for bipeds: clean separated-leg
neutral stance suitable for Hunyuan3D → riggable meshes. Closes the humanoid-only gap.

## Usage notes
- Prompt the pose tokens, not just the trigger; **side view** reads best for quadrupeds.
- Strength 0.8 for clean separation; drop to ~0.5-0.6 if a strong art style is overridden.
- Pick the right sibling: `mv_ortho` (humanoid biped) vs `mv_ortho_quad` (four-legged).

_Judge: Claude (Opus 4.8), visual comparison of the mv_quad roster vs the humanoid-LoRA werewolf._
