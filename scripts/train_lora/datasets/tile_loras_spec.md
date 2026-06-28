# Tile / texture foundation LoRAs — spec (Phase TX)

Two **material/texture-aesthetic Flux LoRAs**, trained with the existing
`scripts/train_lora/` harness, that feed the seamless-texture generation path:

| LoRA | Trigger | Teaches | Source (CC0) | Tasks |
|------|---------|---------|--------------|-------|
| `mat_tile` | `mat_tile` | PBR material surfaces, flat even top-down light | Poly Haven albedo maps | TX1-TX4 |
| `tile_topdown` | `tile_topdown` | top-down RPG game tiles | Kenney / OpenGameArt | TX5-TX8 |

This spec is the contract for TX1-TX8. It captures the proven recipe (identical to
`mv_ortho` / `grimforge_style`), the dataset/caption conventions, and — most importantly
— **what a LoRA can and cannot do for tiling**.

---

## 1. The core insight — the LoRA does NOT make a texture tile

> **Seamlessness is a mechanical property of the convolutions, not something a LoRA
> learns.** A LoRA biases *what* the model paints; it cannot guarantee that the left
> edge of the image continues into the right edge.

Tiling comes from **`ComfyUI-seamless-tiling`** (installed at
`D:\Projects\ComfyUI\custom_nodes\ComfyUI-seamless-tiling`), which monkey-patches every
`torch.nn.Conv2d` in the model (and optionally the VAE) to use **circular padding**
instead of the default zero/constant padding. With circular padding, a feature that runs
off the right edge wraps back in on the left, so the denoiser and decoder produce an
image whose opposite edges are continuous — i.e. it tiles.

The nodes (verified class names from `SeamlessTile.py`):

| Node | Class | What it does |
|------|-------|--------------|
| **Seamless Tile** | `SeamlessTile` | `(model, tiling, copy_model) -> MODEL`. Patches the UNet/transformer Conv2d to circular. `tiling` ∈ `enable / x_only / y_only / disable`. Use `enable` for full 2D tiling. |
| **Circular VAE Decode (tile)** | `CircularVAEDecode` | `(samples, vae, tiling) -> IMAGE`. Same circular patch applied to the VAE before decode — without this the VAE re-introduces a seam at decode time. |
| **Make Circular VAE** | `MakeCircularVAE` | `(vae, tiling, copy_vae) -> VAE`. Alternative: patch the VAE up front and feed it to a normal `VAEDecode`. |
| **Offset Image** | `OffsetImage` | `(pixels, x_percent, y_percent) -> IMAGE`. Rolls the image so the *seam moves to the centre* — the standard way to *see* whether a tile is truly seamless. |

**Both** `SeamlessTile` (model) **and** `CircularVAEDecode`/`MakeCircularVAE` (VAE) are
required. Patching only one leaves a visible seam.

### So what is the LoRA *for*?

The LoRA teaches the **material aesthetic + flat, even, top-down lighting**:

- **Even lighting** — no directional shadows, no hotspots, no vignetting. Directional
  light is the #1 enemy of tiling: a gradient across the tile makes a dark-meets-light
  seam when wrapped, which circular padding cannot hide. Training on evenly-lit,
  flat-lit albedo crops biases the model to *paint* even light, giving the seamless
  machinery clean input.
- **Material identity** — "brick", "cobblestone", "wood planks", "grass tile" rendered
  as a top-down flat surface, not a 3/4 hero shot with perspective.

Mental model: **LoRA = clean, flat, evenly-lit material → seamless nodes = wrap it into a
tile.** Each does half the job.

---

## 2. Deploy constraint — Flux LoRA, NOT the existing SDXL workflow

The harness trains **Flux** LoRAs (`black-forest-labs/FLUX.1-dev`, rank-16). The existing
`workflows/mcp/generate_texture_tile.json` is an **SDXL** graph
(`sd_xl_base_1.0.safetensors` + `LoraLoader`). **A Flux LoRA cannot be loaded into an SDXL
workflow** — different architecture, different tensor names; `LoraLoader` will error or
no-op.

