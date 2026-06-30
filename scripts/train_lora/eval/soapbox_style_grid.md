# soapbox_style — eval (SX3)

*2026-06-30. Base: Flux.1-dev fp8. LoRA: `soapbox_style` (rank 16, 1500 steps,
108 augmented soapboxsabatoge mascot images — low-denoise img2img from 64px
sprites). Eval = base-vs-LoRA via `generate_image_lora`, direct ComfyUI HTTP.
Tested on **NEW mascot subjects never in training** (training = skeletons + a
few animals), across strengths 0.6 / 0.8 / 1.0, fixed seed for comparability.*

## Verdict: **PASS — distinctive, clean, transferable.** Winner: **ckpt 1500 @ 0.8.**

The LoRA reliably reproduces the **gritty cartoon kart-mascot** look — thick black
outlines, flat saturated color, sticker/logo styling, dark background, character +
soapbox/go-kart racer — on **four new subjects it never saw** (robot, frog, wizard,
shark). It learned a transferable *style + composition*, not memorized characters.
This is the distinctive, ownable cartoon-mascot lane (cross-promotes the
soapboxsabatoge game).

### Base vs LoRA (subject = robot, fixed seed)
| Variant | Read | File |
|---------|------|------|
| Base (no LoRA) | Soft Pixar-ish 3D render, muted teal/orange, soft light | `base_robot` |
| **LoRA 0.8** | **Bold flat-color vector mascot, thick black outlines, sticker look** | `lora_robot_s08` |

### Strength sweep (robot, fixed seed)
| Strength | Read | File |
|----------|------|------|
| 0.6 | Full style already; slightly lighter outlines, more detail retained | `lora_robot_s06` |
| **0.8** | **Sweet spot — bold clean outlines, balanced, most legible** | `lora_robot_s08` |
| 1.0 | Strong; outlines a touch heavier / composition busier | `lora_robot_s10` |

### Cross-subject (strength 0.8 unless noted) — all on-style
| Subject | Read | File |
|---------|------|------|
| Robot | yellow-orange robot mascot, kart, thick outlines | `lora_robot_s08` |
| Frog | green frog mascot, orange kart, cracked-ground bg | `lora_frog_s08` |
| Wizard | wizard + hat + stars, orange kart, gritty cartoon | `lora_wizard_s08` |
| Shark | blue shark mascot, teeth, red kart, dark bg | `lora_shark_s06` |

## Recommendation
- **Deploy:** final `soapbox_style.safetensors` → `ComfyUI/models/loras/style/` (done)
  + sidecar `.txt` (done).
- **Strength:** **0.8** default; **0.6** for lighter / more-detailed; **1.0** for max-bold.
- **Prompt pattern:** `soapbox_style, a <character> mascot driving a soapbox go-kart, dark background`.
- **Confidence:** strong — consistent style + composition transfer across 4 unseen
  subjects, no memorization, no overcooking at 1500. The augment-first pipeline
  (low-denoise img2img from 64px sprites) successfully turned tiny sprites into a
  trainable, distinctive style.

## Licensing
FLUX.1-dev derivative → **distribute the LoRA FREE only**; the **outputs** are
commercially usable. List free on CivitAI; sell only generated assets, not weights.
