# Tile / texture foundation LoRAs — spec (Phase TX) — SDXL edition

Two **material/texture-aesthetic SDXL LoRAs** that feed the seamless-texture
generation path:

| LoRA | Trigger | Teaches | Source (CC0) | Tasks |
|------|---------|---------|--------------|-------|
| `mat_tile` | `mat_tile` | PBR material surfaces, flat even top-down light | Poly Haven albedo maps | TX1-TX4 |
| `tile_topdown` | `tile_topdown` | top-down RPG game tiles | Kenney / OpenGameArt | TX5-TX8 |

This spec is the contract for TX1-TX8. **It supersedes the Flux-specific
version**: the previous spec targeted the ai-toolkit Flux harness, but the
seamless-tiling machinery cannot patch Flux at all (Section 2), so the tile
LoRAs are SDXL — trained with kohya sd-scripts, deployed into the *existing*
SDXL `generate_texture_tile.json` workflow.

---

## 1. The core insight — the LoRA does NOT make a texture tile

> **Seamlessness is a mechanical property of the convolutions, not something a
> LoRA learns.** A LoRA biases *what* the model paints; it cannot guarantee that
> the left edge of the image continues into the right edge.

Tiling comes from **`ComfyUI-seamless-tiling`** (installed at
`D:\Projects\ComfyUI\custom_nodes\ComfyUI-seamless-tiling`), which monkey-patches
every `torch.nn.Conv2d` in the model (and optionally the VAE) to use **circular
padding**. A feature that runs off the right edge wraps back in on the left, so
denoiser + decoder produce an image whose opposite edges are continuous.

The nodes (verified class names from `SeamlessTile.py`):

| Node | Class | What it does |
|------|-------|--------------|
| **Seamless Tile** | `SeamlessTile` | `(model, tiling, copy_model) -> MODEL`. Patches the UNet Conv2d to circular. Use `tiling=enable` for full 2D. |
| **Circular VAE Decode (tile)** | `CircularVAEDecode` | Same circular patch on the VAE at decode — without it the VAE re-introduces a seam. |
| **Make Circular VAE** | `MakeCircularVAE` | Alternative: patch the VAE up front, feed a normal `VAEDecode`. |
| **Offset Image** | `OffsetImage` | Rolls the image so the seam lands centre-frame — the standard way to *see* seamlessness. |

**Both** the model patch **and** the VAE patch are required; patching only one
leaves a visible seam.

### So what is the LoRA *for*?

- **Even lighting** — no directional shadows, hotspots, or vignetting.
  Directional light is the #1 enemy of tiling: a brightness gradient makes a
  dark-meets-light seam that circular padding cannot hide. Training on evenly-
  lit albedo crops biases the model to *paint* even light.
- **Material identity** — "brick", "cobblestone", "wood planks" rendered as a
  flat top-down surface, not a 3/4 hero shot with perspective.

Mental model: **LoRA = clean, flat, evenly-lit material → seamless nodes = wrap
it into a tile.** Each does half the job.

---

## 2. Why SDXL and not Flux

**Flux cannot tile through this machinery.** `SeamlessTile` works by patching
`torch.nn.Conv2d` padding to circular — SDXL's UNet is convolutional end to
end, so the patch reaches every spatial operation. **Flux is a DiT
(transformer): it has no Conv2d in the denoising path to patch** — attention
over patch tokens has no padding mode, so circular padding has nothing to hook
into, and the Flux graph produces non-tiling output no matter what the LoRA
does. (This is also why the previous Flux spec's deploy section had to invent
a new workflow: a dead end, now removed.)