Therefore TX4/TX8 author a **new Flux + seamless** workflow rather than reusing the SDXL
one. Target graph:

```
UNETLoader/CheckpointLoader (flux1-dev-fp8)
        │ MODEL                          ┌── CLIP ── CLIPTextEncode (PARAM_PROMPT)
        ▼                                │
   LoraLoader (PARAM_STR_LORA_NAME, strength)   (mat_tile / tile_topdown)
        │ MODEL
        ▼
   SeamlessTile  tiling=enable           ← makes the denoiser tile
        │ MODEL
        ▼
   KSampler (flux: sampler/scheduler, low CFG ~1, ~20 steps)
        │ LATENT
        ▼
   CircularVAEDecode  tiling=enable      ← makes the VAE tile (no seam at decode)
        │ IMAGE
        ▼
   SaveImage
```

`flux1-dev-fp8.safetensors` already exists at
`D:\Projects\ComfyUI\models\checkpoints\` (see CLAUDE.md). The existing SDXL
`generate_texture_tile` workflow stays as-is for SDXL users; the Flux one is additive.

---

## 3. Triggers & caption templates

Captions are **short and trigger-anchored** — these are flat surfaces, so the verbose
Florence2 captioner used for character datasets is the wrong tool (it would hallucinate
objects/scenes). Hand-write or template the captions instead.

**mat_tile:**
```
mat_tile, <material>, seamless texture, even top-down lighting
```
e.g. `mat_tile, red brick wall, seamless texture, even top-down lighting`
     `mat_tile, mossy cobblestone, seamless texture, even top-down lighting`
     `mat_tile, weathered wood planks, seamless texture, even top-down lighting`

**tile_topdown:**
```
tile_topdown, <terrain> tile, top-down RPG tileset, seamless texture, even lighting
```
e.g. `tile_topdown, grass tile, top-down RPG tileset, seamless texture, even lighting`
     `tile_topdown, water tile, top-down RPG tileset, seamless texture, even lighting`
     `tile_topdown, dirt path tile, top-down RPG tileset, seamless texture, even lighting`

Rules:
- Trigger word **first**, always.
- One `<material>`/`<terrain>` noun phrase — keep it to the family + a one-word
  qualifier (colour/condition). Don't over-describe.
- The "seamless texture" / "even lighting" tokens are constant — they anchor the
  aesthetic the LoRA should associate with the trigger.
- `caption_dropout_rate: 0.05` (harness default) keeps the trigger from over-fitting.

**Generation prompt (at use time)** mirrors the caption:
```
mat_tile, <material>, seamless texture, even top-down lighting
```
Recommended LoRA strength **0.8** (0.6-1.0), same as the other style LoRAs.

---

## 4. Dataset sourcing — CC0 ONLY

Both datasets are **CC0 / public-domain only** — these LoRAs may feed shippable game
assets, so no non-commercial or attribution-encumbered sources. ~30-50 images each is
enough for a focused aesthetic LoRA (cf. the 125-image `mv_ortho` and 148-image
`berserkr_style` runs; material aesthetics need fewer because the subject is narrow).

### mat_tile — Poly Haven (CC0)
- **Source:** <https://polyhaven.com/textures> — *all* Poly Haven assets are CC0.
- **What to grab:** the **albedo / diffuse** map of each texture (NOT normal/roughness/
  displacement — we want the colour surface, evenly lit). Poly Haven textures are already
  captured flat and tileable, which is exactly the aesthetic we want the LoRA to learn.
- **Families to cover** (aim for a spread, ~3-5 each): brick, stone/rock, cobblestone,
  wood planks, bark, concrete, metal/rusted metal, fabric/leather, ground/dirt/mud,
  sand, gravel, grass, tiles/pavers.
- **How:** `blender-mcp` `download_polyhaven_asset` (asset_type `textures`,
  resolution `1k` or `2k`, file_format `jpg`/`png`) writes maps into Blender's texture
  dir; OR fetch the albedo JPGs directly from the Poly Haven file CDN over HTTP. Keep
  only the `*_diff_*` / `*_albedo_*` map per asset.

### tile_topdown — Kenney + OpenGameArt (CC0)
- **Kenney:** <https://kenney.nl/assets> — Kenney packs are CC0. Use the top-down /
  roguelike / RPG terrain tile packs (e.g. "Roguelike/RPG", "Tiny Town", "Map Pack").
- **OpenGameArt:** <https://opengameart.org> — **filter to the CC0 license facet only**
  (OGA hosts mixed licenses; CC-BY / GPL assets are excluded here). Search "seamless
  tile" / "top down terrain" / "tileset".
- **What to grab:** individual terrain tiles or seamless terrain textures — grass, dirt,
  water, sand, stone floor, path/road, cliff, snow. If a pack is a tilesheet, slice it
  into per-tile crops (or pick the large seamless terrain textures, which suit Flux's
  ≥512px training better than 16px sprites).
- **Resolution note:** Flux trains at 512/768/1024. Tiny pixel-art tiles (16-32px) are
  too small — prefer the higher-res seamless terrain textures, or upscale a clean
  pixel tile only if it stays crisp. Pixel-art *aesthetic* is fine; pixel-art *size* is
  not.

**Every source asset is recorded in the per-LoRA manifest** (`mat_tile_manifest.md`,
`tile_topdown_manifest.md`) with: filename → source name/slug → URL → license (CC0) →
material/terrain tag. This is the provenance record that makes the output shippable.

---

## 5. Hyperparameters — reuse the proven recipe verbatim

Identical to `configs/mv_ortho.json` / `configs/grimforge_style.json`. `launch_train.py`
already encodes these as defaults; do not deviate.

| Setting | Value | Note |
|---------|-------|------|
| Base model | `black-forest-labs/FLUX.1-dev` (fp8, `quantize: true`) | local fp8 ckpt, no 24GB re-download |
| Network | LoRA, `linear: 16`, `linear_alpha: 16` | rank 16 / alpha 16 |
| Steps | **1500** | `save_every: 250`, keep last 4 |
| LR | **1e-4** | |
| Optimizer | **adamw8bit** | |
| Noise scheduler | **flowmatch** | |
| EMA | **on, decay 0.99** | |
| Resolutions | **[512, 768, 1024]** | multi-res (grimforge used all three) |
| train_unet | true | `train_text_encoder: false` |
| gradient_checkpointing | true | |
| dtype | bf16 | save dtype float16 |
| caption_ext | txt | `caption_dropout_rate: 0.05`, `shuffle_tokens: false` |
| cache_latents_to_disk | true | to E: (C:/D: nearly full) |

**Hardware contract** (see CLAUDE.md + README "Hardware contract"):
- Train on **GPU 1 (RTX 3090 Ti, 24GB)** — `launch_train.py --cuda-device 1` sets
  `CUDA_VISIBLE_DEVICES=1` so ai-toolkit sees only the 3090 Ti as `cuda:0`.
- **Generation and training are sequential** — both want the 24GB. **Stop ComfyUI
  before launching training** (free the VRAM), **restart it after** (`run_3090ti.ps1`).
- Output + HF cache live on **E:** (`E:\ai-training\flux-output`, `E:\ai-training\hf-cache`).
- ai-toolkit venv: `D:\Projects\ai-toolkit\venv` (separate from ComfyUI's — do not cross).

### Commands (per LoRA — substitute `<name>`/`<trigger>`)

```bash
# 1. Prep — normalize CC0 crops into an ai-toolkit training folder (no GPU).
python scripts/train_lora/prep_dataset.py \
    --src "<downloaded CC0 maps dir or glob>" \
    --out "E:/ai-training/datasets/<name>" \
    --max-edge 1024

