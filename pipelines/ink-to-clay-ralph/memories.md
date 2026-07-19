# ink-to-clay-ralph — pipeline memories

Durable facts for this pipeline. Read at loop start; extend as you learn.

## Ground truth
- **This is an image→image transform, NOT text→image.** Every technique choice
  follows from that. A plain style LoRA (text→image) alone is not the deliverable.
- **The acceptance gate is the TRELLIS reconstruction (Stage 6), not the image
  looking clay-ish.** Prove the mesh via `trellis2_image_to_3d`.
- **Target-look reference:** `products/soapbox_characters_v1/concepts/*.png` — the
  clay images `soapbox_char_final_v1` + `mv_ortho` already produce.

## Dataset bootstrap (Stage 1)
- Same subject + **same seed**, two prompt scaffolds via `soapbox_char_final_v1`:
  - clay = `mv_ortho`@0.85 + char@0.65, "plain flat neutral-grey background,
    orthographic, even lighting, no cast shadow".
  - ink  = char@0.9 (no mv_ortho), "heavy black ink linework, cel shading, flat
    2D comic illustration, white background".
- Matched filenames in `{ink,clay}/<id>.png`. Clay halves alone = Approach-A set.
- Curation needs a human-approved montage before training (self-confirmation is
  not approval — see comfyui-toolchain feedback_exemplar_human_curation).

## Training (Stages 2, 4) — GPU-GATED
- FLUX LoRA: rank 16–32, LR 1e-4, 1500–3000 steps, 1024px, save every 250–500
  (char LoRA landed well ~1500). Trainer = ai-toolkit (FLUX dev + Kontext).
- **ollama and ComfyUI both grab the 3090 Ti.** Stop ComfyUI (free 24 GB) before
  training; `ollama stop` too. Restart ComfyUI via run_3090ti.ps1 after. Never
  start a train run without the human's GPU-free confirmation (project_dual_gpu).
- ai-toolkit traps: flat dataset dir (subfolders deadlock latent caching); use a
  FRESH output name (reused output folder resumes and exits in ~7 min without
  training) — see project_aitk_training_gotchas.

## Inference
- A: LoadImage(ink) → VAEEncode → KSampler(denoise 0.55–0.70, clay LoRA @ chosen
  weight) → VAEDecode; add a lineart/canny ControlNet from the ink if the
  silhouette drifts at higher denoise.
- B: FLUX Kontext graph, reference = ink, prompt = the fixed edit instruction,
  + Kontext LoRA → single pass.
- TRELLIS.2 blocks ComfyUI's HTTP server 10+ min during "Reconstructing mesh" —
  trust the job's own DONE, don't kill a busy ComfyUI (project_trellis_
  reconstruction_blocks_server). TRELLIS output ships unwelded — weld before
  smooth/decimate; feed the mesh through `scripts/mesh_product_check.py`.

## Storage
- Datasets → `E:/ai-training/datasets/ink_to_clay_v1/`; LoRAs →
  `E:/ai-training/flux-output/ink_to_clay_v1_{a,b}*`. C:/D: near-full — keep big
  files on E: (project_training_storage).