Consequences:
- Tile LoRAs are **SDXL** (`sd_xl_base_1.0.safetensors` — already local at
  `D:\Projects\ComfyUI\models\checkpoints\`, do not re-download).
- The **existing** `workflows/mcp/generate_texture_tile.json` (SDXL +
  SeamlessTile + CircularVAEDecode) is the deploy target, extended with a
  `LoraLoader` (TX4) — no new workflow needed.
- The ai-toolkit Flux harness (`launch_train.py`, `configs/*.json`) is NOT
  used here; SDXL LoRAs train with **kohya sd-scripts** (Section 5).
  `prep_dataset.py` and `eval/tile_edge_mad.py` are trainer-agnostic
  (Pillow/NumPy only) and are reused as-is.

---

## 3. Triggers & caption templates

Captions are **short and trigger-anchored** — flat surfaces, so the verbose
Florence2 captioner is the wrong tool (it hallucinates objects/scenes). Short
natural tags suit SDXL's text encoders well.

**mat_tile:**
```
mat_tile, <material>, seamless texture, even top-down lighting
```
e.g. `mat_tile, red brick wall, seamless texture, even top-down lighting`
     `mat_tile, mossy cobblestone, seamless texture, even top-down lighting`

**tile_topdown:**
```
tile_topdown, <terrain> tile, top-down RPG tileset, seamless texture, even lighting
```
e.g. `tile_topdown, grass tile, top-down RPG tileset, seamless texture, even lighting`

Rules:
- Trigger word **first**, always.
- One `<material>`/`<terrain>` noun phrase — family + one-word qualifier.
- The "seamless texture" / "even lighting" tokens are constant anchors.
- `--caption_dropout_rate 0.05` keeps the trigger from over-fitting.

**Generation prompt (use time)** mirrors the caption. Recommended LoRA
strength **0.8** (sweep 0.6-1.0 in eval).

---

## 4. Dataset sourcing — CC0 ONLY

Both datasets are **CC0 / public-domain only** — these LoRAs may feed shippable
game assets. ~30-50 images each is enough for a focused aesthetic LoRA.

### mat_tile — Poly Haven (CC0)
- **Source:** <https://polyhaven.com/textures> — all Poly Haven assets are CC0.
- **What:** the **albedo/diffuse** map only (not normal/roughness) — colour
  surface, unlit. Poly Haven textures are captured flat and already tileable:
  exactly the aesthetic to learn. 2k JPG downscaled to 1024 beats native 1k.
- **Families:** brick, stone, cobblestone, wood, planks, bark, metal, concrete,
  plaster, fabric, dirt, sand, rock, grass, tiles (~3-5 each).
- **How:** `scripts/train_lora/fetch_polyhaven_mat_tile.py` (Poly Haven REST
  API; audits family labels — keyword auto-bucketing mislabels ~30%, correct
  by slug before captioning). TX1 (done, user-approved): 55 images, 17
  families, manifest at `pipelines/tileset-ralph/loras/mat_tile/mat_tile_manifest.md`.

### tile_topdown — Kenney + OpenGameArt (CC0)
- **Kenney:** <https://kenney.nl/assets> (all CC0) — top-down/roguelike/RPG
  terrain packs. **OpenGameArt:** <https://opengameart.org> — **CC0 facet
  only** (OGA hosts mixed licenses).
- **What:** terrain tiles / seamless terrain textures — grass, dirt, water,
  sand, stone floor, path, cliff, snow. Slice tilesheets into per-tile crops.
- **Resolution:** SDXL trains at 1024. 16-32px pixel-art tiles are too small —
  prefer high-res seamless terrain textures; pixel-art *aesthetic* fine,
  pixel-art *size* not.

**Every source asset is recorded in the per-LoRA manifest** (filename → slug →
URL → CC0 → material tag). Provenance is what makes the output shippable.
**The prepped dataset contact sheet gets user approval before training**
(lessons/perceptual-ground-truth-needs-human-signoff — training data is ground
truth).

---

## 5. Hyperparameters — kohya sd-scripts SDXL recipe

**Trainer (TX0b — installed 2026-06-30, venv rebuilt + verified 2026-07-16):**
- sd-scripts at `E:\ai-training\sd-scripts`, own venv at
  `E:\ai-training\sd-scripts\venv` (torch 2.4.0+cu124, CUDA verified on the
  3090 Ti). Do NOT mix with the ComfyUI or ai-toolkit venvs.
- History: the 2026-06-30 install completed but pulled numpy 2.x (breaks
  torch 2.4 imports) and its venv was later deleted (disk cleanup). The
  2026-07-16 rebuild pins `numpy<2` (install_sd_scripts.sh step 4b). If the
  venv ever vanishes again, re-run `bash E:/ai-training/install_sd_scripts.sh`
  — idempotent, caches wheels on E:.
- Entry point: `sdxl_train_network.py`. Base model: the LOCAL
  `D:\Projects\ComfyUI\models\checkpoints\sd_xl_base_1.0.safetensors`.
- Re-verify any time:
  `E:/ai-training/sd-scripts/venv/Scripts/python.exe -c "import torch; print(torch.cuda.is_available())"`

| Setting | Value | Flag |
|---------|-------|------|
| Network | LoRA rank 16 / alpha 16 | `--network_module networks.lora --network_dim 16 --network_alpha 16` |
| Steps | **1500** (55 imgs × 3 repeats ≈ 9 epochs @ batch 1) | `--max_train_steps 1500 --save_every_n_steps 250` |
| LR | **1e-4** | `--learning_rate 1e-4` |
| Optimizer | **AdamW8bit** | `--optimizer_type AdamW8bit` |
| Resolution | **1024 (SDXL-native, single res)** | in dataset toml |
| Precision | bf16 train, fp16 save | `--mixed_precision bf16 --save_precision fp16` |
| Memory | gradient checkpointing + cached latents | `--gradient_checkpointing --cache_latents --cache_latents_to_disk` |
| Captions | .txt, dropout 0.05 | `--caption_extension .txt --caption_dropout_rate 0.05` |
| Output | `E:\ai-training\sdxl-output\<name>\` | `--output_dir ... --output_name <name>` |

**Hardware contract:** train on **GPU 1 (3090 Ti, 24GB)** —
`CUDA_DEVICE_ORDER=PCI_BUS_ID` + `CUDA_VISIBLE_DEVICES=1`. Generation and
training are sequential: **stop ComfyUI before training, restart with
`run_3090ti.ps1` after.** Everything heavy stays on E:.

### Dataset config (`E:\ai-training\sdxl-output\<name>\dataset.toml`)

```toml
[general]
enable_bucket = false
caption_extension = ".txt"

[[datasets]]
resolution = 1024
batch_size = 1

  [[datasets.subsets]]
  image_dir = "E:/ai-training/datasets/mat_tile"
  num_repeats = 3
```

### Command (per LoRA — substitute `<name>`)

```bash
# STOP ComfyUI first (frees the 24GB).
cd /e/ai-training/sd-scripts
export CUDA_DEVICE_ORDER=PCI_BUS_ID CUDA_VISIBLE_DEVICES=1
venv/Scripts/accelerate.exe launch --num_cpu_threads_per_process 4 sdxl_train_network.py \
  --pretrained_model_name_or_path "D:/Projects/ComfyUI/models/checkpoints/sd_xl_base_1.0.safetensors" \
  --dataset_config "E:/ai-training/sdxl-output/<name>/dataset.toml" \
  --output_dir "E:/ai-training/sdxl-output/<name>" --output_name <name> \
  --network_module networks.lora --network_dim 16 --network_alpha 16 \
  --learning_rate 1e-4 --optimizer_type AdamW8bit \
  --max_train_steps 1500 --save_every_n_steps 250 \
  --mixed_precision bf16 --save_precision fp16 \
  --gradient_checkpointing --cache_latents --cache_latents_to_disk \
  --caption_extension .txt --caption_dropout_rate 0.05
# Restart ComfyUI (run_3090ti.ps1), then eval (Section 6).

# Deploy — copy the winning checkpoint + trigger sidecar.
cp "E:/ai-training/sdxl-output/<name>/<name>.safetensors" \
   "D:/Projects/ComfyUI/models/loras/style/<name>.safetensors"
#  + write <name>.txt sidecar: "trigger <trigger>, strength 0.8".
```

---

## 6. Eval method — seamless validation + edge MAD

A tile LoRA passes only if **both halves work**: right material aesthetic AND
seamless output through the circular-padding path.

### 6a. 2D quality grid (LoRA working)
Generate **base vs LoRA** at fixed seed across strengths **0.6 / 0.8 / 1.0**
through the SDXL `generate_texture_tile.json` graph (SeamlessTile +
CircularVAEDecode enabled) with the `LoraLoader` inserted (TX4). Judge: flatter,
more evenly-lit, more on-material than base? Record winner in
`eval/<name>_grid.md`.

### 6b. Seamlessness — wrap-edge MAD < 5%
`eval/tile_edge_mad.py` (written in TX3, trainer-agnostic, reused by TX7):

> **Wrap-edge MAD** = mean absolute difference between each border row/column
> and the row/column it wraps onto, as a % of channel range (0-255). For image
> `I` (H×W, averaged over RGB):
> - Horizontal seam: `mean(|I[:, 0] − I[:, W-1]|)`
> - Vertical seam: `mean(|I[0, :] − I[H-1, :]|)`
> - **edge_MAD% = 100 × (horiz + vert) / 2 / 255**
>
> Seamless → **edge_MAD < 5%**. Non-tiling → typically 10-40%.

The script also renders **2×2 and 4×4 mosaics** (`np.tile`) and an
`OffsetImage`-style 50% roll so any seam lands centre-frame. Numbers + mosaics
go in the eval doc.

**Pass criteria:** (1) grid winner visibly flatter/on-material vs base;
(2) `edge_MAD < 5%` at the winner, confirmed in the 2×2/4×4 mosaics.
**Control:** same prompt/seed with tiling `disable` must score HIGH edge_MAD —
proving the metric and the seamless nodes both work.

---

## 7. Task map (Phase TX in plan.md)

| Task | Deliverable | Status |
|------|-------------|--------|
| TX0 | this spec (SDXL rewrite) | this doc |
| TX0b | kohya sd-scripts installed + verified on E:, GPU 1 | **done 2026-07-16** (rebuilt with numpy<2 pin, see §5) |
| TX1 | `mat_tile` dataset + manifest | **done, user-approved 2026-07-16** (55 imgs, 17 families) |
| TX2 | train `mat_tile` SDXL LoRA → checkpoints on E: | pending |
| TX3 | eval `mat_tile` → `eval/tile_edge_mad.py` + `eval/mat_tile_grid.md` | pending |
| TX4 | deploy `mat_tile` + add LoraLoader to `generate_texture_tile.json` | pending |
| TX5 | `tile_topdown` dataset + manifest | pending |
| TX6 | train `tile_topdown` | pending |
| TX7 | eval `tile_topdown` (reuse tile_edge_mad.py) | pending |
| TX8 | deploy `tile_topdown` + document both in README | pending |
