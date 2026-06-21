# Spec — Reusable Flux LoRA Training Harness (Berserkr-style PoC)

*Crystallized: 2026-06-20. Interactive bridge intake.*

## Goal

Stand up a **reusable LoRA-training capability** in the comfyui-toolchain, and
prove it with a proof-of-concept **Berserkr-style Flux LoRA**. The PoC validates
the *pipeline* (install trainer → curate dataset → caption → train on GPU 1 →
eval-grid → deploy), not the dataset. Once proven, the same harness retrains on
ANY image set (other styles, single-character consistency LoRAs, multiview-
consistency LoRAs that feed Hunyuan3D, etc.).

## Locked decisions (interactive intake, 2026-06-20)

- **Base model:** Flux dev (`flux1-dev-fp8.safetensors`, installed).
- **Trainer:** `ostris/ai-toolkit`, in its OWN venv (Python 3.11 + the torch it
  pins — do NOT reuse the ComfyUI venv).
- **PoC subject:** Berserkr style/aesthetic. One reusable style LoRA from
  ~100-150 curated renders across Creature/Character/Equipment. Trigger:
  `brsk_style`.
- **Tooling reusability:** build a reusable harness under `scripts/train_lora/`
  (dataset-prep + caption + train-launch + eval), parameterized by dataset dir
  so future LoRAs are one command. Not a one-off.

## Hardware contract

- **The 3090 Ti (24GB) is the primary card for BOTH generation and training.**
  ComfyUI runs on it via `D:\Projects\ComfyUI\run_3090ti.ps1`
  (`CUDA_DEVICE_ORDER=PCI_BUS_ID` + `CUDA_VISIBLE_DEVICES=1`); training also runs
  on it via `CUDA_VISIBLE_DEVICES=1`. The 3070 (8GB) is secondary.
- **They contend, so phases are sequential:** caption (T4, ComfyUI up) → STOP
  ComfyUI to free 24GB → train (T6) → restart ComfyUI → eval (T7). Flux eval is
  comfortable at 24GB.
- Verify with `nvidia-smi` that VRAM climbs on the 3090 Ti before walking away.
  16GB system RAM is the tighter constraint — cache latents/text-encoder outputs
  to disk.
- Flux LoRA config: rank 16, 512-768px, batch 1, grad-checkpoint ON,
  ~1000-2000 steps (start ~1500). Est. 1.5-2.5h.

## Reuse the existing tooling

- **Captioning:** Florence2 `caption_image` workflow (already wired, REST API).
- **Eval:** `scripts/lora_eval_grid.py` (already hardened) — fixed prompt+seed
  grid at LoRA strengths 0.6/0.8/1.0, AI-judge verdict. Pick winner by judge
  score, not loss curve.
- **Deploy target:** `D:\Projects\ComfyUI\models\loras\style\` with a sidecar
  note (trigger word + recommended strength).

## Deliverables

1. `ostris/ai-toolkit` installed in own venv, confirmed running on GPU 1.
2. `scripts/train_lora/` reusable harness: `prep_dataset.py`, `caption.py`,
   `launch_train.py`, plus a thin README documenting one-command retraining on
   any dataset.
3. A curated ~100-150-image captioned Berserkr training set (trigger
   `brsk_style`).
4. A trained `berserkr_style` Flux LoRA `.safetensors`.
5. An eval grid (base Flux vs +LoRA at 0.6/0.8/1.0) with an AI-judge verdict
   selecting the winning checkpoint/strength.
6. Winning LoRA deployed to `loras/style/` + sidecar note. README explains how
   to point the harness at a new dataset.

## Out of scope (documented in comfy-improve-model skill)

- Skeletal/game animation and rigging → `pipelines/animate-ralph/`,
  `art-to-rig-ralph/` (data/retarget problem, not training).
- Video motion LoRA (Wan/Hunyuan) → future, separate toolchain (musubi-tuner).
- Hunyuan3D/TripoSR finetuning → not done locally; 3D quality is improved
  upstream via a multiview-consistency image LoRA (same harness, different
  dataset).

## Definition of done

Eval grid shows the `brsk_style` LoRA measurably shifts output toward the
Berserkr aesthetic vs base Flux at fixed seeds, the winning LoRA is deployed,
and the harness README lets a future run retrain on an arbitrary dataset dir
without code changes.