# 2. Caption — SHORT, trigger-anchored (hand-written/templated, NOT Florence2).
#    Write each <stem>.txt as: "<trigger>, <material>, seamless texture, even ... lighting"
#    (caption.py's Florence2 path is for character sets; tiles use templated captions.)

# 3. Train — STOP ComfyUI first to free the 24GB.
python scripts/train_lora/launch_train.py \
    --dataset "E:/ai-training/datasets/<name>" \
    --name <name> --trigger <trigger> \
    --steps 1500 --rank 16 --resolutions 512,768,1024 --cuda-device 1
#    (writes configs/<name>.json + launches on GPU 1; verify with nvidia-smi)

# 4. Restart ComfyUI (run_3090ti.ps1), then eval (Section 6).

# 5. Deploy — copy the winning checkpoint + write a trigger sidecar.
cp "E:/ai-training/flux-output/<name>/<name>.safetensors" \
   "D:/Projects/ComfyUI/models/loras/style/<name>.safetensors"
#    + write <name>.txt sidecar: "trigger <trigger>, strength 0.8".
```

---

## 6. Eval method — seamless validation + edge MAD

A tile LoRA passes only if **both halves work**: the LoRA reads as the right material
*and* the output tiles seamlessly through the circular-padding path. Two checks:

### 6a. 2D quality grid (LoRA working)
Generate **base vs LoRA** at fixed seed across strengths **0.6 / 0.8 / 1.0** on material/
terrain prompts, through the **Flux + SeamlessTile + CircularVAEDecode** path (Section 2).
Judge: does the LoRA produce a flatter, more evenly-lit, on-aesthetic material surface
than base? Pick the winning `(checkpoint, strength)`. Record in
`eval/<name>_grid.md` (same format as `eval/mv_ortho_grid.md`).

### 6b. Seamlessness — wrap-edge MAD < 5% (seamless machinery working)
`eval/tile_edge_mad.py` (written in TX3, reused by TX7) measures how continuous the
opposite edges are:

> **Wrap-edge MAD** = the mean absolute difference between each border row/column and the
> row/column it wraps onto, expressed as a percentage of the channel value range (0-255).
>
> For an image `I` of height `H`, width `W`, averaged over RGB:
> - **Horizontal seam:** `mean(|I[:, 0] − I[:, W-1]|)` — left column vs right column.
> - **Vertical seam:** `mean(|I[0, :] − I[H-1, :]|)` — top row vs bottom row.
> - **edge_MAD%** = `100 * (horiz + vert) / 2 / 255`.
>
> A truly seamless tile has near-identical wrapping edges → **edge_MAD < 5%**. A
> non-tiling image shows a hard discontinuity → typically 10-40%.

The script also **renders 2×2 and 4×4 mosaics** of the tile (`np.tile`) and an
**`OffsetImage`-style 50% roll** so the seam, if any, lands in the centre for visual
inspection. Both the numeric `edge_MAD%` and the mosaics go in the eval doc.

**Pass criteria (per LoRA):**
1. 2D grid: LoRA-on cell is visibly flatter / more even / more on-material than base.
2. `edge_MAD < 5%` at the winning cell, confirmed visually in the 2×2 and 4×4 mosaics
   (no seam line, no obvious repetition artefact at the tile boundary).

A useful control: the **same prompt/seed with `SeamlessTile`/`CircularVAEDecode` set to
`disable`** should score a *high* edge_MAD (seam present) — proving the metric and the
seamless nodes are both doing their job, and that the low score is from the circular
padding, not luck.

---

## 7. Task map (Phase TX in plan.md)

| Task | Deliverable |
|------|-------------|
| TX0 | this spec |
| TX1 | `mat_tile` dataset (~30-50 Poly Haven CC0) + `mat_tile_manifest.md` |
| TX2 | train `mat_tile` LoRA → `configs/mat_tile.json` + checkpoints on E: |
| TX3 | eval `mat_tile` → `eval/tile_edge_mad.py` + `eval/mat_tile_grid.md` |
| TX4 | deploy `mat_tile` + author `generate_texture_tile_flux` MCP workflow |
| TX5 | `tile_topdown` dataset (~30-50 Kenney/OGA CC0) + `tile_topdown_manifest.md` |
| TX6 | train `tile_topdown` LoRA → `configs/tile_topdown.json` + checkpoints |
| TX7 | eval `tile_topdown` → `eval/tile_topdown_grid.md` (reuse `tile_edge_mad.py`) |
| TX8 | deploy `tile_topdown` + document both tile LoRAs in `README.md` |
